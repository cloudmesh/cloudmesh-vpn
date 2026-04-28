#!/usr/bin/env python3
import subprocess
import sys
import requests

def get_public_ip():
    try:
        return requests.get('https://ifconfig.me', timeout=10).text.strip()
    except Exception as e:
        print(f"Error fetching public IP: {e}")
        return None

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result
    except Exception as e:
        print(f"Error running command {command}: {e}")
        return None

def test_connectivity(host):
    # Use ping to check connectivity
    result = subprocess.run(['ping', '-c', '1', '-W', '2', host], capture_output=True)
    return result.returncode == 0

def main():
    print("--- Starting Split VPN Test (Python) ---")

    # 1. Capture public IP before connection
    print("Capturing public IP before connection...")
    ip_before = get_public_ip()
    if not ip_before:
        print("Could not determine initial public IP. Exiting.")
        sys.exit(1)
    print(f"IP Before: {ip_before}")

    # 2. Connect to VPN
    print("Connecting to VPN...")
    connect_res = run_command("cms vpn connect")
    if connect_res is None or connect_res.returncode != 0:
        print(f"Error: Failed to connect to VPN.\n{connect_res.stderr if connect_res else ''}")
        sys.exit(1)

    try:
        # 3. Capture public IP after connection
        print("Capturing public IP after connection...")
        ip_after = get_public_ip()
        print(f"IP After:  {ip_after}")

        # 4. Verify internal connectivity
        internal_host = "rivanna.hpc.virginia.edu"
        print(f"Testing connectivity to internal host: {internal_host}...")
        internal_reachable = test_connectivity(internal_host)
        internal_status = "REACHABLE" if internal_reachable else "UNREACHABLE"
        print(f"Internal Host: {internal_status}")

        print("--------------------------------")
        print("RESULTS:")

        if ip_before == ip_after:
            if internal_reachable:
                print("SUCCESS: Split Tunnel is working correctly.")
                print("Public IP remained the same, and internal resources are accessible.")
            else:
                print("FAILURE: Public IP is correct (Split), but internal resources are UNREACHABLE.")
                print("The VPN tunnel might not be routing internal traffic correctly.")
        else:
            print("FAILURE: Full Tunnel detected.")
            print(f"Public IP changed from {ip_before} to {ip_after}.")
            print("All traffic is being routed through the VPN.")
        print("--------------------------------")

    finally:
        # Cleanup: Disconnect VPN
        print("Disconnecting VPN...")
        run_command("cms vpn disconnect")

if __name__ == "__main__":
    main()