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

# put near your imports
import glob
try:
    import winreg
except ModuleNotFoundError:
    winreg = None  # non-Windows


def _get_machine_env(varname, default=None):
    # Prefer live process env if already present
    val = os.environ.get(varname)
    if val:
        return val
    # Read from Machine env via registry (works even if current process missed it)
    if winreg is None:
        return default
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as k:
            val, _ = winreg.QueryValueEx(k, varname)
            return val
    except Exception:
        return default

def get_choco_root():
    return _get_machine_env("ChocolateyInstall", r"C:\ProgramData\Chocolatey")

def get_choco_exe():
    root = get_choco_root()
    exe = os.path.join(root, "bin", "choco.exe")
    return exe if os.path.exists(exe) else None

def get_openconnect_exe():
    root = get_choco_root()
    # 1) Chocolatey shim (preferred)
    shim = os.path.join(root, "bin", "openconnect.exe")
    if os.path.exists(shim):
        return shim
    # 2) Real binary under the package folder (fallback)
    for path in glob.glob(os.path.join(root, "lib", "openconnect", "**", "openconnect.exe"), recursive=True):
        return path
    return None

def ensure_choco_bin_on_process_path():
    root = get_choco_root()
    bin_dir = os.path.join(root, "bin")
    os.environ.setdefault("ChocolateyInstall", root)
    if bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + bin_dir


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

        # try:
        #     r =
        # except subprocess.CalledProcessError as e:

        # command = f'cd {current_script_directory}/bin && choco install chocolatey-core.extension -y && choco pack && choco install cisco-secure-client --debug --verbose --source . --force -y'
            

        # Make sure *this* process can see choco even if PATH wasn't refreshed
        ensure_choco_bin_on_process_path()
        choco = get_choco_exe()
        if not choco:
            raise RuntimeError("choco.exe not found. Check ChocolateyInstall or permissions.")

        Console.msg('Installing OpenConnect...')
        subprocess.check_call([choco, "install", "openconnect", "-y"])

        # Resolve full path to openconnect.exe and return it
        oc = get_openconnect_exe()
        if not oc:
            raise RuntimeError("OpenConnect install finished but openconnect.exe was not found.")
        # Optional: make it visible to this process right away
        ensure_choco_bin_on_process_path()
        # Quick sanity check
        try:
            out = subprocess.check_output([oc, "-V"], text=True, stderr=subprocess.STDOUT)
            print("success")
            print(out)
        except subprocess.CalledProcessError as e:
            print("OpenConnect version check failed:\n", e.output)
        return oc

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

