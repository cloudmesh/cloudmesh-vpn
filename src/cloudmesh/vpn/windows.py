"""Module to handle installation of Cisco AnyConnect VPN client on Windows and macOS.

This module includes functions to install the Cisco AnyConnect VPN client on Windows using Chocolatey
and on macOS using Homebrew.

Functions:
    win_install: Installs Cisco AnyConnect VPN client based on the operating system (Windows or macOS).

"""
from cloudmesh.common.Shell import Shell
from cloudmesh.common.Shell import Console
from cloudmesh.common.systeminfo import os_is_linux
from cloudmesh.common.systeminfo import os_is_mac
from cloudmesh.common.systeminfo import os_is_windows
import os
import subprocess

def win_install():
    """Installs Cisco AnyConnect VPN client on Windows using Chocolatey.

     This function checks the operating system, installs Chocolatey if not installed,
     and then installs the Cisco AnyConnect VPN client using Chocolatey.

     Returns:
         None
     """
    # Get the full path of the current Python script
    current_script_path = os.path.abspath(__file__)

    # Extract the directory path from the script's path
    current_script_directory = os.path.dirname(current_script_path)
    
    if os_is_windows():


        status = Shell.install_chocolatey()
        if status is False:
            os._exit(1)
        Console.msg('Installing OpenConnect...')
        # try:
        #     r =
        # except subprocess.CalledProcessError as e:

        # command = f'cd {current_script_directory}/bin && choco install chocolatey-core.extension -y && choco pack && choco install cisco-secure-client --debug --verbose --source . --force -y'
        command = f'choco install openconnect --version=9.12.0.20231224'
        # try:

        #     r = Shell.run()
        # except subprocess.CalledProcessError as e:
        #     print(e.output)

        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True  # Allows working with text output
        )

        # Read and display the live output
        for line in process.stdout:
            print(line, end="")

        # Wait for the subprocess to complete
        process.wait()

        # print(r)
        try:
            process = subprocess.Popen(
                'openconnect -V',
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True  # Allows working with text output
            )
            print("success")
        except subprocess.CalledProcessError:
            print("failed")


    elif os_is_mac():
        status = Shell.install_brew()
        if status is False:
            os._exit(1)

        # Console.msg('Not implemented :)')
        # try:
        #     r =
        # except subprocess.CalledProcessError as e:

        # command = f'brew install --cask {current_script_directory}/bin/cisco-secure-client.rb'
        command = f'brew install openconnect'
        # command = f'cd {current_script_directory}/bin ; ls'
        print(command)
        Console.info("OpenConnect is now installing...")
        # try:

            # r = Shell.run()
        # except subprocess.CalledProcessError as e:
        #     print(e.output)

        process = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


        # process = subprocess.Popen(
            # command,
            # shell=True,
            # stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            # universal_newlines=True  # Allows working with text output
        # )
        # print('process is,')
        # print(process)
        # print('stdout is,')
        print("Output:", process.stdout.decode('utf-8'))
        print(process.stderr.decode('utf-8'))

