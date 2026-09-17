#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_library_images.py — amplia la biblioteca de imagenes con SerpAPI (17-sep-2026).

Motivo: la regla de Victor de no repetir imagen en < 360 dias. El motor publica ~180
piezas al año y hasta hoy casi todas las tarjetas de blog usaban la misma foto
(1890-finca-manzanos.jpg en 73 de 113). Hace falta un banco grande y sin repetidos.

Que descarga: SOLO ATMOSFERA (brief de Laura §6: stock = ambiente; nunca producto ni
personas protagonistas): viñedos, bodegas, piedra, Haro, Miami, mar, objetos de
despacho. Las fotos de producto y proyectos siguen saliendo de las webs propias.

Licencia: SerpAPI Google Images con `licenses=fmc` (uso comercial y modificacion) y
ademas una LISTA BLANCA de bancos de dominio publico/CC0. Wikimedia Commons solo si
la API de Commons confirma CC0 o dominio publico (CC BY/BY-SA exigen atribucion y
las tarjetas no la llevan).

Todo lo descargado entra como `pending`: NO se usa hasta que alguien lo mire y lo
pase a `approved` (misma leccion que palacio-ig-identidad-imagen.md: una lista
revisada a ojo envejece mejor que cualquier heuristica).

Uso:
    python3 fetch_library_images.py --plan          # cuenta busquedas, no gasta cuota
    python3 fetch_library_images.py [--max-queries N] [--per-query K]
"""
import os, sys, json, time, socket, hashlib, subprocess, urllib.parse, urllib.request, datetime
import image_ledger as L

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
WIKI_UA = "ManzanosEnterprisesIG/1.0 (https://www.manzanosenterprises.com; victor@manzanos.com)"
WEB_IMAGES = os.path.expanduser("~/Code/MANZANOSENTERPRISESWEB/manzanos-new/public/images")

MIN_SIDE = 1000       # WHY: la tarjeta es 1080x1350 recortada tipo cover; por debajo de ~1000 px
                      # en el lado corto se nota el reescalado.
MAX_SIDE = 2400       # WHY: IG no necesita mas y mantiene el repo ligero (<1 MB por imagen).
REQ_TIMEOUT = 75      # WHY: SerpAPI cobra la busqueda aunque el cliente corte; un timeout corto
                      # tira cuota (incidencia mw-lead 11-sep-2026).
QUOTA_FLOOR = 800     # WHY: no dejar la cuenta compartida por debajo de esto; blog-writer,
                      # siglo-daily-pulse y mobility-blog dependen de ella hasta la renovacion.

# Bancos cuya licencia permite uso comercial sin atribucion (o CC0/dominio publico).
SOURCE_OK = ("pxhere", "pixnio", "public domain pictures", "publicdomainpictures", "hippopx",
             "pexels", "unsplash", "pixabay", "rawpixel", "stockvault", "wikimedia", "wikipedia",
             "picryl", "libreshot", "negativespace", "burst", "kaboompics", "isorepublic",
             "freerange", "goodfreephotos", "free stock photos")
# Nunca: bancos de pago/marca de agua, redes, wallpapers de licencia dudosa, premium.
SOURCE_BAD = ("shutterstock", "istock", "getty", "alamy", "dreamstime", "123rf", "depositphotos",
              "adobe", "freepik", "vecteezy", "pinterest", "instagram", "facebook", "wallpaper",
              "plus.unsplash", "canva", "envato", "bigstock", "stocksy", "masterfile")

# tema -> consultas. Temas pensados para el grupo: vino/Rioja, piedra/palacio, Miami/mar,
# obra/arquitectura, y objetos de despacho para los articulos de negocio.
THEMES = {
    "rioja":    ["la rioja vineyards landscape", "haro la rioja town", "rioja alavesa vineyard autumn",
                 "navarra landscape fields", "vineyard rows sunset spain"],
    "wine":     ["wine barrels cellar", "old wine cellar stone", "wine bottles rack cellar",
                 "red wine glass table", "grapes on vine close up"],
    "stone":    ["old stone palace facade spain", "stone arch courtyard spain", "historic wooden door stone",
                 "old library bookshelves", "spanish village street stone"],
    "miami":    ["miami skyline", "biscayne bay miami", "miami beach ocean", "florida marina yachts",
                 "palm trees sunset florida"],
    "sea":      ["sailboat sea horizon", "yacht ocean blue water", "harbor boats mediterranean"],
    "build":    ["construction site crane sky", "modern house architecture exterior",
                 "architectural blueprints", "new residential building facade", "house keys on table"],
    "business": ["fountain pen signing document", "chess pieces board strategy", "compass on old map",
                 "empty boardroom table", "hourglass on desk", "ledger notebook desk vintage",
                 "mountain summit sunrise", "stone bridge river",
                 "lighthouse coast", "city skyline night lights", "open road landscape"],
    "power":    ["electrical panel wiring", "power lines sunset", "light bulb dark"],
    "water":    ["mountain spring water stream", "water glass splash", "natural spring rocks"],
}


def _key():
    return subprocess.check_output(
        [os.path.expanduser("~/Code/CyberSecurity/scripts/secrets.sh"), "get", "SERPAPI_KEY"],
        text=True).strip()


def _get_json(url, ua=UA, timeout=REQ_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def quota():
    d = _get_json("https://serpapi.com/account?api_key=" + _key(), timeout=30)
    return d.get("total_searches_left"), d.get("plan_renewal_date")


def search(q):
    params = {"engine": "google_images", "q": q, "licenses": "fmc", "imgsz": "l",
              "api_key": _key()}
    d = _get_json("https://serpapi.com/search.json?" + urllib.parse.urlencode(params))
    if d.get("error"):
        return []
    return d.get("images_results") or []


def wikimedia_license_ok(url):
    """True solo si Commons dice CC0 / dominio publico para ese fichero."""
    try:
        name = urllib.parse.unquote(url.split("?")[0].rstrip("/").split("/")[-1])
        if "px-" in name:  # miniatura: /thumb/.../1200px-Nombre.jpg
            name = name.split("px-", 1)[1]
        api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo"
               "&iiprop=extmetadata&titles=" + urllib.parse.quote("File:" + name))
        d = _get_json(api, ua=WIKI_UA, timeout=20)
        for page in d["query"]["pages"].values():
            meta = page["imageinfo"][0]["extmetadata"]
            lic = (meta.get("LicenseShortName", {}).get("value", "") + " " +
                   meta.get("License", {}).get("value", "")).lower()
            return ("cc0" in lic) or ("public domain" in lic) or (lic.strip() == "pd")
    except Exception:
        return False
    return False


def download(url, dest):
    r = subprocess.run(["curl", "-sL", "-A", WIKI_UA if "wikimedia" in url else UA,
                        "-H", "Accept: image/jpeg,image/png", "--max-time", "40", url, "-o", dest,
                        "-w", "%{http_code}"], capture_output=True, text=True)
    return os.path.exists(dest) and (r.stdout or "").strip() == "200"


def normalize(src, dest):
    """Valida que es imagen real, tamaño minimo, y la guarda como JPEG RGB <= MAX_SIDE."""
    from PIL import Image
    im = Image.open(src)
    im.load()
    if min(im.size) < MIN_SIDE:
        return False, f"pequeña {im.size}"
    im = im.convert("RGB")
    if max(im.size) > MAX_SIDE:
        im.thumbnail((MAX_SIDE, MAX_SIDE))
    im.save(dest, "JPEG", quality=88, optimize=True, progressive=True)
    return True, f"{im.size[0]}x{im.size[1]}"


def known_hashes():
    """aHash de TODO lo que ya existe: biblioteca, historial y fotos de la web."""
    hs = [r["ahash"] for r in L.library() if r.get("ahash")]
    hs += [r["ahash"] for r in L.history() if r.get("ahash")]
    for sub in ("hero", "blog", "businesses", "slides", "news"):
        d = os.path.join(WEB_IMAGES, sub)
        for n in os.listdir(d) if os.path.isdir(d) else []:
            if n.lower().endswith((".jpg", ".jpeg", ".png")):
                try:
                    hs.append(L.ahash(os.path.join(d, n)))
                except Exception:
                    pass
    return hs


def run(max_queries=None, per_query=6, plan=False, workers=4):
    queries = [(t, q) for t, qs in THEMES.items() for q in qs]
    done = {r.get("query") for r in L.library()}
    queries = [x for x in queries if x[1] not in done]  # WHY: no pagar dos veces la misma busqueda
    if max_queries:
        queries = queries[:max_queries]
    left, renew = quota()
    print(f"SerpAPI: {left} busquedas, renueva {renew}; plan {len(queries)} busquedas", flush=True)
    if plan or not queries:
        return
    if left is None or left - len(queries) < QUOTA_FLOOR:
        print(f"ABORTO: dejaria la cuota por debajo de {QUOTA_FLOOR}.")
        return
    os.makedirs(L.LIBRARY_DIR, exist_ok=True)
    socket.setdefaulttimeout(REQ_TIMEOUT)
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock()
    lib = L.library()
    seen_urls = {r.get("url") for r in lib}
    hashes = known_hashes()

    def one(tq):
        theme, q = tq
        try:
            results = search(q)
        except Exception as e:
            print(f"  ✗ busqueda '{q}': {e}", flush=True)
            return 0
        got = 0
        for x in results:
            if got >= per_query:
                break
            src = (x.get("source") or "").lower()
            url = x.get("original") or ""
            with lock:
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
            if any(b in src or b in url.lower() for b in SOURCE_BAD):
                continue
            if not any(ok in src for ok in SOURCE_OK):
                continue
            if (x.get("original_width") or 0) and min(x.get("original_width", 0), x.get("original_height", 0)) < MIN_SIDE:
                continue
            if ("wikimedia" in url or "wikipedia" in src) and not wikimedia_license_ok(url):
                continue
            key = hashlib.sha1(url.encode()).hexdigest()[:10]
            tmp = os.path.join(L.LIBRARY_DIR, f".tmp-{key}")
            try:
                if not download(url, tmp):
                    continue
                name = f"{theme}-{key}.jpg"
                dest = os.path.join(L.LIBRARY_DIR, name)
                ok, info = normalize(tmp, dest)
                if not ok:
                    continue
                h = L.ahash(dest)
                with lock:
                    if any(L.dist(h, k) <= L.AHASH_MAX_DIST for k in hashes):
                        os.remove(dest)
                        continue
                    hashes.append(h)
                    lib.append({"file": name, "theme": theme, "query": q, "url": url,
                                "page": x.get("link"), "source": x.get("source"), "title": x.get("title"),
                                "ahash": h, "sha1": L.sha1(dest), "size": info,
                                "added": str(datetime.date.today()), "status": "pending"})
                got += 1
            except Exception as e:
                print(f"  ✗ {url[:80]}: {e}", flush=True)
            finally:
                if os.path.exists(tmp):
                    os.remove(tmp)
        with lock:
            # WHY: guardar por consulta (un corte no pierde lo descargado) FUSIONANDO con el disco:
            # si alguien aprueba/rechaza fotos mientras esto corre, no se pisan sus decisiones
            # (pasó el 17-sep-2026 con la primera tanda).
            disk = {r["file"]: r for r in L.library()}
            for r in lib:
                d = disk.get(r["file"])
                if d and d.get("status") != "pending":
                    r.update({k: d[k] for k in ("status", "reason", "reviewed") if k in d})
            L.save_library(lib)
        print(f"  {theme:9s} '{q}': +{got}", flush=True)
        return got

    with ThreadPoolExecutor(max_workers=workers) as ex:
        added = sum(ex.map(one, queries))
    print(f"Añadidas {added} imagenes (pending). Biblioteca: {len(lib)}", flush=True)


if __name__ == "__main__":
    a = sys.argv
    mq = int(a[a.index("--max-queries") + 1]) if "--max-queries" in a else None
    pq = int(a[a.index("--per-query") + 1]) if "--per-query" in a else 6
    run(max_queries=mq, per_query=pq, plan="--plan" in a)
