# Changelog

All notable changes to `cloudmesh-vpn` will be documented in this file.

## [5.0.18] - 2026-04-28

### Added
- **Keychain Management**: Added `vpn keychain` and `vpn keychain remove` commands to securely manage private key passphrases in the macOS Keychain.
- **Shorthand Aliases**: Added `vpn +` for connect and `vpn -` for disconnect.

### Changed
- **Cisco Deprecation**: Deprecated the official Cisco AnyConnect client on macOS in favor of OpenConnect with `vpn-slice`.
- **Provider Restrictions**: Removed `cisco` as a selectable provider via `--provider` to steer users toward supported OpenConnect strategies.
- **Documentation**: Updated `README.md` with Cisco uninstall instructions and keychain management guide.

### Fixed
- **Keychain Strategy**: Fixed `MacOpenConnectKeychainStrategy` to correctly use the `-a` (account) flag and handle missing keychain items gracefully.
- **Security**: Implemented passphrase piping via `stdin` for OpenConnect to avoid insecure command-line arguments.
- **Bug Fixes**: Resolved a string decoding `AttributeError` in the keychain error handler and improved `vpn-slice` binary discovery.

## [5.0.17] - 2026-04-28

### Added
- `vpn watch` command for real-time monitoring of VPN processes and routes.

### Changed
- macOS connections now run as persistent background processes.
- Improved `sudo` handling and connection visibility on macOS.
- Added `username` support in `organizations.yaml`.

### Fixed
- Fixed `Permission denied` and crash issues during macOS connection and disconnection.

## [5.0.16] - 2026-04-27

### Added
- **State Transition Reporting**: Added "before and after" state reporting for `connect` and `disconnect` commands (e.g., "Switched from Org A to Org B").
- **Rich Visualization**: Implemented a professional Rich table with rounded corners and cyan color scheme for the `vpn info` command.
- **Configuration Validation**: Added mandatory key validation for `organizations.yaml` to prevent runtime errors.
- **Pretty Printing**: The `vpn info` method now returns a pretty-printed JSON string.

### Changed
- **Performance Optimizations**:
    - Implemented lazy-loading for configuration and binary discovery to significantly reduce startup time.
    - Optimized `is_enabled` to prioritize local process and client state checks over slow network requests.
    - Reduced `ipinfo.io` timeouts to 2 seconds and removed retry loops to eliminate CLI lag.
- **Reliability & Security**:
    - Improved Windows process termination using a "terminate-then-kill" strategy to prevent zombie `openconnect.exe` processes.
    - Secured password handling in `MacVpnStrategy` using `subprocess.Popen` to avoid passing credentials in the command string.
    - Added certificate path validation for Linux connections.
- **Logging**: Replaced standard `print` calls with `Console` logging for consistent output.
- **Dependencies**: Updated `pyproject.toml` to include `requests`, `rich`, `psutil`, and `pyyaml`.

### Fixed
- Fixed `AttributeError` where `Console.print` was called on the `cloudmesh.common.Shell.Console` wrapper instead of a `rich.console.Console` instance.
- Removed redundant `print()` calls in the command layer that caused duplicate output of IP information.