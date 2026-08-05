#!/usr/bin/env python3
"""Manzanos Enterprises — DAILY ENGINE para @manzanosenterprises.

Clonado del motor probado de @palaciodemanzanos, adaptado a lo que pidió Victor:

- **Un día sí, un día no**, a una **hora distinta cada vez** (franja 9:00–20:00
  hora local del Mac) para que Meta no lo lea como automatización. La hora del
  día es pseudo-aleatoria pero estable durante la jornada (seed = nº de día),
  así varía entre publicaciones pero el motor es idempotente (1 post/día).
- **Paridad opuesta a Palacio**: Palacio publica los días `ordinal%2==1`; este
  publica los `ordinal%2==0`, para no coincidir nunca con la otra cuenta IG y
  repartir la huella.
- **Contenido**: alterna FRASES motivacionales del corporativo (las 80 de la web)
  con DESTACADOS del blog de manzanosenterprises.com. 1 de cada `BLOG_EVERY`
  publicaciones es un destacado de blog; el resto, frases.
- Imágenes con **marco dorado + logo Manzanos Enterprises abajo** (make_me.py),
  alojadas en el repo público para que Meta las pueda leer.
- Caption **bilingüe ES/EN**, hashtags rotados (anti-spam), jitter, email resumen.

Variables de entorno:
  DRY=1     → preview sin publicar ni email (no necesita credenciales)
  FORCE=1   → salta la guardia de día/hora (publica ahora)
"""
import datetime, json, os, random, re, ssl, smtplib, subprocess, time
import urllib.request, urllib.parse, urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

import content

# ──────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────
LOCAL    = os.path.expanduser("~/manzanos-enterprises-social")
SECRETS  = os.path.expanduser("~/Code/CyberSecurity/scripts/secrets.sh")
STATE    = os.path.join(LOCAL, ".daily_state.json")
RAW      = "https://raw.githubusercontent.com/victormanzanos/manzanos-enterprises-social/main"
BASE     = "https://graph.instagram.com/v23.0"
REPO     = "victormanzanos/manzanos-enterprises-social"
H        = "#ManzanosEnterprises"  # brand hashtag — siempre se mantiene

# Cadencia: 1 día sí, 1 día no. Publica cuando ordinal%DIV==DAY.
# DAY=0 → paridad OPUESTA a Palacio (que usa DAY=1) → nunca coinciden.
ME_CYCLE_DIV = 2
ME_CYCLE_DAY = 0

# Hora de publicación: pseudo-aleatoria por día dentro de [MIN, MAX] (hora local).
# El LaunchAgent dispara cada hora en esa franja; el motor publica en el primer
# disparo a partir de la hora objetivo del día. Resultado: hora distinta cada día.
PUBLISH_HOUR_MIN = 9
PUBLISH_HOUR_MAX = 20

# 1 de cada N publicaciones es un destacado del blog; el resto, frases.
BLOG_EVERY = 3

# Foto real intercalada opcional (drop folder) — como en Palacio.
DROP_DIR = os.path.join(LOCAL, "drop")
DONE_DIR = os.path.join(DROP_DIR, "published")
IMG_EXT  = (".jpg", ".jpeg", ".png")
REAL_EVERY = 6  # 1 foto real cada 6 publicaciones de marca, si hay en el drop

# Pools de hashtags por idioma (además del brand). Cada post va en UN idioma.
HASHTAGS_ES = [
    "#Emprendimiento", "#Emprendedores", "#Liderazgo", "#Negocios", "#Exito",
    "#Motivacion", "#Mentalidad", "#Estrategia", "#Inversion", "#EmpresaFamiliar",
    "#VisionEmpresarial", "#CrecimientoEmpresarial", "#Empresa", "#Legado",
]
HASHTAGS_EN = [
    "#Entrepreneurship", "#Entrepreneur", "#Leadership", "#Business", "#Success",
    "#Motivation", "#Mindset", "#Strategy", "#Investing", "#FamilyBusiness",
    "#BusinessVision", "#Growth", "#LongTermThinking", "#Legacy",
]
def hashtags(lang):
    return HASHTAGS_ES if lang == "es" else HASHTAGS_EN

DRY = os.environ.get("DRY") == "1"

# Credenciales — lazy load para que DRY=1 funcione sin credenciales.
TOK = None
IGID = None
def _secret(n):
    return subprocess.check_output([SECRETS, "get", n]).decode().strip()
def ensure_creds():
    global TOK, IGID
    if TOK is None:
        TOK  = _secret("MANZANOSENTERPRISES_IG_ACCESS_TOKEN")
        IGID = _secret("MANZANOSENTERPRISES_IG_ACCOUNT_ID")


# ──────────────────────────────────────────────────────────────────────────
# STATE
# ──────────────────────────────────────────────────────────────────────────
def state():
    s = json.load(open(STATE)) if os.path.exists(STATE) else {}
    s.setdefault("post", 0)        # contador global (decide frase vs blog)
    s.setdefault("quote_idx", 0)   # rotación de frases
    s.setdefault("blog_idx", 0)    # rotación de blog
    s.setdefault("since_real", 0)
    return s
def save_state(s):
    json.dump(s, open(STATE, "w"))


def pick_special(key, sd):
    """Publicación de un día especial de España (content.SPECIAL_DAYS).
    Tarjeta temática en español, mismas rutas/naming sp-<key> que make_me.py."""
    return {
        "kind": "special", "idx": key, "lang": "es",
        "caption": sd["caption"],
        "post_url":  f"{RAW}/posts/sp-{key}.jpg",
        "story_url": f"{RAW}/stories/sp-{key}-st.jpg",
        "post_file":  f"posts/sp-{key}.jpg",
        "story_file": f"stories/sp-{key}-st.jpg",
        "label": f"Día especial · {sd['label']}",
    }


def pick_next(s):
    """Decide la siguiente publicación. Devuelve dict con kind/lang/caption/urls/labels.

    Idioma alterno: post par → español, post impar → inglés. Así unos posts
    salen en español y otros en inglés, cada uno en UN solo idioma."""
    lang = "es" if s["post"] % 2 == 0 else "en"
    if s["post"] % BLOG_EVERY == (BLOG_EVERY - 1):
        idx = s["blog_idx"] % content.blog_count()
        b = content.BLOG[idx]
        return {
            "kind": "blog", "idx": idx, "lang": lang,
            "caption": blog_caption(b, lang),
            "post_url":  f"{RAW}/posts/b{idx:02d}-{lang}.jpg",
            "story_url": f"{RAW}/stories/b{idx:02d}-{lang}-st.jpg",
            "post_file":  f"posts/b{idx:02d}-{lang}.jpg",
            "story_file": f"stories/b{idx:02d}-{lang}-st.jpg",
            "label": f"Blog «{b['title_es']}» [{lang.upper()}]",
        }
    else:
        idx = s["quote_idx"] % content.quote_count()
        es, en = content.QUOTES[idx]
        return {
            "kind": "quote", "idx": idx, "lang": lang,
            "caption": quote_caption(es, en, lang),
            "post_url":  f"{RAW}/posts/q{idx:02d}-{lang}.jpg",
            "story_url": f"{RAW}/stories/q{idx:02d}-{lang}-st.jpg",
            "post_file":  f"posts/q{idx:02d}-{lang}.jpg",
            "story_file": f"stories/q{idx:02d}-{lang}-st.jpg",
            "label": f"Frase {idx + 1}/{content.quote_count()} [{lang.upper()}]",
        }


# ──────────────────────────────────────────────────────────────────────────
# CAPTIONS (bilingües ES/EN) + rotación de hashtags
# ──────────────────────────────────────────────────────────────────────────
def quote_caption(es, en, lang):
    if lang == "es":
        return (
            f"«{es}»\n\n"
            f"— Manzanos Enterprises · Grupo familiar desde 1890\n\n"
            f"{H} " + " ".join(HASHTAGS_ES[:8])
        )
    return (
        f"“{en}”\n\n"
        f"— Manzanos Enterprises · A family-owned group since 1890\n\n"
        f"{H} " + " ".join(HASHTAGS_EN[:8])
    )

def blog_caption(b, lang):
    if lang == "es":
        url = f"{content.SITE}/es/news/{b['slug']}"
        return (
            f"📈 {b['title_es']}\n\n"
            f"{b['hook_es']}\n\n"
            f"Lee el artículo completo 🔗 link en bio\n{url}\n\n"
            f"{H} " + " ".join(HASHTAGS_ES[:8])
        )
    url = f"{content.SITE}/en/news/{b['slug']}"
    return (
        f"📈 {b['title_en']}\n\n"
        f"{b['hook_en']}\n\n"
        f"Read the full article 🔗 link in bio\n{url}\n\n"
        f"{H} " + " ".join(HASHTAGS_EN[:8])
    )

def rotate_caption(cap, lang="es"):
    """Mantiene cuerpo + brand tag; baraja el resto de hashtags y varía el nº.
    Evita que Meta detecte el mismo bloque fijo de hashtags cada día."""
    body, tags = [], []
    for ln in cap.split("\n"):
        toks = ln.split()
        if toks and all(t.startswith("#") for t in toks):
            tags.extend(toks)
        else:
            body.append(ln)
    if not tags:
        return cap
    brand = [t for t in tags if t.lower() == H.lower()]
    rest  = list(dict.fromkeys(t for t in tags if t.lower() != H.lower()))
    extra = [t for t in hashtags(lang) if t not in rest]
    random.shuffle(rest); random.shuffle(extra)
    pool = rest + extra
    k = random.randint(5, 9)
    chosen = brand + pool[:k]
    random.shuffle(chosen)
    return "\n".join(body).rstrip() + "\n\n" + " ".join(chosen)


# ──────────────────────────────────────────────────────────────────────────
# FOTO REAL opcional (drop folder)
# ──────────────────────────────────────────────────────────────────────────
def real_collect():
    if not os.path.isdir(DROP_DIR):
        return []
    out = []
    for name in sorted(os.listdir(DROP_DIR)):
        path = os.path.join(DROP_DIR, name)
        if not os.path.isfile(path):
            continue
        base, ext = os.path.splitext(name)
        if ext.lower() not in IMG_EXT:
            continue
        cap_file = os.path.join(DROP_DIR, base + ".txt")
        cap = open(cap_file, encoding="utf-8").read().strip() if os.path.exists(cap_file) else \
            f"Manzanos Enterprises\n\n{H} " + " ".join(HASHTAGS_ES[:6])
        out.append((path, cap))
    return out

import base64, hashlib
def gh_upload(local_path, remote_name):
    with open(local_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()
    remote_path = f"drop/{remote_name}"
    sha = None
    probe = subprocess.run(["gh", "api", f"/repos/{REPO}/contents/{remote_path}"],
                           capture_output=True, text=True)
    if probe.returncode == 0:
        try:    sha = json.loads(probe.stdout).get("sha")
        except: sha = None
    args = ["gh", "api", "--method", "PUT", f"/repos/{REPO}/contents/{remote_path}",
            "-f", f"message=Add drop photo {remote_name}", "-f", f"content={content_b64}"]
    if sha: args += ["-f", f"sha={sha}"]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh upload failed: {r.stderr.strip()[:300]}")
    return f"{RAW}/{remote_path}"

def archive_real(path):
    os.makedirs(DONE_DIR, exist_ok=True)
    name = os.path.basename(path)
    os.rename(path, os.path.join(DONE_DIR, name))
    cap_file = os.path.join(DROP_DIR, os.path.splitext(name)[0] + ".txt")
    if os.path.exists(cap_file):
        os.rename(cap_file, os.path.join(DONE_DIR, os.path.basename(cap_file)))


# ──────────────────────────────────────────────────────────────────────────
# INSTAGRAM GRAPH API
# ──────────────────────────────────────────────────────────────────────────
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
# WHY: 3 intentos cubren un corte de red puntual (ConnectionResetError, timeout,
# TLS/DNS caído) sin colgar el run; más intentos apenas ayudan y alargan el proceso.
API_MAX_TRIES = 3
API_BACKOFF   = 2   # segundos base; espera 2s tras el 1er fallo, 4s tras el 2º (exponencial)
# WHY: sin timeout, un socket colgado bloquea el run indefinidamente. 30s es holgado
# para la Graph API y permite que el reintento entre en juego ante un cuelgue.
API_TIMEOUT   = 30

def api(path, params, method="POST"):
    data = urllib.parse.urlencode(params).encode()
    hdr  = {"User-Agent": UA}
    if method == "GET":
        req = urllib.request.Request(f"{BASE}/{path}?{data.decode()}", headers=hdr)
    else:
        req = urllib.request.Request(f"{BASE}/{path}", data=data, method="POST", headers=hdr)
    last_err = None
    for attempt in range(API_MAX_TRIES):
        try:
            with urllib.request.urlopen(req, timeout=API_TIMEOUT) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            # Respuesta del servidor (4xx/5xx): no es fallo de transporte → no reintentar.
            return {"_http_error": e.code, "body": e.read().decode()}
        except (urllib.error.URLError, OSError) as e:
            # WHY: ConnectionResetError, timeouts, DNS/TLS caído = transitorio → reintentar.
            # Incidencia 2026-07-01: un ConnectionResetError sin captura tumbó todo el run.
            last_err = e
            if attempt < API_MAX_TRIES - 1:
                time.sleep(API_BACKOFF * (2 ** attempt))
    return {"_net_error": str(last_err)}

def wait_ready(cid):
    for _ in range(20):
        st = api(cid, {"fields": "status_code", "access_token": TOK}, "GET").get("status_code")
        if st in ("FINISHED", "ERROR", "EXPIRED"):
            return st
        time.sleep(4)
    return "TIMEOUT"

def publish_image(url, caption=None, story=False):
    ensure_creds()
    p = {"image_url": url, "access_token": TOK}
    if story:   p["media_type"] = "STORIES"
    if caption: p["caption"]    = caption
    c = api(f"{IGID}/media", p); cid = c.get("id")
    if not cid:
        return {"error": c}
    if wait_ready(cid) != "FINISHED":
        return {"error": "container not ready"}
    r = api(f"{IGID}/media_publish", {"creation_id": cid, "access_token": TOK})
    mid = r.get("id")
    if not mid:
        return {"error": r}
    return api(mid, {"fields": "permalink", "access_token": TOK}, "GET")


# ──────────────────────────────────────────────────────────────────────────
# EMAIL RESUMEN
# ──────────────────────────────────────────────────────────────────────────
def email_summary(html, post_path, story_path, subject):
    pw = _secret("MANZANOS_SMTP_PASSWORD")
    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"]    = "assistant@manzanosenterprises.com"
    msg["To"]      = "victor@manzanos.com"
    msg.attach(MIMEText(html, "html", "utf-8"))
    for cid, path in (("postimg", post_path), ("storyimg", story_path)):
        try:
            with open(path, "rb") as f:
                img = MIMEImage(f.read())
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=os.path.basename(path))
            msg.attach(img)
        except Exception as e:
            print("attach failed", path, e)
    with smtplib.SMTP_SSL("manzanosenterprises-com.correoseguro.dinaserver.com", 465,
                          context=ssl.create_default_context()) as srv:
        srv.login("assistant@manzanosenterprises.com", pw)
        srv.send_message(msg)


# ──────────────────────────────────────────────────────────────────────────
# HORA OBJETIVO DEL DÍA (pseudo-aleatoria, estable durante la jornada)
# ──────────────────────────────────────────────────────────────────────────
def todays_target_hour(ordinal):
    # WHY: seed determinista por día → misma hora objetivo en todos los disparos
    # del día, pero distinta de un día a otro. Rompe el patrón horario fijo.
    rng = random.Random((ordinal * 2654435761) & 0xFFFFFFFF)
    return rng.randint(PUBLISH_HOUR_MIN, PUBLISH_HOUR_MAX)


def last_due_publish_date(today):
    """Fecha del día de publicación esperado más reciente en o antes de `today`.
    En cadencia día-sí-día-no es hoy (si toca) o ayer. Se compara con
    state['last_date'] para detectar un día de publicación perdido (Mac apagado)."""
    o = today.toordinal()
    while o % ME_CYCLE_DIV != ME_CYCLE_DAY:
        o -= 1
    return datetime.date.fromordinal(o)


# ──────────────────────────────────────────────────────────────────────────
# ERP SOCIAL HUB — controles del equipo (agolfcars.com/erp → vista Social)
# ──────────────────────────────────────────────────────────────────────────
# Laura o Victor pueden BLOQUEAR una tarjeta o CORREGIR su caption desde el ERP
# (sección Social, cuenta @manzanosenterprises). Este motor consulta esos
# controles justo ANTES de publicar y los aplica a la rotación de marca.
# Fail-open by design: sin red, sin secreto o con respuesta rara → la rotación
# sigue intacta (nunca bloquea una publicación por un fallo del hub). (2026-08-05)
def _hub_controls():
    import urllib.request as _ur, urllib.parse as _up
    try:
        sec = subprocess.check_output([SECRETS, "get", "AGC_SOCIAL_SYNC_SECRET"],
                                      timeout=15).decode().strip()
        if not sec:
            return set(), {}
        q = _up.urlencode({"handle": "manzanosenterprises", "secret": sec})
        req = _ur.Request("https://agolfcars.com/api/social-sync.php?" + q,
                          headers={"User-Agent": "Mozilla/5.0 (social-engine)"})
        with _ur.urlopen(req, timeout=8) as r:
            d = json.load(r)
        ov = d.get("overrides") or {}
        return set(d.get("blocked") or []), (ov if isinstance(ov, dict) else {})
    except Exception:
        return set(), {}


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────
def main():
    s = state()
    today = datetime.date.today()
    today_s = str(today)

    # ¿Es hoy un día especial de España? (12-oct, Navidad, Nochevieja, Año Nuevo…)
    # WHY: en estas fechas SIEMPRE se publica el saludo temático, aunque toque
    # "día de descanso": salta la cadencia día-sí-día-no (guarda más abajo) y
    # tiene prioridad sobre la rotación de frases/blog y sobre la foto del drop.
    special = content.special_for(today.month, today.day)
    is_special = bool(special)

    real_items = [] if is_special else real_collect()
    do_real = bool(real_items) and s.get("since_real", 0) >= REAL_EVERY

    if is_special:
        nxt = pick_special(today.strftime("%m%d"), special)
        cap = nxt["caption"]   # pie fijo temático — no se baraja (mantiene los hashtags festivos)
    else:
        nxt = pick_next(s)
        cap = rotate_caption(nxt["caption"], nxt["lang"])

    print(f"NEXT = {nxt['kind'].upper()} · {nxt['label']}")
    print(f"POST:  {nxt['post_url']}")
    print(f"STORY: {nxt['story_url']}")
    print(f"--- CAPTION ---\n{cap}\n---")
    if do_real:
        print(f"(esta vez tocaría FOTO REAL del drop: {os.path.basename(real_items[0][0])})")

    if DRY:
        print("DRY RUN — nada publicado.")
        return

    forced = os.environ.get("FORCE") == "1"
    is_publish_today = today.toordinal() % ME_CYCLE_DIV == ME_CYCLE_DAY

    # Catch-up (regla de Victor, 2026-07-31): si el Mac estuvo apagado el día que
    # tocaba publicar y ese post se perdió, en cuanto arranque —aunque hoy sea día
    # de descanso— se publica lo pendiente. EXCEPCIÓN: si hoy ya toca publicación
    # (la cadencia normal lo cubre) o es día especial, NO hay catch-up.
    # WHY: la detección es determinista — comparamos state['last_date'] con el
    # ÚLTIMO día de publicación esperado; si no coinciden, ese día se perdió. No
    # depende de "detectar" que el Mac durmió. Recupera UN solo post (resume la
    # cadencia); NO rellena todos los días perdidos, para no spamear el feed.
    catch_up = False
    if not is_special and not is_publish_today:
        due = last_due_publish_date(today)
        if s.get("last_date") and s["last_date"] != str(due):
            catch_up = True
            print(f"CATCH-UP: el día de publicación {due} se perdió "
                  f"(last_date={s['last_date']}) — publico lo pendiente al arrancar.")

    # Guardia "un día sí, un día no" — SE SALTA en días especiales y en catch-up.
    if not forced and not is_special and not is_publish_today and not catch_up:
        print(f"Día de descanso ({today_s}) — publica cuando ordinal%{ME_CYCLE_DIV}=={ME_CYCLE_DAY}.")
        return
    # Idempotencia: 1 publicación/día
    if s.get("last_date") == today_s:
        print(f"Ya se publicó hoy ({today_s}) — nada que hacer.")
        return
    # Guardia de hora objetivo (hora distinta cada día). En día especial NO se
    # difiere: publica en el primer disparo de la mañana para no arriesgar la
    # felicitación si el Mac se duerme luego (target = primera hora de la franja).
    # En catch-up TAMPOCO se difiere: se publica en el primer disparo tras arrancar.
    target = PUBLISH_HOUR_MIN if (is_special or catch_up) else todays_target_hour(today.toordinal())
    now = datetime.datetime.now()
    if not forced and not catch_up and now.hour < target:
        print(f"Aún no es la hora objetivo de hoy ({now.hour}h < {target}h) — espero a un disparo posterior.")
        return
    time.sleep(random.randint(30, 420))  # jitter humano

    # ── Controles del ERP (bloqueos / correcciones de caption) ────────────
    # Solo aplican a la rotación de marca (no a días especiales ni a fotos del
    # drop, que no viven en el deck que muestra el ERP). Si la tarjeta elegida
    # está bloqueada, se salta a la siguiente AVANZANDO el estado (para no
    # reintentarla en la próxima ejecución); la cota evita cualquier bucle.
    if not is_special and not do_real:
        blocked, overrides = _hub_controls()
        if blocked:
            limit = content.quote_count() + content.blog_count() + 2  # cota dura anti-bucle
            tries = 0
            def _card_blocked(n):
                return (os.path.basename(n["post_file"]) in blocked
                        or os.path.basename(n["story_file"]) in blocked)
            while _card_blocked(nxt) and tries < limit:
                if nxt["kind"] == "blog":
                    s["blog_idx"] += 1
                else:
                    s["quote_idx"] += 1
                s["post"] += 1
                nxt = pick_next(s)
                cap = rotate_caption(nxt["caption"], nxt["lang"])
                tries += 1
            if tries:
                print(f"HUB: {tries} tarjeta(s) bloqueada(s) saltada(s) → publico {nxt['label']}")
        ov = overrides.get(os.path.basename(nxt["post_file"]))
        if ov:
            cap = ov
            print("HUB: caption corregida desde el ERP.")

    # ── POST ──────────────────────────────────────────────────────────────
    is_real = False
    post_url, post_path = nxt["post_url"], os.path.join(LOCAL, nxt["post_file"])
    if do_real:
        real_path, real_cap = real_items[0]
        try:
            h = hashlib.sha1(open(real_path, "rb").read()).hexdigest()[:8]
            base, ext = os.path.splitext(os.path.basename(real_path))
            url = gh_upload(real_path, f"{base}-{h}{ext.lower()}")
            time.sleep(5)
            pr = publish_image(url, caption=rotate_caption(real_cap))
            if pr.get("permalink"):
                is_real = True; cap = real_cap; post_url = url; post_path = real_path
            else:
                print("Foto real falló, fallback a marca:", json.dumps(pr)[:200])
                pr = publish_image(post_url, caption=cap)
        except Exception as e:
            print("EXCEPCIÓN foto real, fallback a marca:", e)
            pr = publish_image(post_url, caption=cap)
    else:
        pr = publish_image(post_url, caption=cap)

    time.sleep(random.randint(20, 120))  # gap humano antes del story
    # WHY: la story NUNCA debe tumbar el guardado de estado tras un feed ya publicado.
    # Incidencia 2026-07-01: un ConnectionResetError en la story propagó y save_state()
    # no corrió → last_date sin avanzar → repetición de frase. api() ya reintenta;
    # esto es el cinturón de seguridad final ante cualquier excepción inesperada.
    try:
        sr = publish_image(nxt["story_url"], story=True)
    except Exception as e:
        print("Story falló (no crítico, se continúa y se guarda estado):", e)
        sr = {"error": str(e)}

    post_ok  = bool(pr.get("permalink"))
    story_ok = bool(sr.get("permalink") or sr.get("id"))
    if post_ok:
        s["last_date"] = today_s
        if is_special:
            # WHY: el saludo temático es un one-off — NO avanza la rotación de
            # frases/blog ni la alternancia ES/EN, para que el día regular
            # siguiente continúe justo donde se quedó.
            pass
        elif is_real:
            archive_real(real_items[0][0])
            s["since_real"] = 0
        else:
            if nxt["kind"] == "blog":
                s["blog_idx"] += 1
            else:
                s["quote_idx"] += 1
            s["post"] += 1
            s["since_real"] = s.get("since_real", 0) + 1
    save_state(s)

    plink = pr.get("permalink") or ("ERROR: " + json.dumps(pr)[:220])
    sok   = "publicada ✅" if story_ok else ("ERROR: " + json.dumps(sr)[:220])
    print("post:", plink, "(real)" if is_real else f"({nxt['kind']})")
    print("story:", sok)

    subj = ("📲 Instagram diario — Manzanos Enterprises"
            if post_ok else
            "⚠️ FALLO al publicar — Instagram Manzanos Enterprises (revisar)")
    story_path = os.path.join(LOCAL, nxt["story_file"])
    kind = "Foto real (drop)" if is_real else nxt["label"]
    when_note = ("recuperación tras Mac apagado" if catch_up
                 else f"hora objetivo {target}h")
    email_summary(
        f"<p>Publicado hoy en <b>@manzanosenterprises</b> · <b>{kind}</b> "
        f"({when_note}):</p>"
        f"<p>📸 <b>Post:</b> <a href='{plink}'>{plink}</a><br>📱 <b>Story:</b> {sok}</p>"
        f"<table cellpadding='6'><tr>"
        f"<td valign='top' align='center'><div style='color:#888;font-size:11px;letter-spacing:1px'>POST</div>"
        f"<img src='cid:postimg' width='300' style='border-radius:10px;border:1px solid #ddd'></td>"
        f"<td valign='top' align='center'><div style='color:#888;font-size:11px;letter-spacing:1px'>STORY</div>"
        f"<img src='cid:storyimg' width='210' style='border-radius:10px;border:1px solid #ddd'></td>"
        f"</tr></table>"
        f"<p style='color:#888;font-size:12px'>Caption:</p>"
        f"<pre style='white-space:pre-wrap;color:#555;font-size:12px'>{cap}</pre>"
        f"<p style='color:#aaa;font-size:11px'>"
        + ("🇪🇸 Día especial de España — publicación garantizada (salta la cadencia)."
           if is_special else
           "♻️ Recuperación: el Mac estuvo apagado el día que tocaba publicar; "
           "se publicó lo pendiente al arrancar (resume la cadencia)."
           if catch_up else
           f"Día alterno · 1 de cada {BLOG_EVERY} es destacado de blog.")
        + "</p>",
        post_path, story_path, subject=subj
    )


if __name__ == "__main__":
    main()
