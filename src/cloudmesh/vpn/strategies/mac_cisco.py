import sys
import subprocess
import psutil
import pexpect
from typing import Any, Dict, Union, Optional

from cloudmesh.common.Shell import Shell, Console
from cloudmesh.vpn.strategies.base import VpnOSStrategy
from cloudmesh.vpn.organizations import organizations

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

    def _manage_routes(self, action: str) -> None:
        """Add or remove specific routes for the connected organization."""
        org_name = self.vpn.service_key.lower()
        config = organizations.get(org_name, {})
        ip_range = config.get("ip")
        if not ip_range:
            return

        # Convert 128.143.0.0 to 128.143.0.0/16 (assuming /16 for UVA)
        network = f"{ip_range}/16"
        
        if action == "add":
            Console.info(f"Adding split route for {org_name}: {network}")
            Shell.run(f"sudo route add -net {network} 0")
        elif action == "remove":
            Console.info(f"Removing split route for {org_name}: {network}")
            Shell.run(f"sudo route delete -net {network}")

    def watch(self) -> List[str]:
        """Check for evidence that the VPN is active and using split-routing."""
        evidence = []
        
        # 1. Check Processes
        processes_to_check = {
            "vpn-slice": ["vpn-slice"],
            "openconnect": ["openconnect"],
            "Cisco VPN": ["vpn", "vpnagentd", "ciscoses"]
        }
        
        found_pids = {}
        try:
            for proc in psutil.process_iter(attrs=["pid", "name"]):
                name = proc.info["name"].lower()
                pid = proc.info["pid"]
                for label, keywords in processes_to_check.items():
                    if any(kw in name for kw in keywords):
                        found_pids.setdefault(label, []).append(str(pid))
        except Exception:
            pass

        for label in ["vpn-slice", "openconnect", "Cisco VPN"]:
            if label in found_pids:
                pids_str = f" (PIDs: {', '.join(found_pids[label])})" if label == "Cisco VPN" else ""
                evidence.append(f"[Process] '{label}' is running{pids_str}")
            else:
                evidence.append(f"[Process] '{label}' is NOT running")

        # 2. Check Routing Table
        try:
            # Get the organization config for the current service
            org_name = self.vpn.service_key.lower()
            config = organizations.get(org_name, {})
            ip_ranges = config.get("ip")
            
            if ip_ranges:
                # Ensure ip_ranges is a list
                if isinstance(ip_ranges, str):
                    ip_ranges = [ip_ranges]
                
                route_out = subprocess.check_output(["netstat", "-rn"], text=True)
                
                import re
                for ip in ip_ranges:
                    ip = ip.strip()
                    # Skip hostnames, only check IP-like strings
                    if "." not in ip or any(c.isalpha() for c in ip):
                        continue
                    
                    # Clean the IP (remove /16 if present for the search)
                    search_ip = ip.split('/')[0].strip()
                    
                    # Use regex to ensure the IP is at the start of a line (Destination column)
                    # We allow for optional trailing characters like /32 or /16 in the table
                    if re.search(rf"^\s*{re.escape(search_ip)}(\s+|/)", route_out, re.MULTILINE):
                        # Format the display network (ensure it has /16)
                        display_net = ip if '/' in ip else f"{ip}/16"
                        evidence.append(f"[Routing Table] Route to {display_net} is active (Org: {org_name})")
        except Exception:
            pass

        return evidence

    def disconnect(self) -> None:
        self._manage_routes("remove")
        if self.anyconnect:
            Shell.run(f'{self.anyconnect} disconnect "{self.vpn.service}"')
        Shell.run("pkill -SIGINT openconnect &> /dev/null || true")