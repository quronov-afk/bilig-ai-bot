#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bilig AI logotipi — Nano Banana Pro bilan variantlar chizish.

Har variant BELGI + «Bilig AI» yozuvidan iborat. Natija PNG bo‘lib
tushadi; ega uni keyin vektorga o‘tkazadi.
"""
import io, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

def load_env():
    for line in open(os.path.join(ROOT, ".env"), encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
load_env()

from google import genai
from google.genai import types
from PIL import Image

OUT = os.path.join(ROOT, "tools", "logo", "out")
os.makedirs(OUT, exist_ok=True)
MODEL = "nano-banana-pro-preview"
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Barcha variantlarga umumiy uslub. Ilovaning o‘z tizimidan olingan:
# Nunito shrifti, ko‘k #4E8EF7, oltin #F59E0B, chiziqli sodda shakllar.
STYLE = (
    "Professional brand identity logo design for a children's reading app. "
    "FLAT VECTOR style: solid shapes, crisp geometric edges, no gradients, "
    "no 3D, no shadows, no textures, no photorealism, no mockup, no background scene. "
    "Pure white background. Perfectly centered with generous white margins. "
    "Exactly two colors plus dark text: a friendly blue #4E8EF7 and a warm gold #F59E0B. "
    "Below the symbol, the wordmark 'Bilig AI' set in a rounded geometric sans-serif "
    "similar to Nunito, medium-bold weight, dark navy #0F172A, correctly spelled, "
    "well-kerned, comfortably spaced from the symbol. "
    "The symbol must stay legible when scaled down to 16 pixels. "
    "World-class quality, the kind of mark a top design studio would deliver. "
    "Do not add any tagline, slogan, extra words, frame, border or watermark."
)

VARIANTS = [
    ("1-kitob-qanot",
     "The symbol is an open book whose right-hand page lifts off and turns into a "
     "stylized wing rising upward, suggesting flight and growth. The book is blue, "
     "the rising wing tip is gold. Confident simple geometry, balanced negative space."),
    ("2-kitob-uchqun",
     "The symbol is a simplified open book built from two soft rounded blue shapes, "
     "with a small four-pointed gold spark rising just above it like an idea taking "
     "shape. Very clean, generous negative space, immediately readable."),
    ("3-b-monogramma",
     "The symbol is a geometric monogram of the capital letter B, constructed so that "
     "the two bowls of the B read as the facing pages of an open book. Blue letterform "
     "with one gold accent detail. Built on a circular grid, mathematically precise."),
    ("4-xatchop-strelka",
     "The symbol is a bookmark ribbon whose notched tail reads as an upward arrow, "
     "suggesting progress and rising achievement. Blue ribbon body with a gold tip. "
     "Extremely simple and bold, the kind of shape that survives at favicon size."),
]


def draw(prompt):
    r = client.models.generate_content(
        model=MODEL, contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1")))
    for part in r.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data.data:
            return Image.open(io.BytesIO(part.inline_data.data)).convert("RGB"), r.usage_metadata
    raise RuntimeError("rasm qaytmadi: %s" % r.candidates[0].finish_reason)


if __name__ == "__main__":
    total_in = total_out = 0
    for name, idea in VARIANTS:
        t0 = time.time()
        try:
            im, usage = draw(STYLE + " " + idea)
            path = os.path.join(OUT, name + ".png")
            im.save(path)
            total_in += getattr(usage, "prompt_token_count", 0) or 0
            total_out += getattr(usage, "candidates_token_count", 0) or 0
            print("  tayyor: %-22s %4.0f soniya  %s" % (name, time.time() - t0, im.size))
        except Exception as e:
            print("  XATO: %s — %r" % (name, e))
    print("tokenlar: kirish %d, chiqish %d" % (total_in, total_out))
