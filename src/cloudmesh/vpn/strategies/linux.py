import os
import time
from typing import Any, Dict, Union, Optional

from cloudmesh.common.Shell import Shell, Console
from cloudmesh.vpn.strategies.base import VpnOSStrategy
from cloudmesh.vpn.organizations import organizations

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

    def watch(self) -> List[str]:
        return ["Watch not implemented for Linux"]

    def disconnect(self) -> None:
        if not (os.path.exists("/.dockerenv") or (os.path.isfile("/proc/self/cgroup") and "docker" in open("/proc/self/cgroup").read())):
            from cloudmesh.common.sudo import Sudo
            Sudo.password()
            Shell.run("sudo pkill -SIGINT openconnect &> /dev/null")
        else:
            Shell.run("pkill -SIGINT openconnect &> /dev/null")
            Shell.run("pkill -SIGINT vpn-slice &> /dev/null")