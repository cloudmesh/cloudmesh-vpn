# cms vpn

## Organizations

### Functional

<div style="display: flex; align-items: flex-start;">
    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/University_of_Virginia_Rotunda_logo.svg/2007px-University_of_Virginia_Rotunda_logo.svg.png" alt="fiu" width="100" style="margin-right: 10px;"/>
    <img src="https://brand.fiu.edu/_assets/images/fiu-alone.png" alt="fiu" width="200" style="margin-right: 10px;"/>
    <img src="https://www.ufl.edu/wp-content/uploads/sites/5/2022/12/UF-logo-500x500-1.png" alt="uf" width="100" style="margin-left: 10px;"/>
</div>

### Untested

* famu
* nyu
* uci
* gmu
* olemiss
* sc

## Install

### Windows

Open powershell as administrator.

Execute these commands:

```bash
python --version
```

If no number shows up, then you do not have Python. Download it from https://www.python.org/downloads/ and check `Add python.exe to PATH` in the installer.

If Python was just installed, open a new powershell as administrator.
Either way, execute:

```bash
mkdir ~/cm & cd ~/cm
pip install cloudmesh-installer
cloudmesh-installer get vpn
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

To disconnect from current VPN, run

```bash
cms vpn disconnect
```

To see info regarding your connection, run

```bash
cms vpn info
```

## Linux

### Requirements

On Linux we use the command `openconnect`. To check if it is available please use

```bash
$ which openconnect
```

If it is not available, you can install it un Ubuntu with 

```bash
$ sudo apt install openssl
$ sudo apt install openconnect
$ sudo apt install network-manager-openconnect
```
and in case you use gnoe also:

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
mkdir -p You will receive a file ending in .p12. In this example we will assume it is named mst3k.p12.
cd ~/.ssh/uva
wget https://download.its.virginia.edu/local-auth/universal/usher.cer
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
openssl pkcs12 -in mst3k.p12 -nocerts -nodes -out mst3k.key
openssl pkcs12 -in mst3k.p12 -clcerts -nokeys -out mst3k.crt
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

To show the status use

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