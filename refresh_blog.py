#!/usr/bin/env python3
"""Manzanos Enterprises — AUTO-REFRESCO de tarjetas de blog para Instagram.

Recoge los artículos NUEVOS del blog de manzanosenterprises.com, crea una tarjeta
de Instagram (ES + EN, post + story) para cada uno y los añade a la rotación, para
que el feed NO se repita: crece solo con cada artículo publicado.

Fuente de verdad del blog: el fichero local `blog-articles.ts` de la web (lo
mantiene al día la rutina `manzanos-enterprises-daily-blog`). Se parsea, se compara
por `slug` contra `blog.json` (lo ya publicado en IG) y solo se añade lo nuevo.

Uso:
    python3 refresh_blog.py            # añade los artículos nuevos y genera sus tarjetas
    python3 refresh_blog.py --dry      # solo muestra qué añadiría, sin escribir nada

Tras añadir, hay que subir las imágenes nuevas + blog.json al repo de hosting
(lo hace la rutina de Claude que lo invoca; ver SKILL.md).
"""
import json, os, re, subprocess, sys

LOCAL    = os.path.expanduser("~/manzanos-enterprises-social")
BLOG_JSON = os.path.join(LOCAL, "blog.json")
ARTICLES_TS = "/Users/victor/Code/MANZANOSENTERPRISESWEB/manzanos-new/src/data/blog-articles.ts"
HERO_DIR = "/Users/victor/Code/MANZANOSENTERPRISESWEB/manzanos-new/public/images/hero"

DRY = "--dry" in sys.argv
# Máx tarjetas nuevas por ejecución — evita una avalancha si hay mucho atrasado.
# Generoso porque el primer run recupera el histórico; luego serán 1-2/semana.
MAX_PER_RUN = 60  # WHY: hay ~56 artículos; deja margen para el catch-up inicial.


def parse_articles(path):
    """Extrae {slug,title,titleEs,excerpt,excerptEs,image,date} de blog-articles.ts."""
    src = open(path, encoding="utf-8").read()
    objs = re.split(r"\n  \{\n", src)[1:]
    out = []
    for o in objs:
        def g(k):
            m = re.search(k + r': "((?:[^"\\]|\\.)*)"', o)
            return m.group(1) if m else None
        slug = g("slug")
        title = g("title")
        if not slug or not title:
            continue
        out.append({
            "slug": slug,
            "date": g("date") or "",
            "title": title,
            "titleEs": g("titleEs") or title,
            "excerpt": g("excerpt") or "",
            "excerptEs": g("excerptEs") or "",
            "image": g("image") or "",
        })
    return out


# Palabras vacías por las que NO debe terminar un titular recortado.
_STOP = {"de", "la", "el", "los", "las", "y", "o", "en", "a", "que", "del",
         "un", "una", "unos", "unas", "para", "con", "por", "su", "sus", "al",
         "the", "of", "a", "an", "to", "and", "or", "in", "on", "for", "why",
         "how", "your", "you", "is", "are", "that", "this"}

def short_title(t, max_chars=46):
    """Título corto y punchy: lo anterior a ':'/'—'; si sigue largo, recorta a
    frontera de palabra sin terminar en palabra vacía, y añade '…'."""
    t = re.split(r"[:—]", t, maxsplit=1)[0].strip()
    if len(t) <= max_chars:
        return t
    words = t[:max_chars].split()
    if len(words) > 1:
        words = words[:-1]  # descarta la palabra probablemente cortada
    while len(words) > 2 and words[-1].lower().strip(",.;") in _STOP:
        words.pop()
    return " ".join(words).rstrip(" ,;.") + "…"


def hook(excerpt, limit=150):
    """Recorta el excerpt a ~150 chars en frontera de frase/palabra."""
    e = excerpt.strip().replace("\n", " ")
    if len(e) <= limit:
        return e
    cut = e[:limit]
    # corta en el último punto o, si no hay, en el último espacio
    dot = cut.rfind(". ")
    if dot > 60:
        return cut[:dot + 1]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > 0 else cut).rstrip(" ,;") + "…"


def image_name(img_path):
    """'/images/hero/miami.jpg' -> 'miami.jpg'. Solo si existe en hero/."""
    name = os.path.basename(img_path or "")
    if name and os.path.exists(os.path.join(HERO_DIR, name)):
        return name
    return None  # make_me usará el degradado de marca si no hay foto


def main():
    blog = json.load(open(BLOG_JSON, encoding="utf-8")) if os.path.exists(BLOG_JSON) else []
    have = {b["slug"] for b in blog}
    articles = parse_articles(ARTICLES_TS)
    # Más recientes primero, pero añadimos en orden cronológico para que los
    # índices nuevos queden al final de la rotación.
    articles.sort(key=lambda a: a["date"])
    new = [a for a in articles if a["slug"] not in have][:MAX_PER_RUN]

    # Modo para la rutina de Claude: vuelca los artículos nuevos EN CRUDO (título
    # y excerpt completos) como JSON, para que Claude escriba títulos/ganchos de
    # calidad. No escribe nada.
    if "--list-new-json" in sys.argv:
        print(json.dumps({"next_index": len(blog), "new": new}, ensure_ascii=False, indent=1))
        return

    if not new:
        print("Sin artículos nuevos — la rotación de blog ya está al día "
              f"({len(blog)} tarjetas).")
        return

    print(f"{len(new)} artículo(s) nuevo(s) para añadir a la rotación de IG:")
    start_idx = len(blog)
    added = []
    for a in new:
        img = image_name(a["image"])
        entry = {
            "slug": a["slug"],
            "image": img or "1890-finca-manzanos.jpg",  # respaldo elegante
            "title_es": short_title(a["titleEs"]),
            "title_en": short_title(a["title"]),
            "hook_es": hook(a["excerptEs"] or a["excerpt"]),
            "hook_en": hook(a["excerpt"] or a["excerptEs"]),
        }
        added.append(entry)
        print(f"  + b{start_idx + len(added) - 1:02d}  «{entry['title_es']}»  ({a['slug']})")

    if DRY:
        print("\n--dry: no se escribió nada.")
        return

    # 1) Persistir en blog.json
    blog.extend(added)
    json.dump(blog, open(BLOG_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n✓ blog.json actualizado: {len(blog)} tarjetas en total.")

    # 2) Generar las imágenes nuevas (ES + EN, post + story) con make_me.py
    print("Generando tarjetas nuevas...")
    for i in range(start_idx, len(blog)):
        for lang in ("es", "en"):
            r = subprocess.run(["python3", os.path.join(LOCAL, "make_me.py"), "blog", str(i), lang],
                               capture_output=True, text=True)
            if r.returncode != 0:
                print(f"  ⚠ b{i:02d}-{lang} ERROR: {r.stderr.strip()[:160]}")
            else:
                print(f"  ✓ b{i:02d}-{lang}")
    print("\nListo. Recuerda subir posts/ stories/ blog.json al repo de hosting "
          "(git add/commit/push) para que Meta pueda leer las imágenes nuevas.")


if __name__ == "__main__":
    main()
