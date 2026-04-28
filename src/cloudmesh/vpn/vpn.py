import os
import subprocess
import time
import sys
import json
from typing import Any, Dict, Optional, Union, List
import yaml

import requests
import keyring as kr

from cloudmesh.common.Shell import Console
from rich.console import Console as RichConsole
from rich.table import Table
from rich.box import ROUNDED
from cloudmesh.common.systeminfo import os_is_linux, os_is_mac, os_is_windows

from cloudmesh.vpn.organizations import organizations as org_config


def get_organizations() -> Dict[str, Any]:
    """Load and validate VPN Organization Configurations from YAML."""
    if not hasattr(get_organizations, "_cache"):
        org_file = os.path.join(os.path.dirname(__file__), "organizations.yaml")
        with open(org_file, "r") as f:
            data = yaml.safe_load(f)
            orgs = data.get("cloudmesh", {}).get("vpn", {})

        # Validate organization configurations
        required_keys = ["host", "connection_check"]
        for org, config in orgs.items():
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                raise ValueError(
                    f"Malformed configuration for organization '{org}': "
                    f"Missing required keys: {', '.join(missing_keys)}"
                )
        get_organizations._cache = orgs
    return get_organizations._cache

# For backward compatibility with existing code that uses 'organizations' globally
organizations = get_organizations()


class Vpn:
    """Context class for managing VPN connections using OS-specific strategies."""

    def __init__(self, service: Optional[str] = None, timeout: Optional[int] = None, debug: bool = False, provider: Optional[str] = None) -> None:
        self.timeout = timeout or 60
        self.debug = debug
        
        # Strategy Selection
        if os_is_windows():
            from cloudmesh.vpn.strategies.windows import WindowsVpnStrategy
            self.strategy = WindowsVpnStrategy(self)
        elif os_is_mac():
            provider = provider.lower() if provider else "openconnect-decrypted"
            if provider == "openconnect-decrypted":
                from cloudmesh.vpn.strategies.mac_openconnect_decrypted import MacOpenConnectDecryptedStrategy
                self.strategy = MacOpenConnectDecryptedStrategy(self)
            elif provider == "openconnect-keychain":
                from cloudmesh.vpn.strategies.mac_openconnect_keychain import MacOpenConnectKeychainStrategy
                self.strategy = MacOpenConnectKeychainStrategy(self)
            elif provider.startswith("openconnect"):
                from cloudmesh.vpn.strategies.mac_openconnect_pw import MacOpenConnectPwStrategy
                self.strategy = MacOpenConnectPwStrategy(self)
            else:
                from cloudmesh.vpn.strategies.mac_cisco import MacCiscoStrategy
                self.strategy = MacCiscoStrategy(self)
            
            # Explicitly log the selected strategy to avoid confusion with imports
            Console.info(f"Selected VPN Strategy: {self.strategy.__class__.__name__}")
        elif os_is_linux():
            from cloudmesh.vpn.strategies.linux import LinuxVpnStrategy
            self.strategy = LinuxVpnStrategy(self)
        else:
            raise NotImplementedError("OS is not supported")

        # Service Configuration
        if service is None or service == "uva":
            self.service_key = "uva"
            self.service = "UVA Anywhere"
        else:
            service_lower = service.lower()
            if service_lower not in organizations:
                available = ", ".join(organizations.keys())
                raise ValueError(f"Invalid VPN service '{service}'. Available: {available}")
            self.service_key = service_lower
            self.service = service

    def _debug(self, msg: str) -> None:
        if self.debug:
            print(msg)

    def is_user_auth(self, org: str) -> bool:
        return organizations[org.lower()]["user"]

    def enabled(self) -> bool:
        return self.strategy.is_enabled()

    def connect(self, *args: Any) -> Union[bool, str, None]:
        if args:
            creds = args[0]
            no_split = creds.get("nosplit", True)
            vpn_name = creds.get("service", "uva")
        else:
            creds = {}
            no_split = True
            vpn_name = "uva"

        # Capture state before action
        before_org = self.strategy.get_current_org()
        
        result = self.strategy.connect(creds, vpn_name, no_split)
        
        if result:
            # Capture state after action
            after_org = self.strategy.get_current_org()
            if before_org and after_org and before_org != after_org:
                Console.ok(f"Switched from {before_org} to {after_org}")
            elif after_org:
                Console.ok(f"Connected to {after_org}")
            else:
                Console.warning("Connection command succeeded, but could not verify organization via IP.")
        
        return result

    def disconnect(self) -> None:
        # Capture state before action
        before_org = self.strategy.get_current_org()
        
        if not self.enabled():
            Console.ok("VPN is already deactivated")
            return
        
        self.strategy.disconnect()
        
        if self.enabled():
            Console.error("VPN is still enabled. Disconnection may have failed.")
        else:
            if before_org:
                Console.ok(f"Disconnected from {before_org}")
            else:
                Console.ok("Successfully disconnected from VPN.")

    def get_reset_commands(self, service: Optional[str] = None) -> List[str]:
        return self.strategy.get_reset_commands(service)

    def reset_routes(self, service: Optional[str] = None) -> bool:
        return self.strategy.reset_routes(service)

    def anyconnect_checker(self, choco: bool = False) -> None:
        """Checks if the VPN client is installed, installs it if needed."""
        try:
            subprocess.run(["openconnect", "-V"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (subprocess.CalledProcessError, FileNotFoundError):
            if os_is_windows():
                if not choco:
                    Console.error("OpenConnect not found. Please install, or use --choco parameter.")
                    os._exit(1)
                else:
                    Console.warning("OpenConnect not found. Installing OpenConnect...")
                    from cloudmesh.vpn.windows import win_install
                    win_install()
            elif os_is_mac():
                if not choco:
                    Console.error("OpenConnect not found. Please install, or use --choco parameter.")
                    os._exit(1)
                else:
                    Console.warning("OpenConnect not found. Installing OpenConnect...")
                    from cloudmesh.vpn.windows import win_install
                    win_install()
                    Console.info(
                        "If your install was successful, please\nchange the System Preferences to allow Cisco,\n"
                        "then run your previous command again (up-arrow + enter)."
                    )
                    os._exit(1)

    def info(self) -> str:
        """Display current IP information in a rich table using multiple fallback providers."""
        providers = [
            {"url": "https://ipinfo.io/json", "type": "json"},
            {"url": "https://ifconfig.me/all.json", "type": "json"},
            {"url": "https://api.ipify.org?format=json", "type": "json"},
            {"url": "https://icanhazip.com", "type": "text"},
        ]

        data = {}
        for provider in providers:
            try:
                res = requests.get(provider["url"], timeout=5)
                if res.status_code == 429:
                    Console.warning(f"Provider {provider['url']} rate limited (429). Trying next...")
                    continue
                res.raise_for_status()
                
                if provider["type"] == "json":
                    data = res.json()
                else:
                    data = {"ip": res.text.strip()}
                
                # If we got a valid IP, we can stop
                if data.get("ip") or data.get("query"):
                    break
            except Exception as e:
                Console.error(f"Provider {provider['url']} failed: {type(e).__name__}: {e}")
                continue

        if not data:
            Console.error("All IP information providers failed to return a valid IP address.")
            return ""

        try:
            table = Table(title="IP Information", box=ROUNDED, show_header=True, header_style="bold magenta")
            table.add_column("Field", style="cyan", width=15)
            table.add_column("Value", style="cyan")

            for key, value in data.items():
                table.add_row(key, str(value))
            
            RichConsole().print(table)
            return json.dumps(data, indent=2)
        except Exception as e:
            Console.error(f"Failed to render IP info table: {e}")
            return ""

    def pw_fetcher(self, org: str):
        if org not in organizations:
            Console.error(f"Unknown service {org}")
            return False
        
        if organizations[org]["auth"] == "pw":
            stored_pw = kr.get_password(org, "cloudmesh-pw")
            if stored_pw is None:
                import getpass
                username = input(f"Enter your {org} username: ")
                while True:
                    password = getpass.getpass(f"Enter your {org} password: ")
                    confirm_password = getpass.getpass("Confirm your password: ")
                    if password == confirm_password: break
                    Console.error("Passwords do not match. Please try again.")
                kr.set_password(org, "cloudmesh-pw", password)
                kr.set_password(org, "cloudmesh-user", username)
            return kr.get_password(org, "cloudmesh-user"), kr.get_password(org, "cloudmesh-pw")
        return False

    def pw_clearer(self, org: str):
        if org not in organizations:
            Console.error(f"Unknown service {org}")
            return False
        kr.delete_password(org, "cloudmesh-pw")
        kr.delete_password(org, "cloudmesh-user")
        Console.ok(f"Credentials for {org} have been cleared.")

    def watch(self) -> List[str]:
        """Check for evidence that the VPN is active and using split-routing."""
        return self.strategy.watch()