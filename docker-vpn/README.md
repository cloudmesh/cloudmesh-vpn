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

# Use IDE

(windows only)
download vcxsrv. you need chocolatey.

```bash
choco install vcxsrv -y
```

(mac only)
download xquartz. you need homebrew.
```bash
brew install --cask xquartz
```

windows:
run vcxsrv by typing xlaunch in windows start
and make sure to check `disable access control`
(use defaults for all other options)

In Git Bash, while not inside any docker environment,
run `echo $(route.exe print | grep 0.0.0.0 | head -1 | awk '{print $4}'):0.0`
then copy that value. 

go to the docker container with corresponding `make shell`
command above. then `export DISPLAY=theValueYouJustWroteDown`

To start visual studio code,

```bash
export DONT_PROMPT_WSL_INSTALL=y
code --no-sandbox --user-data-dir=/app/vscode-1
# and then in the other docker...
code --no-sandbox --user-data-dir=/app/vscode-2
```

