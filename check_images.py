#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_images.py — control de la regla de 360 dias para el monitor diario (17-sep-2026).

Imprime JSON: repeticiones (<360 dias) en image_history.json, fotos reales publicables
en drop/, imagenes libres en la biblioteca, pendientes de revisar y tarjetas de blog que
comparten fondo. `ok` es False si hay repeticion o el stock baja de los umbrales.
"""
import os, json, datetime
import image_ledger as L

DROP_MIN = 6      # WHY: sale ~1 foto real cada 8 dias; 6 dan ~7 semanas de margen para reponer
LIBRARY_MIN = 20  # WHY: la red de seguridad del motor necesita fotos libres si una tarjeta repite fondo

LOCAL = os.path.dirname(os.path.abspath(__file__))
rows = sorted(L.history(), key=lambda r: r["date"])
repeats = []
for i, a in enumerate(rows):
    for b in rows[i + 1:]:
        same = a["sha1"] == b["sha1"] or L.dist(a["ahash"], b["ahash"]) <= L.AHASH_MAX_DIST
        gap = (datetime.date.fromisoformat(b["date"]) - datetime.date.fromisoformat(a["date"])).days
        # WHY: el historial anterior al 17-sep-2026 es reconstruido (backfill) y ya trae las
        # repeticiones que motivaron la regla; solo se alerta de lo publicado desde entonces.
        if same and gap < L.NO_REPEAT_DAYS and not b.get("backfill"):
            repeats.append({"file": b["file"], "date": b["date"], "prev": a["date"], "prev_file": a["file"]})

drop = os.path.join(LOCAL, "drop")
publishable = []
for n in sorted(os.listdir(drop)):
    p = os.path.join(drop, n)
    if n.lower().endswith((".jpg", ".jpeg", ".png")) and os.path.exists(os.path.splitext(p)[0] + ".txt"):
        if not L.used_recently(p):
            publishable.append(n)

lib = L.library()
blog = json.load(open(os.path.join(LOCAL, "blog.json"), encoding="utf-8"))
from collections import Counter
shared = {k: v for k, v in Counter(b["image"] for b in blog).items() if v > 1}
out = {
    "repeats_since_rule": repeats,
    "drop_publishable": len(publishable),
    # WHY: libres = aprobadas, sin uso en 360 dias y NO asignadas ya a una tarjeta de blog
    "library_free": len(L.library_free(exclude_paths=[os.path.join(LOCAL, b["image"]) for b in blog
                                                        if b["image"].startswith("library/")])),
    "library_pending_review": sum(1 for r in lib if r.get("status") == "pending"),
    "blog_cards_sharing_background": shared,
}
out["ok"] = not repeats and out["drop_publishable"] >= DROP_MIN and out["library_free"] >= LIBRARY_MIN and not shared
print(json.dumps(out, ensure_ascii=False, indent=1))
