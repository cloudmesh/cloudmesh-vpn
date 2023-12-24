import subprocess
import re
import subprocess
import re
import os
# converted to python by Gregor von Laszewski
# This script matches the version found at https://gitlab.com/openconnect/vpnc-scripts/-/blob/b749c2cadc2f32e2efffa69302861f9a7d4a4e5f/vpnc-script-win.js
# Updated on 2021-09-24 by Daniel Lenski <dlenski@gmail.com> ("Ensure that vpnc-script-win.js works even if INTERNAL_IP4_{NETADDR,NETMASK} are unset")
#
# vpnc-script-win-python.py
#
# Routing, IP, and DNS configuration script for OpenConnect.

# --------------------------------------------------------------
# Initial setup
# --------------------------------------------------------------

# Your Python code here


accumulatedExitCode = 0
# TODO: find and define WScript
ws = WScript.CreateObject("WScript.Shell")
env = ws.Environment("Process")
comspec = ws.ExpandEnvironmentStrings("%comspec%")

# How to add the default internal route
# 0 - As interface gateway when setting properties
# 1 - As a 0.0.0.0/0 route with a lower metric than the default route
# 2 - As 0.0.0.0/1 + 128.0.0.0/1 routes (override the default route cleanly)
REDIRECT_GATEWAY_METHOD = 1
CISCO_SPLIT_INC = 3
CISCO_SPLIT_INC_LIST = ["192.168.0.0", "10.0.0.0", "172.16.0.0"]
CISCO_SPLIT_INC_MASKS = ["255.255.255.0", "255.0.0.0", "255.240.0.0"]
# --------------------------------------------------------------
# Utilities
# --------------------------------------------------------------

def echo(msg):
    print(msg)

def run(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    exit_code = process.returncode

    if exit_code != 0:
        echo("\"" + cmd + "\" returned non-zero exit status: " + str(exit_code) + ")")
        echo("   stdout+stderr dump: " + stdout.decode() + stderr.decode())

    accumulatedExitCode += exit_code

    return stdout.decode()


def getDefaultGateway():
    output = run("route print")
    match = re.search(r'0\.0\.0\.0 *(0|128)\.0\.0\.0 *([0-9\.]*)', output)
    if match:
        return match.group(2)
    return ""

#
# TODO: not yet sure how to trnalate that as I am not sure if this si something special in js
#
if (!String.prototype.trim) {
    String.prototype.trim = function () {
        return this.replace(/^[\s\uFEFF\xA0]+|[\s\uFEFF\xA0]+$/g, '');
    };
}

// --------------------------------------------------------------
// Script starts here
// --------------------------------------------------------------

def echo(msg):
    print(msg)

def run(cmd):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    exit_code = process.returncode

    if exit_code != 0:
        echo(f'"{cmd}" returned non-zero exit status: {exit_code}')
        echo(f'stdout+stderr dump: {stdout.decode()}{stderr.decode()}')

    return stdout.decode()

def getDefaultGateway():
    output = run("route print")
    match = re.search(r'0\.0\.0\.0 *(0|128)\.0\.0\.0 *([0-9\.]*)', output)
    if match:
        return match.group(2)
    return ""

accumulatedExitCode = 0

reason = os.environ.get("reason")
if reason == "pre-init":
    pass
elif reason == "connect":
    gw = getDefaultGateway()

    INTERNAL_IP4_IP4_NETMASK = os.environ.get("INTERNAL_IP4_NETMASK")
    INTERNAL_IP4_NETADDR = os.environ.get("INTERNAL_IP4_NETADDR")
    INTERNAL_IP4_ADDRESS = os.environ.get("INTERNAL_IP4_ADDRESS")
    INTERNAL_IP4_NETMASKLEN = os.environ.get("INTERNAL_IP4_NETMASKLEN")
    VPNGATEWAY = os.environ.get("VPNGATEWAY")
    TUNDEV = os.environ.get("TUNDEV")
    TUNIDX = os.environ.get("TUNIDX")
    INTERNAL_IP4_MTU = os.environ.get("INTERNAL_IP4_MTU")
    INTERNAL_IP6_ADDRESS = os.environ.get("INTERNAL_IP6_ADDRESS")
    CISCO_SPLIT_EXC = os.environ.get("CISCO_SPLIT_EXC")

    internal_ip4_netmask = INTERNAL_IP4_NETMASK or "255.255.255.255"
    internal_ip4_netaddr = INTERNAL_IP4_NETADDR or INTERNAL_IP4_ADDRESS
    internal_gw_array = internal_ip4_netaddr.split(".")
    if internal_ip4_netmask.strip() != "255.255.255.255" and INTERNAL_IP4_NETMASKLEN != "32":
        internal_gw_array[3] += 1
    internal_gw = ".".join(internal_gw_array)

    echo("VPN Gateway: " + VPNGATEWAY)
    echo("Internal Address: " + INTERNAL_IP4_ADDRESS)
    echo("Internal Netmask: " + internal_ip4_netmask)
    echo("Internal Gateway: " + internal_gw)
    echo("Interface: \"" + TUNDEV + "\" / " + TUNIDX)

    if INTERNAL_IP4_MTU:
        echo("MTU: " + INTERNAL_IP4_MTU)
        run("netsh interface ipv4 set subinterface " + TUNIDX +
            " mtu=" + INTERNAL_IP4_MTU + " store=active")

        if INTERNAL_IP6_ADDRESS:
            run("netsh interface ipv6 set subinterface " + TUNIDX +
                " mtu=" + INTERNAL_IP4_MTU + " store=active")

    echo("Configuring \"" + TUNDEV + "\" / " + TUNIDX + " interface for Legacy IP...")

    #
    # todo: not sure if CISCO_SPLIT_INC is handled correctly
    # could ther be a problem with having an os.environ.get and a regular int set with the smae name
    #
    if not CISCO_SPLIT_INC and REDIRECT_GATEWAY_METHOD != 2:
        run("netsh interface ip set interface \"" + TUNIDX + "\" metric=1 store=active")
    elif CISCO_SPLIT_INC or REDIRECT_GATEWAY_METHOD > 0:
        run("netsh interface ip set address \"" + TUNIDX + "\" static " +
            INTERNAL_IP4_ADDRESS + " " + internal_ip4_netmask + " store=active")
    else:
        run("netsh interface ip set address \"" + TUNIDX + "\" static " +
            INTERNAL_IP4_ADDRESS + " " + internal_ip4_netmask + " " + internal_gw +
            " gwmetric=999 store=active")

    run("route add " + VPNGATEWAY + " mask 255.255.255.255 " + gw)

    run("netsh interface ipv4 del wins " + TUNIDX + " all")
    if INTERNAL_IP4_NBNS:
        wins = INTERNAL_IP4_NBNS.split(" ")
        for win in wins:
            run("netsh interface ipv4 add wins " + TUNIDX + " " + win)
        echo("Configured " + str(len(wins)) + " WINS servers: " + " ".join(wins))

    run("netsh interface ipv4 del dns " + TUNIDX + " all")

    # run("netsh interface ipv6 del dns " + TUNIDX + " all")
    # if INTERNAL_IP4_DNS:
    #     dns = INTERNAL_IP4_DNS.split(" ")
    #     for i in range(len(dns)):
    #         protocol = "ipv6" if ":" in dns[i] else "ipv4"
    #         run("netsh interface " + protocol + " add dns " + TUNIDX + " " + dns[i])
    #     echo("Configured " + str(len(dns)) + " DNS servers: " + " ".join(dns))
    # echo("done.")

    echo("Configuring Legacy IP networks:")
    if CISCO_SPLIT_INC:
        for i in range(int(CISCO_SPLIT_INC)):
            network = CISCO_SPLIT_INC_LIST[i]
            netmask = CISCO_SPLIT_INC_MASKS[i]
            run("route add " + network + " mask " + netmask +
                " 0.0.0.0 " + " if " + TUNIDX)
            echo("Configured Legacy IP split-include route: " + network + "/" + netmask)
    elif REDIRECT_GATEWAY_METHOD == 1:
        run("route add 0.0.0.0 mask 0.0.0.0 " + internal_gw + " metric 999")
        echo("Configured Legacy IP default route.")
    elif REDIRECT_GATEWAY_METHOD == 2:
        run("route add 0.0.0.0 mask 128.0.0.0 " + internal_gw)
        run("route add 128.0.0.0 mask 128.0.0.0 " + internal_gw)
        echo("Configured Legacy IP default route pair (0.0.0.0/1, 128.0.0.0/1)")

    if CISCO_SPLIT_EXC:
        for i in range(int(CISCO_SPLIT_EXC)):
            network = os.environ.get(CISCO_SPLIT_EXC_" + str(i) + "_ADDR")
            netmask = os.environ.get("CISCO_SPLIT_EXC_" + str(i) + "_MASK")
            netmasklen = os.environ.get("CISCO_SPLIT_EXC_" + str(i) + "_MASKLEN")
            run("route add " + network + " mask " + netmask + " " + gw)
            echo("Configured Legacy IP split-exclude route: " + network + "/" + netmasklen)
    echo("Legacy IP route configuration done.")

    if INTERNAL_IP6_ADDRESS:
        echo("Configuring \"" + TUNDEV + "\" / " + TUNIDX + " interface for IPv6...")

        run("netsh interface ipv6 set address " + TUNIDX + " " + INTERNAL_IP6_ADDRESS + " store=active")

        echo("done.")

        echo("Configuring IPv6 networks:")
        if INTERNAL_IP6_NETMASK and not INTERNAL_IP6_NETMASK.endswith("/128"):
            run("netsh interface ipv6 add route " + INTERNAL_IP6_NETMASK +
                " " + TUNIDX + " store=active")

        if os.environ.get("CISCO_IPV6_SPLIT_INC"):
            for i in range(int(CISCO_IPV6_SPLIT_INC)):
                network = os.environ.get("CISCO_IPV6_SPLIT_INC_" + str(i) + "_ADDR")
                netmasklen = os.environ.get("CISCO_IPV6_SPLIT_INC_" + str(i) + "_MASKLEN")
                run("netsh interface ipv6 add route " + network + "/" +
                    netmasklen + " " + os.environ.get("TUNIDX") + " store=active")
                echo("Configured IPv6 split-include route: " + network + "/" + netmasklen)
        else:
            echo("Setting default IPv6 route through VPN.")
            run("netsh interface ipv6 add route 2000::/3 " + TUNIDX + " store=active")

        echo("IPv6 route configuration done.")

    if os.environ.get("CISCO_BANNER"):
        echo("--------------------------------------------------")
        echo(os.environ.get("CISCO_BANNER"))
        echo("--------------------------------------------------")
elif reason == "disconnect":
    run("route delete " + VPNGATEWAY + " mask 255.255.255.255")
    run("netsh interface ipv4 del address " + TUNIDX + " " +
        INTERNAL_IP4_ADDRESS + " gateway=all")
    if INTERNAL_IP6_ADDRESS:
        run("netsh interface ipv6 del address " + TUNIDX + " " + INTERNAL_IP6_ADDRESS"))

    CISCO_SPLIT_EXC = os.environ.get("CISCO_SPLIT_EXC")
    if CISCO_SPLIT_EXC:
        for i in range(int(CISCO_SPLIT_EXC)):
            network = os.environ.get("CISCO_SPLIT_EXC_" + str(i) + "_ADDR")
            netmask = os.environ.get("CISCO_SPLIT_EXC_" + str(i) + "_MASK")
            netmasklen = os.environ.get("CISCO_SPLIT_EXC_" + str(i) + "_MASKLEN")
            run("route delete " + network + " mask " + netmask)
            echo("Configured Legacy IP split-exclude route: " + network + "/" + netmasklen)

WScript.Quit(accumulatedExitCode)
