#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bugun (2026-09-05) chizilgan/yuklab olingan muqovalarni asosiy
katalogga qo‘shadi: `webapp/covers/` ga WebP qilib ko‘chiradi va
`webapp/covers/index.json` ni yangilaydi.

DIQQAT: bu skript FAQAT `tools/make_covers.py` chiqargan yangi
fayllarni qo‘shadi (`_manifest.json` orqali). 2026-08-29 dagi 147 ta
qayta chizilgan ESKI muqova (`redesign_covers.py`) ga tegilmaydi —
ular hali ega tasdiqlashini kutmoqda ([[muqova-dizayni]]).
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW_DIR = os.path.join(ROOT, "webapp", "covers_new")
COVERS = os.path.join(ROOT, "webapp", "covers")
INDEX = os.path.join(COVERS, "index.json")
MANIFEST = os.path.join(ROOT, "tools", "book_out2", "_cover_manifest.json")

from PIL import Image  # noqa: E402


def ckey(s):
    s = (s or "").lower()
    for ch in "ʻʼ‘’'`´":
        s = s.replace(ch, " ")
    import re
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9а-яё\s]+", " ", s)).strip()


def main():
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    idx = json.load(open(INDEX, encoding="utf-8"))

    added = skipped = 0
    for jpg_name, info in manifest.items():
        src = os.path.join(NEW_DIR, jpg_name)
        if not os.path.exists(src):
            skipped += 1
            continue
        webp_name = jpg_name[:-4] + ".webp"
        dst = os.path.join(COVERS, webp_name)
        im = Image.open(src).convert("RGB")
        im.save(dst, "WEBP", quality=82)

        title, author = info["title"], info.get("author", "")
        for k in {ckey(title), ckey(title + " " + author)}:
            if k:
                idx[k] = webp_name
        added += 1

    io.open(INDEX, "w", encoding="utf-8").write(
        json.dumps(idx, ensure_ascii=False, indent=1))
    print("Qo‘shildi: %d ta muqova, indeksda jami %d kalit (o‘tkazib yuborildi: %d)"
          % (added, len(idx), skipped))


if __name__ == "__main__":
    main()
