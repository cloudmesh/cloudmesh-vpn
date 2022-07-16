import os

from cloudmesh.common.console import Console
from cloudmesh.common.debug import VERBOSE
from cloudmesh.common.util import yn_choice
from cloudmesh.shell.command import PluginCommand
from cloudmesh.shell.command import command
from cloudmesh.shell.command import map_parameters
from cloudmesh.common.Shell import Shell


class VpnCommand(PluginCommand):

    # noinspection PyUnusedLocal
    @command
    def do_vpn(self, args, arguments):
        """
        ::

          Usage:
                vpn connect [--service=SERVICE]
                vpn disconnect
                vpn info
                vpn install

          This command manages the von connection

          Arguments:
              FILE   a file name

          Options:
              -f      specify the file

        """

        map_parameters(arguments, "service")

        from cloudmesh.vpn.vpn import Vpn
        vpn = Vpn(arguments.service)

        if arguments.connect:
            Console.ok("Connecting ...")
            vpn.connect()

        elif arguments.disconnect:
            Console.ok("Disconnecting ...")
            vpn.disconnect()

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
