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
                vpn connect [--service=SERVICE] [-v]
                vpn disconnect [-v]
                vpn status [-v]
                vpn info

          This command manages the von connection

          Options:
              -v      debug [default: False]

        """

        map_parameters(arguments, "service")

        from cloudmesh.vpn.vpn import Vpn
        vpn = Vpn(arguments.service, debug=arguments["-v"])

        if arguments.connect:
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
