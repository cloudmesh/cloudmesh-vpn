
import os
import subprocess
from typing import Any, Dict, Optional, Union
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
        vpn + [--service=SERVICE] [--timeout=TIMEOUT] [-v] [--choco] [--nosplit] [--provider=PROVIDER]
        vpn disconnect [-v]
        vpn - [-v]
        vpn status [-v]
        vpn info
        vpn reset [--service=SERVICE]
        vpn watch [INTERVAL]
        vpn keychain [remove]

          This command manages the vpn connection

  Options:
       -v       debug [default: False]
       --choco  installs chocolatey [default: False]
        --provider=PROVIDER  vpn provider for macOS (openconnect-decrypted, openconnect-keychain, openconnect) [default: openconnect-decrypted]

          Description:
            vpn info
               prints out information about your current location as
               obtained via the vpn connection.

            vpn status
                prints out "True" if the vpn is connected
                and "False" if it is not.

            vpn disconnect
            vpn -
                disconnects from the VPN.

            vpn connect [--service=SERVICE]
            vpn +
                connects to the UVA Anywhere VPN.

                If the VPN is already connected a warning is shown.

                You can connect to other VPNs while specifying their names
                as given to you by the VPN provider with e service option.

            vpn reset [--service=SERVICE]
                clears the credentials for the VPN service

            vpn keychain
                securely adds the VPN private key passphrase to the macOS Keychain.

            vpn keychain remove
                removes the VPN private key passphrase from the macOS Keychain.


        """

        map_parameters(arguments, "service", "timeout", "choco", "nosplit", "provider")

        # Support shorthand aliases: + for connect, - for disconnect
        arg_list = args.split() if isinstance(args, str) else args
        if arg_list:
            if '+' in arg_list:
                arguments.connect = True
            if '-' in arg_list:
                arguments.disconnect = True

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

        elif arguments.keychain:
            # Handle 'remove' subcommand
            arg_list = args.split() if isinstance(args, str) else args
            if arg_list and 'remove' in arg_list:
                try:
                    subprocess.run(
                        ["security", "delete-generic-password", "-a", "uva", "-s", "uva-key-pass"],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    Console.ok("Successfully removed passphrase from macOS Keychain.")
                    return True
                except subprocess.CalledProcessError as e:
                    Console.error(f"Failed to remove passphrase from keychain: {e.stderr.strip()}")
                    return False

            # Default: Add passphrase
            import getpass
            Console.info("Setting up VPN Keychain credentials...")
            passphrase = getpass.getpass("Enter your private key passphrase: ")
            if not passphrase:
                Console.error("Passphrase cannot be empty.")
                return False
            
            try:
                # Use -w to provide the password from the prompt
                subprocess.run(
                    ["security", "add-generic-password", "-a", "uva", "-s", "uva-key-pass", "-w", passphrase],
                    check=True,
                    capture_output=True,
                    text=True
                )
                Console.ok("Successfully added passphrase to macOS Keychain.")
                return True
            except subprocess.CalledProcessError as e:
                if "already exists" in e.stderr.lower():
                    Console.warning("Keychain item already exists. Use 'cms vpn keychain remove' to remove it first.")
                else:
                    Console.error(f"Failed to add passphrase to keychain: {e.stderr.strip()}")
                return False

        elif arguments.watch:
            # Determine if we should run once or loop
            run_once = False
            interval = 1
            
            try:
                # Ensure args is a list of words
                arg_list = args.split() if isinstance(args, str) else args
                if arg_list and 'watch' in arg_list:
                    idx = arg_list.index('watch')
                    if idx + 1 < len(arg_list):
                        val = arg_list[idx + 1]
                        if val == 'now':
                            run_once = True
                        elif val.isdigit():
                            interval = int(val)
            except (ValueError, IndexError):
                pass

            if run_once:
                # Execute once and exit
                from datetime import datetime
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                try:
                    git_version = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
                except Exception:
                    git_version = "unknown"
                
                output = [f"Current Time: {now}", f"Git Version: {git_version}", "-" * 40]
                evidence = vpn.watch()
                if evidence:
                    for item in evidence:
                        output.append(f"Evidence found: {item}")
                else:
                    output.append("No evidence of split-vpn found.")
                
                print("\n".join(output))
                print("-" * 40)
            else:
                # Loop mode
                Console.info(f"Watching for split-vpn evidence every {interval} second(s). Press Ctrl+C to stop.")
                try:
                    import time
                    from datetime import datetime
                    while True:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        try:
                            git_version = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
                        except Exception:
                            git_version = "unknown"
                            
                        output = [f"Current Time: {now}", f"Git Version: {git_version}", "-" * 40]
                        evidence = vpn.watch()
                        if evidence:
                            for item in evidence:
                                output.append(f"Evidence found: {item}")
                        else:
                            output.append("No evidence of split-vpn found.")
                        
                        # Clear screen and reset cursor for loop mode
                        print("\033[H\033[J", end="")
                        print("\n".join(output))
                        print("-" * 40)
                        time.sleep(interval)
                except KeyboardInterrupt:
                    Console.ok("\nStopped watching.")

        return ""
