import pkg_resources
import requests

from cloudmesh.common.Shell import Shell
from cloudmesh.common.systeminfo import os_is_linux
from cloudmesh.common.systeminfo import os_is_mac
from cloudmesh.common.systeminfo import os_is_windows
from cloudmesh.common.util import readfile
from cloudmesh.common.util import writefile


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


# dig -4 TXT +short o-o.myaddr.l.google.com @ns1.google.com
# "128.143.1.11" = uva

#
# open:
#   /opt/cisco/anyconnect/bin/vpn connect "UVA Anywhere";
# high security:
#   /opt/cisco/anyconnect/bin/vpn connect "UVA High Security VPN";
# more security:
#   /opt/cisco/anyconnect/bin/vpn connect "UVA More Secure Network";
# close:
#   /opt/cisco/anyconnect/bin/vpn disconnect;

class Vpn:

    def __init__(self, service=None, debug=False):
        self.debug = debug
        if service is None or service == "uva":
            self.service = "UVA Anywhere"
            # self.service = "https://uva-anywhere-1.itc.virginia.edu"
        else:
            self.service = service

    def _debug(self, msg):
        if self.debug:
            print(msg)

    @property
    def enabled(self):
        state = False
        if os_is_windows():
            result = Shell.run("route print").strip()
            state = "Cisco AnyConnect" in result
        elif os_is_mac():
            command = f'echo state | /opt/cisco/anyconnect/bin/vpn -s'
            result = Shell.run(command)
            state = "state: Connected" in result
        elif os_is_linux():
            command = f'echo state | /opt/cisco/anyconnect/bin/vpn -s'
            result = Shell.run(command)
            state = "state: Connected" in result
        self._debug(result)
        return state

    @property
    def is_uva(self):
        state = False
        if os_is_windows():
            result = requests.get("ipinfo.io")
            state = "University of Virginia" in result["org"]
        elif os_is_mac():
            command = f'/opt/cisco/anyconnect/bin/vpn'
            result = Shell.run(command)
            state = "virginia.edu" in result
        elif os_is_linux():
            command = f'/opt/cisco/anyconnect/bin/vpn'
            result = Shell.run(command)
            state = "virginia.edu" in result
        self._debug(result)
        return state

    def connect(self):
        if os_is_windows():
            raise NotImplementedError
        elif os_is_mac():

            connect = readfile(pkg_resources.resource_filename(__name__, 'etc/connect-uva.exp'))
            writefile("/tmp/connect-uva.exp", connect)
            result = Shell.run("expect /tmp/connect-uva.exp")
            Shell.rm("/tmp/connect-uva.exp")

            #command = f'yes | /opt/cisco/anyconnect/bin/vpn connect "{self.service}"'
            #result = Shell.run(command)
        elif os_is_linux():

            connect = readfile(pkg_resources.resource_filename(__name__, 'etc/connect-uva.exp'))
            writefile("/tmp/connect-uva.exp", connect)
            result = Shell.run("expect /tmp/connect-uva.exp")
            Shell.rm("/tmp/connect-uva.exp")

            # command = f'yes | /opt/cisco/anyconnect/bin/vpn connect "{self.service}"'
            # result = Shell.run(command)
        self._debug(result)

    def disconnect(self):
        if os_is_windows():
            raise NotImplementedError
        elif os_is_mac():
            command = f'/opt/cisco/anyconnect/bin/vpn disconnect "{self.service}"'
            result = Shell.run(command)
        elif os_is_linux():
            command = f'/opt/cisco/anyconnect/bin/vpn disconnect "{self.service}"'
            result = Shell.run(command)
        self._debug(result)



