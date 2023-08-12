Docker is necessary.

# UFL

```bash
make build VPN=ufl
make shell VPN=ufl
# one more time
make shell VPN=ufl
python3 setup.py
# mkdir /app/remote_mount
# sshfs me@mycoolschool.edu:/home/me /app/remote_mount
```

# UVA

To get a certificate for your device, go to

    https://cloud.securew2.com/public/82116/limited/?device=Unknown

Fill it out, remember the passphrase that you choose as you will need
to enter it later, and download the key by clicking P12

Also go to

    https://download.its.virginia.edu/local-auth/universal/usher.cer

This cannot be automated by wget, as authentication is needed,
so download it through web browser.

```bash
# using windows downloads path... change accordingly if other os...
cp ~/Downloads/*.p12 user.p12
cp ~/Downloads/usher.cer .
make build VPN=uva
make shell VPN=uva
# one more time
make shell VPN=uva
mkdir -p ~/.ssh/uva/
openssl pkcs12 -in user.p12 -nocerts -nodes -out ~/.ssh/uva/user.key
openssl pkcs12 -in user.p12 -clcerts -nokeys -out ~/.ssh/uva/user.crt
openssl x509 -inform DER -in usher.cer -out ~/.ssh/uva/usher.crt

cp *.cer ~/.ssh/uva/
cms vpn connect
# error may happen, but you are likely connected
curl icanhazip.com
```

# Dual vpn

It is now possible to connect to two HPC, one in each terminal, by using
each vpn's `make shell`