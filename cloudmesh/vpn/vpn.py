import os

import requests
import pexpect
import time
import sys
from pexpect.popen_spawn import PopenSpawn

from cloudmesh.common.Shell import Shell
from cloudmesh.common.Shell import Console
from cloudmesh.common.systeminfo import os_is_linux
from cloudmesh.common.systeminfo import os_is_mac
from cloudmesh.common.systeminfo import os_is_windows

if os_is_windows():
    import pyuac

# mac /opt/cisco/secureclient/bin/vpn
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

    def __init__(self,
                 service=None,
                 timeout=None,
                 debug=False):

        if timeout is None:
            self.timeout = 60
        else:
            self.timeout = timeout

        if os_is_windows():
            self.anyconnect = r'C:\Program Files (x86)\Cisco\Cisco Secure Client\vpncli.exe'
        elif os_is_mac():
            self.anyconnect = None
            for command in ["/opt/cisco/anyconnect/bin/vpn",
                            "/opt/cisco/secureclient/bin/vpn"]:
                if os.path.isfile(command):
                    self.anyconnect = command
                    break;
            if self.anyconnect is None:
                raise NotImplementedError("vpn cCLI not found")
        elif os_is_linux():
            self.anyconnect = "/opt/cisco/anyconnect/bin/vpn"
        else:
            raise NotImplementedError("OS is not yet supported for anyconnect")

        self.debug = debug
        if service is None or service == "uva":
            self.service = "UVA Anywhere"
            # self.service = "https://uva-anywhere-1.itc.virginia.edu"
        else:
            self.service = service

    def _debug(self, msg):
        if self.debug:
            print(msg)

    def enabled(self=None):
        state = False
        result = ""
        if os_is_windows():
            result = Shell.run("route print").strip()
            state = "Cisco AnyConnect" in result
        elif os_is_mac():
            command = f'echo state | {self.anyconnect} -s'
            result = Shell.run(command)
            state = "state: Connected" in result
        elif os_is_linux():
            result = requests.get("https://ipinfo.io")
            state = "University of Virginia" in result.json()["org"]
        if self:
            Vpn._debug(self, result)
        return state

    @property
    def is_uva(self):
        state = False
        if os_is_windows():
            result = requests.get("ipinfo.io")
            state = "University of Virginia" in result.json()["org"]
        elif os_is_mac():
            command = self.anyconnect
            result = Shell.run(command)
            state = "virginia.edu" in result
        elif os_is_linux():
            result = requests.get("ipinfo.io")
            state = "University of Virginia" in result.json()["org"]
        else:
            result = requests.get("ipinfo.io")
            state = "University of Virginia" in result.json()["org"]

        self._debug(result)
        return state

    def connect(self):
        if self.enabled():
            Console.warning("VPN is already activated")
            return ""

        if os_is_windows():
            if not pyuac.isUserAdmin():
                pyuac.runAsAdmin()

            mycommand = rf'{self.anyconnect} connect "UVA Anywhere"'
            service_started = False
            while not service_started:
                r = pexpect.popen_spawn.PopenSpawn(mycommand)
                r.timeout = 3
                sys.stdout.reconfigure(encoding='utf-8')
                r.logfile = sys.stdout.buffer
                result = r.expect([pexpect.TIMEOUT,
                                   r"^.*accept.*$",
                                   r"^.*Another Cisco Secure Client.*$",
                                   r"^.*VPN service is unavailable.*$",
                                   pexpect.EOF])
                if result in [0, 2, 3]:
                    Console.warning('Restarting vpnagent to avoid conflict')

                    try:
                        r = os.system('taskkill /im vpnagent.exe /F')
                    except:
                        pass

                    try:
                        r = Shell.run('net stop csc_vpnagent')
                    except:
                        pass

                    try:
                        r = Shell.run('net start csc_vpnagent')
                    except:
                        pass

                    try:
                        r = os.system('taskkill /im csc_ui.exe /F')
                    except:
                        pass

                if result == 1:
                    service_started = True
                    r.sendline('y')
                    result2 = r.expect([pexpect.TIMEOUT, "^.*Connected.*$", pexpect.EOF])
                    if result2 == 1:
                        Console.ok('Successfully connected')
                        return True

        elif os_is_mac():

            mycommand = rf'{self.anyconnect} connect "UVA Anywhere"'
            service_started = False
            while not service_started:
                r = pexpect.spawn(mycommand)
                r.timeout = self.timeout
                sys.stdout.reconfigure(encoding='utf-8')
                r.logfile = sys.stdout.buffer
                result = r.expect([pexpect.TIMEOUT,
                                   r"^.*accept.*$",
                                   r"^.*Another AnyConnect application.*$",
                                   r"^.*The VPN Service is not available.*$",
                                   pexpect.EOF])
                if result in [0, 2, 3]:
                    Console.error('Please kill the AnyConnect windows.')
                    return False

                if result == 1:
                    service_started = True
                    r.sendline('y')
                    result2 = r.expect(
                        [pexpect.TIMEOUT, "^.*Connected.*$", pexpect.EOF])
                    if result2 == 1:
                        Console.ok('Successfully connected')
                        return True

        elif os_is_linux():
            from cloudmesh.common.sudo import Sudo

            Sudo.password()
            home = os.environ["HOME"]
            command = 'sudo openconnect -b -v ' \
                      '--protocol=anyconnect ' \
                      f'--cafile="{home}/.ssh/uva/usher.cer" ' \
                      f'--sslkey="{home}/.ssh/uva/user.key" ' \
                      f'--certificate="{home}/.ssh/uva/user.crt" ' \
                      'uva-anywhere-1.itc.virginia.edu  2>&1 > /dev/null'

            self._debug(command)

            try:
                os.system(command)
            except Exception as e:
                print("KKKK")
                print(e)
            while not self.enabled():
                time.sleep(1)
        # self._debug(result)

    def disconnect(self):
        if not self.enabled():
            Console.warning("VPN is already deactivated")
            return ""

        if os_is_windows():
            mycommand = fr'{self.anyconnect} disconnect "{self.service}"'
            # mycommand = mycommand.replace("\\", "/")
            r = pexpect.popen_spawn.PopenSpawn(mycommand)
            sys.stdout.reconfigure(encoding='utf-8')
            r.logfile = sys.stdout.buffer
            # time.sleep(5)
            # r.sendline('y')

            result = r.expect([pexpect.TIMEOUT, r"^.*Disconnected.*$", pexpect.EOF])
            if result == 1:
                Console.ok('Successfully disconnected')
        elif os_is_mac():
            command = f'{self.anyconnect} disconnect "{self.service}"'
            result = Shell.run(command)
        elif os_is_linux():
            from cloudmesh.common.sudo import Sudo
            Sudo.password()

            command = f'sudo pkill -SIGINT openconnect &> /dev/null'
            result = Shell.run(command)
        # self._debug(result)

    def info(self):
        r = Shell.run('curl -s ipinfo.io')
        return r
