# cms vpn

## Linux

```
ls ~/.ssh/uva/
user.crt  user.key  user.p12  usher.cer  usher.crt
```

Now I need to develop a commandline tool with open connect as it is already installed on ubuntu.

So I can say what you see next. HOwever I still get an error and the connection hangs. I could possibly put that in & but the dev seems wrong. DO you know how to avoid this?


```
$sudo openconnect  --protocol=anyconnect --cafile="$HOME/.ssh/uva/usher.cer" --sslkey="$HOME/.ssh/uva/user.key" --certificate="$HOME/.ssh/uva/user.crt" --user=UVAUSER uva-anywhere-1.itc.virginia.edu
```

we can leave of --user

```
$sudo openconnect  --protocol=anyconnect --cafile="$HOME/.ssh/uva/usher.cer" --sslkey="$HOME/.ssh/uva/user.key" --certificate="$HOME/.ssh/uva/user.crt" uva-anywhere-1.itc.virginia.edu
```

kill:

```
sudo kill -9 `pgrep openconnect`
```