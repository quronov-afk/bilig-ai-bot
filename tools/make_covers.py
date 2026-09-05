#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Muqovasi yo‘q kitoblarga muqova tayyorlash (ega qarori, 2026-09-05).

Ikki xil yo‘l bilan ishlaydi:

  1. SHAXSIY RIVOJLANISH kitoblari — muqova mutolaa.com'dan ASLIDA
     olinadi. Sabab: bular zamonaviy nashrlar, ularning muqovasi
     tanilgan va uni qayta chizishning ma'nosi yo‘q. Ega mutolaa.com
     rahbari, ruxsat bergan.

  2. QOLGAN HAMMASI — kitobning MAZMUNIDAN kelib chiqib chiziladi.
     Eski muqovalarimiz bilan bir xil uslub: `redesign_covers.py`
     dagi ART uslublari, joylashuv qoidasi va shrift tanlovi shu
     yerdan olinadi — natija bitta oilaga o‘xshab tursin.

Model: `gemini-3.1-flash-lite-image` — ega ataylab shu modelni
tanladi, qolganlari qimmat.

Ishlatish:
    python3 tools/make_covers.py --namuna 2     # 2 ta sinov
    python3 tools/make_covers.py --asl          # faqat mutolaa nusxalari
    python3 tools/make_covers.py --hammasi
    python3 tools/make_covers.py --narx         # faqat hisob
"""
import gzip
import io
import json
import os
import re
import sys
import time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def load_env():
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


load_env()

import requests                                        # noqa: E402
from PIL import Image                                  # noqa: E402
from tools import redesign_covers as rc                 # noqa: E402

OUT_DIR = os.path.join(ROOT, "webapp", "covers_new")
RAW_DIR = os.path.join(OUT_DIR, "_xom")
SEED = os.path.join(ROOT, "books_seed.json.gz")
WORK_INDEX = os.path.join(ROOT, "tools", "book_work2", "index.json")
COVER_INDEX = os.path.join(ROOT, "webapp", "covers", "index.json")
SLUGS = os.path.join(ROOT, "tools", "kitob_royxat", "mut_books.txt")
MUTOLAA = "https://mutolaa.com/uz/book/"

# gemini-3.1-flash-lite-image tarifi, $ / 1 mln token
PRICE_IN, PRICE_OUT = 0.10, 0.40
IMG_TOKENS = 1290          # bitta rasm uchun chiqish tokeni (1024x1024)


# ==========================================================
# 1-QISM — QAYSI KITOBGA MUQOVA KERAK
# ==========================================================
def norm(s):
    """Solishtirish uchun soddalashtirilgan ko‘rinish."""
    s = (s or "").lower()
    for ch in "ʻʼ‘’'`´":
        s = s.replace(ch, "")
    return re.sub(r"[^a-z0-9а-яё]+", "", s)


def slug_form(s):
    """Nomni mutolaa.com dagi manzil ko‘rinishiga o‘xshatadi."""
    s = (s or "").lower()
    for ch in "ʻʼ‘’'`´":
        s = s.replace(ch, "-")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def missing_books():
    """To‘plamdagi kitoblardan muqovasi yo‘qlari, bo‘limi bilan birga."""
    idx = json.load(open(COVER_INDEX, encoding="utf-8"))
    have = {norm(k) for k in idx}

    data = json.loads(gzip.decompress(open(SEED, "rb").read()).decode("utf-8"))
    books = data.get("books") or []

    work = json.load(open(WORK_INDEX, encoding="utf-8"))
    items = work if isinstance(work, list) else work.get("books", work)
    section = {norm(b["title"]): b.get("section", "") for b in items}
    genre = {norm(b["title"]): b.get("genre", "") for b in items}

    out = []
    for b in books:
        t = b.get("title") or ""
        if norm(t) in have:
            continue
        p = b.get("passport") or {}
        out.append({
            "title": t,
            "author": b.get("author") or "",
            "section": section.get(norm(t), ""),
            "genre": genre.get(norm(t), ""),
            "age_band": p.get("age_band") or "",
            "mood": p.get("mood") or "",
            "topics": ", ".join(p.get("topics") or []),
            "summary": p.get("summary") or "",
            "characters": p.get("characters") or "",
            "theme": p.get("theme") or "",
        })
    return out


def out_name(book):
    return slug_form(book["title"])[:60] + ".jpg"


# ==========================================================
# 2-QISM — MUTOLAA'DAN ASL MUQOVA
# ==========================================================
_slug_cache = None


def slug_list():
    global _slug_cache
    if _slug_cache is None:
        seen = set()
        for line in open(SLUGS, encoding="utf-8"):
            s = line.strip().split('"')[0].strip()
            if s and re.fullmatch(r"[a-z0-9\-]+", s):
                seen.add(s)
        _slug_cache = sorted(seen)
    return _slug_cache


def find_slug(title):
    """Kitob nomiga ANIQ mos mutolaa manzilini topadi.

    DIQQAT (2026-09-05 da tuzatilgan xato): ilgari bu yerda "taxminiy"
    moslashtirish ham bor edi — nom manzil ichida qisman uchrasa ham
    mos deb olinardi. Natijada «Ego — dushmaning» kitobiga «dushman»
    degan BUTUNLAY BOSHQA kitobning muqovasi (hattoki mutolaa
    logotipi bilan) yopishtirilib qoldi. Endi FAQAT ANIQ MOS kelgan
    manzil qabul qilinadi — mos kelmasa, chaqiruvchi tomon kitobni
    mazmunidan chizadi (asl nusxa yo‘qligi xato emas, oddiy holat)."""
    want = slug_form(title).replace("-", "")
    for s in slug_list():
        if s.replace("-", "") == want:
            return s
    return None


def original_cover(title):
    """mutolaa.com dan asl muqovani yuklab oladi. Topilmasa None."""
    slug = find_slug(title)
    if not slug:
        return None, "manzil topilmadi"
    try:
        html = requests.get(MUTOLAA + slug, timeout=25).text
    except Exception as e:
        return None, "sahifa ochilmadi: %r" % (e,)
    m = re.search(r"url=(https%3A%2F%2Fcdn-minio\.mutolaa\.com%2F[^&\"']+)", html)
    if not m:
        return None, "muqova manzili yo‘q"
    url = urllib.parse.unquote(m.group(1))
    try:
        r = requests.get(url, timeout=40)
        r.raise_for_status()
        return Image.open(io.BytesIO(r.content)).convert("RGB"), slug
    except Exception as e:
        return None, "rasm yuklanmadi: %r" % (e,)


# ==========================================================
# 3-QISM — MAZMUNDAN CHIZISH
# ==========================================================
def desc_from_book(b):
    """Pasportdan `redesign_covers` kutadigan tavsif tuzadi.

    Eski vositada bu tavsif ESKI MUQOVAGA qarab yozilardi. Bu yerda
    muqova yo‘q — shuning uchun kitobning o‘z mazmuni ishlatiladi.
    """
    return {
        "subject": b["summary"][:700],
        "characters": b["characters"][:300],
        "setting": b["theme"][:300],
        "mood": b["mood"] or b["topics"],
        "palette": "",
        "audience": "",
        "tone": "",
    }


def draw_cover(b):
    """Kitobga muqova chizadi va nom/muallifni yozadi."""
    d = desc_from_book(b)
    art_key, font_key, group, tone = rc.pick(d, b)

    # Dostonlar va tarixiy asarlarda personaj chizish xavfli (mashhur
    # tarixiy shaxslar) — ularda manzara muqovasi ishlatiladi.
    manzara = (tone == "tarixiy" or "doston" in (b.get("genre") or "")
               or b["section"] in ("Diniy-ma'rifiy", "Navoiy va Sharq dostonlari"))
    prompt = (rc.scene_prompt(d, art_key) if manzara
              else rc.art_prompt(d, art_key))

    im, usage = rc.make_art(prompt)
    raw = os.path.join(RAW_DIR, out_name(b).replace(".jpg", ".png"))
    im.save(raw)
    # DIQQAT: draw_text YANGI rasm qaytaradi (o‘lchamini ham to‘g‘rilaydi),
    # eskisini o‘zgartirmaydi. Qaytgan qiymatni olish SHART.
    im = rc.draw_text(im, b["title"], b["author"], font_key)
    return im, usage, art_key, manzara


# ==========================================================
# 4-QISM — ISHGA TUSHIRISH
# ==========================================================
MANIFEST = os.path.join(ROOT, "tools", "book_out2", "_cover_manifest.json")


def _remember(manifest, book):
    manifest[out_name(book)] = {"title": book["title"], "author": book["author"]}


def main():
    args = sys.argv[1:]
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    manifest = {}
    if os.path.exists(MANIFEST):
        manifest = json.load(open(MANIFEST, encoding="utf-8"))

    books = missing_books()
    asl = [b for b in books if b["section"] == "Shaxsiy rivojlanish"]
    chiz = [b for b in books if b["section"] != "Shaxsiy rivojlanish"]

    # Allaqachon tayyor bo‘lganlarini o‘tkazib yuboramiz
    asl = [b for b in asl if not os.path.exists(os.path.join(OUT_DIR, out_name(b)))]
    chiz = [b for b in chiz if not os.path.exists(os.path.join(OUT_DIR, out_name(b)))]

    if "--narx" in args:
        est = len(chiz) * (2000 / 1e6 * PRICE_IN + IMG_TOKENS / 1e6 * PRICE_OUT)
        print("Mutolaa'dan olinadi: %d ta (tekin)" % len(asl))
        print("Chiziladi:           %d ta, taxminan $%.2f" % (len(chiz), est))
        return 0

    limit = 0
    if "--namuna" in args:
        limit = int(args[args.index("--namuna") + 1])
        asl, chiz = asl[:1], chiz[:limit]
    if "--asl" in args:
        chiz = []

    print("Mutolaa'dan: %d ta · chiziladi: %d ta\n" % (len(asl), len(chiz)))

    ok = xato = 0
    tin = tout = 0
    for b in asl:
        im, info = original_cover(b["title"])
        if im is not None:
            im.save(os.path.join(OUT_DIR, out_name(b)), quality=90)
            _remember(manifest, b)
            print("  ✓ %-42s asl nusxa (%s)" % (b["title"][:42], info))
            ok += 1
            continue
        # Asl nusxa topilmadi (odatiy holat) — mazmunidan chizamiz.
        try:
            im, usage, art, manzara = draw_cover(b)
            im.save(os.path.join(OUT_DIR, out_name(b)), quality=90)
            tin += getattr(usage, "prompt_token_count", 0) or 0
            tout += getattr(usage, "candidates_token_count", 0) or 0
            _remember(manifest, b)
            print("  ✓ %-42s chizildi (%s — %s)" % (b["title"][:42], info, art))
            ok += 1
        except Exception as e:
            print("  ✗ %-42s asl yo‘q (%s), chizish ham chiqmadi: %r"
                  % (b["title"][:42], info, e))
            xato += 1

    for i, b in enumerate(chiz, 1):
        t0 = time.time()
        try:
            im, usage, art, manzara = draw_cover(b)
            im.save(os.path.join(OUT_DIR, out_name(b)), quality=90)
            tin += getattr(usage, "prompt_token_count", 0) or 0
            tout += getattr(usage, "candidates_token_count", 0) or 0
            _remember(manifest, b)
            print("  ✓ [%d/%d] %-38s %s%s  %.0fs"
                  % (i, len(chiz), b["title"][:38], art,
                     " (manzara)" if manzara else "", time.time() - t0))
            ok += 1
        except Exception as e:
            print("  ✗ [%d/%d] %-38s %r" % (i, len(chiz), b["title"][:38], e))
            xato += 1

    json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    narx = tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT
    print("\nYAKUN: %d ta tayyor, %d ta chiqmadi. Sarflandi: $%.2f" % (ok, xato, narx))
    return 0


if __name__ == "__main__":
    sys.exit(main())
