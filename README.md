# Manzanos Enterprises — Instagram Automation (@manzanosenterprises)

Sistema de publicación automática clonado de `~/palacio-social`, adaptado a lo
que pediste: **frases motivacionales del corporativo + destacados del blog**, en
imágenes con **marco dorado y el logo de Manzanos Enterprises abajo**, publicando
**un día sí, un día no, a hora distinta cada vez** para no parecer automatización.

## Cómo funciona (en una frase)

Cada hora entre las 9:00 y las 20:00 (hora del Mac), `daily_engine.py` mira si
hoy toca (días `ordinal%2==0`, paridad **opuesta** a Palacio) y si ya ha llegado
la **hora objetivo pseudo-aleatoria del día**; cuando toca, elige la siguiente
tarjeta (frase o destacado de blog), baraja hashtags, y publica post + story vía
Instagram Graph API leyendo las imágenes del repo público. Luego manda un email
resumen a victor@manzanos.com.

## Contenido

- **80 frases** de emprendimiento del corporativo de la web (`/rsc` — "Words That
  Drive Us"), en español sobre fondo charcoal con marco dorado y logo.
- **16 destacados del blog** de manzanosenterprises.com/news (foto de la web
  oscurecida + título + gancho + "link en bio").
- Alterna: **1 de cada 3** publicaciones es un destacado del blog; el resto, frases.
- **Idioma alterno**: un post en español, el siguiente en inglés, y así. Cada post
  va en **UN solo idioma** (imagen + caption + hashtags + URL coherentes). Lo decide
  la paridad del contador: post par → ES, post impar → EN.
- El logo lleva una **placa oscura** detrás con zona de seguridad: el texto nunca
  se solapa con el logo, en ningún idioma ni formato.
- Fuente única de verdad: `content.py`. Para añadir frases o artículos, edítalo
  y regenera (`python3 make_me.py batch`).

## Estructura

```
~/manzanos-enterprises-social/
├── content.py            # 80 frases (ES/EN) + 16 destacados de blog — single source of truth
├── make_me.py            # genera tarjetas 1080×1350 (post) y 1080×1920 (story) con marco dorado + logo
├── daily_engine.py       # motor diario (decide, publica, email)
├── refresh_token.py      # renueva el token de IG (domingos)
├── run_daily.sh / run_refresh.sh        # wrappers para los LaunchAgents
├── com.manzanosenterprises.dailyig.plist           # LaunchAgent — cada hora 9–20
├── com.manzanosenterprises.igtokenrefresh.plist    # LaunchAgent — domingos 10:15
├── posts/                # 192 JPG · q##-es/-en (frases) + b##-es/-en (blog)
├── stories/              # 192 JPG (versión 1080×1920, -st)
├── drop/                 # OPCIONAL: deja aquí una foto real y se publica intercalada
└── .daily_state.json     # estado de rotación (se crea solo)
```

## Cadencia y hora

- **Un día sí, un día no**: publica cuando `today.toordinal() % 2 == 0`.
  Palacio usa `== 1`, así que **nunca coinciden** (reduce huella anti-bot).
- **Hora distinta cada día**: `todays_target_hour()` deriva una hora en `[9, 20]`
  con seed = nº de día → estable durante la jornada, distinta de un día a otro.
- Para cambiar la franja o la cadencia, edita en `daily_engine.py`:
  `ME_CYCLE_DIV/ME_CYCLE_DAY`, `PUBLISH_HOUR_MIN/MAX`, `BLOG_EVERY`.

---

## SETUP — pasos que tienes que hacer TÚ una vez (Claude no puede)

### 1. Cuenta de Instagram profesional (Business)
En @manzanosenterprises: Ajustes → Cuenta → Cambiar a cuenta profesional →
**Empresa**. Vincúlala a una página de Facebook "Manzanos Enterprises".

### 2. Meta App
- https://developers.facebook.com/apps/ → Create App → tipo **Business** →
  nombre `Manzanos Enterprises Social`.
- Añade producto **Instagram** ("API setup with Instagram login") y conecta
  @manzanosenterprises.
- **Déjala en modo Development** (pasar a Live invalida los tokens).

### 3. Token largo + IG Account ID
```bash
# long-lived token (60 días)
curl -sG 'https://graph.instagram.com/access_token' \
  --data-urlencode 'grant_type=ig_exchange_token' \
  --data-urlencode 'client_secret=<APP_SECRET>' \
  --data-urlencode 'access_token=<SHORT_TOKEN>'
# IG account id
curl -sG 'https://graph.instagram.com/me' \
  --data-urlencode 'fields=id,username' \
  --data-urlencode 'access_token=<LONG_TOKEN>'
```

### 4. Guardar credenciales en el Keychain
```bash
~/Code/CyberSecurity/scripts/secrets.sh set MANZANOSENTERPRISES_IG_ACCESS_TOKEN
~/Code/CyberSecurity/scripts/secrets.sh set MANZANOSENTERPRISES_IG_ACCOUNT_ID
```
(El SMTP para el email ya está: `MANZANOS_SMTP_PASSWORD`.)

### 5. Repo público en GitHub (para que Meta lea las imágenes)
```bash
gh repo create victormanzanos/manzanos-enterprises-social --public \
  --description "Image hosting for @manzanosenterprises Instagram automation"
cd ~/manzanos-enterprises-social
git init -b main
git add content.py make_me.py daily_engine.py refresh_token.py run_*.sh *.plist README.md .gitignore posts/ stories/
git commit -m "Initial: 80 quote cards + 16 blog cards (gold frame + ME logo)"
git remote add origin git@github.com:victormanzanos/manzanos-enterprises-social.git
git push -u origin main
# comprueba acceso público:
curl -sI https://raw.githubusercontent.com/victormanzanos/manzanos-enterprises-social/main/posts/q00-es.jpg | head -1   # → HTTP/2 200
```

### 6. Test sin publicar, luego primer post manual
```bash
DRY=1   python3 ~/manzanos-enterprises-social/daily_engine.py    # preview
FORCE=1 python3 ~/manzanos-enterprises-social/daily_engine.py    # publica AHORA (salta guardias)
```

### 7. Instalar los LaunchAgents
```bash
cp ~/manzanos-enterprises-social/com.manzanosenterprises.dailyig.plist        ~/Library/LaunchAgents/
cp ~/manzanos-enterprises-social/com.manzanosenterprises.igtokenrefresh.plist ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.manzanosenterprises.dailyig.plist
launchctl load -w ~/Library/LaunchAgents/com.manzanosenterprises.igtokenrefresh.plist
launchctl list | grep manzanosenterprises
```

---

## OPERACIÓN

| Acción | Comando |
|---|---|
| Preview sin publicar | `DRY=1 python3 ~/manzanos-enterprises-social/daily_engine.py` |
| Publicar AHORA | `FORCE=1 python3 ~/manzanos-enterprises-social/daily_engine.py` |
| Regenerar TODAS las imágenes | `python3 ~/manzanos-enterprises-social/make_me.py batch` |
| Regenerar 1 frase / 1 blog | `make_me.py quote <i>` · `make_me.py blog <i>` |
| Renovar token a mano | `python3 ~/manzanos-enterprises-social/refresh_token.py` |
| Ver estado | `cat ~/manzanos-enterprises-social/.daily_state.json` |
| Pausar | `launchctl unload ~/Library/LaunchAgents/com.manzanosenterprises.dailyig.plist` |
| Reanudar | `launchctl load -w ~/Library/LaunchAgents/com.manzanosenterprises.dailyig.plist` |

**Foto real puntual**: deja un JPG (y opcional `.txt` con su caption) en `drop/`.
Se publica intercalado (1 cada 6) y se archiva en `drop/published/`.

**Si regeneras imágenes**, vuelve a subirlas al repo:
```bash
cd ~/manzanos-enterprises-social && git add posts/ stories/ content.py && git commit -m "update" && git push
```

## Seguridad
- Tokens **solo** en Keychain vía `secrets.sh` — nunca en código.
- El repo público contiene **solo** código e imágenes (`.gitignore` excluye estado/logs/drop).

## Troubleshooting
| Síntoma | Causa | Fix |
|---|---|---|
| HTTPError 400 `code:190` | token caducado | regenerar + `secrets.sh set MANZANOSENTERPRISES_IG_ACCESS_TOKEN` |
| `code:200` API blocked | Meta detectó automatización | NO reintentar; pausa 24–48h |
| `container not ready` | Meta no descarga la imagen | `curl -I` a la URL raw; esperar 10 min (CDN) |
| "Aún no es la hora objetivo" | normal | publicará en un disparo posterior del día |
| email no llega | SMTP caducado | `secrets.sh set MANZANOS_SMTP_PASSWORD` |
