from cloudmesh.common.console import Console
from cloudmesh.shell.command import PluginCommand
from cloudmesh.shell.command import command
from cloudmesh.shell.command import map_parameters


class VpnCommand(PluginCommand):

    # noinspection PyUnusedLocal
    @command
    def do_vpn(self, args, arguments):
        """
        ::

          Usage:
                vpn connect [--service=SERVICE] [--timeout=TIMEOUT] [-v] [--choco]
                vpn disconnect [-v]
                vpn status [-v]
                vpn info

          This command manages the vpn connection

          Options:
              -v       debug [default: False]
              --choco  installs chocolatey [default: False]

          Description:
            vpn info
               prints out information about your current location as
               obtained via the vpn connection.

            vpn status
                prints out "True" if the vpn is connected
                and "False" if it is not.

            vpn disconnect
                disconnects from the VPN.

            vpn connect [--service=SERVICE]
                connects to the UVA Anywhere VPN.

                If the VPN is already connected a warning is shown.

                You can connect to other VPNs while specifying their names
                as given to you by the VPN provider with e service option.


        """

        map_parameters(arguments, "service", "timeout", "choco")

        from cloudmesh.vpn.vpn import Vpn
        vpn = Vpn(arguments.service,
                  timeout=arguments.timeout,
                  debug=arguments["-v"])

        if arguments.connect:
            vpn.anyconnect_checker(arguments['choco'])
            if arguments['service']:
                service = arguments['service'].lower()
                status = vpn.pw_fetcher(service)
                
                if not status:
                    if vpn.is_user_auth(service):
                        Console.error("failed")
                        return
                else:
                    Console.ok("Connecting ... ")
                    vpn.connect({'user': status[0],
                                 'pw': status[1],
                                 'service': service})
                    if vpn.enabled():
                        Console.ok("ok")
                    else:
                        Console.error("failed")
                    return True

                    
                
            Console.ok("Connecting ... ")
            vpn.connect()
            if vpn.enabled():
                Console.ok("ok")
            else:
                Console.error("failed")

        elif arguments.disconnect:
            Console.ok("Disconnecting ... ")
            vpn.disconnect()
            if not vpn.enabled():
                Console.ok("ok")
            else:
                Console.error("failed")

        elif arguments.status:
            print(vpn.enabled())

        elif arguments.info:
            print(vpn.info())

        # elif arguments.install:
        #     found = Shell.which("openconnect")
        #
        #     if found is None:
        #         Console.ok("Installing")
        #         if yn_choice("This command is only supported on Ubunto. Continue"):
        #             os.system("sudo apt-get install openconnect")
        #         else:
        #             Console.error("cms vpn is only supported on Linux.")
        #
        #     else:
        #         Console.error("vpn client is already installed")

        return ""
