import os
from typing import Any, Dict, Optional
from cloudmesh.common.console import Console
from cloudmesh.shell.command import PluginCommand
from cloudmesh.shell.command import command
from cloudmesh.shell.command import map_parameters


class VpnCommand(PluginCommand):

    # noinspection PyUnusedLocal
    @command
    def do_vpn(self, args: Any, arguments: Any) -> Optional[Union[bool, str]]:
        """
        ::

  Usage:
        vpn connect [--service=SERVICE] [--timeout=TIMEOUT] [-v] [--choco] [--nosplit] [--provider=PROVIDER]
        vpn disconnect [-v]
        vpn status [-v]
        vpn info
        vpn reset [--service=SERVICE]
        vpn watch [INTERVAL]

          This command manages the vpn connection

  Options:
       -v       debug [default: False]
       --choco  installs chocolatey [default: False]
        --provider=PROVIDER  vpn provider for macOS (cisco, openconnect) [default: openconnect]

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

            vpn reset [--service=SERVICE]
                clears the credentials for the VPN service


        """

        map_parameters(arguments, "service", "timeout", "choco", "nosplit", "provider")

        from cloudmesh.vpn.vpn import Vpn
        vpn = Vpn(arguments.service,
                   timeout=arguments.timeout,
                   debug=arguments["-v"],
                   provider=arguments.provider)

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
                                  'service': service,
                                  'nosplit': arguments['nosplit']})
                    if vpn.enabled():
                        Console.ok("ok")
                    else:
                        Console.error("failed")
                    return True

                    
            Console.ok("Connecting ... ")
            vpn.connect(
                {
                    'service': "uva",
                    'nosplit': arguments['nosplit'],
                }
            )
            if vpn.enabled():
                Console.ok("ok")
                vpn.info()
            else:
                Console.error("failed")
                vpn.info()

        elif arguments.disconnect:
            Console.ok("Disconnecting ... ")
            vpn.disconnect()
            
            # Give the system a moment to update the network state
            import time
            for _ in range(5):
                if not vpn.enabled():
                    break
                time.sleep(1)
            
            if not vpn.enabled():
                Console.ok("ok")
            else:
                Console.error("failed")
            vpn.info()

        elif arguments.status:
            print(vpn.enabled())

        elif arguments.info:
            vpn.info()

        elif arguments.reset:
            # 1. Preview commands
            commands = vpn.get_reset_commands(arguments.service)
            if commands:
                print("\nThe following commands will be executed to clean up the routing table:")
                for cmd in commands:
                    print(f"- {cmd}")
                print("")

                # 2. Double confirmation loop
                confirm1 = input("Are you sure you want to proceed? (y/n): ").lower().strip()
                if confirm1 == 'y':
                    confirm2 = input("Are you ABSOLUTELY sure? This will modify your system routing table. (y/n): ").lower().strip()
                    if confirm2 == 'y':
                        Console.info("Cleaning up routes...")
                        if vpn.reset_routes(arguments.service):
                            Console.ok("Routing table cleaned successfully.")
                        else:
                            Console.error("Some routes could not be removed.")
                    else:
                        Console.info("Reset cancelled.")
                else:
                    Console.info("Reset cancelled.")
            else:
                Console.warning("No routes found to reset.")

            # 3. Clear credentials if service is specified
            if arguments['service']:
                vpn.pw_clearer(arguments['service'])
            else:
                Console.info("No service specified, skipping credential cleanup.")

        elif arguments.watch:
            # Determine interval
            interval = 1
            # Look for a number in the args list after 'watch'
            try:
                if args and 'watch' in args:
                    idx = args.index('watch')
                    if idx + 1 < len(args):
                        interval = int(args[idx + 1])
            except (ValueError, IndexError):
                pass

            Console.info(f"Watching for split-vpn evidence every {interval} second(s). Press Ctrl+C to stop.")
            try:
                import time
                from datetime import datetime
                while True:
                    # Gather all output first to prevent blinking
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    output = [f"Current Time: {now}", "-" * 40]
                    
                    evidence = vpn.watch()
                    if evidence:
                        for item in evidence:
                            output.append(f"Evidence found: {item}")
                    else:
                        output.append("No evidence of split-vpn found.")
                    
                    # Clear and print everything at once
                    os.system('clear')
                    print("\n".join(output))
                    
                    time.sleep(interval)
            except KeyboardInterrupt:
                Console.ok("\nStopped watching.")

        return ""