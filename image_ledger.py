#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""image_ledger.py — regla de NO repetir imagen en @manzanosenterprises (Victor, 17-sep-2026).

Victor: "no podemos repetir imagenes en menos de 360 dias". Este modulo es la
memoria de lo publicado y la biblioteca de imagenes nuevas:

  image_history.json   una fila por imagen publicada: fecha, sha1, ahash, tipo, ref.
  image_library.json   imagenes descargadas (SerpAPI) y su estado de revision.
  library/             los ficheros de la biblioteca.

WHY hash perceptual y no solo sha1: la MISMA foto reescalada o recomprimida tiene
otro sha1 (pasó en agolfcars el 10-sep-2026, ver agolfcars-ig-engine.md). Dos fotos
con aHash a distancia de Hamming <= AHASH_MAX_DIST se tratan como la misma.
"""
import os, json, hashlib, datetime

LOCAL        = os.path.dirname(os.path.abspath(__file__))
HISTORY      = os.path.join(LOCAL, "image_history.json")
LIBRARY_JSON = os.path.join(LOCAL, "image_library.json")
LIBRARY_DIR  = os.path.join(LOCAL, "library")

NO_REPEAT_DAYS = 360  # Regla de Victor (17-sep-2026): ninguna imagen se repite en < 360 dias.
AHASH_MAX_DIST = 6    # WHY: 6/256 bits tolera recompresion y reescalado sin confundir fotos
                      # distintas; es el umbral que ya funciono en el motor de agolfcars.


def sha1(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def ahash(path):
    """aHash 16x16 como cadena hex de 64 caracteres (256 bits)."""
    from PIL import Image
    im = Image.open(path).convert("L").resize((16, 16))
    px = list(im.getdata())
    avg = sum(px) / len(px)
    bits = "".join("1" if p > avg else "0" for p in px)
    return "%064x" % int(bits, 2)


def dist(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def _load(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(p, data):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def history():
    return _load(HISTORY, [])


def last_used(path, today=None):
    """Fecha (date) del ultimo uso de esta imagen (o una casi identica), o None."""
    try:
        s, h = sha1(path), ahash(path)
    except Exception:
        return None
    best = None
    for row in history():
        same = row.get("sha1") == s or (row.get("ahash") and dist(row["ahash"], h) <= AHASH_MAX_DIST)
        if same:
            d = datetime.date.fromisoformat(row["date"])
            best = d if best is None or d > best else best
    return best


def used_recently(path, days=NO_REPEAT_DAYS, today=None):
    today = today or datetime.date.today()
    d = last_used(path)
    return d is not None and (today - d).days < days


def record(path, kind, ref, date=None):
    """Anota una publicacion. Se llama JUSTO despues de publicar con exito."""
    rows = history()
    rows.append({
        "date": str(date or datetime.date.today()),
        "sha1": sha1(path), "ahash": ahash(path),
        "kind": kind, "ref": ref, "file": os.path.basename(path),
    })
    _save(HISTORY, rows)


# ── Biblioteca ───────────────────────────────────────────────────────────────
def library():
    return _load(LIBRARY_JSON, [])


def save_library(rows):
    _save(LIBRARY_JSON, rows)


def library_free(theme=None, exclude_paths=()):
    """Imagenes APROBADAS de la biblioteca, sin uso en 360 dias y no reservadas por
    otra tarjeta (exclude_paths). Filtra por tema si se pide, con fallback a todas."""
    rows = [r for r in library() if r.get("status") == "approved"]
    excl = set(os.path.abspath(p) for p in exclude_paths)
    out = []
    for r in rows:
        p = os.path.join(LIBRARY_DIR, r["file"])
        if not os.path.exists(p) or os.path.abspath(p) in excl:
            continue
        if used_recently(p):
            continue
        out.append((r, p))
    if theme:
        themed = [x for x in out if x[0].get("theme") == theme]
        if themed:
            return themed
    return out
