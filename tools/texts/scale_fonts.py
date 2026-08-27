# -*- coding: utf-8 -*-
"""Ilovadagi shrift o‘lchamlarini kattalashtiradi.

Bolalar ilovasi uchun 10-13px juda mayda. Jadval pastki (mayda)
o‘lchamlarni ko‘proq, yuqorigilarini kamroq kattalashtiradi —
shunda sarlavha bilan izoh orasidagi farq saqlanadi.

Ishlatish:
    python3 tools/texts/scale_fonts.py          # ko‘rish
    python3 tools/texts/scale_fonts.py --yoz    # yozish

Qaytarish: git checkout webapp/style.css webapp/app.js
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FILES = ["webapp/style.css", "webapp/app.js"]

# eski -> yangi. Pastda +2, tepada +1 — tartib buzilmaydi.
TABLE = {
    "9.5": "11.5", "10": "12", "10.5": "12.5",
    "11": "13", "11.5": "13.5",
    "12": "14", "12.5": "14.5", "12.8": "14.5",
    "13": "15", "13.5": "15.5",
    "14": "16", "14.5": "16.5",
    "15": "17", "15.5": "17.5",
    "16": "18", "17": "19", "18": "20",
    "22": "23", "24": "25", "27": "28", "28": "29", "30": "31", "38": "39",
}


def main():
    write = "--yoz" in sys.argv
    total = 0
    for rel in FILES:
        path = os.path.join(ROOT, rel)
        src = io.open(path, encoding="utf-8").read()
        seen = {}

        def sub(m):
            old = m.group(2)
            new = TABLE.get(old)
            if not new:
                return m.group(0)
            seen[old] = seen.get(old, 0) + 1
            return m.group(1) + new + "px"

        out = re.sub(r"(font-size:\s*)([0-9.]+)px", sub, src)
        n = sum(seen.values())
        total += n
        if write and n:
            io.open(path, "w", encoding="utf-8").write(out)
        print("%s — %d ta o‘lcham" % (rel, n))
        for old in sorted(seen, key=float):
            print("    %5s px → %-5s px   (%d joyda)" % (old, TABLE[old], seen[old]))
        print()

    print("Jami: %d ta%s" % (total, "" if write else "   [faqat ko‘rish]"))


if __name__ == "__main__":
    main()
