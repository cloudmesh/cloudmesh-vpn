// This script matches the version found at https://gitlab.com/openconnect/vpnc-scripts/-/blob/b749c2cadc2f32e2efffa69302861f9a7d4a4e5f/vpnc-script-win.js
// Updated on 2021-09-24 by Daniel Lenski <dlenski@gmail.com> ("Ensure that vpnc-script-win.js works even if INTERNAL_IP4_{NETADDR,NETMASK} are unset")
//
// vpnc-script-win.js
//
// Routing, IP, and DNS configuration script for OpenConnect.

// --------------------------------------------------------------
// Initial setup
// --------------------------------------------------------------

var accumulatedExitCode = 0;
var ws = WScript.CreateObject("WScript.Shell");
var env = ws.Environment("Process");
var comspec = ws.ExpandEnvironmentStrings("%comspec%");

// How to add the default internal route
// 0 - As interface gateway when setting properties
// 1 - As a 0.0.0.0/0 route with a lower metric than the default route
// 2 - As 0.0.0.0/1 + 128.0.0.0/1 routes (override the default route cleanly)
var REDIRECT_GATEWAY_METHOD = 1;
var CISCO_SPLIT_INC = 3;
var CISCO_SPLIT_INC_LIST = ["192.168.0.0", "10.0.0.0", "172.16.0.0"];
var CISCO_SPLIT_INC_MASKS = ["255.255.255.0", "255.0.0.0", "255.240.0.0"];

// --------------------------------------------------------------
// Utilities
// --------------------------------------------------------------

function echo(msg) {
    WScript.echo(msg);
}

function run(cmd) {
    var oExec = ws.Exec(comspec + " /C \"" + cmd + "\" 2>&1");
    oExec.StdIn.Close();

    var s = oExec.StdOut.ReadAll();

    var exitCode = oExec.ExitCode;
    if (exitCode != 0) {
        echo("\"" + cmd + "\" returned non-zero exit status: " + exitCode + ")");
        echo("   stdout+stderr dump: " + s);
    }
    accumulatedExitCode += exitCode;

    return s;
}

function getDefaultGateway() {
    if (run("route print").match(/0\.0\.0\.0 *(0|128)\.0\.0\.0 *([0-9\.]*)/)) {
        return (RegExp.$2);
    }
    return ("");
}

if (!String.prototype.trim) {
    String.prototype.trim = function () {
        return this.replace(/^[\s\uFEFF\xA0]+|[\s\uFEFF\xA0]+$/g, '');
    };
}

// --------------------------------------------------------------
// Script starts here
// --------------------------------------------------------------

switch (env("reason")) {
    case "pre-init":
        break;
    case "connect":
        var gw = getDefaultGateway();
        // Calculate the first legal host address in subnet
        // (identical to the INTERNAL_IP4_ADDRESS if the netmask is
        // 255.255.255.255, otherwise increment the last octet)
        // We also need to work around the fact that
        // INTERNAL_IP4_{NETMASK,NETADDR} are not always set for
        // all protocols.
        var internal_ip4_netmask = env("INTERNAL_IP4_NETMASK") || "255.255.255.255";
        var internal_ip4_netaddr = env("INTERNAL_IP4_NETADDR") || env("INTERNAL_IP4_ADDRESS");
        var internal_gw_array = internal_ip4_netaddr.split(".");
        if (internal_ip4_netmask.trim() != "255.255.255.255" && env("INTERNAL_IP4_NETMASKLEN") != 32)
            internal_gw_array[3]++;
        var internal_gw = internal_gw_array.join(".");

        echo("VPN Gateway: " + env("VPNGATEWAY"));
        echo("Internal Address: " + env("INTERNAL_IP4_ADDRESS"));
        echo("Internal Netmask: " + internal_ip4_netmask);
        echo("Internal Gateway: " + internal_gw);
        echo("Interface: \"" + env("TUNDEV") + "\" / " + env("TUNIDX"));


        if (env("INTERNAL_IP4_MTU")) {
            echo("MTU: " + env("INTERNAL_IP4_MTU"));
            run("netsh interface ipv4 set subinterface " + env("TUNIDX") +
                " mtu=" + env("INTERNAL_IP4_MTU") + " store=active");

            if (env("INTERNAL_IP6_ADDRESS")) {
                run("netsh interface ipv6 set subinterface " + env("TUNIDX") +
                    " mtu=" + env("INTERNAL_IP4_MTU") + " store=active");
            }
        }

        echo("Configuring \"" + env("TUNDEV") + "\" / " + env("TUNIDX") + " interface for Legacy IP...");

        if (!CISCO_SPLIT_INC && REDIRECT_GATEWAY_METHOD != 2) {
            // Interface metric must be set to 1 in order to add a route with metric 1 since Windows Vista
            run("netsh interface ip set interface \"" + env("TUNIDX") + "\" metric=1 store=active");
        }

        else if (env(CISCO_SPLIT_INC) || REDIRECT_GATEWAY_METHOD > 0) {
            run("netsh interface ip set address \"" + env("TUNIDX") + "\" static " +
                env("INTERNAL_IP4_ADDRESS") + " " + internal_ip4_netmask + " store=active");
        }
        else {
            // The default route will be added automatically
            run("netsh interface ip set address \"" + env("TUNIDX") + "\" static " +
                env("INTERNAL_IP4_ADDRESS") + " " + internal_ip4_netmask + " " + internal_gw +
                " gwmetric=999 store=active");
        }

        // Add direct route for the VPN gateway to avoid routing loops
        // FIXME: handle IPv6 gateway address
        run("route add " + env("VPNGATEWAY") + " mask 255.255.255.255 " + gw);

        run("netsh interface ipv4 del wins " + env("TUNIDX") + " all");
        if (env("INTERNAL_IP4_NBNS")) {
            var wins = env("INTERNAL_IP4_NBNS").split(/ /);
            for (var i = 0; i < wins.length; i++) {
                run("netsh interface ipv4 add wins " + env("TUNIDX") + " " + wins[i]);
            }
            echo("Configured " + wins.length + " WINS servers: " + wins.join(" "));
        }

        run("netsh interface ipv4 del dns " + env("TUNIDX") + " all");
        // run("netsh interface ipv6 del dns " + env("TUNIDX") + " all");
        // if (env("INTERNAL_IP4_DNS")) {
        //     var dns = env("INTERNAL_IP4_DNS").split(/ /);
        //     for (var i = 0; i < dns.length; i++) {
        //         var protocol = dns[i].indexOf(":") !== -1 ? "ipv6" : "ipv4";
        //         run("netsh interface " + protocol + " add dns " + env("TUNIDX") + " " + dns[i]);
        //     }
        //     echo("Configured " + dns.length + " DNS servers: " + dns.join(" "));
        // }
        // echo("done.");

        // Add internal network routes
        echo("Configuring Legacy IP networks:");
        if (CISCO_SPLIT_INC) {
            for (var i = 0; i < parseInt(CISCO_SPLIT_INC); i++) {
                var network = CISCO_SPLIT_INC_LIST[i];
                var netmask = CISCO_SPLIT_INC_MASKS[i];
                run("route add " + network + " mask " + netmask +
                    " 0.0.0.0 " + " if " + env("TUNIDX"));
                echo("Configured Legacy IP split-include route: " + network + "/" + netmask);
            }
        } else if (REDIRECT_GATEWAY_METHOD == 1) {
            run("route add 0.0.0.0 mask 0.0.0.0 " + internal_gw + " metric 999");
            echo("Configured Legacy IP default route.");
        } else if (REDIRECT_GATEWAY_METHOD == 2) {
            run("route add 0.0.0.0 mask 128.0.0.0 " + internal_gw);
            run("route add 128.0.0.0 mask 128.0.0.0 " + internal_gw);
            echo("Configured Legacy IP default route pair (0.0.0.0/1, 128.0.0.0/1)");
        }

        // Add excluded routes
        if (env("CISCO_SPLIT_EXC")) {
            for (var i = 0; i < parseInt(env("CISCO_SPLIT_EXC")); i++) {
                var network = env("CISCO_SPLIT_EXC_" + i + "_ADDR");
                var netmask = env("CISCO_SPLIT_EXC_" + i + "_MASK");
                var netmasklen = env("CISCO_SPLIT_EXC_" + i + "_MASKLEN");
                run("route add " + network + " mask " + netmask + " " + gw);
                echo("Configured Legacy IP split-exclude route: " + network + "/" + netmasklen);
            }
        }
        echo("Legacy IP route configuration done.");

        if (env("INTERNAL_IP6_ADDRESS")) {
            echo("Configuring \"" + env("TUNDEV") + "\" / " + env("TUNIDX") + " interface for IPv6...");

            run("netsh interface ipv6 set address " + env("TUNIDX") + " " + env("INTERNAL_IP6_ADDRESS") + " store=active");

            echo("done.");

            // Add internal network routes
            echo("Configuring IPv6 networks:");
            if (env("INTERNAL_IP6_NETMASK") && !env("INTERNAL_IP6_NETMASK").match("/128$")) {
                run("netsh interface ipv6 add route " + env("INTERNAL_IP6_NETMASK") +
                    " " + env("TUNIDX") + " store=active");
            }

            if (env("CISCO_IPV6_SPLIT_INC")) {
                for (var i = 0; i < parseInt(env("CISCO_IPV6_SPLIT_INC")); i++) {
                    var network = env("CISCO_IPV6_SPLIT_INC_" + i + "_ADDR");
                    var netmasklen = env("CISCO_IPV6_SPLIT_INC_" + i + "_MASKLEN");
                    run("netsh interface ipv6 add route " + network + "/" +
                        netmasklen + " " + env("TUNIDX") + " store=active")
                    echo("Configured IPv6 split-include route: " + network + "/" + netmasklen);
                }
            } else {
                echo("Setting default IPv6 route through VPN.");
                run("netsh interface ipv6 add route 2000::/3 " + env("TUNIDX") + " store=active");
            }

            // FIXME: handle IPv6 split-excludes

            echo("IPv6 route configuration done.");
        }

        if (env("CISCO_BANNER")) {
            echo("--------------------------------------------------");
            echo(env("CISCO_BANNER"));
            echo("--------------------------------------------------");
        }
        break;
    case "disconnect":
        // Delete direct route for the VPN gateway
        // FIXME: handle IPv6 gateway address
        run("route delete " + env("VPNGATEWAY") + " mask 255.255.255.255");

        // Delete address
        run("netsh interface ipv4 del address " + env("TUNIDX") + " " +
            env("INTERNAL_IP4_ADDRESS") + " gateway=all");
        if (env("INTERNAL_IP6_ADDRESS")) {
            run("netsh interface ipv6 del address " + env("TUNIDX") + " " + env("INTERNAL_IP6_ADDRESS"));
        }

        // Delete Legacy IP split-exclude routes
        if (env("CISCO_SPLIT_EXC")) {
            for (var i = 0; i < parseInt(env("CISCO_SPLIT_EXC")); i++) {
                var network = env("CISCO_SPLIT_EXC_" + i + "_ADDR");
                var netmask = env("CISCO_SPLIT_EXC_" + i + "_MASK");
                var netmasklen = env("CISCO_SPLIT_EXC_" + i + "_MASKLEN");
                exec("route delete " + network + " mask " + netmask);
            }
        }

    // FIXME: handle IPv6 split-excludes
}
WScript.Quit(accumulatedExitCode);