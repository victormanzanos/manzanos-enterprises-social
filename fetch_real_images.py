#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_real_images.py — Fase 2 del brief de Laura (2026-08-10).

Alimenta la carpeta `drop/` con FOTOS REALES de las divisiones para que el motor
(daily_engine.py) las intercale (1 de cada REAL_EVERY) con caption de calidad:
bilingüe ES/EN, @mención de la división (colaboración), hashtags de nicho/leads,
CTA y geoetiqueta, según el brief.

Fuentes (por orden de preferencia, para no gastar cuota de SerpAPI):
  1) Imágenes REALES ya en local del sitio principal
     (~/Code/MANZANOSENTERPRISESWEB/manzanos-new/public/images/hero/).
  2) `og:image` de las webs de división (descarga con User-Agent de navegador;
     los WAF de Dinahosting rechazan el UA por defecto de urllib -> 406/HTML).
  3) Pexels (GRATIS, sin cuota mensual como SerpAPI) SOLO para ATMÓSFERA
     (paisaje/textura), NUNCA producto ni personas (brief Laura §6). Función
     `pexels_atmosphere(query, dest)`; clave en Keychain `PEXELS_API_KEY`
     (compartida por todas las rutinas de IG). OJO: pedir Accept image/jpeg (no
     webp) o Instagram no lo admite; y usar curl, no urllib (Pexels da 403 al UA
     de urllib). Reservada para Reels/fondos, no para posts de producto.
  4) SerpAPI Google Images SOLO si se pasa `--serpapi` (cuota compartida: 5000/mes,
     renueva el día 21; ver regla serpapi-quota.md). No se usa por defecto.

Cada imagen se valida como imagen REAL (cabecera mágica JPEG/PNG), NUNCA una
página HTML de error guardada con extensión .jpg. Idempotente: no re-descarga lo
ya presente en drop/ ni lo ya publicado (drop/published/).

Uso:
    python3 fetch_real_images.py            # rellena hasta MAX_IN_DROP desde webs/local
    python3 fetch_real_images.py --division palacio
    python3 fetch_real_images.py --serpapi  # permite completar con SerpAPI si falta
    python3 fetch_real_images.py --dry       # no escribe, solo informa
"""
import os, sys, ssl, json, socket, hashlib, subprocess, urllib.request

LOCAL   = os.path.dirname(os.path.abspath(__file__))
DROP    = os.path.join(LOCAL, "drop")
DONE    = os.path.join(DROP, "published")
# Biblioteca de imágenes de Manzanos Enterprises (ruta indicada por Victor/Laura,
# 2026-08-10). Es la MISMA que sirve manzanosenterprises.com en vivo. Tiene carpetas
# por tipo y `businesses/` con un hero por empresa del grupo. Los `local` de cada
# división cuelgan de aquí (subcarpeta/fichero). NO usar hero-dboat / hero-music
# (marca vetada por Laura). Cuando el equipo suba una galería más rica de proyectos,
# apuntar aquí (o a la carpeta del servidor que indique Victor).
IMAGES  = os.path.expanduser("~/Code/MANZANOSENTERPRISESWEB/manzanos-new/public/images")
UA      = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
# Tope de fotos reales en cola: el motor consume 1 cada REAL_EVERY(=6) publicaciones,
# así que una cola pequeña dura ~2 semanas. Evita inundar el drop.
MAX_IN_DROP = 8
socket.setdefaulttimeout(12)

# ── Config por división (brief §1, §7, §8) ────────────────────────────────────
# nicho = capa de hashtags de leads (Laura §7). collab = @cuenta a invitar como
# colaborador. Los captions se redactan SIN raya larga (regla de marca de Victor).
DIVISIONS = {
    "palacio": {
        "collab": "@palaciodemanzanos",
        "geo": "📍 Haro, La Rioja",
        "local": ["hero/palacio-hero.jpg", "hero/palacio-exterior.jpg", "hero/palacio-lifestyle.jpg",
                  "hero/palacio-espacios.jpg", "hero/palacio-detalle.jpg"],
        "og": ["https://palaciodemanzanos.com/images/Palacio-de-Manzanos-scaled.jpg"],
        "cap_es": "Un palacio del siglo XVIII en Haro para ti solo. Alquiler íntegro, "
                  "para una celebración o una escapada privada en el corazón de Rioja.",
        "cap_en": "An 18th-century palace in Haro, all yours. Full private rental for a "
                  "celebration or a private escape in the heart of Rioja.",
        "cta": "Reserva el palacio completo / Book the whole palace, palaciodemanzanos.com",
        "nicho": ["#PalacioDeManzanos", "#Haro", "#LaRioja", "#Rioja", "#Enoturismo",
                  "#TurismoRioja", "#EscapadaConEncanto", "#EscapadaRomantica", "#LuxuryTravel"],
    },
    "wines": {
        "collab": "@manzanoswinesusa",
        "geo": "📍 Miami, Florida",
        "local": ["hero/mhsa.jpg", "hero/mhsa-v2.jpg", "hero/miami.jpg"],
        "og": ["https://manzanoswinesusa.com/images/og-cover.jpg"],
        # Excepcion Wines USA (brief §3): ingles primero, luego espanol.
        "cap_es": "Del viñedo de Rioja a tu mesa en EE. UU. Importamos vino premium de "
                  "España, Francia, Italia, Chile y Sudáfrica desde Miami a todo el país.",
        "cap_en": "From the Rioja vineyard to your table in the US. We import premium wine "
                  "from Spain, France, Italy, Chile and South Africa, Miami to all 50 states.",
        "cta": "Trade inquiries welcome / Distribuidores y restaurantes, hablemos, manzanoswinesusa.com",
        "nicho": ["#ManzanosWinesUSA", "#MiamiWine", "#FloridaWineLovers", "#WineImporter",
                  "#SpanishWine", "#RiojaWine", "#WineDistributor", "#MiamiLifestyle"],
        "en_first": True,
    },
    "habitat": {
        "collab": "@manzanoshabitat",
        "geo": "📍 La Rioja y Navarra",
        "local": ["businesses/hero-habitat.jpg"],
        "og": ["https://www.manzanoshabitat.com/images/og/home.jpg"],
        "cap_es": "Obra nueva en La Rioja y Navarra: Haro, Calahorra, Azagra, Villafranca, "
                  "San Adrián. Construimos hogares y creamos comunidad.",
        "cap_en": "New-build homes in La Rioja and Navarra: Haro, Calahorra, Azagra, "
                  "Villafranca, San Adrián. We build homes and create community.",
        "cta": "Descubre el proyecto y solicita precio / Ask for pricing, manzanoshabitat.com",
        "nicho": ["#ManzanosHabitat", "#ObraNueva", "#ObraNuevaLaRioja", "#Haro", "#Calahorra",
                  "#Navarra", "#LaRioja", "#ViviendaNueva", "#CasaConPiscina"],
    },
    "mobility": {
        "collab": "@manzanosmobility",
        "geo": "📍 Miami · La Rioja",
        "local": ["businesses/hero-mobility.jpg"],
        "og": [],
        "cap_es": "Movilidad de lujo Manzanos Mobility: náutica, experiencias exclusivas y "
                  "alquiler de coches premium. Del mar de Florida a las carreteras de Rioja.",
        "cap_en": "Manzanos Mobility, luxury mobility: boats, exclusive experiences and premium "
                  "car rental. From the Florida sea to the roads of Rioja.",
        "cta": "Descúbrelo / Discover it, manzanosmobility.com/es",
        "nicho": ["#ManzanosMobility", "#Nautica", "#BoatingFlorida", "#MiamiBoating",
                  "#LuxuryCars", "#AlquilerDeCoches", "#MiamiLifestyle", "#Yachting"],
    },
    "electricity": {  # Electricidad JMC (@electricidadjmc), sin web propia
        "collab": "@electricidadjmc",
        "geo": "📍 La Rioja y Navarra",
        "local": ["businesses/hero-electricity.jpg"],
        "og": [],
        "cap_es": "Electricidad JMC: instalaciones y mantenimiento eléctrico para hogar, "
                  "obra y empresa en La Rioja y Navarra. Trabajo bien hecho, sin sustos.",
        "cap_en": "Electricidad JMC: electrical installation and maintenance for homes, "
                  "construction and business across La Rioja and Navarra. Work done right.",
        "cta": "Escríbenos para tu instalación / Message us for your project",
        "nicho": ["#ElectricidadJMC", "#InstalacionesElectricas", "#Electricidad",
                  "#Mantenimiento", "#LaRioja", "#Navarra", "#Obra"],
    },
    "mineraqua": {  # Mineraqua / agua Peña Clara (@aguapenaclara), sin web propia
        "collab": "@aguapenaclara",
        "geo": "📍 La Rioja",
        "local": ["businesses/hero-mineraqua.jpg"],
        "og": [],
        "cap_es": "Agua mineral natural premium. Del manantial a tu mesa, pureza de origen "
                  "para el día a día y para la alta restauración.",
        "cap_en": "Premium natural mineral water. From the spring to your table, source purity "
                  "for everyday life and for fine dining.",
        "cta": "Descúbrela / Discover it en @aguapenaclara",
        "nicho": ["#AguaPenaClara", "#Mineraqua", "#AguaMineral", "#AguaPremium",
                  "#LaRioja", "#Manantial", "#SinCastigo"],
    },
    "legacy": {  # grupo / legado 1890 (brief §4 pilar Legado)
        "collab": "",
        "geo": "📍 La Rioja · Navarra · Miami",
        "local": ["hero/1890-finca-manzanos.jpg", "hero/legacy.jpg", "hero/legacy-v2.jpg"],
        "og": [],
        "cap_es": "Cinco generaciones desde 1890. De una bodega familiar en Rioja a un grupo "
                  "internacional en vino, inmobiliaria, hospitalidad y más.",
        "cap_en": "Five generations since 1890. From a family winery in Rioja to an "
                  "international group across wine, real estate, hospitality and more.",
        "cta": "Descubre el grupo / Discover the group, manzanosenterprises.com",
        "nicho": ["#Desde1890", "#Since1890", "#FamilyBusiness", "#EmpresaFamiliar",
                  "#LaRioja", "#Rioja", "#Legado", "#Legacy"],
    },
}

# Atmósfera vía Pexels (brief Laura §6: STOCK SOLO para ambiente, NUNCA producto ni
# personas protagonistas). Gratis y sin cuota mensual como SerpAPI. La clave está en
# el Keychain compartido (PEXELS_API_KEY) → disponible para TODAS las rutinas de IG.
PEXELS_ATMOSPHERE = {  # temas neutros permitidos: paisaje/textura, sin producto/personas
    "rioja":   "la rioja vineyard landscape",
    "miami":   "miami coast skyline",
    "wine":    "vineyard rows autumn",
    "stone":   "old stone architecture detail",
    "sea":     "mediterranean sea boat horizon",
}
def _pexels_key():
    try:
        return subprocess.check_output(
            [os.path.expanduser("~/Code/CyberSecurity/scripts/secrets.sh"), "get", "PEXELS_API_KEY"],
            text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""

def pexels_atmosphere(query, dest):
    """Descarga UNA foto de atmósfera (paisaje) de Pexels a `dest`. Devuelve (ok,info).
    Solo ambiente; el llamador NO debe usarla como producto ni con personas."""
    key = _pexels_key()
    if not key:
        return False, "sin PEXELS_API_KEY en Keychain"
    try:
        import urllib.parse
        url = ("https://api.pexels.com/v1/search?orientation=landscape&per_page=1&query="
               + urllib.parse.quote(query))
        # curl (no urllib): Pexels bloquea el UA por defecto de urllib con 403.
        r = subprocess.run(["curl", "-s", "-A", UA, "-H", f"Authorization: {key}",
                            "--max-time", "15", url], capture_output=True, text=True)
        data = json.loads(r.stdout or "{}")
        photos = data.get("photos") or []
        if not photos:
            return False, f"sin resultados ({data.get('error') or data.get('status') or 'vacio'})"
        src = photos[0]["src"].get("large2x") or photos[0]["src"].get("large")
        return _download(src, dest)
    except Exception as e:
        return False, str(e)

def _log(*a):
    print(*a, flush=True)

def _is_real_image(path):
    """True solo si el fichero es realmente JPEG/PNG (cabecera mágica), no HTML."""
    try:
        with open(path, "rb") as f:
            head = f.read(12)
    except OSError:
        return False
    return head[:3] == b"\xff\xd8\xff" or head[:8] == b"\x89PNG\r\n\x1a\n"

_CARD_BG = None
def _card_background_hashes():
    """(sha1, aHash) de los fondos que YA usan las tarjetas de blog.

    WHY (17-sep-2026): `hero/palacio-hero.jpg` estaba a la vez como fondo de la tarjeta
    b45 y en la cola del drop como foto real, o sea la MISMA foto dos veces en el feed.
    El motor lo habría salvado al publicar (real_collect mira el historial y
    ensure_fresh_blog_bg cambia el fondo), pero es mejor no encolar el duplicado.
    """
    global _CARD_BG
    if _CARD_BG is None:
        _CARD_BG = []
        try:
            import image_ledger as L, make_me
            blog = json.load(open(os.path.join(LOCAL, "blog.json"), encoding="utf-8"))
            for card in blog:
                p = make_me.resolve_image(card.get("image", ""))
                if os.path.exists(p):
                    _CARD_BG.append((L.sha1(p), L.ahash(p)))
        except Exception as e:   # nunca reventar el encolado por esto
            _log(f"  ⚠ no pude leer los fondos de las tarjetas ({e}); sigo sin ese chequeo.")
    return _CARD_BG

def _is_card_background(path):
    try:
        import image_ledger as L
        s, a = L.sha1(path), L.ahash(path)
    except Exception:
        return False
    for cs, ca in _card_background_hashes():
        if cs == s or L.dist(ca, a) <= L.AHASH_MAX_DIST:
            return True
    return False

def _existing_bases():
    """Nombres base (sin ext) ya en cola o publicados, para idempotencia."""
    seen = set()
    for d in (DROP, DONE):
        if os.path.isdir(d):
            for n in os.listdir(d):
                seen.add(os.path.splitext(n)[0])
    return seen

def _caption(div):
    c = DIVISIONS[div]
    order = [c["cap_en"], c["cap_es"]] if c.get("en_first") else [c["cap_es"], c["cap_en"]]
    parts = [order[0], "", "⸻", "", order[1], "", c["cta"], c["geo"]]
    if c["collab"]:
        # La Graph API no crea el post-colaboración (co-autoría) en automático:
        # esto es una MENCIÓN honesta que invita a la cuenta de la división.
        parts.append(f"Descúbrelo en {c['collab']} / More at {c['collab']}")
    parts += ["", " ".join(c["nicho"])]  # brand (#ManzanosEnterprises…) lo añade rotate_caption
    return "\n".join(parts)

def _download(url, dest):
    # Usa curl con UA de navegador: es el patrón fiable del proyecto (evita WAF de
    # Dinahosting 406 y el bloqueo de CDNs como Pexels al fingerprint de urllib).
    try:
        # Accept fuerza JPEG/PNG (NO avif/webp): Pexels honra el Accept y devolvería
        # WebP, que Instagram no admite y _is_real_image rechaza por magic bytes.
        r = subprocess.run(
            ["curl", "-sL", "-A", UA, "-H", "Accept: image/jpeg,image/png",
             "--max-time", "20", url, "-o", dest, "-w", "%{http_code}"],
            capture_output=True, text=True)
        code = (r.stdout or "").strip()
        if not os.path.exists(dest):
            return False, f"sin descarga (HTTP {code or '?'})"
        if not _is_real_image(dest):
            os.remove(dest)
            return False, f"no es una imagen real (HTTP {code}, ¿HTML de error?)"
        return True, f"{os.path.getsize(dest)//1024} KB"
    except Exception as e:  # nunca reventar
        if os.path.exists(dest):
            os.remove(dest)
        return False, str(e)

# Personas VETADAS en imágenes (regla permanente de Victor, 2026-08-14): David ya no
# está en Manzanos Enterprises; NUNCA encolar una foto suya (ni de Victor con David).
BLOCKED_PERSON_TOKENS = ("david",)

def _stage(div, src_is_local, src, seen, dry):
    """Coloca UNA imagen de la división en drop/ con su .txt de caption."""
    base = f"{div}-{os.path.splitext(os.path.basename(src))[0]}".replace(" ", "_")[:60]
    if base in seen:
        return False
    if any(tok in base.lower() or tok in os.path.basename(src).lower()
           for tok in BLOCKED_PERSON_TOKENS):
        _log(f"  ⛔ {div}: fuente vetada por persona ({src}) — no se encola a David.")
        return False
    dest = os.path.join(DROP, base + ".jpg")
    if dry:
        _log(f"  [DRY] {div}: {'local' if src_is_local else src}  ->  {base}.jpg")
        seen.add(base)
        return True
    if src_is_local:
        if not _is_real_image(src):
            _log(f"  ✗ {div}: local {src} no es imagen válida"); return False
        if _is_card_background(src):
            _log(f"  ♻️ {div}: {os.path.basename(src)} ya es el fondo de una tarjeta de blog — no se encola.")
            return False
        with open(src, "rb") as a, open(dest, "wb") as b:
            b.write(a.read())
        ok, info = True, "local"
    else:
        ok, info = _download(src, dest)
    if not ok:
        _log(f"  ✗ {div}: {info}  ({src})"); return False
    if not src_is_local and _is_card_background(dest):
        # Descargada: el duplicado solo se ve tras bajarla, asi que se borra aqui.
        os.remove(dest)
        _log(f"  ♻️ {div}: {src} ya es el fondo de una tarjeta de blog — no se encola.")
        return False
    with open(os.path.join(DROP, base + ".txt"), "w", encoding="utf-8") as f:
        f.write(_caption(div))
    _log(f"  ✓ {div}: {base}.jpg  ({info})")
    seen.add(base)
    return True

def run(only=None, use_serpapi=False, dry=False):
    os.makedirs(DROP, exist_ok=True)
    seen = _existing_bases()
    in_drop = len([n for n in os.listdir(DROP) if n.lower().endswith((".jpg", ".jpeg", ".png"))]) if os.path.isdir(DROP) else 0
    _log(f"Cola actual en drop/: {in_drop} · tope {MAX_IN_DROP}")
    divs = [only] if only else list(DIVISIONS.keys())
    added = 0
    for div in divs:
        if div not in DIVISIONS:
            _log(f"  ⚠ división desconocida: {div}"); continue
        if in_drop + added >= MAX_IN_DROP:
            _log("Cola llena, no añado más."); break
        c = DIVISIONS[div]
        # 1) local primero (cero riesgo de red)
        for name in c["local"]:
            if in_drop + added >= MAX_IN_DROP:
                break
            p = os.path.join(IMAGES, name)
            if os.path.exists(p) and _stage(div, True, p, seen, dry):
                added += 1
                break  # 1 por división por pasada, para que el feed varíe
        else:
            # 2) og:image de la web si no había local util
            for url in c["og"]:
                if in_drop + added >= MAX_IN_DROP:
                    break
                if _stage(div, False, url, seen, dry):
                    added += 1
                    break
    _log(f"Añadidas {added} imagen(es) reales a drop/.")
    if use_serpapi and in_drop + added < MAX_IN_DROP:
        _log("(--serpapi) Hueco libre: puedes completar con SerpAPI Google Images. "
             "No implementado en automático para no gastar cuota; ver serpapi-quota.md.")
    return added

if __name__ == "__main__":
    only = None; serp = "--serpapi" in sys.argv; dry = "--dry" in sys.argv
    if "--division" in sys.argv:
        i = sys.argv.index("--division")
        only = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
    run(only=only, use_serpapi=serp, dry=dry)
