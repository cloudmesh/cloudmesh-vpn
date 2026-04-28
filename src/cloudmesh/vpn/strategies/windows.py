import os
import sys
import subprocess
import psutil
from typing import Any, Dict, List, Union, Optional

from cloudmesh.common.Shell import Console
from cloudmesh.common.systeminfo import os_is_windows
from cloudmesh.vpn.strategies.base import VpnOSStrategy
from cloudmesh.vpn.organizations import organizations
from cloudmesh.vpn.windows import win_install, ensure_choco_bin_on_process_path, get_openconnect_exe

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
            from cloudmesh.common.Shell import Shell
            Shell.run("net stop csc_vpnagent")
        except Exception:
            pass
        try:
            from cloudmesh.common.Shell import Shell
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
        import pyuac
        if not pyuac.isUserAdmin():
            Console.error("Please run your terminal as administrator")
            sys.exit(1)

        ensure_choco_bin_on_process_path()
        
        oc_exe = self.openconnect or get_openconnect_exe() or win_install()
        self._openconnect = oc_exe

        if not oc_exe or not os.path.exists(oc_exe):
            Console.error(f"VPN binary not found. Please install OpenConnect.")
            return False

        script_location = os.path.join(os.path.dirname(__file__), "..", "bin", "split-script-win.js")
        
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
                from cloudmesh.common.Shell import Shell
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
                command = [self.openconnect, f"--certificate={almighty_cert}", organizations[vpn_name]["host"]]
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

    def watch(self) -> List[str]:
        return ["Watch not implemented for Windows"]

    def disconnect(self) -> None:
        if self.anyconnect:
            from pexpect.popen_spawn import PopenSpawn
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
                    try:
                        p.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        Console.warning(f"Process {pid} did not terminate, killing it.")
                        p.kill()
                except psutil.NoSuchProcess:
                    pass
