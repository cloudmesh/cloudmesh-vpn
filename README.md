# cms vpn

## Windows

This requires installation of the Cisco
Secure Client located at <https://in.virginia.edu/vpn>.

To connect to the UVA Anywhere VPN, run

```bash
cms vpn connect
```

To disconnect from UVA Anywhere, run

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
