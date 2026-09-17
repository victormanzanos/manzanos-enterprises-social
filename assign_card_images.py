#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assign_card_images.py — da a CADA tarjeta de blog una foto de fondo unica (17-sep-2026).

Problema: 73 de 113 tarjetas llevaban 1890-finca-manzanos.jpg porque el SKILL de refresco
solo aceptaba ficheros de hero/. Regla de Victor: ninguna imagen se repite en < 360 dias.

Orden de preferencia por tarjeta:
  1. La portada PROPIA del articulo en la web (/images/blog/...), si nadie mas la usa.
  2. La foto de hero/ que ya tenia, si es la primera tarjeta en usarla.
  3. Una imagen APROBADA de la biblioteca (library/), del tema que mejor encaje.
Unicidad por contenido (aHash), no por nombre. Tampoco se asigna una foto publicada hace
< 360 dias a una tarjeta que va a salir pronto.

Uso:
    python3 assign_card_images.py --dry      # informe, no escribe
    python3 assign_card_images.py            # reescribe blog.json y regenera las tarjetas cambiadas
"""
import os, sys, json, datetime, subprocess
import image_ledger as L
import refresh_blog, make_me

LOCAL = os.path.dirname(os.path.abspath(__file__))
BLOG_JSON = os.path.join(LOCAL, "blog.json")
# Portadas de la web que NO valen para Instagram (personas protagonistas, marcas de terceros,
# marcas de agua). Revisadas a ojo el 17-sep-2026; brief de Laura §4 y §6.
try:
    COVER_BLOCK = json.load(open(os.path.join(LOCAL, "cover_blocklist.json"), encoding="utf-8"))
except (OSError, ValueError):
    COVER_BLOCK = {}
DAYS_PER_BLOG_CARD = 2.6  # WHY: publica cada 2 dias y 4 de cada 5 posts de marca son blog,
                          # con 1 foto real cada 3; ~2,6 dias entre tarjetas de blog.

# Palabras del titulo -> tema preferido de la biblioteca (el primero que case gana).
THEME_WORDS = [
    ("wine", ("vino", "wine", "bodega", "rioja", "viñedo", "vendimia")),
    ("build", ("inmobiliari", "vivienda", "real estate", "obra", "construc", "casa", "home")),
    ("miami", ("miami", "florida", "estados unidos", "ee. uu", "usa", "americ")),
    ("sea", ("náutic", "barco", "yate", "boat", "mar ")),
    ("stone", ("legado", "legacy", "1890", "familia", "family", "historia", "generacion", "palacio")),
    ("power", ("electric", "energía", "energy")),
    ("water", ("agua", "water", "mineral")),
]


def theme_for(card):
    t = (card.get("title_es", "") + " " + card.get("title_en", "") + " " + card.get("hook_es", "")).lower()
    for theme, words in THEME_WORDS:
        if any(w in t for w in words):
            return theme
    return "business"


def main(dry):
    blog = json.load(open(BLOG_JSON, encoding="utf-8"))
    arts = {a["slug"]: a for a in refresh_blog.parse_articles(refresh_blog.ARTICLES_TS)}
    state = json.load(open(os.path.join(LOCAL, ".daily_state.json")))
    nxt = state["blog_idx"] % len(blog)
    today = datetime.date.today()
    # Orden de publicacion: primero las proximas tarjetas, para que las fotos "buenas"
    # (portadas propias) no se las quede una tarjeta que no sale hasta dentro de un año.
    order = [(nxt + k) % len(blog) for k in range(len(blog))]

    used_hashes = []   # aHash ya asignados en esta pasada
    lib = [r for r in L.library() if r.get("status") == "approved"]
    lib_by_theme = {}
    for r in lib:
        lib_by_theme.setdefault(r["theme"], []).append(r)

    def taken(h):
        return any(L.dist(h, k) <= L.AHASH_MAX_DIST for k in used_hashes)

    def recently_published(path, eta_days):
        d = L.last_used(path)
        return d is not None and (today + datetime.timedelta(days=eta_days) - d).days < L.NO_REPEAT_DAYS

    changes, kept, unresolved = [], 0, []
    for pos, idx in enumerate(order):
        card = blog[idx]
        eta = int(pos * DAYS_PER_BLOG_CARD)
        candidates = []
        own = (arts.get(card["slug"]) or {}).get("image", "")
        if own.startswith("/images/blog/"):
            candidates.append(own)
        candidates.append(card["image"])
        th = theme_for(card)
        pool = lib_by_theme.get(th, []) + [r for r in lib if r["theme"] != th]
        candidates += ["library/" + r["file"] for r in pool]
        chosen = None
        for c in candidates:
            if c in COVER_BLOCK:
                continue
            p = make_me.resolve_image(c)
            if not os.path.exists(p):
                continue
            h = L.ahash(p)
            if taken(h) or recently_published(p, eta):
                continue
            chosen = (c, h)
            break
        if not chosen:
            unresolved.append(idx)
            continue
        used_hashes.append(chosen[1])
        if chosen[0] != card["image"]:
            changes.append((idx, card["image"], chosen[0]))
            card["image"] = chosen[0]
        else:
            kept += 1

    print(f"Tarjetas: {len(blog)} · se quedan igual: {kept} · cambian: {len(changes)} · sin foto libre: {len(unresolved)}")
    for idx, old, new in changes:
        print(f"  b{idx:02d}: {old}  ->  {new}")
    if unresolved:
        print("SIN RESOLVER (faltan fotos aprobadas en la biblioteca):", unresolved)
    if dry or not changes:
        return
    json.dump(blog, open(BLOG_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for idx, _, _ in changes:
        for lang in ("es", "en"):
            subprocess.run([sys.executable, os.path.join(LOCAL, "make_me.py"), "blog", str(idx), lang], check=True)
    print("blog.json actualizado y tarjetas regeneradas. Falta git add/commit/push de posts/ stories/ blog.json.")


if __name__ == "__main__":
    main(dry="--dry" in sys.argv)
