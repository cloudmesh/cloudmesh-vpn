import os

import psutil
import requests
import pexpect
import time
import sys
from pexpect.popen_spawn import PopenSpawn
import subprocess

from cloudmesh.common.Shell import Shell
from cloudmesh.common.Shell import Console
from cloudmesh.common.util import path_expand
from cloudmesh.common.systeminfo import os_is_linux
from cloudmesh.common.systeminfo import os_is_mac
from cloudmesh.common.systeminfo import os_is_windows

from cloudmesh.vpn.windows import win_install

import keyring as kr


if os_is_windows():
    import pyuac

# 2fa does not refer to duo but rather second password
organizations = {'ufl': {"auth": "pw",
                         "name": "Gatorlink VPN",
                         "host": "vpn.ufl.edu",
                         "user": True,
                         "2fa": False,
                         "group": False,
                         "domain": "ufl.edu",
                         },
                 'uva': {"auth": "cert",
                         "name": "UVA Anywhere",
                         "host": "uva-anywhere-1.itc.virginia.edu",
                        # UVA Anywhere Primary VPN Concentrator: https://uva-anywhere-1.itc.virginia.edu/
                        # UVA Anywhere Secondary VPN Concentrator: https://uva-anywhere-2.itc.virginia.edu/
                        # More Secure Network Primary VPN Concentrator: https://moresecure-vpn-1.itc.virginia.edu/
                        # More Secure Network Secondary VPN Concentrator: https://moresecure-vpn-2.itc.virginia.edu/
                        # High Security VPN Primary VPN Concentrator: https://joint-vpn-1.itc.virginia.edu/
                        # High Security VPN Secondary VPN Concentrator: https://joint-vpn-2.itc.virginia.edu/
                         "user": False,
                         "2fa": False,
                         "group": False,
                         "ip": "128.143.0.0",
                         "domain": "virginia.edu",
                         },
                 'fiu': {"auth": "pw",
                         "name": "vpn.fiu.edu",
                         "host": "vpn.fiu.edu",
                         "user": True,
                         "2fa": True,
                         "group": False,
                         "ip": "131.94.0.0",
                         "domain": "fiu.edu",
                         },
                 'famu': {"auth": "pw",
                         "name": "vpn.famu.edu",
                         "host": "vpn.famu.edu",
                         "user": True,
                         "2fa": False,
                         "group": False},
                 'nyu': {"auth": "pw",
                         "name": "vpn.nyu.edu",
                         "host": "vpn.nyu.edu",
                         "user": True,
                         "2fa": True,
                         "group": "NYU VPN: NYU-NET Traffic Only"},
                 'uci': {"auth": "pw",
                         "name": "vpn.uci.edu",
                         "host": "vpn.uci.edu",
                         "user": True,
                         "2fa": False,
                         "group": True},
                 'gmu': {"auth": "pw",
                         "name": "vpn.gmu.edu",
                         "host": "vpn.gmu.edu",
                         "user": True,
                         "2fa": False,
                         "group": False},
                 'olemiss': {"auth": "pw",
                         "name": "vpn.olemiss.edu",
                         "host": "vpn.olemiss.edu",
                         "user": True,
                         "2fa": False,
                         "group": False},
                 'sc': {"auth": "pw",
                         "name": "vpn.sc.edu",
                         "host": "vpn.sc.edu",
                         "user": True,
                         "2fa": False,
                         "group": True,
                         "pw_concat": True},
                }

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

"""Provides a VPN (Virtual Private Network) class for managing VPN connections and disconnections.

This module supports different VPN services and their configurations, including 
authentication methods and group memberships.

Attributes:
    organizations (dict): A dictionary containing information about various VPN organizations.

Classes:
    Vpn: A class for managing VPN connections and disconnections.

"""

class Vpn:
    """A class for managing VPN connections and disconnections."""

    def __init__(self,
                 service=None,
                 timeout=None,
                 debug=False):
        """Initializes the Vpn object.

        Args:
            service (str): The VPN service name. Defaults to None.
            timeout (int): The timeout value for various operations. Defaults to None.
            debug (bool): If True, enables debug mode. Defaults to False.
        """
        if timeout is None:
            self.timeout = 60
        else:
            self.timeout = timeout

        self.openconnect = r'openconnect'

        if os_is_windows():
            system_drive = os.environ.get('SYSTEMDRIVE', 'C:')
            self.anyconnect = fr'{system_drive}\Program Files (x86)\Cisco\Cisco Secure Client\vpncli.exe'

        elif os_is_mac():
            
            self.anyconnect = "/opt/cisco/secureclient/bin/vpn"
            
            
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

        self.any = False

    def anyconnect_checker(self,
                           choco=False):
        """Checks if the AnyConnect VPN client is installed, installs it if needed.

        Args:
            choco (bool): If True, installs AnyConnect using Chocolatey. Defaults to False.
        """
        # if not os.path.isfile(self.anyconnect):
        try:
            Shell.run('openconnect -V')
        except RuntimeError:
            if os_is_windows():
                if choco is False:
                    Console.error('OpenConnect not found. Please install, or use --choco parameter.')
                    os._exit(1)
                else:
                    Console.warning('OpenConnect not found. Installing OpenConnect...')
                    win_install()

                    
            if os_is_mac():
                if choco is False:
                    Console.error('OpenConnect not found. Please install, or use --choco parameter.')
                    os._exit(1)
                else:
                    Console.warning('OpenConnect not found. Installing OpenConnect...')
                    win_install()
                    Console.info("If your install was successful, please\nchange the System Preferences to allow Cisco,\n"
                                 "then run your previous command again (up-arrow + enter).")
                    os._exit(1)

    def close_cisco_secure_client(self):
        try:
            # AppleScript command to quit the Cisco Secure Client application
            applescript_command = 'tell application "Cisco Secure Client" to quit'
            # Execute the AppleScript command
            subprocess.run(['osascript', '-e', applescript_command])
            print("Cisco Secure Client application has been closed.")
        except Exception as e:
            print(f"An error occurred: {e}")


    def windows_stop_service(self):
        """Restarts the vpnagent service on Windows to avoid conflicts."""

        Console.warning('Restarting vpnagent to avoid conflict')

        for program in ['vpnagent.exe', 'vpncli.exe']:
            try:
                r = os.system(f'taskkill /im {program} /F')
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

    def is_docker(self):
        path = '/proc/self/cgroup'
        return (
            os.path.exists('/.dockerenv') or
            os.path.isfile(path) and any('docker' in line for line in open(path))
        )

    def _debug(self, msg):
        """Prints debug messages if debug mode is enabled.

        Args:
            msg (str): The debug message to print.
        """
        if self.debug:
            print(msg)

    def is_user_auth(self, org):
        """Checks if the specified organization requires user authentication.

        Args:
            org (str): The organization name.

        Returns:
            bool: True if user authentication is required, False otherwise.
        """
        return organizations[org.lower()]['user']

    def enabled(self=None):
        state = False
        result = ""
        if os_is_windows():
            # r = str(subprocess.run(f"{self.anyconnect} state",
            #                         capture_output=True,
            #                         text=True))
            
            # state = 'state: Connected' in r
            # # result = Shell.run("route print").strip()
            # # state = "Cisco AnyConnect" in result
            # if state is True:
            #     self.any = True
            # if state is False:
            self.any = False
            process_name = "openconnect.exe"  # Adjust as needed
            for process in psutil.process_iter(attrs=['name']):
                if process.info['name'] == process_name:
                    state = True

        elif os_is_mac():
            for proc in psutil.process_iter(attrs=['pid', 'name']):
                # Check if the process name is 'openconnect'
                if proc.info['name'] == 'openconnect':
                    state = True
                    break
            
        elif os_is_linux():
            result = requests.get("https://ipinfo.io")
            state = "University of Virginia" in result.json()["org"]
            if (state is False) and (self.is_docker()):
                if 'openconnect' in Shell.run('ps -u'):
                    state = True

        if self:
            Vpn._debug(self, result)
        return state

    @property
    def is_uva(self):
        """Checks if the VPN connection is to the University of Virginia (UVA).

        Returns:
            bool: True if connected to UVA, False otherwise.
        """
        state = False
        if os_is_windows():
            result = requests.get("https://ipinfo.io")
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

    def connect(self, *args):
        """Connects to the VPN using the specified credentials.

        Args:
            args (tuple): Tuple containing dictionary with user credentials.

        Returns:
            bool: True if connection is successful, False otherwise.
        """

        # args[0] is dict with
        # keys named user, pw, and service.

        # temporarily commented to allow for dual
        
        # if self.enabled():
            # Console.ok("VPN is already activated")
            # return ""

        if args:
            creds = args[0]
            no_split = args[0]['nosplit']
            vpn_name = creds['service']
        else:
            creds = False
            no_split = True
            vpn_name = 'uva'

        if os_is_windows():
            if not pyuac.isUserAdmin():
                Console.error("Please run your terminal as administrator")
                sys.exit(1)

            # mycommand = rf'{self.anyconnect} {organizations[vpn_name]["host"]} --os=win --protocol=anyconnect --user={creds["user"]} --passwd-on-stdin'

            if 'user' in creds and 'pw' in creds:
                base = f'{creds["user"]}\n{creds["pw"]}'            
                inner_command = base

                if organizations[vpn_name]["group"]:

                    ### nyu
                    if no_split:
                        organizations["nyu"]["group"] = "NYU VPN: All Traffic"
                    ###

                    # inner_command = rf'\n{creds["user"]}\n{creds["pw"]}\npush\ny'
                    inner_command = organizations[vpn_name]["group"] + '\n' + inner_command
                if organizations[vpn_name]["2fa"]:
                    inner_command += '\npush\n'
                if organizations[vpn_name].get("pw_concat", False):
                    inner_command = f'\n{creds["pw"]},push\ny'

            else:
                inner_command = ""


            
            # full_command = rf'printf "{inner_command}" | "{self.anyconnect}" -s connect "{organizations[vpn_name]["host"]}"'
            script_location = os.path.join(os.path.dirname(__file__),  'bin', 'split-script-win.js')
            # script_location = os.path.abspath(os.path.expanduser('~/cm/cloudmesh-vpn/src/cloudmesh/vpn/bin/split-script-win.js')).replace(os.sep, '/')
            print('this is script location', script_location)

            
            if no_split:
                full_command = f'printf \"{inner_command}\" | "{self.openconnect}" "{organizations[vpn_name]["host"]}"'
            else:
                full_command = f'printf \"{inner_command}\" | "{self.openconnect}" --script="{script_location}" "{organizations[vpn_name]["host"]}"'
            # print(full_command)
            service_started = False
            while not service_started:
                
                env_vars = os.environ.copy()
                domain = organizations.get(vpn_name, {}).get('domain')
                iprange = organizations.get(vpn_name, {}).get('ip')

                if domain:
                    env_vars.update({
                        'VPN_DOMAIN': domain,
                    })

 
                if iprange:

                    env_vars.update({
                        'CISCO_SPLIT_INC': '2', # the first two route 10.* and 172.16* thru 172.31*
                        'CISCO_SPLIT_INC_1_ADDR': iprange,
                        'CISCO_SPLIT_INC_1_MASK': '255.255.0.0',
                        'CISCO_SPLIT_INC_1_MASKLEN': '16',
                    })


                if organizations[vpn_name]["user"] is True:
                    Console.warning('It will ask you for your password,\n'
                                'but it is already entered. Just confirm DUO.\n')
                    self.windows_stop_service()
                    # print(':)', fr'"C:\Program Files\Git\bin\bash.exe" -c "{full_command}"')
                    
                    # r = subprocess.run(fr'"C:\Program Files\Git\bin\bash.exe" -c "{full_command} &"')

                    command = [
                        'openconnect',
                        organizations[vpn_name]["host"],
                        f'--user={creds["user"]}',
                        '--passwd-on-stdin'
                    ]

                    if not no_split:
                        command.append(f'--script={script_location}')

                    process = subprocess.Popen(
                        command,
                        stdin=subprocess.PIPE,
                        start_new_session=True,
                        env=env_vars
                    )

                    # Send the password to the openconnect command
                    
                    process.stdin.write(creds['pw'].encode('utf-8') + b'\n')
                    if organizations[vpn_name]["2fa"]:
                        process.stdin.write('push'.encode('utf-8') + b'\n')
                        # process.stdin.flush()
                    process.stdin.flush()
                
                    service_started = True
                    return True
                
                                
                elif organizations[vpn_name]["auth"] == "cert":
                    try:
                        r = Shell.run("list-system-keys")
                    except RuntimeError:
                        Console.error("You do not have the special chocolatey openconnect package, "
                                    "why don't you run choco uninstall openconnect -y, then "
                                    "choco install openconnect -y\nThen try the command again.")
                        return False

                    rightful_index = 0
                    almighty_cert = False
                    # iterate through r for a line that has University of Virginia in it
                    for index, line in enumerate(r.splitlines()):
                        if 'University of Virginia' in line:
                            # i dont like magic numbers
                            rightful_index = index - 2

                            almighty_cert = r.splitlines()[rightful_index].split('Cert URI: ')[-1].replace(';', r'\;')
                    
                    if almighty_cert:
                        # Define the environment variables
                        # iprange = organizations.get(vpn_name, {}).get('ip')
 
                        full_command = rf'{self.openconnect} --certificate={almighty_cert} ' \
                                    rf'{organizations[vpn_name]["host"]}'
                        if not no_split:
                            full_command += rf' --script="{script_location.replace(os.sep, "/").replace("C:", "/c")}"'
                            # if iprange:

                            #     env_vars.update({
                            #         'CISCO_SPLIT_INC': '3', # the first two route 10.* and 172.16* thru 172.31*
                            #         'CISCO_SPLIT_INC_2_ADDR': iprange,
                            #         'CISCO_SPLIT_INC_2_MASK': '255.255.0.0',
                            #         'CISCO_SPLIT_INC_2_MASKLEN': '16',
                            #     })


                        # full_command = rf'{self.openconnect} --certificate={almighty_cert} ' \
                                    # rf'{organizations[vpn_name]["host"]}'
                        self.windows_stop_service()
                        # print(':)', fr'"C:\Program Files\Git\bin\bash.exe" -c "{full_command}"')
                        r = subprocess.run(
                            fr'"C:\Program Files\Git\bin\bash.exe" -c "{full_command} &"', 
                            env=env_vars
                        )
                    
                        service_started = True
                        return True
            
                    else:
                        Console.error("Something went wrong with the list-system-keys parsing\nmaybe you need to install certificate?")
                        return False


                r = pexpect.popen_spawn.PopenSpawn(mycommand, logfile=sys.stdout.buffer)
                r.timeout = 25

                result = r.expect([pexpect.TIMEOUT,
                                r"^.*accept.*$",
                                r"^.*Another Cisco Secure Client.*$",
                                r"^.*VPN service is unavailable.*$",
                                r"^.*No valid certificate.*$",
                                r"^.*sername.*$",
                                r"^.*'yes' to accept,.*$",
                                pexpect.EOF])
                
                if result in [0, 2, 3]:
                    self.windows_stop_service()

                # PW AUTHENTICATION
                if result == 5:
                    # import ctypes
                    if len(r.after.strip()) > len("Username:"):
                        # this means that default user exists
                        r.sendline()  # Send a line break to clear any additional input
                    else:       
                        r.sendline(creds['user'])  # Send the actual username
                    
                    result2 = r.expect([pexpect.TIMEOUT, "^.*ssword.*$", pexpect.EOF])
                    if result2 == 1:
                        r.sendline(creds['pw'])
                    Console.msg("Check DUO")
                    
                    r.timeout = 60
                    result2 = r.expect([pexpect.TIMEOUT, "^.*Got CONNECT response: HTTP/1.1 200 OK.*$", "failed"])
                    if result2 == 1:
                        # r.detach()
                        service_started = True
                        Console.msg("You are connected but nonblocking has not yet been implemented")
                        r.wait()
                        return True
                    if result2 == 2:
                        import keyring as kr
                        Console.error('Incorrect password.\n'
                                      'Deleting password...')
                        kr.delete_password(vpn_name, "cloudmesh-pw")
                        kr.delete_password(vpn_name, "cloudmesh-user")
                        os._exit(1)
                    
                    
                if result == 1:
                    service_started = True
                    r.sendline('y')
                    result2 = r.expect([pexpect.TIMEOUT, "^.*Connected.*$", "^.*Downloading Cisco.*$", pexpect.EOF])
                    if result2 == 1:
                        Console.ok('Successfully connected')
                        
                        return True
                    elif result2 == 2:
                        Console.error("Cisco has decided to begin updating!\nPlease finish the update process.")
                        return
                        

                elif result == 4:
                    import ctypes  # An included library with Python install.
                    # 0x1000 keeps it topmost
                    ctypes.windll.user32.MessageBoxW(0, "Your UVA certificate has expired!\nRedirecting you to the appropriate UVA webpage...",
                                                    "Oops", 0x1000)
                    Shell.browser('https://in.virginia.edu/installcert')
                    return False
                if result == 6:
                    r.sendline('yes')
                    result2 = r.expect([pexpect.TIMEOUT, "^.*ssword.*$", pexpect.EOF])
                    if result2 == 1:
                        r.sendline(creds['pw'])
                        
        elif os_is_mac():

            # redone
            # redone
            # redone

            # if not os.path.isdir(path_expand('~/.ssh/uva')) or not os.path.isfile(path_expand('~/.ssh/uva/mst3k.key')):
            #     print("Please follow the instructions at https://github.com/cloudmesh/cloudmesh-vpn#linux-and-macos")
            #     quit(1)

            # from cloudmesh.common.sudo import Sudo
            # Sudo.password()

            # full_uva = path_expand('~/.ssh/uva')
            # if not full_uva[-1] == '/':
            #     full_uva += '/'
            
            # command = [
            #     'sudo', 'openconnect', '-b', '-v', '--protocol=anyconnect',
            #     f'--cafile={full_uva}usher.cer',
            #     f'--sslkey={full_uva}mst3k.key',
            #     f'--certificate={full_uva}mst3k.crt',
            #     'uva-anywhere-1.itc.virginia.edu',
            #     '-s', 'vpn-slice rivanna.hpc.virginia.edu'
            # ]

            # process = subprocess.Popen(command)

            # return
        
            # redone
            # redone
            # redone
        

            inner_command = ""

            if not organizations[vpn_name]["user"]:
                mycommand = rf'{self.anyconnect} connect "{organizations[vpn_name]["host"]}"'
                
            else:
                # full_command = rf'{self.openconnect} {organizations[vpn_name]["host"]} --os=win --protocol=anyconnect --user={creds["user"]}'
                inner_command = rf'{creds["user"]}\n{creds["pw"]}\ny'
            if organizations[vpn_name]["2fa"]:
                inner_command = rf'{creds["user"]}\n{creds["pw"]}\npush\ny'
            if organizations[vpn_name].get("pw_concat", False):
                inner_command = rf'{creds["user"]}\n{creds["pw"]}\n{creds["pw"]},push\ny'
            if organizations[vpn_name]["group"]:
                # inner_command = rf'\n{creds["user"]}\n{creds["pw"]}\npush\ny'
                inner_command = rf'\n' + inner_command
            
            full_command = rf'printf "{inner_command}" | "{self.anyconnect}" -s connect "{organizations[vpn_name]["host"]}"'
            # print(mycommand)
            service_started = False
            while not service_started:
                if organizations[vpn_name]["user"] is True:
                    Console.warning('It will ask you for your password,\n'
                                'but it is already entered. Just confirm DUO.\n')
                    # self.windows_stop_service()
                    os.system(full_command)
                
                    service_started = True
                    return True

                r = pexpect.spawn(mycommand, logfile=sys.stdout.buffer)
                r.timeout = 25

                result = r.expect([pexpect.TIMEOUT,
                                r"^.*accept.*$",
                                r"^.*Another Cisco Secure Client.*$",
                                r"^.*VPN service is unavailable.*$",
                                r"^.*No valid certificate.*$",
                                r"^.*sername.*$",
                                r"^.*'yes' to accept,.*$",
                                pexpect.EOF])
                
                if result in [0, 2, 3]:
                    self.close_cisco_secure_client()
                    # Console.error("Not implemented to stop service on mac")
                    # return False

                # PW AUTHENTICATION
                if result == 5:
                    # import ctypes
                    if len(r.after.strip()) > len("Username:"):
                        # this means that default user exists
                        r.sendline()  # Send a line break to clear any additional input
                    else:       
                        r.sendline(creds['user'])  # Send the actual username
                    
                    result2 = r.expect([pexpect.TIMEOUT, "^.*ssword.*$", pexpect.EOF])
                    if result2 == 1:
                        r.sendline(creds['pw'])
                    Console.msg("Check DUO")
                    
                    r.timeout = 60
                    result2 = r.expect([pexpect.TIMEOUT, "^.*Got CONNECT response: HTTP/1.1 200 OK.*$", "failed"])
                    if result2 == 1:
                        # r.detach()
                        service_started = True
                        Console.msg("You are connected but nonblocking has not yet been implemented")
                        r.wait()
                        return True
                    if result2 == 2:
                        import keyring as kr
                        Console.error('Incorrect password.\n'
                                      'Deleting password...')
                        kr.delete_password(vpn_name, "cloudmesh-pw")
                        kr.delete_password(vpn_name, "cloudmesh-user")
                        os._exit(1)
                    
                    
                if result == 1:
                    service_started = True
                    r.sendline('y')
                    result2 = r.expect([pexpect.TIMEOUT, "^.*Connected.*$", "^.*Downloading Cisco.*$", pexpect.EOF])
                    if result2 == 1:
                        Console.ok('Successfully connected')
                        
                        return True
                    elif result2 == 2:
                        Console.error("Cisco has decided to begin updating!\nPlease finish the update process.")
                        return
                        

                elif result == 4:
                    applescript = """
                    display dialog "Your UVA certificate has expired!\nRedirecting you to the appropriate UVA webpage..." ¬
                    with title "Oops" ¬
                    with icon caution ¬
                    buttons {"OK"}
                    """

                    subprocess.call("osascript -e '{}'".format(applescript),
                                    shell=True)
                    Shell.browser('https://in.virginia.edu/installcert')
                    return False
                if result == 6:
                    r.sendline('yes')
                    result2 = r.expect([pexpect.TIMEOUT, "^.*ssword.*$", pexpect.EOF])
                    if result2 == 1:
                        r.sendline(creds['pw'])

            # mycommand = rf'{self.anyconnect} connect "UVA Anywhere"'
            # service_started = False
            # while not service_started:
            #     r = pexpect.spawn(mycommand)
            #     r.timeout = self.timeout
            #     sys.stdout.reconfigure(encoding='utf-8')
            #     r.logfile = sys.stdout.buffer
            #     result = r.expect([pexpect.TIMEOUT,
            #                        r"^.*accept.*$",
            #                        r"^.*Another AnyConnect application.*$",
            #                        r"^.*The VPN Service is not available.*$",
            #                        r"^.*No valid certificate.*$",
            #                        pexpect.EOF])
            #     if result in [0, 2, 3]:
            #         Console.error('Please kill the AnyConnect windows.')
            #         return False

            #     if result == 1:
            #         service_started = True
            #         r.sendline('y')
            #         result2 = r.expect(
            #             [pexpect.TIMEOUT, "^.*Connected.*$", pexpect.EOF])
            #         if result2 == 1:
            #             Console.ok('Successfully connected')
            #             return True

            #     elif result == 4:
            #         applescript = """
            #         display dialog "Your UVA certificate has expired!\nRedirecting you to the appropriate UVA webpage..." ¬
            #         with title "Oops" ¬
            #         with icon caution ¬
            #         buttons {"OK"}
            #         """

            #         subprocess.call("osascript -e '{}'".format(applescript),
            #                         shell=True)
            #         Shell.browser('https://in.virginia.edu/installcert')
            #         return False

        elif os_is_linux():

            home = os.environ["HOME"]

            if not self.is_docker():
                print('here you are')
                from cloudmesh.common.sudo import Sudo

                
                Sudo.password()
                command = 'sudo openconnect -b -v ' \
                      '--protocol=anyconnect ' \
                      f'--cafile="{home}/.ssh/uva/usher.cer" ' \
                      f'--sslkey="{home}/.ssh/uva/user.key" ' \
                      f'--certificate="{home}/.ssh/uva/user.crt" ' \
                      'uva-anywhere-1.itc.virginia.edu  2>&1 > /dev/null'
                print(command)
                print('that was th ecommand')
            else:
                # if docker
                command = 'openconnect -b -v ' \
                      '--protocol=anyconnect ' \
                      f'--cafile="/root/.ssh/uva/usher.cer" ' \
                      f'--sslkey="/root/.ssh/uva/user.key" ' \
                      f'--certificate="/root/.ssh/uva/user.crt" ' \
                      f'-m 1290 ' \
                       'uva-anywhere-1.itc.virginia.edu ' \
                       '--script=\'vpn-slice --prevent-idle-timeout rivanna.hpc.virginia.edu ' \
                       'biihead1.bii.virginia.edu biihead2.bii.virginia.edu\''
              
            self._debug(command)
    
            try:
                os.system(command)
            except Exception as e:
                print("KKKK")
                print(e)
            while not self.enabled():
                time.sleep(1)
        # self._debug(result)

    def remove_nrpt_rules_combined(self):
        # Collect all domains in a list, prefixed with a dot (e.g. ".ufl.edu")
        domains = [f".{org['domain']}" for org in organizations.values() if 'domain' in org]
        
        # Build a single condition string like:
        # ( $_.Namespace -eq '.ufl.edu' ) -or ( $_.Namespace -eq '.virginia.edu' )
        conditions = " -or ".join(f"( $_.Namespace -eq '{d}' )" for d in domains)
        
        # Final PowerShell command
        # Example:
        #   Get-DnsClientNrptRule |
        #       Where-Object { ($_.Namespace -eq '.ufl.edu') -or ($_.Namespace -eq '.virginia.edu') } |
        #       Remove-DnsClientNrptRule -Force
        ps_command = (
            "powershell.exe -Command "
            f"\"Get-DnsClientNrptRule | "
            f"Where-Object {{ {conditions} }} | "
            f"Remove-DnsClientNrptRule -Force\""
        )
        
        print("Removing NRPT rules for domains:", domains)
        os.system(ps_command)

    def disconnect(self):
        """Disconnects from the VPN."""
        if not self.enabled():
            if os_is_windows():
                self.remove_nrpt_rules_combined()
            Console.ok("VPN is already deactivated")
            return ""

        if os_is_windows():
            
            if self.any is True:
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
                return

            self.remove_nrpt_rules_combined()
            # Define the process name to search for
            process_name = "openconnect.exe"  # Adjust as needed

            # Iterate through all running processes and terminate those with the specified name
            for process in psutil.process_iter(attrs=['pid', 'name']):
                if process.info['name'] == process_name:
                    print(f"Terminating process {process.info['pid']}")
                    try:
                        psutil.Process(process.info['pid']).terminate()
                    except psutil.NoSuchProcess:
                        pass

        elif os_is_mac():
            # command = f'{self.anyconnect} disconnect "{self.service}"'
            # result = Shell.run(command)
            from cloudmesh.common.sudo import Sudo
            Sudo.password()
            command = f'sudo pkill -SIGINT openconnect &> /dev/null'
            result = Shell.run(command)

        elif os_is_linux():
            if not self.is_docker():
                from cloudmesh.common.sudo import Sudo
                Sudo.password()

                command = f'sudo pkill -SIGINT openconnect &> /dev/null'
            else:
                command = f'pkill -SIGINT openconnect &> /dev/null'
                result = Shell.run(command)
                command = f'pkill -SIGINT vpn-slice &> /dev/null'

            result = Shell.run(command)
        # self._debug(result)

    def info(self):
        """Retrieves information about the current network.

        Returns:
           str: Information about the current network.
        """
        r = Shell.run('curl -s ipinfo.io')
        return r

    def pw_fetcher(self,
                   org):
        """Fetches the username and password for the specified organization.

        Args:
            org (str): The organization name.

        Returns:
            tuple: Tuple containing username and password.
        """

        if org not in organizations:
            Console.error(f'Unknown service {org}')
            return False
        else:
            Console.ok("recognized")
            if organizations[org]['auth'] == 'pw':
                
                import keyring as kr
                import getpass

                stored_pw = kr.get_password(org, "cloudmesh-pw")
                if stored_pw is None:
                    Console.msg("There is no password stored.")
                    username = input(f"Enter your {org} username: ")

                    while True:
                        password = getpass.getpass(f"Enter your {org} password: ")
                        confirm_password = getpass.getpass("Confirm your password: ")

                        if password == confirm_password:
                            break
                        else:
                            print("Passwords do not match. Please try again.")
                    # we need to use cloudmesh as the username,
                    # it is just an arbitrary alias.
                    # and this is ok since we are allowed to enter
                    # multiple organizations to the keyring
                    kr.set_password(org,"cloudmesh-pw", password)
                    kr.set_password(org,"cloudmesh-user", username)
                
                return kr.get_password(org, "cloudmesh-user"), kr.get_password(org, "cloudmesh-pw")
                    
                # print(kr.get_password(org, "cloudmesh"))

    def pw_clearer(self,
                    org):
        """Clears the stored credentials for the specified organization.

        Args:
            org (str): The organization name.
        """
        if org not in organizations:
            Console.error(f'Unknown service {org}')
            return False
        kr.delete_password(org, "cloudmesh-pw")
        kr.delete_password(org, "cloudmesh-user")
        Console.ok(f'Credentials for {org} have been cleared.')
                

