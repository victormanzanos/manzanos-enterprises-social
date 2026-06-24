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
def api(path, params, method="POST"):
    data = urllib.parse.urlencode(params).encode()
    hdr  = {"User-Agent": UA}
    if method == "GET":
        req = urllib.request.Request(f"{BASE}/{path}?{data.decode()}", headers=hdr)
    else:
        req = urllib.request.Request(f"{BASE}/{path}", data=data, method="POST", headers=hdr)
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "body": e.read().decode()}

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


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────
def main():
    s = state()
    real_items = real_collect()
    do_real = bool(real_items) and s.get("since_real", 0) >= REAL_EVERY

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

    today = datetime.date.today()
    today_s = str(today)
    forced = os.environ.get("FORCE") == "1"

    # Guardia "un día sí, un día no"
    if not forced and today.toordinal() % ME_CYCLE_DIV != ME_CYCLE_DAY:
        print(f"Día de descanso ({today_s}) — publica cuando ordinal%{ME_CYCLE_DIV}=={ME_CYCLE_DAY}.")
        return
    # Idempotencia: 1 publicación/día
    if s.get("last_date") == today_s:
        print(f"Ya se publicó hoy ({today_s}) — nada que hacer.")
        return
    # Guardia de hora objetivo (hora distinta cada día)
    target = todays_target_hour(today.toordinal())
    now = datetime.datetime.now()
    if not forced and now.hour < target:
        print(f"Aún no es la hora objetivo de hoy ({now.hour}h < {target}h) — espero a un disparo posterior.")
        return
    time.sleep(random.randint(30, 420))  # jitter humano

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
    sr = publish_image(nxt["story_url"], story=True)

    post_ok  = bool(pr.get("permalink"))
    story_ok = bool(sr.get("permalink") or sr.get("id"))
    if post_ok:
        s["last_date"] = today_s
        if is_real:
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
    email_summary(
        f"<p>Publicado hoy en <b>@manzanosenterprises</b> · <b>{kind}</b> "
        f"(hora objetivo {target}h):</p>"
        f"<p>📸 <b>Post:</b> <a href='{plink}'>{plink}</a><br>📱 <b>Story:</b> {sok}</p>"
        f"<table cellpadding='6'><tr>"
        f"<td valign='top' align='center'><div style='color:#888;font-size:11px;letter-spacing:1px'>POST</div>"
        f"<img src='cid:postimg' width='300' style='border-radius:10px;border:1px solid #ddd'></td>"
        f"<td valign='top' align='center'><div style='color:#888;font-size:11px;letter-spacing:1px'>STORY</div>"
        f"<img src='cid:storyimg' width='210' style='border-radius:10px;border:1px solid #ddd'></td>"
        f"</tr></table>"
        f"<p style='color:#888;font-size:12px'>Caption:</p>"
        f"<pre style='white-space:pre-wrap;color:#555;font-size:12px'>{cap}</pre>"
        f"<p style='color:#aaa;font-size:11px'>Día alterno · 1 de cada {BLOG_EVERY} es destacado de blog.</p>",
        post_path, story_path, subject=subj
    )


if __name__ == "__main__":
    main()
