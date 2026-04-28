import os
import subprocess
import time
import sys
import psutil
import pexpect
from typing import Any, Dict, Union, Optional

from cloudmesh.common.Shell import Console
from cloudmesh.vpn.strategies.base import VpnOSStrategy
from cloudmesh.vpn.organizations import organizations

class MacOpenConnectPwStrategy(VpnOSStrategy):
    def __init__(self, vpn_context: 'Vpn'):
        super().__init__(vpn_context)
        self._pid = None

    def _discover_openconnect(self) -> Optional[str]:
        return self._discover_binary("openconnect", ["/usr/bin/openconnect", "/usr/local/bin/openconnect", "/opt/homebrew/bin/openconnect"])

    def _discover_anyconnect(self) -> Optional[str]:
        return None

    def _discover_vpn_slice(self) -> Optional[str]:
        path = self._discover_binary("vpn-slice", ["/usr/local/bin/vpn-slice", "/opt/homebrew/bin/vpn-slice"])
        if path and "shims" in path:
            try:
                actual_path = subprocess.check_output(["pyenv", "which", "vpn-slice"], text=True).strip()
                return actual_path
            except Exception:
                return path
        return path

    @property
    def vpn_slice(self) -> Optional[str]:
        return self._discover_vpn_slice()

    def is_enabled(self) -> bool:
        for proc in psutil.process_iter(attrs=["name"]):
            if proc.info["name"] == "openconnect": return True
        return False

    def connect(self, creds: Dict[str, Any], vpn_name: str, no_split: bool) -> Union[bool, str, None]:
        oc_exe = self.openconnect
        if not oc_exe:
            Console.error("OpenConnect binary not found. Please install it via Homebrew: brew install openconnect")
            return False
        
        vs_exe = self.vpn_slice
        if not vs_exe and not no_split:
            Console.error("vpn-slice binary not found. Please install it: brew install vpn-slice")
            return False

        host = organizations[vpn_name]["host"]
        
        from cloudmesh.common.sudo import Sudo
        Sudo.password()

        script_arg = ""
        if not no_split:
            org_config = organizations.get(vpn_name, {})
            ip_range = org_config.get("ip")
            if isinstance(ip_range, list):
                slice_target = " ".join(ip_range)
            else:
                slice_target = ip_range if ip_range else host
            script_arg = f"--script='{vs_exe} -v {slice_target}'"

        command = f"sudo {oc_exe} --protocol=anyconnect {script_arg} {host}"
        Console.info(f"Connecting via OpenConnect (PW): {command}")
        try:
            r = pexpect.spawn(command)
            r.timeout = 60
            while True:
                index = r.expect([pexpect.TIMEOUT, "Username:", "Password:", "Connected", "failed", pexpect.EOF])
                if index == 1: r.sendline(creds.get("user", ""))
                elif index == 2: r.sendline(creds.get("pw", ""))
                elif index == 3: 
                    for proc in psutil.process_iter(['pid', 'name']):
                        if proc.info['name'] == 'openconnect':
                            self._pid = proc.info['pid']
                    return True
                elif index in [4, 5] or index == 0: return False
                else: continue
        except Exception as e:
            Console.error(f"OpenConnect connection failed: {e}")
            return False
        
        return False

    def watch(self) -> List[str]:
        evidence = []
        
        # 1. Check for vpn-slice process and get PIDs
        try:
            pids = [str(proc.pid) for proc in psutil.process_iter(['name']) if 'vpn-slice' in proc.info['name']]
            if pids:
                evidence.append(f"[Process] 'vpn-slice' is running (PIDs: {', '.join(pids)})")
            else:
                evidence.append("[Process] 'vpn-slice' is NOT running")
        except Exception:
            pass

        # 2. Check for openconnect process and get PIDs
        try:
            pids = [str(proc.pid) for proc in psutil.process_iter(['name']) if 'openconnect' in proc.info['name']]
            if pids:
                evidence.append(f"[Process] 'openconnect' is running (PIDs: {', '.join(pids)})")
                # Also check if it's running with vpn-slice script
                out = subprocess.check_output(["ps", "aux"], text=True)
                if "vpn-slice" in out:
                    evidence.append("[OpenConnect] Running with vpn-slice script")
            else:
                evidence.append("[Process] 'openconnect' is NOT running")
        except Exception:
            pass

        # 3. Check for Cisco VPN processes (vpnagentd)
        try:
            cisco_pids = [str(proc.pid) for proc in psutil.process_iter(['name']) if 'vpnagentd' in proc.info['name'] or 'Cisco Secure Client' in proc.info['name']]
            if cisco_pids:
                evidence.append(f"[Process] 'Cisco VPN' is running (PIDs: {', '.join(cisco_pids)})")
            else:
                evidence.append("[Process] 'Cisco VPN' is NOT running")
        except Exception:
            pass

        # 4. Check routing table for organization IP
        # First, try to detect the currently connected organization
        current_org = self.get_current_org()
        org_name = current_org.lower() if current_org else self.vpn.service_key.lower()
        
        ip_range = organizations.get(org_name, {}).get("ip")
        if ip_range:
            targets = ip_range if isinstance(ip_range, list) else [ip_range]
            for target in targets:
                try:
                    route_out = subprocess.check_output(["netstat", "-rn"], text=True)
                    import re
                    search_ip = target.split('/')[0].strip()
                    if re.search(rf"^\s*{re.escape(search_ip)}(\s+|/)", route_out, re.MULTILINE):
                        display_net = target if '/' in target else f"{target}/16"
                        evidence.append(f"[Routing Table] Route to {display_net} found in system routing table (netstat -rn) (Org: {org_name})")
                except Exception:
                    pass

        return evidence

    def disconnect(self) -> None:
        Console.info("Disconnecting OpenConnect...")
        if self._pid:
            try:
                Console.info(f"Sending SIGINT to OpenConnect process {self._pid}")
                os.kill(self._pid, 2) # SIGINT
                time.sleep(2)
                if psutil.pid_exists(self._pid):
                    Console.warning(f"Process {self._pid} still exists, forcing termination")
                    os.kill(self._pid, 15) # SIGTERM
            except ProcessLookupError:
                pass
            except Exception as e:
                Console.error(f"Error during targeted disconnect: {e}")
        else:
            from cloudmesh.common.Shell import Shell
            Shell.run("sudo pkill -SIGINT openconnect")
        
        from cloudmesh.common.Shell import Shell
        Shell.run("sudo pkill vpn-slice")

    def get_reset_commands(self, service: Optional[str] = None) -> List[str]:
        commands = []
        target_orgs = [service.lower()] if service else list(organizations.keys())
        
        for org in target_orgs:
            ip_range = organizations.get(org, {}).get("ip")
            if ip_range:
                targets = ip_range if isinstance(ip_range, list) else [ip_range]
                for target in targets:
                    commands.append(f"sudo route delete -net {target}")
        return commands

    def reset_routes(self, service: Optional[str] = None) -> bool:
        # 1. Kill processes first, otherwise they will just re-add the routes
        self.disconnect()
        
        commands = self.get_reset_commands(service)
        if not commands:
            return True
        
        success = True
        for cmd in commands:
            # Try deleting as a network first, then as a host if it fails
            # Extract the target IP from the command 'sudo route delete -net <target>'
            target = cmd.split()[-1]
            
            # Try -net first
            try:
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if res.returncode != 0 and "not found" not in res.stderr.lower():
                    # Try without -net (as a host route)
                    host_cmd = f"sudo route delete {target}"
                    res_host = subprocess.run(host_cmd, shell=True, capture_output=True, text=True)
                    if res_host.returncode != 0 and "not found" not in res_host.stderr.lower():
                        Console.error(f"Failed to remove route {target}: {res_host.stderr.strip()}")
                        success = False
            except Exception as e:
                Console.error(f"Exception while removing route {target}: {e}")
                success = False
        return success
