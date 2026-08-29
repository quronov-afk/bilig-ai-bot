#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Maskot rasmini ilova formatiga o‘tkazadi.

Ega yangi maskot chizdirsa (oq fonli PNG/JPG), shu skript uni ilovadagi
uch xil ko‘rinishga aylantiradi:

  webapp/mascots/mascot-<nom>.webp          — oq fonli (800x436)
  webapp/mascots/mascot-<nom>-cutout.webp   — foni shaffof (800x436)
  webapp/mascots/trim/mascot-<nom>.webp     — chetlari qirqilgan, shaffof

Shuningdek `trim/index.json` ga maskotning asosiy rangi yoziladi — u
ilovada lenta va kartochkalarda ishlatiladi.

Ishlatish:
    python3 tools/add_mascot.py ~/Desktop/qaldirgoch.png qaldirgoch-tekshiruv
"""

import json
import os
import sys
from collections import Counter

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASCOTS = os.path.join(ROOT, "webapp", "mascots")
TRIM = os.path.join(MASCOTS, "trim")
INDEX = os.path.join(TRIM, "index.json")

BOX = (800, 436)          # boshqa maskotlar bilan bir xil o‘lcham
BG_TOLERANCE = 26         # fon rangidan shuncha farq qilsa ham «fon» sanaladi


def drop_background(im):
    """Fonni shaffofga aylantiradi.

    Fon rangi burchak pikselidan olinadi — u har doim oq bo‘lavermaydi
    (ba'zi chizmalarda sutrang yoki krem fon bo‘ladi).

    Diqqat: shunchaki «shu rangdagi hamma pikselni o‘chirish» YARAMAYDI —
    rasm ichidagi oq joylar (xat, qorincha, ko‘z) ham yo‘qolib ketardi.
    Shuning uchun faqat CHETDAN boshlab tutashgan maydon olib tashlanadi.
    """
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    # To‘rtala burchakning o‘rtachasi — fon rangi
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    bg_r = sum(c[0] for c in corners) // 4
    bg_g = sum(c[1] for c in corners) // 4
    bg_b = sum(c[2] for c in corners) // 4

    def is_bg(x, y):
        r, g, b, a = px[x, y]
        return (a > 0 and abs(r - bg_r) <= BG_TOLERANCE
                and abs(g - bg_g) <= BG_TOLERANCE and abs(b - bg_b) <= BG_TOLERANCE)

    stack = []
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))

    seen = set()
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or x < 0 or y < 0 or x >= w or y >= h:
            continue
        seen.add((x, y))
        if not is_bg(x, y):
            continue
        px[x, y] = (bg_r, bg_g, bg_b, 0)
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def fit_into(im, box, background=None):
    """Rasmni belgilangan ramkaga sig‘dirib, markazga qo‘yadi."""
    out = Image.new("RGBA", box, background or (255, 255, 255, 0))
    src = im.copy()
    src.thumbnail(box, Image.LANCZOS)
    out.paste(src, ((box[0] - src.width) // 2, (box[1] - src.height) // 2), src)
    return out


def main_color(im):
    """Maskotning asosiy rangi — eng ko‘p uchraydigan to‘q rang."""
    small = im.convert("RGBA").resize((64, 64))
    counter = Counter()
    for r, g, b, a in small.getdata():
        if a < 200:
            continue
        if r > 235 and g > 235 and b > 235:      # oq
            continue
        if r < 40 and g < 40 and b < 40:         # qora chiziqlar
            continue
        counter[(r // 24 * 24, g // 24 * 24, b // 24 * 24)] += 1
    if not counter:
        return "#8A8A8A"
    r, g, b = counter.most_common(1)[0][0]
    return "#%02X%02X%02X" % (r, g, b)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src_path, name = sys.argv[1], sys.argv[2].strip()
    if not os.path.isfile(src_path):
        print("Fayl topilmadi:", src_path)
        return 1
    os.makedirs(TRIM, exist_ok=True)

    im = Image.open(src_path)
    cut = drop_background(im)

    bbox = cut.getbbox()
    if not bbox:
        print("Rasm bo‘sh chiqdi — fon olib tashlanmadi.")
        return 1
    trimmed = cut.crop(bbox)

    base = "mascot-" + name
    # 1) oq fonli
    fit_into(trimmed, BOX, (255, 255, 255, 255)).convert("RGB").save(
        os.path.join(MASCOTS, base + ".webp"), "WEBP", quality=88, method=6)
    # 2) shaffof fonli
    fit_into(trimmed, BOX).save(
        os.path.join(MASCOTS, base + "-cutout.webp"), "WEBP", quality=88, method=6)
    # 3) chetlari qirqilgani — ilova aynan shuni ishlatadi
    small = trimmed.copy()
    small.thumbnail((480, 480), Image.LANCZOS)
    small.save(os.path.join(TRIM, base + ".webp"), "WEBP", quality=90, method=6)

    # 4) asosiy rang
    try:
        with open(INDEX, encoding="utf-8") as fh:
            index = json.load(fh)
    except Exception:
        index = {}
    index[base] = main_color(trimmed)
    with open(INDEX, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)

    print("Tayyor:")
    print("  ", base + ".webp", "va", base + "-cutout.webp", BOX)
    print("  ", "trim/" + base + ".webp", small.size)
    print("   asosiy rang:", index[base])
    return 0


if __name__ == "__main__":
    sys.exit(main())
