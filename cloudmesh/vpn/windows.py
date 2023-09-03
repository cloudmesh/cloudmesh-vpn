from cloudmesh.common.Shell import Shell
from cloudmesh.common.Shell import Console
import os
import subprocess

def win_install():
    

    # Get the full path of the current Python script
    current_script_path = os.path.abspath(__file__)

    # Extract the directory path from the script's path
    current_script_directory = os.path.dirname(current_script_path)

    status = Shell.install_chocolatey()
    if status is False:
        os._exit(1)
    Console.msg('Installing cisco...')
    # try:
    #     r =
    # except subprocess.CalledProcessError as e:

    command = f'cd {current_script_directory}/bin && choco install chocolatey-core.extension -y && choco pack && choco install cisco-secure-client --debug --verbose --source . --force -y'

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
            'vpncli',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True  # Allows working with text output
        )
        print("success")
    except subprocess.CalledProcessError:
        print("failed")

