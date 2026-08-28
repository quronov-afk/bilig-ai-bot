#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kitob matnini Word fayllardan ajratib olish — AI'siz, bepul.

Ilova katalogidagi kitoblarni «Mutolaa Word» papkasidan topadi, matnini
ajratadi va uzunligiga qarab tayyorlaydi:

    A daraja  (< 60 000 belgi)   — TO‘LIQ matn
    B daraja  (60–200 ming)      — boshi + o‘rtasidan 10 oyna + oxiri
    C daraja  (> 200 ming)       — birinchi bob + bob sarlavhalari
                                   + o‘rtasidan 20 oyna + oxirgi bob

Nega shunday: badiiy asarda pasport uchun kerak ma'lumot (qahramonlar,
muammo, yechim, saboq) boshi va oxirida to‘plangan; o‘rtasi — voqealar
rivoji, uni oynalar va bob sarlavhalari orqali kuzatib bo‘ladi.

Ishlatish:
    python3 tools/extract_books.py
"""

import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BOOKS_DIR = os.path.expanduser("~/Desktop/Mutolaa Word 28.08.2026")
OUT_DIR = os.path.join("tools", "book_work")

TIER_A_MAX = 60_000        # shundan kichigi to‘liq o‘qiladi
TIER_B_MAX = 200_000       # shundan kichigi tuzilmali kesma

B_HEAD = 0.20              # B: boshining ulushi
B_TAIL = 0.15              # B: oxirining ulushi
B_WINDOWS = 10             # B: o‘rtadagi oynalar soni
B_WINDOW = 2_500           # B: bitta oyna hajmi

C_HEAD = 25_000            # C: birinchi bob o‘rniga shuncha belgi
C_TAIL = 20_000            # C: oxirgi bob
C_WINDOWS = 20             # C: o‘rtadagi oynalar
C_WINDOW = 2_500
C_MAX_HEADINGS = 250       # bob sarlavhalari ro‘yxati chegarasi


# ----------------------------------------------------------------------
# Word fayldan matn
# ----------------------------------------------------------------------
_TAG = re.compile(r"<[^>]+>")
_PARA = re.compile(r"<w:p[ >].*?</w:p>|<w:p/>", re.S)
_STYLE = re.compile(r'w:pStyle w:val="([^"]*)"')
# Word'ning ichki buyruqlari (PAGEREF, TOC, HYPERLINK). Matn emas — tashlanadi.
_INSTR = re.compile(r"<w:instrText[^>]*>.*?</w:instrText>", re.S)
# Mundarija qatori: qisqa va raqam bilan tugaydi («Yigirma birinchi bob   511»)
# Ajratuvchi bo‘lmasligi ham mumkin: Word'ning tab belgisi teg ichida
# yo‘qolganda «Ikki o‘t orasida475» ko‘rinishida qolib ketadi.
# Uzunlik chegarasi keng: ba'zi kitoblarda mundarija qatori butun bir
# jumla bo‘ladi («…qanday suhbat qurganlari xususida hikoya 270»).
_TOC_LINE = re.compile(r"^(?!.*[.!?»”\)]$).{2,400}?\s?\d{1,4}$")


_PAGES = re.compile(r"<Pages>(\d+)</Pages>")


def read_pages(path):
    """Word fayl o‘zida saqlaydigan haqiqiy sahifa soni (topilmasa 0)."""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("docProps/app.xml").decode("utf-8", "ignore")
        m = _PAGES.search(xml)
        return int(m.group(1)) if m else 0
    except Exception:
        return 0


def read_paragraphs(path):
    """Word fayldan (abzas, sarlavhami) juftliklarini qaytaradi."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = _INSTR.sub("", xml)
    # Tab belgisi teg ichida — uni bo‘shliqqa aylantiramiz, aks holda
    # mundarijada bob nomi va sahifa raqami yopishib qoladi.
    xml = re.sub(r"<w:tab\s*/>", " ", xml)
    out = []
    for chunk in _PARA.findall(xml):
        style = _STYLE.search(chunk)
        style = style.group(1).lower() if style else ""
        text = _TAG.sub("", chunk)
        text = text.replace("\xa0", " ").strip()
        if not text:
            continue
        is_head = "heading" in style or "sarlavha" in style or style.startswith("h")
        out.append((text, is_head))
    return drop_toc(out)


def drop_toc(paras, run=8):
    """Mundarija bloklarini olib tashlaydi.

    Mundarija odatda kitob OXIRIDA turadi. Uni qoldirsak, «kitob oxiri»
    deb asar yakunini emas, bob nomlari ro‘yxatini o‘qigan bo‘lardik —
    undan na xulosa, na test chiqadi.

    Belgisi: ketma-ket kelgan qisqa qatorlar, har biri raqam bilan
    tugaydi. Shunday qatorlar `run` tadan ko‘p bo‘lsa — blok tashlanadi.
    """
    flags = [bool(_TOC_LINE.match(t)) or t.strip().isdigit() for t, _ in paras]
    keep = [True] * len(paras)
    i = 0
    while i < len(flags):
        if not flags[i]:
            i += 1
            continue
        j = i
        while j < len(flags) and flags[j]:
            j += 1
        if j - i >= run:
            for k in range(i, j):
                keep[k] = False
        i = j
    return [p for p, k in zip(paras, keep) if k]


def guess_headings(paras):
    """Uslub belgilanmagan fayllarda sarlavhalarni taxmin qiladi.

    Sarlavha — qisqa, nuqta bilan tugamaydigan va ketidan uzun abzas
    keladigan qator. Bu qo‘pol, lekin kitob skeletini olish uchun yetarli.
    """
    heads = []
    for i, (text, is_head) in enumerate(paras):
        if is_head:
            heads.append(text)
            continue
        if len(text) > 70 or text.endswith((".", "!", "?", ":", ",", ";")):
            continue
        nxt = paras[i + 1][0] if i + 1 < len(paras) else ""
        if len(nxt) > 200:
            heads.append(text)
    return heads


# ----------------------------------------------------------------------
# Uzunligiga qarab tayyorlash
# ----------------------------------------------------------------------
def windows(text, start, end, count, size):
    """[start, end] oralig‘idan teng masofada `count` ta oyna kesib oladi."""
    span = end - start
    if span <= 0 or count <= 0:
        return []
    step = span / count
    parts = []
    for i in range(count):
        a = int(start + i * step)
        parts.append(text[a:a + size])
    return parts


def prepare(text, paras):
    """(tayyor_matn, qamrov) qaytaradi."""
    n = len(text)
    if n <= TIER_A_MAX:
        return text, "to‘liq"

    if n <= TIER_B_MAX:
        head = int(n * B_HEAD)
        tail = int(n * B_TAIL)
        mid = windows(text, head, n - tail, B_WINDOWS, B_WINDOW)
        body = ("[KITOB BOSHI — to‘liq]\n" + text[:head] +
                "\n\n[O‘RTASIDAN KESMALAR]\n" +
                "\n\n[...]\n\n".join(mid) +
                "\n\n[KITOB OXIRI — to‘liq]\n" + text[n - tail:])
        return body, "kesma"

    heads = guess_headings(paras)[:C_MAX_HEADINGS]
    mid = windows(text, C_HEAD, n - C_TAIL, C_WINDOWS, C_WINDOW)
    skeleton = ""
    if heads:
        skeleton = ("\n\n[KITOB SKELETI — bob sarlavhalari, boshidan oxirigacha]\n" +
                    "\n".join("· " + h for h in heads))
    body = ("[KITOB BOSHI — to‘liq]\n" + text[:C_HEAD] +
            skeleton +
            "\n\n[O‘RTASIDAN KESMALAR]\n" +
            "\n\n[...]\n\n".join(mid) +
            "\n\n[KITOB OXIRI — to‘liq]\n" + text[n - C_TAIL:])
    return body, "kesma"


# ----------------------------------------------------------------------
# Katalog bilan solishtirish
# ----------------------------------------------------------------------
def norm(t):
    t = (t or "").lower()
    for ch in ("ʻ", "`", "'", "’"):
        t = t.replace(ch, "‘")
    t = re.sub(r"[^\w\s‘]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def slug(t):
    t = norm(t).replace("‘", "")
    return re.sub(r"\s+", "-", t)[:60]


def main():
    from config import RECOMMENDED_BOOKS

    if not os.path.isdir(BOOKS_DIR):
        print("Papka topilmadi:", BOOKS_DIR)
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)

    files = [f for f in os.listdir(BOOKS_DIR)
             if f.endswith(".docx") and "_tanishuv" not in f]
    normed = [(f, norm(f)) for f in files]

    index, missing, seen = [], [], set()
    for age, titles in RECOMMENDED_BOOKS.items():
        for raw in titles:
            text = (raw or "").strip().rstrip(".")
            if "." in text:
                title, author = text.split(".", 1)
            else:
                title, author = text, ""
            title, author = title.strip(), author.strip()
            key = norm(title)
            if len(key) < 4:
                missing.append(title)
                continue
            hits = [f for f, nf in normed if key in nf]
            if not hits:
                missing.append(title)
                continue
            # Bir nechta mos kelsa — nomi eng qisqasi (aniqrog‘i) olinadi
            fname = sorted(hits, key=len)[0]
            if fname in seen:
                continue
            seen.add(fname)

            path = os.path.join(BOOKS_DIR, fname)
            try:
                paras = read_paragraphs(path)
            except Exception as e:
                missing.append("%s (o‘qib bo‘lmadi: %s)" % (title, e))
                continue
            full = "\n".join(p for p, _ in paras)
            body, coverage = prepare(full, paras)

            genre = re.search(r"\(([^)]*)\)", fname)
            genre = genre.group(1) if genre else ""

            out_name = slug(title) + ".txt"
            with open(os.path.join(OUT_DIR, out_name), "w", encoding="utf-8") as fh:
                fh.write("NOMI: %s\nMUALLIFI: %s\nJANRI: %s\n"
                         "YOSH GURUHI: %s\nJAMI BELGI: %d\nQAMROV: %s\n\n%s\n"
                         % (title, author, genre, age, len(full), coverage,
                            "=" * 60))
                fh.write(body)

            index.append({
                "title": title, "author": author, "genre": genre,
                "pages": read_pages(path),
                "age_group": age, "file": fname, "work_file": out_name,
                "chars": len(full), "sent_chars": len(body),
                "coverage": coverage, "done": False,
            })

    index.sort(key=lambda b: (b["age_group"], b["title"]))
    with open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)

    total = sum(b["chars"] for b in index)
    sent = sum(b["sent_chars"] for b in index)
    print("Tayyorlandi: %d ta kitob" % len(index))
    print("  to‘liq o‘qiladi : %d ta" % sum(1 for b in index if b["coverage"] == "to‘liq"))
    print("  kesma           : %d ta" % sum(1 for b in index if b["coverage"] == "kesma"))
    print("  kitoblar matni  : %.1f mln belgi" % (total / 1e6))
    print("  men o‘qiydiganim: %.1f mln belgi (%.0f%% tejaldi)"
          % (sent / 1e6, 100 - sent * 100.0 / total))
    print("  papka           : %s" % OUT_DIR)
    if missing:
        print("\nTopilmadi (%d ta): %s" % (len(missing), ", ".join(missing[:8])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
