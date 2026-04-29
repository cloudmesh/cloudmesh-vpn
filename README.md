# cloudmesh-vpn

This library is a wrapper around [openconnect](https://gitlab.com/openconnect/openconnect)
with added functionality. Key features include secure password saving using
the native OS keyring and **VPN-Slicing (Split Tunneling)**.

VPN-Slicing ensures that only traffic destined for specific school servers is
routed through the VPN tunnel, while all other internet traffic remains on
your local connection. This improves performance, preserves privacy, and
allows you to maintain access to local network resources while connected
to the VPN.

The library also provides an easy way to install OpenConnect via package
managers (Chocolatey for Windows, Homebrew for macOS) automatically on-the-fly,
requiring no dependencies other than Python.

## Table of Contents
- [Install](#install)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Changelog](#changelog)
- [Acknowledgments](#acknowledgments)
- [Manual Page](#manual-page)

## Field tests

| School | Tested | VPN-Slicing |
| :--- | :---: | :---: |
| **UVA** <img src="https://upload.wikimedia.org/wikipedia/commons/d/dd/University_of_Virginia_Rotunda_logo.svg" alt="uva" height="15"/> | ✅ | ✅ |
| **FIU** <img src="https://digicdn.fiu.edu/core/_assets/images/logo-top.svg" alt="fiu" width="25"/> | ✅ | ✅ |
| **UFL** <img src="https://www.ufl.edu/wp-content/uploads/sites/5/2022/12/UF-logo-500x500-1.png" alt="uf" height="15"/> | ✅ | ✅ |
| **NYU** | ✅ | ❌ |

## Install

> [!TIP]
> **Best Practice:** It is highly recommended to use a virtual environment
> (such as `venv` or `pyenv`) to install this library. This prevents
> conflicts with other Python packages on your system and keeps your
> global environment clean.

### Windows

Open any terminal (git bash, cmd, powershell) as administrator.

[Download Python from the Python website.](https://www.python.org/downloads/)
Your Python version can be checked with the command `python -V`.
Try doing the following.

**Check Python version:**
```bash
python -V
```
*If `python` is not found, use `python3` for the following commands.*

**Create Virtual Environment (Run as Administrator):**
- **Git Bash:**
  ```bash
  python -m venv ~/ENV3
  source ~/ENV3/Scripts/activate
  ```
- **CMD / PowerShell:**
  ```bash
  python -m venv "%USERPROFILE%\ENV3"
  "%USERPROFILE%\ENV3\Scripts\activate.bat"
  ```

```bash
# now you see (ENV3)
pip install cloudmesh-vpn
```

### macOS

1. **Install Dependencies:**
   ```bash
   brew install openconnect vpn-slice
   ```
2. **Install Library:**
   ```bash
   pip install cloudmesh-vpn
   ```

### Linux (Ubuntu/Debian)

1. **Install Dependencies:**
   ```bash
   sudo apt update
   sudo apt install openssl openconnect network-manager-openconnect
   ```
   *If using GNOME:*
   ```bash
   sudo apt install network-manager-gnome network-manager-openconnect-gnome
   ```
2. **Install Library:**
   ```bash
   pip install cloudmesh-vpn
   ```

## Configuration

Most users can start using the tool immediately after installation. If you
are using a service that requires custom certificates (like UVA), please
see the **FAQ** section for a detailed setup guide.

## Usage

### Connecting to VPN

To connect to the UVA Anywhere VPN, run

```bash
# YOU MUST BE IN YOUR VIRTUAL ENVIRONMENT.
# see the previous commands on how to activate it first.
cms vpn connect
```

For other organizations, use the `--service` flag:

```bash
cms vpn connect --service=ufl
# Supported services: uva, fiu, ufl
```

### VPN-Slicing (Split Tunneling)

By default, `cloudmesh-vpn` enables VPN-Slicing to optimize your
connection. If you need to route **all** traffic through the VPN
(disabling split tunneling), use the `--nosplit` flag:

```bash
cms vpn connect --nosplit
```

Note: On macOS, the connection now runs as a persistent background process.

To disconnect from current VPN, run

```bash
cms vpn disconnect
```

### Command Shorthands

For faster access, you can use the following shorthand aliases:

- `+` is an alias for `connect`
- `-` is an alias for `disconnect`

**Example:**
```bash
cms vpn +       # Connects to the VPN
cms vpn -       # Disconnects from the VPN
```

### Monitoring

To see information regarding your connection, run:

```bash
cms vpn info
```
The `info` command displays a formatted table with your current IP and location.

On macOS, you can monitor the connection status and active routes in real-time:

```bash
cms vpn watch
```

To run the monitor once and exit:
```bash
cms vpn watch now
```

### Keychain Management

If you are using the `openconnect-keychain` provider, you can manage your private key passphrase securely:

To add your passphrase to the macOS Keychain:
```bash
cms vpn keychain
```

To remove your passphrase from the macOS Keychain:
```bash
cms vpn keychain remove
```

### Removing Cisco AnyConnect

If you have the official Cisco AnyConnect client installed, it is
recommended to uninstall it to avoid conflicts with OpenConnect. You can
do this by running the official uninstaller:

```bash
sudo /opt/cisco/anyconnect/bin/vpn_uninstall.sh
```
If the uninstaller is not found, you can manually remove the application from your `/Applications` folder.

## Troubleshooting

Sometimes DNS lookup is broken entirely

To fix this on Windows use:

```powershell
Get-DnsClientNrptRule | Remove-DnsClientNrptRule -Force
netsh interface ipv4 delete winsservers name="Ethernet" all
netsh interface ipv4 delete winsservers name="Wi-Fi" all
rasdial /disconnect
net start dnscache
net stop dnscache
ping google.com
```

## FAQ

### How do I set up and convert certificates for UVA?

If you are connecting to the University of Virginia, follow these steps to
prepare your certificates:

1. **Create the directory:**
   ```bash
   mkdir -p ~/.ssh/uva
   cd ~/.ssh/uva
   ```

2. **Download the Root Certificate:**
   ```bash
   wget --no-check-certificate https://download.its.virginia.edu/local-auth/universal/usher.cer
   ```

3. **Obtain your User Certificate:**
   Go to [SecureW2](https://cloud.securew2.com/public/82116/limited/?device=Unknown),
   complete the form, and download your `.p12` file. Move this file to
   `~/.ssh/uva/user.p12`.

4. **Convert the certificates:**
   ```bash
   openssl pkcs12 -in user.p12 -nocerts -nodes -out user.key
   openssl pkcs12 -in user.p12 -clcerts -nokeys -out user.crt
   openssl x509 -inform DER -in usher.cer -out usher.crt
   ```

5. **Verify the files:**
   Run `ls ~/.ssh/uva/`. You should see: `user.crt`, `user.key`, `user.p12`,
   `usher.cer`, and `usher.crt`.

### What is VPN-Slicing and why should I use it?

VPN-Slicing (Split Tunneling) ensures that only traffic destined for school
servers goes through the VPN. Your regular internet traffic stays on your
local connection, which improves speed and allows you to access local
devices (like printers) while connected.

### Why do I need to use a virtual environment?

Using a virtual environment (`venv`) prevents this library's dependencies
from conflicting with other Python projects on your system, ensuring a
stable and clean installation.

### How do I handle password prompts on macOS?

You can use the `cms vpn keychain` command to securely store your private
key passphrase in the macOS Keychain, eliminating the need to enter it
manually every time you connect.

## Changelog

For a detailed list of changes, see [CHANGELOG.md](CHANGELOG.md).

## Acknowledgments

An early version of cloudmesh-vpn was in part developed to support the NSF
CyberTraining: CIC: CyberTraining for Students and Technologies from
Generation Z with the award numbers 1829704 and 2200409 and used by
participating students. Version 6 was in part refactored with the help of
Gemma4.


## Manual Page

<!add uninstall instructions for -- START-MANUAL -->
```
Command vpn
===========

  Usage:
        vpn connect [--service=SERVICE] [--timeout=TIMEOUT] 
                    [-v] [--choco] [--nosplit] [--provider=PROVIDER]
        vpn + [--service=SERVICE] [--timeout=TIMEOUT] 
              [-v] [--choco] [--nosplit] [--provider=PROVIDER]
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
        --provider=PROVIDER  vpn provider for macOS (openconnect-decrypted, 
                   openconnect-keychain, openconnect) [default: openconnect-decrypted]

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



```
<!-- STOP-MANUAL -->