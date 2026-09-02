#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yakuniy ro‘yxatdagi kitoblar matnini «Mutolaa Word» papkasidan ajratadi.

Manba: ~/Desktop/Mutolaa Word 28.08.2026 (3407 ta .docx).
Ro‘yxat: tools/kitob_royxat/final_list.py (183 ta asar).
Natija: tools/book_work2/<slug>.txt + index.json

AI ishlatilmaydi — bepul va tez.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tools.extract_books import read_pages, read_paragraphs, prepare, slug  # noqa

SRC = os.path.expanduser("~/Desktop/Mutolaa Word 28.08.2026")
OUT_DIR = os.path.join(ROOT, "tools", "book_work2")
LISTDIR = os.path.join(ROOT, "tools", "kitob_royxat")

# yosh toifasi -> eski «age_group» (variantlar soni shunga qarab: 12 -> 4 ta)
BAND2GROUP = {"7-8": "6", "9-10": "8", "11-13": "12", "14-16": "12", "17-19": "12"}


def load_list():
    old = os.getcwd()
    os.chdir(LISTDIR); sys.path.insert(0, LISTDIR)
    import final_list as FL
    os.chdir(old)
    return FL


def main():
    FL = load_list()
    os.makedirs(OUT_DIR, exist_ok=True)
    old = os.getcwd(); os.chdir(LISTDIR)
    import match
    index, missing, seen = [], [], set()
    for section, rows in FL.SECTIONS:
        diniy = section.startswith("Diniy")
        for title, author, band, ok, izoh in rows:
            t = title.strip("«»").split(" (")[0]
            s, x = match.find(t, author)
            if s < 0.8:
                s2, x2 = match.find(t)
                if s2 >= 0.9: s, x = s2, x2
            if s < 0.8 or not x:
                missing.append((title, author)); continue
            fname = x["f"]
            if x["tan"]:                     # faqat tanishuv parchasi bo‘lsa
                alt = [y for y in match.files
                       if y['n'] == x['n'] and y['na'] == x['na'] and not y['tan']]
                if alt: fname = alt[0]["f"]
            if fname in seen: continue
            seen.add(fname)
            path = os.path.join(SRC, fname)
            try:
                paras = read_paragraphs(path)
            except Exception as e:
                missing.append((title, "o‘qilmadi: %s" % e)); continue
            full = "\n".join(p for p, _ in paras)
            # Mutolaa matnlarida oʻ/gʻ uchun U+02BB, tutuq uchun U+02BC
            # ishlatilgan. Bizning imlo qoidamizga keltiramiz.
            full = full.replace("\u02bb", "\u2018").replace("\u02bc", "'")
            body, coverage = prepare(full, paras)
            genre = x["janr"] or ("doston" if "doston" in section.lower()
                                  else "diniy-ma'rifiy" if diniy else "asar")
            out_name = slug(t) + ".txt"
            with open(os.path.join(OUT_DIR, out_name), "w", encoding="utf-8") as fh:
                fh.write("NOMI: %s\nMUALLIFI: %s\nJANRI: %s\nYOSH TOIFASI: %s\n"
                         "JAMI BELGI: %d\nQAMROV: %s\n\n%s\n"
                         % (t, author, genre, band, len(full), coverage, "=" * 60))
                fh.write(body)
            index.append({
                "title": t, "author": author, "genre": genre,
                "band": band, "age_group": BAND2GROUP.get(band, "12"),
                "section": section, "mode": "diniy" if diniy else "oddiy",
                "pages": read_pages(path), "file": fname, "work_file": out_name,
                "chars": len(full), "sent_chars": len(body),
                "coverage": coverage, "done": False,
            })
    os.chdir(old)
    index.sort(key=lambda b: (b["band"], b["title"]))
    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
    print("Tayyorlandi: %d ta kitob" % len(index))
    for band in sorted({b["band"] for b in index}):
        print("  %-6s %3d ta" % (band, sum(1 for b in index if b["band"] == band)))
    print("  to‘liq: %d · kesma: %d"
          % (sum(1 for b in index if b["coverage"] == "to‘liq"),
             sum(1 for b in index if b["coverage"] != "to‘liq")))
    print("Topilmadi: %d ta" % len(missing))
    for t, a in missing[:40]:
        print("   ·", t, "|", a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
