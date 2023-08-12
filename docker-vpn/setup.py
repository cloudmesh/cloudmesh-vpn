import subprocess

def get_vpn_credentials():
    vpn_hostname = input("Enter VPN Hostname: ")
    vpn_username = input("Enter VPN Username: ")
    vpn_password = input("Enter VPN Password: ")
    return vpn_hostname, vpn_username, vpn_password

def main():
    vpn_hostname, vpn_username, vpn_password = get_vpn_credentials()

    # Start the openconnect command in the background
    openconnect_cmd = [
        "nohup",
        "openconnect",
        vpn_hostname,
        "--background",
        "--protocol=anyconnect",
        "--user=" + vpn_username,
        "--passwd-on-stdin"
    ]

    log_file = "openconnect.log"
    with open(log_file, "a") as log:
        subprocess.run(openconnect_cmd, input=vpn_password, text=True, stdout=log, stderr=subprocess.STDOUT)

    # Your script can continue executing other tasks
    print("done")

if __name__ == "__main__":
    main()
