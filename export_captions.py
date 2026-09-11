#!/usr/bin/env python3
"""Publica captions.json en el repo publico de @manzanosenterprises.

WHY (Victor, 11-sep-2026): la vista Social del ERP de Art's lista las tarjetas
futuras de esta cuenta desde posts/ y stories/ del repo publico, pero el texto de
cada una se genera al vuelo (blog_caption / quote_caption / SPECIAL_DAYS) y nadie
podia leerlo para decidir si bloquear una tarjeta. Este script vuelca
{"posts": {fichero: caption}, "stories": {fichero: caption}} a captions.json en la
raiz del repo. Se ejecuta al final de run_daily.sh; solo sube si cambia.
"""
import base64, json, os, subprocess, sys, urllib.request

os.environ.setdefault("DRY", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import content                                # noqa: E402
import daily_engine as E                      # noqa: E402  (credenciales lazy: no toca el Keychain)

def build():
    posts, stories = {}, {}
    for idx, b in enumerate(content.BLOG):
        for lang in ("es", "en"):
            cap = E.blog_caption(b, lang)
            posts[f"b{idx:02d}-{lang}.jpg"] = cap
            stories[f"b{idx:02d}-{lang}-st.jpg"] = cap
    for idx, (es, en) in enumerate(content.QUOTES):
        for lang in ("es", "en"):
            cap = E.quote_caption(es, en, lang)
            posts[f"q{idx:02d}-{lang}.jpg"] = cap
            stories[f"q{idx:02d}-{lang}-st.jpg"] = cap
    for key, sd in content.SPECIAL_DAYS.items():
        cap = sd.get("caption") or sd.get("title", "")
        posts[f"sp-{key}.jpg"] = cap
        stories[f"sp-{key}-st.jpg"] = cap
    return {"posts": posts, "stories": stories}

def remote_current():
    try:
        return urllib.request.urlopen(E.RAW + "/captions.json", timeout=20).read().decode()
    except Exception:
        return None

def upload(text):
    remote_path = "captions.json"
    sha = None
    probe = subprocess.run(["gh", "api", f"/repos/{E.REPO}/contents/{remote_path}"], capture_output=True, text=True)
    if probe.returncode == 0:
        try: sha = json.loads(probe.stdout).get("sha")
        except Exception: sha = None
    body = {"message": "Update captions.json (ERP social hub)", "content": base64.b64encode(text.encode()).decode()}
    if sha: body["sha"] = sha
    r = subprocess.run(["gh", "api", "--method", "PUT", f"/repos/{E.REPO}/contents/{remote_path}", "--input", "-"],
                       input=json.dumps(body), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("gh upload failed: " + r.stderr.strip()[:300])

if __name__ == "__main__":
    data = build()
    text = json.dumps(data, ensure_ascii=False, indent=1)
    cur = remote_current()
    if cur is not None and json.loads(cur) == data:
        print(f"captions.json up to date ({len(data['posts'])} posts, {len(data['stories'])} stories)")
    else:
        upload(text)
        print(f"captions.json uploaded ({len(data['posts'])} posts, {len(data['stories'])} stories)")
