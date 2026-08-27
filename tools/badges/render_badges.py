# -*- coding: utf-8 -*-
"""Nishon chizmalarini SVG fayllarga chiqaradi.

Ishlatish (loyiha ildizidan):
    python3 tools/badges/render_badges.py

Natija: webapp/badges/<slug>.svg (29 ta) va webapp/badges/index.json
(har bir nishonning nomi va berilish sharti).
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from badges_core import frame          # noqa: E402
from badge_defs import BADGES, PAL, MSG  # noqa: E402

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "webapp", "badges"
)


def svg(slug, uid=None):
    name, cond, pal, emblem = BADGES[slug]
    p = PAL[pal]
    uid = uid or slug.replace("-", "")
    return (f'<svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="{name}">'
            f'{frame(uid, p[0], p[1], p[2], p[3], p[4], p[5], p[6])}{emblem}</svg>')


def all_svgs():
    return {s: (BADGES[s][0], BADGES[s][1], svg(s)) for s in BADGES}


def palette_of(slug):
    """Nishonning rang oilasi va asosiy ranglari.

    Tabrik ekrani foni shu ranglardan quriladi — har bir nishon o‘z
    rangida nishonlanadi, fon nishon bilan uyg‘un bo‘ladi.
    """
    pal = BADGES[slug][2]
    rim_a, rim_b, field_a, field_b, orn = PAL[pal][:5]
    return {"pal": pal, "rim": rim_a, "rim_dark": rim_b,
            "field": field_a, "orn": orn}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    meta = {}
    for slug, (name, cond, markup) in all_svgs().items():
        io.open(os.path.join(OUT_DIR, slug + ".svg"), "w", encoding="utf-8").write(markup)
        meta[slug] = dict({"name": name, "cond": cond, "msg": MSG.get(slug, "")},
                          **palette_of(slug))
    io.open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8").write(
        json.dumps(meta, ensure_ascii=False, indent=1)
    )
    print(f"{len(meta)} ta nishon saqlandi: {OUT_DIR}")


if __name__ == "__main__":
    main()
