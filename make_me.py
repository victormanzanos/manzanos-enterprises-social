#!/usr/bin/env python3
"""Manzanos Enterprises — Instagram image generator.

Builds branded cards, 1080×1350 (post) and 1080×1920 (story), each with a GOLD
double frame, art-deco corners, a dark plate + the Manzanos Enterprises GOLD
logo at the bottom (text never overlaps the logo — there is a guaranteed safe
zone above it).

Each card is rendered in ONE language (es or en); the daily engine alternates
between them so some posts are Spanish and others English.

  QUOTE cards — an entrepreneurial motivation phrase on a deep charcoal gradient.
  BLOG cards  — a real article from manzanosenterprises.com/news over a darkened
                hero photo (eyebrow + title + hook + "link in bio").

Usage:
    python3 make_me.py batch                 # ALL quote + blog cards, both langs
    python3 make_me.py quote 7 es            # one quote card (idx 7, Spanish)
    python3 make_me.py blog 0 en             # one blog card (idx 0, English)

Naming (so the engine can address any card):
    posts/q07-es.jpg   stories/q07-es-st.jpg
    posts/b00-en.jpg   stories/b00-en-st.jpg
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import content

# ── Paths ────────────────────────────────────────────────────────────────
LOCAL       = os.path.expanduser("~/manzanos-enterprises-social")
WEB         = "/Users/victor/Code/MANZANOSENTERPRISESWEB/manzanos-new/public/images"
SOURCE_HERO = os.path.join(WEB, "hero")
LOGO_GOLD   = os.path.join(WEB, "logos", "me-gold.png")
OUT_POSTS   = os.path.join(LOCAL, "posts")
OUT_STORIES = os.path.join(LOCAL, "stories")

# ── Brand palette (Manzanos Enterprises: charcoal · gold · cream) ──────────
GOLD     = (193, 160, 95)
GOLD_LT  = (216, 190, 132)
GOLD_DK  = (139, 112, 64)
CREAM    = (244, 238, 226)
DIM      = (176, 166, 150)
BG_TOP   = (28, 24, 20)
BG_BOT   = (9, 9, 11)

# ── Fonts (macOS system) ───────────────────────────────────────────────────
FB = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FR = "/System/Library/Fonts/Supplemental/Georgia.ttf"
FI = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
FH = "/System/Library/Fonts/Helvetica.ttc"

POST_W,  POST_H  = 1080, 1350
STORY_W, STORY_H = 1080, 1920

# ── Per-language UI strings ────────────────────────────────────────────────
STR = {
    "es": {
        "eyebrow_q": "PALABRAS QUE NOS MUEVEN",
        "eyebrow_b": "DEL BLOG  ·  MANZANOS ENTERPRISES",
        "cta":       "LEE EL ARTÍCULO COMPLETO  ·  LINK EN BIO",
    },
    "en": {
        "eyebrow_q": "WORDS THAT DRIVE US",
        "eyebrow_b": "FROM THE BLOG  ·  MANZANOS ENTERPRISES",
        "cta":       "READ THE FULL ARTICLE  ·  LINK IN BIO",
    },
}


# ════════════════════════════════════════════════════════════════════════
# Low-level helpers
# ════════════════════════════════════════════════════════════════════════
def font(path, size):
    return ImageFont.truetype(path, size)


def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    nw, nh = int(im.width * s + 1), int(im.height * s + 1)
    im = im.resize((nw, nh), Image.LANCZOS)
    x0, y0 = (nw - w) // 2, (nh - h) // 2
    return im.crop((x0, y0, x0 + w, y0 + h))


def gradient_bg(w, h):
    """Warm-charcoal vertical gradient + soft gold glow + faint 'M' watermark."""
    col = Image.new("RGB", (1, h))
    cp = col.load()
    for y in range(h):
        t = y / (h - 1)
        cp[0, y] = (
            int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t),
            int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t),
            int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t),
        )
    base = col.resize((w, h))
    glow = Image.new("L", (w // 4, h // 4), 0)
    gd = ImageDraw.Draw(glow)
    cx, cy = w // 8, int(h * 0.30) // 4
    gd.ellipse([cx - 130, cy - 130, cx + 130, cy + 130], fill=46)
    glow = glow.resize((w, h)).filter(ImageFilter.GaussianBlur(120))
    gold_layer = Image.new("RGB", (w, h), GOLD)
    base = Image.composite(gold_layer, base, glow)
    wm = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    wd = ImageDraw.Draw(wm)
    wd.text((w * 0.62, h * 0.55), "M", font=font(FB, int(h * 0.62)), fill=GOLD + (12,))
    return Image.alpha_composite(base.convert("RGBA"), wm).convert("RGB")


def darken(im, top=0.45, bottom=0.86):
    w, h = im.size
    col = Image.new("L", (1, h))
    sp = col.load()
    for y in range(h):
        t = y / (h - 1)
        sp[0, y] = int(255 * (top + (bottom - top) * t))
    scrim = col.resize((w, h))
    black = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(black, im, scrim)


def spaced(draw, cx, y, text, fnt, fill, sp):
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths) + sp * (len(text) - 1)
    x = cx - total / 2
    for c, wdt in zip(text, widths):
        draw.text((x, y), c, font=fnt, fill=fill)
        x += wdt + sp


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_lines(draw, text, font_path, max_w, max_h, hi, lo, line_ratio=1.28):
    for size in range(hi, lo - 1, -2):
        fnt = font(font_path, size)
        lines = wrap(draw, text, fnt, max_w)
        line_h = int(size * line_ratio)
        if line_h * len(lines) <= max_h:
            return fnt, lines, line_h
    fnt = font(font_path, lo)
    return fnt, wrap(draw, text, fnt, max_w), int(lo * line_ratio)


def draw_frame(im, margin, gap=16, outer=3, inner=1):
    w, h = im.size
    canvas = im.convert("RGBA")
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle([margin, margin, w - margin - 1, h - margin - 1], outline=GOLD, width=outer)
    mi = margin + gap
    d.rectangle([mi, mi, w - mi - 1, h - mi - 1], outline=GOLD, width=inner)
    return Image.alpha_composite(canvas, ov).convert("RGB")


def draw_corners(im, margin, size=70, line=3):
    w, h = im.size
    canvas = im.convert("RGBA")
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.line([(margin, margin + size), (margin, margin)], fill=GOLD, width=line)
    d.line([(margin, margin), (margin + size, margin)], fill=GOLD, width=line)
    d.line([(w - margin - size, margin), (w - margin - 1, margin)], fill=GOLD, width=line)
    d.line([(w - margin - 1, margin), (w - margin - 1, margin + size)], fill=GOLD, width=line)
    d.line([(margin, h - margin - size), (margin, h - margin - 1)], fill=GOLD, width=line)
    d.line([(margin, h - margin - 1), (margin + size, h - margin - 1)], fill=GOLD, width=line)
    d.line([(w - margin - size, h - margin - 1), (w - margin - 1, h - margin - 1)], fill=GOLD, width=line)
    d.line([(w - margin - 1, h - margin - size), (w - margin - 1, h - margin - 1)], fill=GOLD, width=line)
    return Image.alpha_composite(canvas, ov).convert("RGB")


_LOGO_CACHE = {}
def _logo(target_w):
    if target_w not in _LOGO_CACHE:
        lg = Image.open(LOGO_GOLD).convert("RGBA")
        ratio = target_w / lg.width
        _LOGO_CACHE[target_w] = lg.resize((target_w, int(lg.height * ratio)), Image.LANCZOS)
    return _LOGO_CACHE[target_w]


def logo_metrics(story):
    """Single source of truth for where the logo sits, so layout + plate agree."""
    bottom_pad = 96 if story else 80
    target_w   = 400 if story else 360
    logo = _logo(target_w)
    h = (STORY_H if story else POST_H)
    top = h - bottom_pad - logo.height          # y where the logo starts
    return logo, bottom_pad, top


def add_logo(im, story):
    """Dark plate at the bottom (legibility + separation) + centered ME logo."""
    logo, bottom_pad, top = logo_metrics(story)
    w, h = im.size
    canvas = im.convert("RGBA")
    # Soft dark plate covering the logo band so the gold logo always reads and
    # is visually separated from the content above.
    plate_top = top - 36
    plate = Image.new("L", (1, h - plate_top))
    pp = plate.load()
    span = h - plate_top
    for i in range(span):
        t = i / max(1, span - 1)
        # ramp up to ~190 alpha, hold
        pp[0, i] = int(min(195, 70 + 200 * t))
    plate = plate.resize((w, span))
    dark = Image.new("RGBA", (w, span), (8, 7, 6, 255))
    dark.putalpha(plate)
    canvas.alpha_composite(dark, (0, plate_top))
    # thin gold hairline above the plate
    ImageDraw.Draw(canvas).line([(w * 0.34, plate_top), (w * 0.66, plate_top)], fill=GOLD_DK + (160,), width=1)
    # logo
    canvas.alpha_composite(logo, ((w - logo.width) // 2, top))
    return canvas.convert("RGB")


def safe_bottom(story):
    """Top Y of the logo's protected zone — text must stay above this."""
    _, _, top = logo_metrics(story)
    return top - 54  # 54px breathing room above the plate's hairline


def _frame_corners(img, story):
    margin = 54 if story else 44
    csize  = 90 if story else 70
    cline  = 4 if story else 3
    img = draw_frame(img, margin, gap=(20 if story else 16), outer=(4 if story else 3), inner=1)
    img = draw_corners(img, margin, size=csize, line=cline)
    return img


# ════════════════════════════════════════════════════════════════════════
# Card builders (lang-aware)
# ════════════════════════════════════════════════════════════════════════
def make_quote_card(idx, lang, story=False):
    es, en = content.QUOTES[idx]
    text = es if lang == "es" else en
    w, h = (STORY_W, STORY_H) if story else (POST_W, POST_H)
    img = gradient_bg(w, h)
    d = ImageDraw.Draw(img)

    eyebrow_y = int(h * (0.16 if story else 0.13))
    spaced(d, w / 2, eyebrow_y, STR[lang]["eyebrow_q"], font(FH, 22), GOLD, sp=7)
    d.line([(w * 0.38, eyebrow_y + 42), (w * 0.62, eyebrow_y + 42)], fill=GOLD_DK, width=1)

    qm_y = int(h * (0.24 if story else 0.22))
    d.text((w / 2 - 24, qm_y), "“", font=font(FB, 150), fill=GOLD_DK)

    box_w = int(w * 0.78)
    box_h = int(h * (0.40 if story else 0.38))
    fnt, lines, line_h = fit_lines(d, text, FB, box_w, box_h,
                                   hi=(76 if story else 70), lo=34, line_ratio=1.3)
    y = int(h * (0.40 if story else 0.36))
    for ln in lines:
        lw = d.textlength(ln, font=fnt)
        d.text(((w - lw) / 2, y), ln, font=fnt, fill=CREAM)
        y += line_h
    d.line([(w * 0.42, y + 26), (w * 0.58, y + 26)], fill=GOLD, width=2)

    img = _frame_corners(img, story)
    img = add_logo(img, story)
    return img


def make_blog_card(idx, lang, story=False):
    b = content.BLOG[idx]
    title = b["title_es"] if lang == "es" else b["title_en"]
    hook  = b["hook_es"] if lang == "es" else b["hook_en"]
    w, h = (STORY_W, STORY_H) if story else (POST_W, POST_H)

    src = os.path.join(SOURCE_HERO, b["image"])
    if os.path.exists(src):
        img = darken(cover(Image.open(src).convert("RGB"), w, h), top=0.40, bottom=0.90)
    else:
        img = gradient_bg(w, h)
    d = ImageDraw.Draw(img)

    eyebrow_y = int(h * (0.15 if story else 0.12))
    spaced(d, w / 2, eyebrow_y, STR[lang]["eyebrow_b"], font(FH, 20), GOLD, sp=4)

    box_w = int(w * 0.80)
    tf, tlines, tlh = fit_lines(d, title, FB, box_w, int(h * 0.26),
                                hi=(72 if story else 64), lo=34, line_ratio=1.18)
    hf = font(FR, 30 if story else 27)
    hlines = wrap(d, hook, hf, box_w)
    hlh = int((30 if story else 27) * 1.32)
    cf = font(FH, 22 if story else 20)

    # Anchor the whole block so the CTA ends exactly at the safe line.
    block_h = tlh * len(tlines) + 24 + 18 + hlh * len(hlines) + 14 + 26
    y = safe_bottom(story) - block_h

    for ln in tlines:
        lw = d.textlength(ln, font=tf)
        d.text(((w - lw) / 2, y), ln, font=tf, fill=CREAM)
        y += tlh
    y += 24
    d.line([(w * 0.44, y), (w * 0.56, y)], fill=GOLD, width=2)
    y += 18
    for ln in hlines:
        lw = d.textlength(ln, font=hf)
        d.text(((w - lw) / 2, y), ln, font=hf, fill=DIM)
        y += hlh
    y += 14
    spaced(d, w / 2, y, STR[lang]["cta"], cf, GOLD_LT, sp=2)

    img = _frame_corners(img, story)
    img = add_logo(img, story)
    return img


# ════════════════════════════════════════════════════════════════════════
# Output
# ════════════════════════════════════════════════════════════════════════
def save(img, out_dir, name):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    img.save(path, "JPEG", quality=92, optimize=True)
    return path


def build_quote(idx, lang):
    save(make_quote_card(idx, lang, story=False), OUT_POSTS,   f"q{idx:02d}-{lang}.jpg")
    save(make_quote_card(idx, lang, story=True),  OUT_STORIES, f"q{idx:02d}-{lang}-st.jpg")
    print(f"  ✓ quote {idx:02d} [{lang}]")


def build_blog(idx, lang):
    save(make_blog_card(idx, lang, story=False), OUT_POSTS,   f"b{idx:02d}-{lang}.jpg")
    save(make_blog_card(idx, lang, story=True),  OUT_STORIES, f"b{idx:02d}-{lang}-st.jpg")
    print(f"  ✓ blog  {idx:02d} [{lang}]")


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    mode = sys.argv[1]
    if mode == "batch":
        print(f"Generando {content.quote_count()} quotes + {content.blog_count()} blogs × 2 idiomas...\n")
        for lang in ("es", "en"):
            for i in range(content.quote_count()):
                build_quote(i, lang)
            for i in range(content.blog_count()):
                build_blog(i, lang)
        print(f"\n✓ Listo. Posts en {OUT_POSTS}, stories en {OUT_STORIES}")
    elif mode == "quote" and len(sys.argv) >= 4:
        build_quote(int(sys.argv[2]), sys.argv[3])
    elif mode == "blog" and len(sys.argv) >= 4:
        build_blog(int(sys.argv[2]), sys.argv[3])
    else:
        print(__doc__); sys.exit(1)


if __name__ == "__main__":
    main()
