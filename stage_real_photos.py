#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""stage_real_photos.py — encola en drop/ fotos REALES de las divisiones, revisadas a ojo.

17-sep-2026. Hasta hoy el drop solo tenia 7 heroes y la foto de JMC se repetia. Estas
fotos salen de las webs propias de cada division (Palacio, Habitat, Wines USA) y se han
revisado una a una en hojas de contacto: sin personas protagonistas, sin David, sin
marcas vetadas (D-Boat, Music), sin la tele con logo de terceros, interiores del Palacio
solo del Palacio (regla palacio-ig-identidad-imagen.md).

Cada foto lleva su propia primera linea (ES y EN) para que el pie no se repita, y se
recorta al rango de proporciones que Instagram acepta (4:5 a 1.91:1).

Uso:  python3 stage_real_photos.py [--dry]
"""
import os, sys
from PIL import Image
import fetch_real_images as F
import image_ledger as L

CODE = os.path.expanduser("~/Code")
P  = CODE + "/PalaciodeManzanosweb/public/images/palacio/"
H  = CODE + "/ManzanosHabitat/manzanoshabitat-new/public/images/"
WP = CODE + "/manzanoswinesusa/app/public/wines/winery-photos/"
WG = CODE + "/manzanoswinesusa/app/public/images/wineries/haro/"

IG_MIN_RATIO = 0.8    # WHY: Instagram rechaza feed mas alto que 4:5
IG_MAX_RATIO = 1.91   # WHY: y mas ancho que 1.91:1
OUT_MAX_W    = 1440   # WHY: ancho maximo que IG conserva; mas solo pesa

# (division, fichero, linea ES, linea EN)
PHOTOS = [
    ("palacio", P + "DSC_4339-HDR-Editar.jpg", "Sala de juegos con billar y cine privado.", "Games room with pool table and private cinema."),
    ("palacio", P + "DSC_4392.jpg", "La escalera de madera que une las plantas del palacio.", "The wooden staircase that links every floor of the palace."),
    ("palacio", P + "Manzanos-1.jpg", "Dormitorios luminosos, pensados para descansar de verdad.", "Bright bedrooms, designed for real rest."),
    ("palacio", P + "Manzanos-10.jpg", "Cada habitación, con su propia personalidad.", "Every room with its own personality."),
    ("palacio", P + "Manzanos-14.jpg", "Habitaciones para las familias y los más pequeños.", "Rooms for families and the little ones."),
    ("palacio", P + "Manzanos-17.jpg", "Bajo cubierta, vigas de madera y luz cenital.", "Under the roof: wooden beams and skylights."),
    ("palacio", P + "Manzanos-2.jpg", "Desayuno en la cama, sin prisa.", "Breakfast in bed, no rush."),
    ("palacio", P + "Manzanos-28.jpg", "Zona de bienestar con sauna y gimnasio.", "Wellness area with sauna and gym."),
    ("palacio", P + "Manzanos-6.jpg", "Detalles que convierten una escapada en un recuerdo.", "Details that turn a getaway into a memory."),
    ("palacio", P + "Manzanos_interior-11.jpg", "Cocina equipada para grupos y celebraciones.", "A kitchen equipped for groups and celebrations."),
    ("habitat", H + "calle-grande-28/gallery/exterior-01.jpg", "Calle Grande 28, Calahorra: cuatro viviendas de lujo.", "Calle Grande 28, Calahorra: four luxury homes."),
    ("habitat", H + "calle-grande-28/gallery/rooftop-07.jpg", "Terraza en cubierta de Calle Grande 28 (render del proyecto).", "Rooftop terrace at Calle Grande 28 (project render)."),
    ("habitat", H + "calle-grande-28/gallery/rooftop-01.jpg", "Calle Grande 28 vista desde arriba (render del proyecto).", "Calle Grande 28 from above (project render)."),
    ("habitat", H + "calle-grande-28/gallery/comunes-07.jpg", "Zonas comunes de Calle Grande 28 (render del proyecto).", "Shared spaces at Calle Grande 28 (project render)."),
    ("habitat", H + "calle-grande-28/gallery/salon-04.jpg", "Cocina y comedor abiertos en Calle Grande 28 (render).", "Open kitchen and dining at Calle Grande 28 (render)."),
    ("habitat", H + "calle-grande-28/gallery/interior-07.jpg", "Baños de piedra natural en Calle Grande 28 (render).", "Natural stone bathrooms at Calle Grande 28 (render)."),
    ("habitat", H + "mh-villafranca/gallery/ext-05.jpg", "MH Villafranca: piscina comunitaria (render del proyecto).", "MH Villafranca: community pool (project render)."),
    ("habitat", H + "mh-villafranca/gallery/ext-07.jpg", "MH Villafranca: pista de pádel dentro de la urbanización (render).", "MH Villafranca: padel court inside the community (render)."),
    ("habitat", H + "mh-villafranca/gallery/ext-03-1.jpg", "MH Villafranca: calle interior privada (render del proyecto).", "MH Villafranca: private inner street (project render)."),
    ("legacy", WG + "gallery-02.jpg", "La fachada de Bodegas Manzanos en Haro.", "The façade of Bodegas Manzanos in Haro."),
    ("legacy", WG + "gallery-08.jpg", "Haro, La Rioja: donde empezó todo.", "Haro, La Rioja: where it all began."),
    ("legacy", WP + "Winery-Haro-03.jpg", "La prensa antigua que guardamos en la bodega de Haro.", "The old wine press we keep in our Haro cellar."),
    ("legacy", WP + "Winery-Haro-05.jpg", "La nave de barricas de Haro.", "The barrel hall in Haro."),
    ("legacy", WG + "gallery-06.jpg", "Un nombre que llevamos desde 1890.", "A name we have carried since 1890."),
    ("legacy", WG + "gallery-04.jpg", "Botellas en reposo, a la espera de su momento.", "Bottles at rest, waiting for their moment."),
    ("wines", WP + "Winery-Azagra-05.jpg", "Nuestra bodega de Azagra, Navarra, entre viñedos.", "Our winery in Azagra, Navarra, among the vines."),
    ("wines", WP + "Winery-Azagra-07.jpg", "Azagra al anochecer.", "Azagra at dusk."),
    ("wines", WP + "Winery-Campanas-05.jpg", "Las Campanas, Navarra.", "Las Campanas, Navarra."),
    ("wines", WP + "Winery-Campanas-07.jpg", "Barricas en reposo en Las Campanas.", "Barrels resting at Las Campanas."),
    ("wines", WP + "Winery-Chateau-Jolys-01.jpg", "Château Jolys, Jurançon, Francia: una de las bodegas con las que trabajamos.", "Château Jolys, Jurançon, France: one of our partner estates."),
    ("wines", WP + "Winery-Chateau-Jolys-05.jpg", "Amanece sobre las colinas de Jurançon.", "Morning over the Jurançon hills."),
    ("wines", WP + "Winery-Cremaschi-Furlotti-01.jpg", "Viñedos de Cremaschi Furlotti, valle del Maule, Chile.", "Cremaschi Furlotti vineyards, Maule Valley, Chile."),
    ("wines", WP + "Winery-DuchessaLia-01.jpg", "La bodega de Duchessa Lia, Piamonte, Italia.", "The cellar at Duchessa Lia, Piedmont, Italy."),
]


def fit_for_ig(src, dest):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    r = w / h
    if r > IG_MAX_RATIO:
        nw = int(h * IG_MAX_RATIO); x = (w - nw) // 2; im = im.crop((x, 0, x + nw, h))
    elif r < IG_MIN_RATIO:
        nh = int(w / IG_MIN_RATIO); y = (h - nh) // 2; im = im.crop((0, y, w, y + nh))
    if im.size[0] > OUT_MAX_W:
        im = im.resize((OUT_MAX_W, int(im.size[1] * OUT_MAX_W / im.size[0])), Image.LANCZOS)
    im.save(dest, "JPEG", quality=90, optimize=True, progressive=True)


def caption(div, line_es, line_en):
    c = F.DIVISIONS[div]
    es = line_es + " " + c["cap_es"]
    en = line_en + " " + c["cap_en"]
    first, second = (en, es) if c.get("en_first") else (es, en)  # Wines USA: ingles primero (brief §3)
    parts = [first, "", "⸻", "", second, "", c["cta"], c["geo"]]
    if c["collab"]:
        parts.append(f"Descúbrelo en {c['collab']} / More at {c['collab']}")
    parts += ["", " ".join(c["nicho"])]
    text = "\n".join(parts)
    assert "—" not in text, "raya larga prohibida"
    return text


def main(dry):
    os.makedirs(F.DROP, exist_ok=True)
    # Orden intercalado por division para que el feed alterne (el motor toma el drop por nombre).
    by_div = {}
    for row in PHOTOS:
        by_div.setdefault(row[0], []).append(row)
    order, i = [], 0
    while any(by_div.values()):
        for d in list(by_div):
            if by_div[d]:
                order.append(by_div[d].pop(0))
    existing = [L.ahash(os.path.join(F.DROP, n)) for n in os.listdir(F.DROP)
                if n.lower().endswith(".jpg")]
    n = 0
    for k, (div, src, les, len_) in enumerate(order):
        if not os.path.exists(src):
            print("FALTA", src); continue
        if any(t in src.lower() for t in F.BLOCKED_PERSON_TOKENS):
            print("VETADA", src); continue
        base = f"r{k:03d}-{div}-{os.path.splitext(os.path.basename(src))[0]}"[:60]
        dest = os.path.join(F.DROP, base + ".jpg")
        if dry:
            print("[DRY]", base); continue
        fit_for_ig(src, dest)
        h = L.ahash(dest)
        if L.used_recently(dest) or any(L.dist(h, e) <= L.AHASH_MAX_DIST for e in existing):
            os.remove(dest); print("repetida, se salta:", base); continue
        existing.append(h)
        with open(os.path.join(F.DROP, base + ".txt"), "w", encoding="utf-8") as f:
            f.write(caption(div, les, len_))
        n += 1
    print(f"Encoladas {n} fotos reales.")


if __name__ == "__main__":
    main("--dry" in sys.argv)
