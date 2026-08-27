# -*- coding: utf-8 -*-
"""Paneldagi tahrirlarni loyiha fayllariga ko‘chiradi.

Ishlatish (loyiha ildizidan):
    python3 tools/texts/apply_texts.py <panel.html>            # ko‘rish (hech nima o‘zgarmaydi)
    python3 tools/texts/apply_texts.py <panel.html> --yoz      # haqiqatan yozish

<panel.html> — Artifact'dan o‘qib olingan fayl.

Har bir tahrir aynan mos keladigan matn bo‘yicha almashtiriladi.
Xavfsizlik: matn topilmasa yoki 3 tadan ko‘p joyda uchrasa — ogohlantiradi
va o‘sha matnni o‘tkazib yuboradi.
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEXTS = os.path.join(ROOT, "tools", "texts", "texts.json")


def read_panel(path):
    """Panel HTML ichidan saqlangan ma'lumotni ajratib oladi."""
    html = io.open(path, encoding="utf-8").read()
    m = re.search(r'<script type="application/json" id="pnl-data">(.*?)</script>',
                  html, re.S)
    if not m:
        raise SystemExit("Panel ma'lumoti topilmadi: %s" % path)
    return json.loads(m.group(1))


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Ishlatish: python3 tools/texts/apply_texts.py <panel.html> [--yoz]")
    panel_path = sys.argv[1]
    write = "--yoz" in sys.argv

    data = read_panel(panel_path)
    edits = data.get("edits") or {}
    items = {it["id"]: it for it in json.load(io.open(TEXTS, encoding="utf-8"))}

    if not edits:
        print("Panelda hali tahrir yo‘q.")
        return

    # Fayl bo‘yicha guruhlaymiz
    by_file = {}
    skipped = []
    for eid, new in edits.items():
        it = items.get(eid)
        if not it:
            skipped.append(("noma'lum belgi", eid, new))
            continue
        old = it["text"]
        if old.strip() == new.strip():
            continue
        # Nishon nomi oddiy matn emas — u bazada saqlanadi. Uni faqat
        # rename_badges.py orqali o‘zgartirish mumkin.
        if it["area"] == "Nishonlar — nomi":
            skipped.append(("nishon nomi — rename_badges.py ishlating", old, new))
            continue
        by_file.setdefault(it["file"], []).append((old, new.strip(), it["area"]))

    total = 0
    for rel, pairs in sorted(by_file.items()):
        path = os.path.join(ROOT, rel)
        src = io.open(path, encoding="utf-8").read()
        changed = 0
        for old, new, area in pairs:
            n = src.count(old)
            if n == 0:
                skipped.append(("topilmadi (%s)" % rel, old, new))
                continue
            if n > 3:
                skipped.append(("%d joyda uchradi (%s)" % (n, rel), old, new))
                continue
            src = src.replace(old, new)
            changed += n
            total += 1
            print("  %-26s %r\n  %-26s %r\n" % (area + " — eski:", old[:72], "yangi:", new[:72]))
        if write and changed:
            io.open(path, "w", encoding="utf-8").write(src)
        print("%s — %d ta matn (%d joyda)%s\n"
              % (rel, len([p for p in pairs]), changed, "" if write else "  [faqat ko‘rish]"))

    if skipped:
        print("O‘TKAZIB YUBORILDI:")
        for why, old, new in skipped:
            print("  [%s] %r" % (why, old[:70]))

    print("Jami almashtirildi: %d" % total)
    if not write:
        print("\nHaqiqatan yozish uchun oxiriga --yoz qo‘shing.")


if __name__ == "__main__":
    main()
