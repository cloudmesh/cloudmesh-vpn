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
from cloudmesh.common.systeminfo import os_is_linux
from cloudmesh.common.systeminfo import os_is_mac
from cloudmesh.common.systeminfo import os_is_windows

from cloudmesh.vpn.windows import win_install

if os_is_windows():
    import pyuac

# 2fa does not refer to duo but rather second password
organizations = {'ufl': {"auth": "pw",
                         "name": "Gatorlink VPN",
                         "host": "vpn.ufl.edu",
                         "user": True,
                         "2fa": False,
                         "group": False},
                 'uva': {"auth": "cert",
                         "name": "UVA Anywhere",
                         "host": "uva-anywhere-1.itc.virginia.edu",
                         "user": False,
                         "2fa": False,
                         "group": False},
                 'fiu': {"auth": "pw",
                         "name": "vpn.fiu.edu",
                         "host": "vpn.fiu.edu",
                         "user": True,
                         "2fa": True,
                         "group": False},
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
                         "group": True},
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
            system_drive = os.environ.get('SYSTEMDRIVE', 'C:')
            self.anyconnect = fr'{system_drive}\Program Files (x86)\Cisco\Cisco Secure Client\vpncli.exe'
                
            self.openconnect = r'openconnect'

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
        if not os.path.isfile(self.anyconnect):
            if os_is_windows():
                if choco is False:
                    Console.error('Anyconnect not found. Please install, or use --choco parameter.')
                    os._exit(1)
                else:
                    Console.warning('Anyconnect not found. Installing anyconnect...')
                    win_install()

                    
            if os_is_mac:
                if choco is False:
                    Console.error('Anyonnect not found. Please install, or use --choco parameter.')
                    os._exit(1)
                else:
                    Console.warning('Anyconnect not found. Installing anyconnect...')
                    win_install()
                    Console.info("If your install was successful, please\nchange the System Preferences to allow Cisco,\n"
                                 "then run your previous command again (up-arrow + enter).")
                    os._exit(1)

    def windows_stop_service(self):
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
        if self.debug:
            print(msg)

    def is_user_auth(self, org):
        return organizations[org.lower()]['user']

    def enabled(self=None):
        state = False
        result = ""
        if os_is_windows():
            r = str(subprocess.run(f"{self.anyconnect} state",
                                    capture_output=True,
                                    text=True))
            
            state = 'state: Connected' in r
            # result = Shell.run("route print").strip()
            # state = "Cisco AnyConnect" in result
            if state is True:
                self.any = True
            if state is False:
                process_name = "openconnect.exe"  # Adjust as needed
                for process in psutil.process_iter(attrs=['name']):
                    if process.info['name'] == process_name:
                        state = True

        elif os_is_mac():
            command = f'echo state | {self.anyconnect} -s'
            result = Shell.run(command)
            state = "state: Connected" in result
            
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
        # args[0] is dict with
        # keys named user, pw, and service.
        
        if self.enabled():
            Console.ok("VPN is already activated")
            return ""

        if args:
            creds = args[0]
            vpn_name = creds['service']
        else:
            vpn_name = 'uva'
            

        if os_is_windows():
            if not pyuac.isUserAdmin():
                pyuac.runAsAdmin()

            # mycommand = rf'{self.anyconnect} {organizations[vpn_name]["host"]} --os=win --protocol=anyconnect --user={creds["user"]} --passwd-on-stdin'
            
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
                    self.windows_stop_service()
                    os.system(full_command)
                
                
                    service_started = True
                    return True
                # import pystray
                # from PIL import Image
                # # Load your custom image for the icon
                # script_directory = os.path.dirname(os.path.abspath(__file__))

                # # Construct the full path to the image file
                # image_filename = "favicon.png"
                # image_path = os.path.join(script_directory, image_filename)

                # # Define a function to activate when the icon is clicked
                # def on_clicked(icon, item):
                #     print("Icon clicked!")

                # # Load the custom image for the icon
                # image = Image.open(image_path)

                # # Create a menu with an item
                # menu = (
                #     pystray.MenuItem("Click me!", on_clicked),
                # )

                # # Create the system tray icon
                # icon = pystray.Icon("name_of_your_icon", image, "Tooltip text", menu)
                # # Run the icon in the background
                # icon.run_detached()



                # print('im here')
                # try:
                #     print('a')

                #     # subprocess.run(mycommand, input=creds['pw'], text=True, stderr=subprocess.STDOUT)
                #     print('b')
                #     p = subprocess.Popen(mycommand.split(),stdout=subprocess.PIPE,stdin=subprocess.PIPE)
                #     print('c')
                #     p.stdin.write(str.encode(creds['pw'])) #expects a bytes type object
                #     print('d')
                    
                #     print('e')
                #     p.stdin.close()
                    
                # except KeyboardInterrupt:
                #     icon.stop()
                #     exit()

                # Console.ok('Confirm DUO Mobile if needed.')
                # time.sleep()
                # return True
                # with open(os.devnull, 'wb') as nullfile:
                    # r = pexpect.popen_spawn.PopenSpawn(mycommand, logfile=nullfile)
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
                    # self.windows_stop_service()
                    Console.error("Not implemented to stop service on mac")
                    return False

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
                from cloudmesh.common.sudo import Sudo

                Sudo.password()
                command = 'sudo openconnect -b -v ' \
                      '--protocol=anyconnect ' \
                      f'--cafile="{home}/.ssh/uva/usher.cer" ' \
                      f'--sslkey="{home}/.ssh/uva/user.key" ' \
                      f'--certificate="{home}/.ssh/uva/user.crt" ' \
                      'uva-anywhere-1.itc.virginia.edu  2>&1 > /dev/null'
            else:
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

    def disconnect(self):
        if not self.enabled():
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

            import psutil
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
            command = f'{self.anyconnect} disconnect "{self.service}"'
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
        r = Shell.run('curl -s ipinfo.io')
        return r

    def pw_fetcher(self,
                   org):
        
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
                

