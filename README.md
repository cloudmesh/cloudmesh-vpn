# cms vpn

## Windows

This requires installation of the Cisco AnyConnect
Secure Mobility Client located at <https://in.virginia.edu/vpn>.

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

```
ls ~/.ssh/uva/
user.crt  user.key  user.p12  usher.cer  usher.crt
```

Now I need to develop a commandline tool with open connect as it is already installed on ubuntu.

So I can say what you see next. HOwever I still get an error and the connection hangs. I could possibly put that in & but the dev seems wrong. DO you know how to avoid this?


```
sudo openconnect -b -v  --protocol=anyconnect --cafile="$HOME/.ssh/uva/usher.cer" --sslkey="$HOME/.ssh/uva/user.key" --certificate="$HOME/.ssh/uva/user.crt" --passtos  -b uva-anywhere-1.itc.virginia.edu &> /dev/null 2>&1
```


kill:

```
# sudo kill -9 `pgrep openconnect`
sudo pkill -SIGINT openconnect
```