#!/usr/bin/env python3
"""Manzanos Enterprises — refresh del long-lived Instagram access token.

Los tokens de Instagram Graph API duran ~60 días. Este script los renueva
ANTES de que caduquen (LaunchAgent semanal, domingos). Guarda el nuevo token
en el Keychain sobrescribiendo MANZANOSENTERPRISES_IG_ACCESS_TOKEN.

Endpoint: GET https://graph.instagram.com/refresh_access_token
  ?grant_type=ig_refresh_token&access_token=<TOKEN_ACTUAL>
"""
import datetime, json, os, subprocess, time, urllib.request, urllib.parse

SECRETS = os.path.expanduser("~/Code/CyberSecurity/scripts/secrets.sh")
LOG     = os.path.expanduser("~/manzanos-enterprises-social/token-refresh.log")

# WHY: Meta devuelve 500 transitorios con frecuencia (fallos 2026-07-05 y 2026-07-19).
# Sin reintento, un 500 aislado tumbaba el refresh semanal entero. 4 intentos con
# backoff 15/60/240s cubren de sobra un bache momentáneo sin alargar el LaunchAgent.
ATTEMPTS = 4
BACKOFF  = [15, 60, 240]
TIMEOUT  = 30  # s — el endpoint responde en <2s; 30 corta cuelgues de red sin falsos negativos

def secret(n):       return subprocess.check_output([SECRETS, "get", n]).decode().strip()
def set_secret(n, v): subprocess.run([SECRETS, "set", n, v], check=True)

def log_line(line):
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def fetch(url):
    """Devuelve el body parseado, o None tras agotar reintentos. NUNCA lanza."""
    last = None
    for i in range(ATTEMPTS):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
                return json.load(r)
        except Exception as e:  # WHY: HTTPError, URLError, DNS, timeout, JSON roto — ninguno debe matar el script
            last = e
            if i < ATTEMPTS - 1:
                time.sleep(BACKOFF[i])
    log_line(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] "
             f"FALLO · {ATTEMPTS} intentos agotados · último error: {type(last).__name__}: {str(last)[:200]}")
    return None

def main():
    tok = secret("MANZANOSENTERPRISES_IG_ACCESS_TOKEN")
    params = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": tok})
    url = f"https://graph.instagram.com/refresh_access_token?{params}"
    body = fetch(url)
    if body is None:
        # WHY: el token vigente sigue siendo válido ~60 días; el refresh del domingo
        # siguiente reintenta. Salir en 0 evita que el LaunchAgent marque error ruidoso.
        return
    new = body.get("access_token")
    exp = body.get("expires_in")
    line = f"[{datetime.datetime.now().isoformat(timespec='seconds')}] "
    if new:
        set_secret("MANZANOSENTERPRISES_IG_ACCESS_TOKEN", new)
        line += f"OK · nuevo token guardado · expira en {exp}s (~{int(exp)//86400} días)"
    else:
        line += f"FALLO · respuesta: {json.dumps(body)[:300]}"
    log_line(line)

if __name__ == "__main__":
    main()
