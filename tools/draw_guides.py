#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==========================================================
# tools/draw_guides.py
# ----------------------------------------------------------
# KO‘RSATMA CHIZMALARINI chizadi — bola o‘qimasdan ham nima qilishini
# tushunadigan ikkita rasm:
#
#   sahifa — sahifani rasmga olish oynasi uchun
#   ovoz   — ovozli xulosa oynasi uchun
#
# NEGA AI: avval bu chizmalar qo‘lda (SVG) chizilgan edi. Ega ma'nosini
# ma'qulladi, lekin «chiroyli chiqmagan» dedi — shuning uchun ilovaning
# maskotlari bilan bir uslubda qayta chizdiriladi.
#
# SABOQ (muqovalardan): AI rasm ichiga YOZUV yozsa, o‘zbekcha imlo
# buziladi. Shuning uchun promptda yozuv butunlay taqiqlanadi; kerakli
# raqam (bet raqami) ham chizilmaydi — uni keyin o‘zimiz qo‘yamiz.
#
# Ishlatish:
#   python3 tools/draw_guides.py                 (ikkalasi, 1 tadan)
#   python3 tools/draw_guides.py --only sahifa
#   python3 tools/draw_guides.py --variants 2    (har biriga 2 xil namuna)
#
# Natija: tools/guides_raw/<nom>-1.png
# ==========================================================
import argparse
import io
import os
import sys
import time

from google import genai
from google.genai import types
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "tools", "guides_raw")

IMAGE_MODEL = "gemini-3.1-flash-lite-image"


def load_env():
    """.env faylidan kalitni o‘qiydi (python-dotenv o‘rnatilmagan)."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


load_env()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    sys.exit("GEMINI_API_KEY topilmadi (.env faylini tekshiring)")

client = genai.Client(api_key=API_KEY)


# ==========================================================
# USLUB — ilovadagi maskotlar bilan bir xil bo‘lishi shart
# ----------------------------------------------------------
# Namuna: webapp/mascots/mascot-boyogli-oqish.webp — qalin iliq jigarrang
# konturli, yassi ranglar bilan chizilgan, krem fonli bolalar kitobi
# uslubi. Yangi chizma undan ajralib turmasligi kerak.
# ==========================================================
STYLE = (
    "Flat vector cartoon illustration in a warm children's picture-book style. "
    "Thick, even, dark warm-brown outlines around every shape. Flat fill colours "
    "with only very soft shading, no gradients, no photo realism, no 3D render. "
    "Warm limited palette: amber, honey, terracotta, soft brown, cream, with one "
    "calm blue accent. Plain flat cream background (#F6EBD4), completely empty — "
    "no pattern, no border, no frame, no vignette, no shadow behind the scene. "
    "Friendly, rounded, cosy, cute. Centred composition with generous empty margin "
    "on all four sides."
)

# MUHIM: rasm ichida hech qanday yozuv bo‘lmasin.
NO_TEXT = (
    "ABSOLUTELY NO text anywhere: no letters, no words, no numbers, no digits, "
    "no captions, no labels, no signature, no watermark, no logo, no speech "
    "bubble with writing. The book pages must show only faint plain horizontal "
    "lines standing in for writing, never real letters."
)

SCENES = {
    # ------------------------------------------------------
    # 1. Sahifani rasmga olish.
    # Bola shuni tushunishi kerak: telefonni ochiq betga to‘g‘rila.
    # Shuning uchun telefon EKRANI ko‘rinadi va unda o‘sha bet turadi.
    # ------------------------------------------------------
    "sahifa": (
        "A cute cartoon owl character with large friendly eyes, wearing a small "
        "square embroidered Uzbek doppi cap, sitting behind a big open book that "
        "lies flat on a table with its pages facing up. The owl holds up a modern "
        "smartphone in both wings, horizontally above the book, pointing the phone's "
        "camera straight down at the open right-hand page. The phone screen faces "
        "the viewer and clearly shows that same open book page inside it, so it "
        "reads as a live camera view. Four small blue camera focus corner brackets "
        "sit inside the phone screen around the page. Two tiny blue sparkles near "
        "the top corner of the phone suggest the picture being taken. The owl looks "
        "cheerful and is looking at the phone screen. Full body, seen from the front."
    ),

    # ------------------------------------------------------
    # 3. Bet raqamini qo‘lda yozish.
    # Bola shuni tushunishi kerak: kitobning burchagidagi raqamni
    # ko‘chirib yoz. Shuning uchun boyo‘g‘li bir qo‘li bilan bet
    # burchagini ko‘rsatib, ikkinchisi bilan telefonga yozyapti.
    # ------------------------------------------------------
    "raqam": (
        "A cute cartoon owl character with large friendly eyes, wearing a small "
        "square embroidered Uzbek doppi cap, sitting behind a big open book that "
        "lies flat on a table with its pages facing up. With one wing the owl points "
        "with a wooden pencil at the bottom outer corner of the open right-hand page, "
        "where a small blue circle marks the spot. With its other wing it holds a "
        "modern smartphone upright, screen facing the viewer, showing one single "
        "large empty rounded input box outlined in blue in the middle of the screen "
        "and a small blue button below it. The owl looks focused and helpful, glancing "
        "between the page corner and the phone. Full body, seen from the front."
    ),

    # ------------------------------------------------------
    # 2. Ovozli xulosa.
    # Bola shuni tushunishi kerak: kitob haqida OVOZDA gapir.
    # ------------------------------------------------------
    "ovoz": (
        "A cute cartoon owl character with large friendly eyes, wearing a small "
        "square embroidered Uzbek doppi cap, sitting cheerfully with its beak open "
        "as if talking warmly. A closed book rests against its side. The owl holds "
        "a modern smartphone up near its beak in one wing, like a microphone, with "
        "the screen turned slightly away. Three simple curved blue sound-wave arcs "
        "of increasing size come out towards the right side, showing that it is "
        "speaking. The owl looks happy and animated, mid-sentence. Full body, seen "
        "from the front."
    ),
}


def draw(name, index):
    prompt = SCENES[name] + " " + STYLE + " " + NO_TEXT
    last = None
    for attempt in range(4):
        try:
            r = client.models.generate_content(
                model=IMAGE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="16:9"),
                ),
            )
            for part in r.candidates[0].content.parts:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    im = Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
                    os.makedirs(OUT_DIR, exist_ok=True)
                    path = os.path.join(OUT_DIR, "%s-%d.png" % (name, index))
                    im.save(path)
                    return path
            last = "rasm qaytmadi"
        except Exception as e:
            last = repr(e)
            time.sleep(2 + attempt * 3)
    print("  XATO (%s): %s" % (name, last))
    return None


# ==========================================================
# ILOVA FORMATIGA O‘TKAZISH
# ----------------------------------------------------------
# Tanlangan xom rasm chetidagi bo‘sh maydon qirqiladi va webp ga
# o‘tkaziladi. Fon KREM holicha qoladi (shaffof qilinmaydi): sahifa
# chizmasidagi stol rasmning chetigacha boradi, uni kesib olsak
# g‘alati ko‘rinadi. Ilovada chizma o‘sha krem kartochkada turadi.
# ==========================================================
GUIDE_DIR = os.path.join(ROOT, "webapp", "guides")
OUT_W = 760                      # ikki barobar — qalin ekranlar uchun
BG_TOL = 12


def trim_border(im):
    """Chetdagi bir xil rangli bo‘sh maydonni qirqadi."""
    im = im.convert("RGB")
    w, h = im.size
    px = im.load()
    bg = px[2, 2]

    def same(c):
        return all(abs(c[i] - bg[i]) <= BG_TOL for i in range(3))

    def row_empty(y):
        return all(same(px[x, y]) for x in range(0, w, 3))

    def col_empty(x):
        return all(same(px[x, y]) for y in range(0, h, 3))

    top = 0
    while top < h - 1 and row_empty(top):
        top += 1
    bottom = h - 1
    while bottom > top and row_empty(bottom):
        bottom -= 1
    left = 0
    while left < w - 1 and col_empty(left):
        left += 1
    right = w - 1
    while right > left and col_empty(right):
        right -= 1

    pad = 14
    box = (max(0, left - pad), max(0, top - pad),
           min(w, right + 1 + pad), min(h, bottom + 1 + pad))
    return im.crop(box), bg


def install(name, src_index):
    """Xom rasmni ilovaga qo‘yadi: webapp/guides/<nom>.webp"""
    src = os.path.join(OUT_DIR, "%s-%d.png" % (name, src_index))
    if not os.path.exists(src):
        print("  topilmadi:", src)
        return None
    im, bg = trim_border(Image.open(src))
    # Ikkala chizma BIR XIL keng o‘lchamda bo‘lsin: rasm qirqilgach,
    # 16:9 lik krem maydonning o‘rtasiga qo‘yiladi. Aks holda biri keng,
    # ikkinchisi deyarli kvadrat chiqib, oynalarda har xil ko‘rinardi.
    w, h = im.size
    cw, ch = max(w, round(h * 16 / 9)), max(h, round(w * 9 / 16))
    canvas = Image.new("RGB", (cw, ch), bg)
    canvas.paste(im, ((cw - w) // 2, (ch - h) // 2))
    im = canvas.resize((OUT_W, round(OUT_W * 9 / 16)), Image.LANCZOS)
    os.makedirs(GUIDE_DIR, exist_ok=True)
    out = os.path.join(GUIDE_DIR, "%s.webp" % name)
    im.save(out, "WEBP", quality=88, method=6)
    print("  %s  →  %s  (%dx%d, %.0f KB, fon #%02X%02X%02X)"
          % (os.path.basename(src), os.path.relpath(out, ROOT),
             im.size[0], im.size[1], os.path.getsize(out) / 1024, *bg))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(SCENES))
    ap.add_argument("--variants", type=int, default=1)
    ap.add_argument("--install", nargs="*", metavar="NOM=RAQAM",
                    help="tanlangan namunani ilovaga qo‘yadi, masalan: sahifa=1 ovoz=1")
    a = ap.parse_args()

    if a.install is not None:
        for pair in a.install:
            nm, _, idx = pair.partition("=")
            install(nm, int(idx or 1))
        return

    names = [a.only] if a.only else sorted(SCENES)
    done = 0
    for name in names:
        for i in range(1, a.variants + 1):
            print("chizilmoqda: %s-%d …" % (name, i))
            p = draw(name, i)
            if p:
                done += 1
                print("  tayyor:", os.path.relpath(p, ROOT))
    print("\nJami chizildi: %d ta (taxminiy sarf: $%.2f)" % (done, done * 0.035))


if __name__ == "__main__":
    main()
