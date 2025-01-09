# cloudmesh-vpn

| School  | Tested | VPN-Slicing |
| ------- | ------ | ----------- |
| UVA&nbsp; <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/University_of_Virginia_Rotunda_logo.svg/2007px-University_of_Virginia_Rotunda_logo.svg.png" alt="uva" height="15"/> | ✅ | ✅ |
| FIU&nbsp; <img src="https://brand.fiu.edu/_assets/images/fiu-alone.png" alt="fiu" height="15"/> | ✅ | ✅ |
| UFL&nbsp; <img src="https://www.ufl.edu/wp-content/uploads/sites/5/2022/12/UF-logo-500x500-1.png" alt="uf" height="15"/> | ✅ | ✅ |
| FAMU | ❌ | ❌ |
| NYU | ✅ | ❌ |
| UCI | ❌ | ❌ |
| GMU | ❌ | ❌ |
| OleMiss | ❌ | ❌ |
| SC | ❌ | ❌ |

## Install

### Windows

Open any terminal (git bash, cmd, powershell) as administrator.

Python 3.12 is recommended, which can be
[downloaded from the Python website.](https://www.python.org/downloads/) Your Python version can be checked
with the command `python -V`

Once confirming Python, execute:

```bash
pip install cloudmesh-vpn
```

## Usage

To connect to the UVA Anywhere VPN, run

```bash
cms vpn connect
```

For other organizations, the `--service` flag can be used:

```bash
cms vpn connect --service=ufl
# possible services are uva fiu ufl
```

Note- currently the output will be piped to the terminal
and will end in response to `Ctrl + C`
consider executing the following:

`nohup cms vpn connect --service=ufl >/dev/null 2>&1`

To disconnect from current VPN, run

```bash
cms vpn disconnect
```

To see info regarding your connection, run

```bash
cms vpn info
```

## Troubleshooting

Sometimes DNS lookup is broken entirely

To fix:

```powershell
Get-DnsClientNrptRule | Remove-DnsClientNrptRule -Force
netsh interface ipv4 delete winsservers name="Ethernet" all
netsh interface ipv4 delete winsservers name="Wi-Fi" all
rasdial /disconnect
net start dnscache
net stop dnscache
ping google.com
```

## Linux and macOS

### Requirements

We use the command `openconnect`. To check if it is available please use

```bash
$ which openconnect
```

If it is not available, on macOS do:

```bash
brew install openconnect
```

you can install it on Ubuntu with 

```bash
$ sudo apt install openssl
$ sudo apt install openconnect
$ sudo apt install network-manager-openconnect
```
and in case you use gnome also:

```bash
$ sudo apt install network-manager-gnome
$ sudo apt install network-manager-openconnect-gnome
```

### Getting certificates

We have tested this tool only with University of Virginia, but it should be simple to adapt. Just follow the 
instructions to obtain the certificates from your provider.

At UVA you find the certificate and other documentation at 

* <https://www.rc.virginia.edu/userinfo/linux/uva-anywhere-vpn-linux/>

we place all certificates into ~/.ssh/uva

```
mkdir -p ~/.ssh/uva
# You will receive a file ending in .p12. In this example we will assume it is named mst3k.p12.
cd ~/.ssh/uva
# wget https://download.its.virginia.edu/local-auth/universal/usher.cer
wget --no-check-certificate https://download.its.virginia.edu/local-auth/universal/usher.cer
```

To get a certificate for your device, go to 

* <https://cloud.securew2.com/public/82116/limited/?device=Unknown>

Fill it out and get the key. You will receive a 
file ending in .p12. In this example we will assume it 
is named mst3k.p12 and place it into ~/.ssh/uva/user.p12

It is important for us to rename this key to user.p12
so we have a simpler way of identifying it and writing this documentation.

Now convert the keys and certificates with the following commands

```bash
cd ~/.ssh/uva
openssl pkcs12 -in user.p12 -nocerts -nodes -out user.key
openssl pkcs12 -in user.p12 -clcerts -nokeys -out user.crt
openssl x509 -inform DER -in usher.cer -out usher.crt
```


Now your UVA directory should have the following files in it.

```
ls ~/.ssh/uva/
user.crt  user.key  user.p12  usher.cer  usher.crt
```


### Install and using the command

You can now use the cloudmesh cms vpn command.


```bash
$ pip install cloudmesh-vpn
$ cms help
```

To connect use 


```bash
$ cms vpn connect 
```


To disconnect

```bash
$ cms vpn disconnect
```

## Acknowledgments

This work was in part funded by the NSF
CyberTraining: CIC: CyberTraining for Students and Technologies
from Generation Z with the award numbers 1829704 and 2200409.



## Manual Page

<!-- START-MANUAL -->
```
Command vpn
===========

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


```
<!-- STOP-MANUAL -->
