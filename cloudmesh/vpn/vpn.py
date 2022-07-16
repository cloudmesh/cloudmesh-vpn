from cloudmesh.common.Shell import Shell
from cloudmesh.common.systeminfo import os_is_windows
from cloudmesh.common.systeminfo import os_is_mac
from cloudmesh.common.systeminfo import os_is_linux
from cloudmesh.common.console import Console
import os


# mac: /opt/cisco/anyconnect/bin

# windows
# $ 'C:\Program Files (x86)\Cisco\Cisco AnyConnect Secure Mobility Client\vpncli.exe'
# Cisco AnyConnect Secure Mobility Client (version 4.10.05095) .
#
# Copyright (c) 2004 - 2022 Cisco Systems, Inc.  All Rights Reserved.
#
#
#   >> state: Connected
#   >> state: Connected
#   >> registered with local VPN subsystem.
#   >> state: Connected
#   >> notice: Connected to uva-anywhere-1.itc.virginia.edu.

class Vpn:

    def __init__(self, service=None):
        if service is None or service == "uva":
            self.service = "https://uva-anywhere-1.itc.virginia.edu"
        elif service == "iu":
            self.service = "https://vpn.iu.edu"
        else:
            self.service = service

    @property
    def enabled(self):
        state = False
        if os_is_windows():
            result = Shell.run("route print").strip()
            state = "Cisco AnyConnect" in result
        elif os_is_mac():
            raise NotImplementedError
        elif os_is_linux():
            result = Shell.ps()
            state = "/usr/sbin/openconnect --servercert pin-sha256:" in result
        return state

    @property
    def is_uva(self):
        state = False
        if os_is_windows():
            raise NotImplementedError
        elif os_is_mac():
            raise NotImplementedError
        elif os_is_linux():
            result = Shell.run("route").strip()
            state = "uva-anywhere" in result
        return state

    def connect(self):
        if os_is_windows():
            raise NotImplementedError
        elif os_is_mac():
            # DOES NNOT WORK
            os.system("sudo openconnect -b"
                      " --cafile /etc/ssl/certs/ca-certificates.crt"
                      f" --protocol=pulse {self.service}")
        elif os_is_linux():
            # DOES NNOT WORK
            os.system("sudo openconnect -b"
                      " --cafile /etc/ssl/certs/ca-certificates.crt"
                      f" --protocol=pulse {self.service}")

    def disconnect(self):
        if os_is_windows():
            raise NotImplementedError
        elif os_is_mac():
            # DOES NNOT WORK
            Console.ok("Disconnecting ...")
            os.system("sudo killall -SIGINT openconnect")
        elif os_is_linux():
            # DOES NNOT WORK
            Console.ok("Disconnecting ...")
            os.system("sudo killall -SIGINT openconnect")

