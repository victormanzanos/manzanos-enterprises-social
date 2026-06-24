#!/usr/bin/env python3
"""Manzanos Enterprises — refresh del long-lived Instagram access token.

Los tokens de Instagram Graph API duran ~60 días. Este script los renueva
ANTES de que caduquen (LaunchAgent semanal, domingos). Guarda el nuevo token
en el Keychain sobrescribiendo MANZANOSENTERPRISES_IG_ACCESS_TOKEN.

Endpoint: GET https://graph.instagram.com/refresh_access_token
  ?grant_type=ig_refresh_token&access_token=<TOKEN_ACTUAL>
"""
import datetime, json, os, subprocess, urllib.request, urllib.parse

SECRETS = os.path.expanduser("~/Code/CyberSecurity/scripts/secrets.sh")
LOG     = os.path.expanduser("~/manzanos-enterprises-social/token-refresh.log")

def secret(n):       return subprocess.check_output([SECRETS, "get", n]).decode().strip()
def set_secret(n, v): subprocess.run([SECRETS, "set", n, v], check=True)

def main():
    tok = secret("MANZANOSENTERPRISES_IG_ACCESS_TOKEN")
    params = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": tok})
    url = f"https://graph.instagram.com/refresh_access_token?{params}"
    with urllib.request.urlopen(url) as r:
        body = json.load(r)
    new = body.get("access_token")
    exp = body.get("expires_in")
    line = f"[{datetime.datetime.now().isoformat(timespec='seconds')}] "
    if new:
        set_secret("MANZANOSENTERPRISES_IG_ACCESS_TOKEN", new)
        line += f"OK · nuevo token guardado · expira en {exp}s (~{int(exp)//86400} días)"
    else:
        line += f"FALLO · respuesta: {json.dumps(body)[:300]}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

if __name__ == "__main__":
    main()
