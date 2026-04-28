import os
import shutil
import subprocess
import time
import sys
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

import psutil
import requests
import pexpect
from pexpect.popen_spawn import PopenSpawn

from cloudmesh.common.Shell import Shell
from cloudmesh.common.Shell import Console
from rich.console import Console as RichConsole
from rich.table import Table
from rich.box import ROUNDED
from cloudmesh.common.util import path_expand
from cloudmesh.common.systeminfo import os_is_linux, os_is_mac, os_is_windows

from cloudmesh.vpn.windows import win_install
import yaml
import keyring as kr

if os_is_windows():
    import pyuac

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

class VpnOSStrategy(ABC):
    """Abstract Base Class for OS-specific VPN strategies."""

    def __init__(self, vpn_context: 'Vpn'):
        self.vpn = vpn_context
        self._openconnect = None
        self._anyconnect = None

    @property
    def openconnect(self) -> Optional[str]:
        if self._openconnect is None:
            self._openconnect = self._discover_openconnect()
        return self._openconnect

    @property
    def anyconnect(self) -> Optional[str]:
        if self._anyconnect is None:
            self._anyconnect = self._discover_anyconnect()
        return self._anyconnect

    @abstractmethod
    def _discover_openconnect(self) -> Optional[str]:
        pass

    @abstractmethod
    def _discover_anyconnect(self) -> Optional[str]:
        pass

    @abstractmethod
    def connect(self, creds: Dict[str, Any], vpn_name: str, no_split: bool) -> Union[bool, str, None]:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        pass

    def _verify_certs(self, cert_paths: List[str]) -> bool:
        for path in cert_paths:
            expanded_path = path_expand(path)
            if not os.path.exists(expanded_path):
                Console.error(f"Certificate file not found: {expanded_path}")
                return False
        return True

    def _check_ip_info(self) -> bool:
        """Check if the current public IP belongs to the configured organization."""
        try:
            # Reduced timeout to 2s to prevent CLI lag
            res = requests.get("https://ipinfo.io", timeout=2)
            res.raise_for_status()
            org_info = res.json().get("org", "")
            checks = organizations.get(self.vpn.service_key.lower(), {}).get("connection_check", [])
            return any(check in org_info for check in checks)
        except (requests.RequestException, ValueError):
            return False

    def get_current_org(self) -> Optional[str]:
        """Identify which configured organization is currently connected."""
        try:
            res = requests.get("https://ipinfo.io", timeout=2)
            res.raise_for_status()
            org_info = res.json().get("org", "")
            for org_name, config in organizations.items():
                checks = config.get("connection_check", [])
                if any(check in org_info for check in checks):
                    return org_name
        except (requests.RequestException, ValueError):
            pass
        return None

    def _discover_binary(self, binary_name: str, common_paths: List[str]) -> Optional[str]:
        path = shutil.which(binary_name)
        if path:
            return path
        for p in common_paths:
            if os.path.exists(p) and os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        return None

class WindowsVpnStrategy(VpnOSStrategy):
    def _discover_openconnect(self) -> Optional[str]:
        return self._discover_binary("openconnect", [
            "/usr/bin/openconnect",
            "/usr/local/bin/openconnect",
            "/opt/homebrew/bin/openconnect",
        ])

    def _discover_anyconnect(self) -> Optional[str]:
        system_drive = os.environ.get("SYSTEMDRIVE", "C:")
        return self._discover_binary("vpncli.exe", [
            rf"{system_drive}\Program Files (x86)\Cisco\Cisco Secure Client\vpncli.exe",
            rf"{system_drive}\Program Files (x86)\Cisco\Cisco AnyConnect Secure Mobility Client\vpncli.exe",
        ])

    def _stop_vpn_services(self) -> None:
        Console.warning("Restarting vpnagent to avoid conflict")
        for program in ["vpnagent.exe", "vpncli.exe"]:
            subprocess.run(
                ["taskkill", "/im", program, "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        try:
            Shell.run("net stop csc_vpnagent")
        except Exception:
            pass
        try:
            Shell.run("net start csc_vpnagent")
        except Exception:
            pass
        subprocess.run(
            ["taskkill", "/im", "csc_ui.exe", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def _remove_nrpt_rules(self) -> None:
        domains = [f".{org['domain']}" for org in organizations.values() if "domain" in org]
        conditions = " -or ".join(f"( $_.Namespace -eq '{d}' )" for d in domains)
        ps_command = (
            "powershell.exe -Command "
            f'"Get-DnsClientNrptRule | '
            f"Where-Object {{ {conditions} }} | "
            f'Remove-DnsClientNrptRule -Force"'
        )
        Console.info(f"Removing NRPT rules for domains: {domains}")
        os.system(ps_command)

    def is_enabled(self) -> bool:
        process_name = "openconnect.exe"
        for process in psutil.process_iter(attrs=["name"]):
            if process.info["name"] == process_name:
                return True
        return False

    def connect(self, creds: Dict[str, Any], vpn_name: str, no_split: bool) -> Union[bool, str, None]:
        if not pyuac.isUserAdmin():
            Console.error("Please run your terminal as administrator")
            sys.exit(1)

        from cloudmesh.vpn.windows import ensure_choco_bin_on_process_path, get_openconnect_exe
        ensure_choco_bin_on_process_path()
        
        oc_exe = self.openconnect or get_openconnect_exe() or win_install()
        self._openconnect = oc_exe

        if not oc_exe or not os.path.exists(oc_exe):
            Console.error(f"VPN binary not found. Please install OpenConnect.")
            return False

        script_location = os.path.join(os.path.dirname(__file__), "bin", "split-script-win.js")
        
        env_vars = os.environ.copy()
        domain = organizations.get(vpn_name, {}).get("domain")
        iprange = organizations.get(vpn_name, {}).get("ip")
        if domain: env_vars["VPN_DOMAIN"] = domain
        if iprange:
            env_vars.update({
                "CISCO_SPLIT_INC": "2",
                "CISCO_SPLIT_INC_1_ADDR": iprange,
                "CISCO_SPLIT_INC_1_MASK": "255.255.0.0",
                "CISCO_SPLIT_INC_1_MASKLEN": "16",
            })

        if organizations[vpn_name]["user"]:
            Console.warning("It will ask you for your password, but it is already entered. Just confirm DUO.")
            self._stop_vpn_services()
            
            command = [oc_exe, organizations[vpn_name]["host"], f'--user={creds["user"]}', "--passwd-on-stdin"]
            if not no_split:
                command.append(f"--script={script_location}")

            process = subprocess.Popen(command, stdin=subprocess.PIPE, start_new_session=True, env=env_vars)
            process.stdin.write(creds["pw"].encode("utf-8") + b"\n")
            if organizations[vpn_name]["2fa"]:
                process.stdin.write("push".encode("utf-8") + b"\n")
            process.stdin.flush()
            return True

        elif organizations[vpn_name]["auth"] == "cert":
            try:
                r = Shell.run("list-system-keys")
            except RuntimeError:
                Console.error("Certificate keys not found. Please install certificate.")
                return False

            almighty_cert = None
            for index, line in enumerate(r.splitlines()):
                if "University of Virginia" in line:
                    almighty_cert = r.splitlines()[index - 2].split("Cert URI: ")[-1]
                    break

            if almighty_cert:
                command = [oc_exe, f"--certificate={almighty_cert}", organizations[vpn_name]["host"]]
                if not no_split:
                    command.append(f"--script={script_location}")
                self._stop_vpn_services()
                try:
                    subprocess.Popen(command, start_new_session=True, env=env_vars)
                    return True
                except OSError as e:
                    Console.error(f"Failed to start OpenConnect: {e}")
                    return False
            
            Console.error("Failed to parse system keys.")
            return False
        
        return False

    def disconnect(self) -> None:
        if self.anyconnect:
            mycommand = rf'{self.anyconnect} disconnect "{self.vpn.service}"'
            try:
                r = PopenSpawn(mycommand)
                r.expect([pexpect.TIMEOUT, r"^.*Disconnected.*$", pexpect.EOF])
                Console.ok("Successfully disconnected")
            except Exception:
                pass
        
        self._remove_nrpt_rules()
        for process in psutil.process_iter(attrs=["pid", "name"]):
            if process.info["name"] == "openconnect.exe":
                try:
                    pid = process.info["pid"]
                    Console.info(f"Terminating process {pid}")
                    p = psutil.Process(pid)
                    p.terminate()
                    # Wait up to 3 seconds for process to terminate
                    try:
                        p.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        Console.warning(f"Process {pid} did not terminate, killing it.")
                        p.kill()
                except psutil.NoSuchProcess:
                    pass

class MacCiscoStrategy(VpnOSStrategy):
    def _discover_openconnect(self) -> Optional[str]:
        return self._discover_binary("openconnect", ["/usr/bin/openconnect", "/usr/local/bin/openconnect", "/opt/homebrew/bin/openconnect"])

    def _discover_anyconnect(self) -> Optional[str]:
        return self._discover_binary("vpn", ["/opt/cisco/secureclient/bin/vpn", "/opt/cisco/anyconnect/bin/vpn"])

    def is_enabled(self) -> bool:
        # Prioritize fast local checks over slow network requests
        # 1. Check for openconnect process (fastest)
        for proc in psutil.process_iter(attrs=["name"]):
            if proc.info["name"] == "openconnect": return True
        
        # 2. Check anyconnect state (fast)
        if self.anyconnect:
            try:
                result = Shell.run(f"{self.anyconnect} state")
                if "state: connected" in result.lower(): return True
            except Exception:
                pass
        
        # 3. Check public IP (slowest)
        if self._check_ip_info():
            return True
            
        return False

    def connect(self, creds: Dict[str, Any], vpn_name: str, no_split: bool) -> Union[bool, str, None]:
        if not organizations[vpn_name]["user"]:
            mycommand = rf'{self.anyconnect} connect "{organizations[vpn_name]["host"]}"'
        else:
            inner_command = rf'{creds["user"]}\n{creds["pw"]}\ny'
            if organizations[vpn_name]["2fa"]:
                inner_command = rf'{creds["user"]}\n{creds["pw"]}\npush\ny'
            if organizations[vpn_name].get("pw_concat", False):
                inner_command = rf'{creds["user"]}\n{creds["pw"]}\n{creds["pw"]},push\ny'
            if organizations[vpn_name]["group"]:
                inner_command = rf"\n" + inner_command
            
            # Use subprocess.Popen to avoid passing credentials in the command string
            command = [self.anyconnect, "-s", "connect", organizations[vpn_name]["host"]]
            process = subprocess.Popen(command, stdin=subprocess.PIPE, text=True)
            process.stdin.write(inner_command + "\n")
            process.stdin.close()
            process.wait()
            return True

        # For non-user auth (cert), we still need to handle the command
        r = pexpect.spawn(mycommand, logfile=sys.stdout.buffer)
        r.timeout = 25
        result = r.expect([pexpect.TIMEOUT, r"^.*accept.*$", r"^.*Another Cisco Secure Client.*$", 
                           r"^.*VPN service is unavailable.*$", r"^.*No valid certificate.*$", 
                           r"^.*sername.*$", r"^.*'yes' to accept.*$", pexpect.EOF])
        
        if result == 5: # PW AUTH
            if len(r.after.strip()) > len("Username:"): r.sendline()
            else: r.sendline(creds["user"])
            if r.expect([pexpect.TIMEOUT, "^.*ssword.*$", pexpect.EOF]) == 1:
                r.sendline(creds["pw"])
            r.timeout = 60
            if r.expect([pexpect.TIMEOUT, "^.*Got CONNECT response: HTTP/1.1 200 OK.*$", "failed"]) == 1:
                r.wait()
                return True
        elif result == 1:
            r.sendline("y")
            if r.expect([pexpect.TIMEOUT, "^.*Connected.*$", "^.*Downloading Cisco.*$", pexpect.EOF]) == 1:
                return True
        
        # If we reached here and connected, apply split routes if requested
        if not no_split:
            self._manage_routes("add")
            
        return False

        r = pexpect.spawn(mycommand, logfile=sys.stdout.buffer)
        r.timeout = 25
        result = r.expect([pexpect.TIMEOUT, r"^.*accept.*$", r"^.*Another Cisco Secure Client.*$", 
                           r"^.*VPN service is unavailable.*$", r"^.*No valid certificate.*$", 
                           r"^.*sername.*$", r"^.*'yes' to accept.*$", pexpect.EOF])
        
        if result == 5: # PW AUTH
            if len(r.after.strip()) > len("Username:"): r.sendline()
            else: r.sendline(creds["user"])
            if r.expect([pexpect.TIMEOUT, "^.*ssword.*$", pexpect.EOF]) == 1:
                r.sendline(creds["pw"])
            r.timeout = 60
            if r.expect([pexpect.TIMEOUT, "^.*Got CONNECT response: HTTP/1.1 200 OK.*$", "failed"]) == 1:
                r.wait()
                return True
        elif result == 1:
            r.sendline("y")
            if r.expect([pexpect.TIMEOUT, "^.*Connected.*$", "^.*Downloading Cisco.*$", pexpect.EOF]) == 1:
                return True
        return False

    def _manage_routes(self, action: str) -> None:
        """Add or remove specific routes for the connected organization."""
        org_name = self.vpn.service_key.lower()
        config = organizations.get(org_name, {})
        ip_range = config.get("ip")
        if not ip_range:
            return

        # Convert 128.143.0.0 to 128.143.0.0/16 (assuming /16 for UVA)
        # In a real scenario, we might want the mask in organizations.yaml
        network = f"{ip_range}/16"
        
        if action == "add":
            Console.info(f"Adding split route for {org_name}: {network}")
            # We use sudo to modify routing table
            Shell.run(f"sudo route add -net {network} 0") # 0 often works as it uses the default VPN interface
        elif action == "remove":
            Console.info(f"Removing split route for {org_name}: {network}")
            Shell.run(f"sudo route delete -net {network}")

    def disconnect(self) -> None:
        self._manage_routes("remove")
        if self.anyconnect:
            Shell.run(f'{self.anyconnect} disconnect "{self.vpn.service}"')
        Shell.run("pkill -SIGINT openconnect &> /dev/null || true")

class MacOpenConnectStrategy(VpnOSStrategy):
    def _discover_openconnect(self) -> Optional[str]:
        return self._discover_binary("openconnect", ["/usr/bin/openconnect", "/usr/local/bin/openconnect", "/opt/homebrew/bin/openconnect"])

    def _discover_anyconnect(self) -> Optional[str]:
        return None

    def is_enabled(self) -> bool:
        for proc in psutil.process_iter(attrs=["name"]):
            if proc.info["name"] == "openconnect": return True
        return False

    def connect(self, creds: Dict[str, Any], vpn_name: str, no_split: bool) -> Union[bool, str, None]:
        oc_exe = self.openconnect
        if not oc_exe:
            Console.error("OpenConnect binary not found. Please install it via Homebrew: brew install openconnect")
            return False
        
        vpn_slice = self._discover_binary("vpn-slice", ["/usr/local/bin/vpn-slice", "/opt/homebrew/bin/vpn-slice"])
        if not vpn_slice:
            Console.error("vpn-slice binary not found. Please install it: brew install vpn-slice")
            return False

        host = organizations[vpn_name]["host"]
        
        # Build the command
        # We use sudo because openconnect needs to create a tun device
        if not no_split:
            # Use vpn-slice for split tunneling
            # We pass the host as a target for vpn-slice to ensure it's routed
            script_cmd = f"{vpn_slice} {host}"
            command = f"sudo {oc_exe} -b --protocol=anyconnect --script='{script_cmd}' {host}"
        else:
            command = f"sudo {oc_exe} -b --protocol=anyconnect {host}"

        Console.info(f"Connecting via OpenConnect: {command}")
        
        # OpenConnect -b runs in background. We need to handle credentials.
        # For simplicity in this implementation, we assume the user will be prompted 
        # or we can use the same pexpect logic as Cisco if needed.
        # However, -b is non-interactive. For interactive auth, we remove -b.
        
        # Let's use the interactive approach for consistency with Cisco
        command = command.replace(" -b", "")
        
        try:
            r = pexpect.spawn(command, logfile=sys.stdout.buffer)
            r.timeout = 60
            
            # Handle auth
            if r.expect([pexpect.TIMEOUT, "Username:", "Password:", pexpect.EOF]) == 1:
                r.sendline(creds.get("user", ""))
            if r.expect([pexpect.TIMEOUT, "Password:", pexpect.EOF]) == 0:
                r.sendline(creds.get("pw", ""))
            
            # Wait for connected
            if r.expect([pexpect.TIMEOUT, "Connected", "failed", pexpect.EOF]) == 1:
                return True
        except Exception as e:
            Console.error(f"OpenConnect connection failed: {e}")
            
        return False

    def disconnect(self) -> None:
        Console.info("Disconnecting OpenConnect...")
        Shell.run("sudo pkill -SIGINT openconnect")
        Shell.run("sudo pkill vpn-slice")

class LinuxVpnStrategy(VpnOSStrategy):
    def _discover_openconnect(self) -> Optional[str]:
        return self._discover_binary("openconnect", ["/usr/bin/openconnect", "/usr/local/bin/openconnect"])

    def _discover_anyconnect(self) -> Optional[str]:
        return self._discover_binary("vpn", ["/opt/cisco/anyconnect/bin/vpn"])

    def is_enabled(self) -> bool:
        # Prioritize local process check over network request
        if os.path.exists("/.dockerenv") or (os.path.isfile("/proc/self/cgroup") and "docker" in open("/proc/self/cgroup").read()):
            if "openconnect" in Shell.run("ps -u"): return True
        
        if self._check_ip_info():
            return True
            
        return False

    def connect(self, creds: Dict[str, Any], vpn_name: str, no_split: bool) -> Union[bool, str, None]:
        home = os.environ.get("HOME", "")
        cert_paths = [
            f"{home}/.ssh/uva/usher.cer" if not (os.path.exists("/.dockerenv") or (os.path.isfile("/proc/self/cgroup") and "docker" in open("/proc/self/cgroup").read())) else "/root/.ssh/uva/usher.cer",
            f"{home}/.ssh/uva/user.key" if not (os.path.exists("/.dockerenv") or (os.path.isfile("/proc/self/cgroup") and "docker" in open("/proc/self/cgroup").read())) else "/root/.ssh/uva/user.key",
            f"{home}/.ssh/uva/user.crt" if not (os.path.exists("/.dockerenv") or (os.path.isfile("/proc/self/cgroup") and "docker" in open("/proc/self/cgroup").read())) else "/root/.ssh/uva/user.crt",
        ]
        if not self._verify_certs(cert_paths):
            return False

        if not (os.path.exists("/.dockerenv") or (os.path.isfile("/proc/self/cgroup") and "docker" in open("/proc/self/cgroup").read())):
            from cloudmesh.common.sudo import Sudo
            Sudo.password()
            command = (
                "sudo openconnect -b -v --protocol=anyconnect "
                f'--cafile="{cert_paths[0]}" '
                f'--sslkey="{cert_paths[1]}" '
                f'--certificate="{cert_paths[2]}" '
                "uva-anywhere-1.itc.virginia.edu 2>&1 > /dev/null"
            )
        else:
            command = (
                "openconnect -b -v --protocol=anyconnect "
                f'--cafile="{cert_paths[0]}" '
                f'--sslkey="{cert_paths[1]}" '
                f'--certificate="{cert_paths[2]}" -m 1290 '
                "uva-anywhere-1.itc.virginia.edu "
                "--script='vpn-slice --prevent-idle-timeout rivanna.hpc.virginia.edu biihead1.bii.virginia.edu biihead2.bii.virginia.edu'"
            )
        Console.info(f"Executing command: {command}")
        os.system(command)
        while not self.is_enabled():
            time.sleep(1)
        return True

    def disconnect(self) -> None:
        if not (os.path.exists("/.dockerenv") or (os.path.isfile("/proc/self/cgroup") and "docker" in open("/proc/self/cgroup").read())):
            from cloudmesh.common.sudo import Sudo
            Sudo.password()
            Shell.run("sudo pkill -SIGINT openconnect &> /dev/null")
        else:
            Shell.run("pkill -SIGINT openconnect &> /dev/null")
            Shell.run("pkill -SIGINT vpn-slice &> /dev/null")

class Vpn:
    """Context class for managing VPN connections using OS-specific strategies."""

    def __init__(self, service: Optional[str] = None, timeout: Optional[int] = None, debug: bool = False, provider: Optional[str] = None) -> None:
        self.timeout = timeout or 60
        self.debug = debug
        
        # Strategy Selection
        if os_is_windows():
            self.strategy = WindowsVpnStrategy(self)
        elif os_is_mac():
            provider = provider.lower() if provider else "cisco"
            if provider == "openconnect":
                self.strategy = MacOpenConnectStrategy(self)
            else:
                self.strategy = MacCiscoStrategy(self)
        elif os_is_linux():
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

    def anyconnect_checker(self, choco: bool = False) -> None:
        """Checks if the VPN client is installed, installs it if needed.

        Args:
            choco (bool): If True, installs using Chocolatey (Windows). Defaults to False.
        """
        try:
            Shell.run("openconnect -V")
        except RuntimeError:
            if os_is_windows():
                if not choco:
                    Console.error("OpenConnect not found. Please install, or use --choco parameter.")
                    os._exit(1)
                else:
                    Console.warning("OpenConnect not found. Installing OpenConnect...")
                    win_install()

            elif os_is_mac():
                if not choco:
                    Console.error("OpenConnect not found. Please install, or use --choco parameter.")
                    os._exit(1)
                else:
                    Console.warning("OpenConnect not found. Installing OpenConnect...")
                    win_install()
                    Console.info(
                        "If your install was successful, please\nchange the System Preferences to allow Cisco,\n"
                        "then run your previous command again (up-arrow + enter)."
                    )
                    os._exit(1)

    def info(self) -> str:
        """Display current IP information in a rich table."""
        try:
            res = requests.get("https://ipinfo.io", timeout=5)
            res.raise_for_status()
            data = res.json()
            
            table = Table(title="IP Information", box=ROUNDED, show_header=True, header_style="bold magenta")
            table.add_column("Field", style="cyan", width=15)
            table.add_column("Value", style="cyan")

            for key, value in data.items():
                table.add_row(key, str(value))
            
            RichConsole().print(table)
            return json.dumps(data, indent=2)
        except Exception as e:
            Console.error(f"Failed to fetch IP info: {e}")
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
