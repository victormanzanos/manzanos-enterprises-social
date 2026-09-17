#!/usr/bin/env python3
"""contact_sheet.py — hojas de contacto numeradas para revisar imagenes a ojo.
Uso: python3 contact_sheet.py OUT_PREFIX img1 img2 ...   (12 por hoja, 4x3)"""
import sys, os
from PIL import Image, ImageDraw, ImageFont
out, files = sys.argv[1], sys.argv[2:]
TW, TH, COLS, ROWS = 420, 300, 4, 3
F = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
for s in range(0, len(files), COLS * ROWS):
    chunk = files[s:s + COLS * ROWS]
    sheet = Image.new("RGB", (COLS * TW, ROWS * (TH + 30)), "white")
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(chunk):
        try:
            im = Image.open(f).convert("RGB"); im.thumbnail((TW - 8, TH - 8))
        except Exception:
            continue
        x, y = (i % COLS) * TW, (i // COLS) * (TH + 30)
        sheet.paste(im, (x + 4, y + 4))
        d.text((x + 6, y + TH + 2), f"{s + i}: {os.path.basename(f)[:30]}", fill="black", font=F)
    sheet.save(f"{out}-{s // (COLS * ROWS):02d}.jpg", quality=80)
print("ok")
