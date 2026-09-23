import os, sys
sys.path.insert(0, os.path.expanduser("~/manzanos-enterprises-social"))
from PIL import Image, ImageDraw
import make_me as M

WEB = M.WEB
OUT = "out"; os.makedirs(OUT, exist_ok=True)
GOLD, GOLD_DK = M.GOLD, M.GOLD_DK

def frame(im, margin, size, line, gap, outer):
    im = M.draw_frame(im, margin, gap=gap, outer=outer, inner=1)
    return M.draw_corners(im, margin, size=size, line=line)

def logo_plate(im, logo_w, pad):
    """Bottom plate + centered gold wordmark, same recipe as the IG cards."""
    logo = M._logo(logo_w)
    w, h = im.size
    top = h - pad - logo.height
    canvas = im.convert("RGBA")
    plate_top = top - 30
    span = h - plate_top
    plate = Image.new("L", (1, span)); pp = plate.load()
    for i in range(span):
        pp[0, i] = int(min(195, 70 + 200 * (i / max(1, span - 1))))
    dark = Image.new("RGBA", (w, span), (8, 7, 6, 255)); dark.putalpha(plate.resize((w, span)))
    canvas.alpha_composite(dark, (0, plate_top))
    ImageDraw.Draw(canvas).line([(w * 0.36, plate_top), (w * 0.64, plate_top)], fill=GOLD_DK + (160,), width=1)
    canvas.alpha_composite(logo, ((w - logo.width) // 2, top))
    return canvas.convert("RGB")

def save(im, name, q=92):
    p = os.path.join(OUT, name); im.save(p, "JPEG", quality=q, optimize=True, subsampling=0); print(name, im.size, os.path.getsize(p)//1024, "KB")

# ── 1) LOGO 720x720 (Google recomienda 720x720, cuadrado) ─────────────────
def logo_square(variant):
    W = 720
    bg = M.gradient_bg(W, W)
    bg = frame(bg, 26, 44, 2, 10, 2)
    c = bg.convert("RGBA")
    if variant == "icon":
        ic = Image.open(os.path.join(WEB, "logos", "m-icon-hd.png")).convert("RGBA")
        tw = 380; ic = ic.resize((tw, int(ic.height * tw / ic.width)), Image.LANCZOS)
        c.alpha_composite(ic, ((W - ic.width) // 2, (W - ic.height) // 2 - 6))
    else:
        lg = M._logo(560)
        c.alpha_composite(lg, ((W - lg.width) // 2, (W - lg.height) // 2))
    d = ImageDraw.Draw(c)
    M.spaced(d, W / 2, 596, "SINCE 1890", M.font(M.FH, 22), GOLD + (255,), 6)
    return c.convert("RGB")

save(logo_square("icon"), "01-logo-720x720-icono-M.jpg", 95)
save(logo_square("word"), "02-logo-720x720-wordmark.jpg", 95)

# ── 2) COVER 1920x1080 (16:9; Google: recomendado 1024x576, maximo 2120x1192) ──
def cover_brand():
    W, H = 1920, 1080
    bg = M.gradient_bg(W, H)
    bg = frame(bg, 46, 110, 4, 20, 4)
    c = bg.convert("RGBA"); d = ImageDraw.Draw(c)
    lg = M._logo(1100); c.alpha_composite(lg, ((W - lg.width) // 2, 330))
    M.spaced(d, W / 2, 700, "GRUPO FAMILIAR INTERNACIONAL DESDE 1890", M.font(M.FH, 30), GOLD + (255,), 7)
    d.line([(W * 0.40, 766), (W * 0.60, 766)], fill=GOLD_DK + (200,), width=1)
    M.spaced(d, W / 2, 796, "VINOS  ·  INMOBILIARIA  ·  MUSICA  ·  AGUA MINERAL  ·  MOVILIDAD  ·  ENERGIA", M.font(M.FH, 22), M.DIM + (255,), 4)
    M.spaced(d, W / 2, 900, "HARO  ·  MADRID  ·  MIAMI", M.font(M.FR, 26), M.CREAM + (255,), 6)
    return c.convert("RGB")

def cover_photo(src):
    W, H = 1920, 1080
    im = M.cover(Image.open(src).convert("RGB"), W, H)
    im = M.darken(im, top=0.30, bottom=0.78)
    im = frame(im, 46, 110, 4, 20, 4)
    c = im.convert("RGBA"); d = ImageDraw.Draw(c)
    lg = M._logo(1000); c.alpha_composite(lg, ((W - lg.width) // 2, 400))
    M.spaced(d, W / 2, 750, "GRUPO FAMILIAR INTERNACIONAL DESDE 1890", M.font(M.FH, 30), GOLD + (255,), 7)
    M.spaced(d, W / 2, 850, "HARO  ·  MADRID  ·  MIAMI", M.font(M.FR, 26), M.CREAM + (255,), 6)
    return c.convert("RGB")

save(cover_brand(), "03-cover-1920x1080-marca.jpg", 92)
save(cover_photo(os.path.join(WEB, "hero", "1890-finca-manzanos.jpg")), "04-cover-1920x1080-foto.jpg", 92)

# ── 3) 10 FOTOS 1600x1200 con marco dorado + logo ─────────────────────────
PHOTOS = [
    ("hero/1890-finca-manzanos.jpg",     "05-vinos-1890-finca-manzanos.jpg"),
    ("hero/palacio-de-manzanos.jpg",     "06-palacio-de-manzanos-haro.jpg"),
    ("hero/hero-clean.jpg",              "07-palacio-interior.jpg"),
    ("hero/palacio-lifestyle.jpg",       "08-palacio-experiencia.jpg"),
    ("hero/miami.jpg",                   "09-miami-florida.jpg"),
    ("hero/mhsa.jpg",                    "10-manzanos-habitat-mhsa.jpg"),
    ("businesses/hero-habitat.jpg",      "11-manzanos-habitat-residencial.jpg"),
    ("businesses/hero-mobility.jpg",     "12-manzanos-mobility.jpg"),
    ("businesses/hero-electricity.jpg",  "13-manzanos-electricity.jpg"),
    (os.path.expanduser("~/manzanos-enterprises-social/drop/mineraqua-hero-mineraqua.jpg"), "14-mineraqua-manantial.jpg"),
]
for src, name in PHOTOS:
    p = src if src.startswith("/") else os.path.join(WEB, src)
    im = M.cover(Image.open(p).convert("RGB"), 1600, 1200)
    im = frame(im, 40, 90, 3, 16, 3)
    im = logo_plate(im, 380, 64)
    save(im, name, 90)
