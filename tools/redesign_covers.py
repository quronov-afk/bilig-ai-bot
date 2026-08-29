# ==========================================================
# tools/redesign_covers.py
# ----------------------------------------------------------
# Ilovadagi kitob muqovalarini QAYTA CHIZADI.
#
# NEGA: hozirgi muqovalar mutolaa.com'dan olingan va ularda o‘sha
# saytning logotipi turibdi. Bizga o‘zimizniki kerak.
#
# QANDAY ISHLAYDI (uch qadam):
#   1. AI eski muqovaga QARAYDI va undagi rasmni SO‘Z bilan tasvirlaydi.
#      Matn, sarlavha, logotip — hammasi e'tiborsiz qoldiriladi.
#   2. AI faqat o‘sha so‘zlardan YANGI rasm chizadi. Eski faylni ko‘rmaydi.
#      Ya'ni bu nusxa emas — qayta hikoya qilish.
#   3. Sarlavha va muallifni BIZ o‘zimiz yozamiz (AI emas). Sabab: AI
#      «o‘» va «g‘» belgisini taxminan yarmida xato yozadi.
#
# Ishlatish:
#   python3 tools/redesign_covers.py --only sariq-devni-minib     (sinov)
#   python3 tools/redesign_covers.py --limit 5
#   python3 tools/redesign_covers.py                              (hammasi)
#
# Natija `webapp/covers_new/` ga tushadi — eski fayllarga TEGILMAYDI.
# ==========================================================
import argparse
import io
import json
import os
import re
import sqlite3
import sys
import time

from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from config import RECOMMENDED_BOOKS, GEMINI_API_KEY

COVERS = os.path.join(ROOT, "webapp", "covers")
OUT_DIR = os.path.join(ROOT, "webapp", "covers_new")
FONT_DIR = os.path.join(ROOT, "tools", "fonts")
DB = os.path.join(ROOT, "bot_base.db")
RAW_DIR = os.path.join(ROOT, "tools", "covers_raw")

DESCRIBE_MODEL = "gemini-3.1-flash-lite"
IMAGE_MODEL = "gemini-3.1-flash-lite-image"

# Ega qarori: «Galaktikada bir kun» — o‘zining kitobi, muqovasi o‘zgarmaydi.
SKIP = ("galaktikada-bir-kun",)

W, H = 450, 600           # yangi muqova o‘lchami (eskisi 298x400 edi)
TOP_BAND = 0.32           # yuqoridagi shu qism matn uchun bo‘sh qoldiriladi

client = genai.Client(api_key=GEMINI_API_KEY)


# ==========================================================
# 1-QISM — RASM USLUBLARI
# ----------------------------------------------------------
# Ega bergan to‘rtta namuna asosida yozildi (This is Gus, Lila and the
# Midnight Lantern, The Dark Lord's Daughter, Lightfall).
# ==========================================================
ART = {
 "gus": (
  "Bold contemporary picture-book cover illustration. Choose the SINGLE most "
  "important character from the scene and draw ONLY that one, large and close up; "
  "leave out every other character. Soft rounded shapes with no black outlines, "
  "rich brush texture and subtle paper grain. FLAT single saturated background "
  "colour with no scenery. Slightly exaggerated cartoon proportions, big "
  "characterful eyes, warm humour. Clean, modern, high contrast, playful."),
 "ertak": (
  "Soft painterly digital storybook illustration. Atmospheric scene with one warm "
  "glowing light source against cooler surroundings, delicate brushwork, gentle rich "
  "colour, fine detail in foliage and fabric, dreamy magical mood. Sweet character "
  "with rosy cheeks and a tender expression. Cinematic depth, darker tones framing "
  "a luminous centre."),
 "sarguzasht": (
  "Dramatic middle-grade adventure book cover, painterly digital illustration. "
  "Confident hero figure in the foreground, striking landscape or architecture "
  "silhouetted behind, bold theatrical lighting, saturated jewel colours with strong "
  "contrast, dynamic diagonal composition, a real sense of adventure and stakes. "
  "Detailed but graphic, never photorealistic."),
 "gouash": (
  "Graphic-novel cover art painted in gouache. Wide landscape, figures small within "
  "it, an enormous painted sky, soft warm-to-cool cloud gradients, muted sophisticated "
  "palette, visible textured brush strokes, quiet and awe-inspiring. Hand-made "
  "painterly feel, generous open space."),
}


# ==========================================================
# 2-QISM — SHRIFTLAR
# ----------------------------------------------------------
# Ega Google Fonts'dan yuklab bergan (hammasi tijorat uchun bepul).
# Har biri «o‘» va «g‘» belgisini TO‘G‘RI, chapga qaragan holda chizadi —
# tekshirilgan. Avenir va Futura aynan shu sababdan rad etilgan.
# ==========================================================
FONTS = {
 "baloo":     ("Baloo2-ExtraBold.ttf",        "Quicksand-SemiBold.ttf"),
 "quicksand": ("Quicksand-Bold.ttf",          "Quicksand-SemiBold.ttf"),
 "lilita":    ("LilitaOne-Regular.ttf",       "Quicksand-SemiBold.ttf"),
 "anton":     ("Anton-Regular.ttf",           "PlayfairDisplay-Medium.ttf"),
 "playfair":  ("PlayfairDisplay-Black.ttf",   "PlayfairDisplay-Medium.ttf"),
 "cormorant": ("CormorantGaramond-Bold.ttf",  "CormorantGaramond-SemiBold.ttf"),
}

# (yosh guruhi, kayfiyat) -> (rasm uslubi, shrift)
CHOICE = {
 ("kichik", "kulgili"):    ("gus",        "baloo"),
 ("kichik", "yumshoq"):    ("ertak",      "quicksand"),
 ("kichik", "sarguzasht"): ("gus",        "baloo"),
 ("kichik", "jiddiy"):     ("ertak",      "quicksand"),
 ("kichik", "tarixiy"):    ("ertak",      "quicksand"),
 ("orta",   "kulgili"):    ("gus",        "lilita"),
 ("orta",   "yumshoq"):    ("ertak",      "quicksand"),
 ("orta",   "sarguzasht"): ("sarguzasht", "lilita"),
 ("orta",   "jiddiy"):     ("gouash",     "playfair"),
 ("orta",   "tarixiy"):    ("gouash",     "cormorant"),
 ("katta",  "kulgili"):    ("sarguzasht", "lilita"),
 ("katta",  "yumshoq"):    ("gouash",     "playfair"),
 ("katta",  "sarguzasht"): ("sarguzasht", "anton"),
 ("katta",  "jiddiy"):     ("gouash",     "playfair"),
 ("katta",  "tarixiy"):    ("gouash",     "cormorant"),
}

BAND_GROUP = {"4-6": "kichik", "7-8": "kichik", "9-10": "orta",
              "11-13": "katta", "14-16": "katta"}


# ==========================================================
# 3-QISM — KITOB NOMI VA MUALLIFI
# ==========================================================
def ckey(s):
    """Muqova jadvalidagi kalit ko‘rinishi (app.js dagi coverKey bilan bir xil)."""
    s = (s or "").lower()
    for ch in "ʻʼ‘’'`´":
        s = s.replace(ch, " ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def catalog():
    """Katalogni nom va muallifga ajratadi.

    DIQQAT: ajratish OXIRGI nuqtadan bo‘ladi, birinchisidan emas. Sabab:
    turkumli kitoblarda ikkita nuqta bor —
    «Xorazmiy. 0 bilan tanishuv. Dinara Muminova». Birinchi nuqtadan
    ajratilsa, muallif «0 bilan tanishuv...» bo‘lib qolardi.
    """
    out = {}
    for age, titles in RECOMMENDED_BOOKS.items():
        for raw in titles:
            t = (raw or "").strip().rstrip(".")
            if not t:
                continue
            if "." in t:
                title, author = t.rsplit(".", 1)
            else:
                title, author = t, ""
            title, author = title.strip(), author.strip()
            out.setdefault(ckey(title + " " + author), (title, author, age))
            out.setdefault(ckey(title), (title, author, age))
    return out


def book_meta():
    """Har bir muqova fayli uchun: nom, muallif, yosh toifasi, kayfiyat."""
    idx = json.load(open(os.path.join(COVERS, "index.json"), encoding="utf-8"))
    file_keys = {}
    for k, fn in idx.items():
        file_keys.setdefault(fn, []).append(k)

    cat = catalog()
    base = {}
    if os.path.exists(DB):
        con = sqlite3.connect(DB)
        for t, a, ab, mo, tp in con.execute(
                "SELECT title, author, COALESCE(age_band,''), COALESCE(mood,''), "
                "COALESCE(topics,'') FROM Book_Base"):
            base.setdefault(ckey(t + " " + (a or "")), (ab, mo, tp))
            base.setdefault(ckey(t), (ab, mo, tp))
        con.close()

    meta = {}
    for fn, keys in file_keys.items():
        hit = None
        for k in sorted(keys, key=len, reverse=True):
            if k in cat:
                hit = cat[k]
                break
        if not hit:
            continue
        title, author, age = hit
        ab = mo = tp = ""
        for k in sorted(keys, key=len, reverse=True):
            if k in base:
                ab, mo, tp = base[k]
                break
        meta[fn] = {"title": title, "author": author, "age_key": age,
                    "age_band": ab, "mood": mo, "topics": tp}
    return meta


def author_case(name):
    """Muallif ismi: faqat bosh harflar katta (ega qarori).

    «XUDOYBERDI TO‘XTABOYEV» yoki «xudoyberdi to‘xtaboyev» —
    ikkalasi ham «Xudoyberdi To‘xtaboyev» bo‘ladi.
    Diqqat: «o‘g‘li» kabi qo‘shimchalar kichik qoladi.
    """
    small = {"o‘g‘li", "qizi", "ibn", "al", "va", "bin"}
    out = []
    for w in (name or "").split():
        lw = w.lower()
        if lw in small:
            out.append(lw)
        elif "-" in w:
            out.append("-".join(p[:1].upper() + p[1:].lower() for p in lw.split("-")))
        else:
            out.append(lw[:1].upper() + lw[1:])
    return " ".join(out)


# ==========================================================
# 4-QISM — AI CHAQIRUVLARI
# ==========================================================
DESCRIBE = """You are looking at a children's book cover illustration.
Describe ONLY the artwork. Completely ignore any text, title, author name,
logo or watermark that appears on it.

Return strict JSON:
  "subject": the main subject in one sentence
  "characters": list of visible characters (age/species, clothing, expression, pose)
  "setting": environment and time of day
  "mood": 3-5 mood words
  "palette": 4-6 dominant colours in plain words
  "tone": exactly one of "kulgili" (funny), "yumshoq" (gentle/tender),
          "sarguzasht" (adventure/action), "jiddiy" (serious/thoughtful),
          "tarixiy" (historical or biography)
  "audience": exactly one of "kichik" (4-8), "orta" (9-10), "katta" (11-16)
Be concrete and visual. English only, except "tone" and "audience"."""

# Ega talabi: «odamlarning yuziga yozuv tushib qolmasin».
# Shuning uchun AI ga yuqoridagi bo‘lakni BO‘SH qoldirish buyuriladi.
LAYOUT = (
 "COMPOSITION — this is the most important instruction. Frame the scene so that the "
 "upper part of the picture is generous, calm, open space: sky, distant haze, still "
 "water, a plain wall or soft empty air above the subject. The main character must "
 "sit LOW in the frame — the top of their head no higher than the middle of the "
 "image. No face, no head, no hands and no important detail anywhere near the top "
 "edge, because a title will be printed there.\n"
 "The picture must be ONE continuous scene painted edge to edge. Do NOT divide it "
 "into strips or halves, do NOT add a flat colour block, banner, box, border or "
 "frame, and do NOT leave any straight horizontal line across the image. The open "
 "area at the top must be part of the scene itself and blend naturally into it.")

NOTEXT = ("Absolutely no text, no letters, no numbers, no logo, no watermark and no "
          "signature anywhere in the image.")

CHECK = ("Look only at the top {pc}% of this image. Is that band free of faces, heads, "
         "hands and any important detail — that is, is it calm enough to print a "
         "title over? Answer strict JSON: {{\"clear\": true or false}}")


def _retry(fn, tries=3, wait=4):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            last = e
            if i < tries - 1:
                time.sleep(wait * (i + 1))
    raise last


def describe(path):
    im = Image.open(path).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    r = _retry(lambda: client.models.generate_content(
        model=DESCRIBE_MODEL,
        contents=[types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"), DESCRIBE],
        config=types.GenerateContentConfig(response_mime_type="application/json")))
    return json.loads(r.text), r.usage_metadata


def _flat(v):
    if isinstance(v, list):
        return "; ".join(x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in v)
    return str(v or "")


def scene_prompt(d, art_key):
    """Personajsiz manzara muqovasi — qahramonlarsiz, faqat joy va kayfiyat.

    NEGA KERAK: mashhur, mualliflik huquqi bilan himoyalangan personajlarda
    (Vinni Pux, Maugli) AI chizishdan butunlay bosh tortadi
    (`PROHIBITED_CONTENT`) — tavsifdan ularni tanib qoladi. Bunday kitobda
    qahramonni emas, KITOBNING DUNYOSINI chizamiz. Bu kitob muqovalarida
    keng tarqalgan yo‘l va muammoni butunlay chetlab o‘tadi.
    """
    return ("Front cover artwork for a children's book, vertical 3:4 portrait format, "
            "illustration filling the whole frame edge to edge.\n\n"
            "STYLE: " + ART[art_key] +
            "\n\nPaint an EMPTY SCENE — the place itself, with NO people and NO animals "
            "anywhere in the picture. Let the landscape, the light and the atmosphere "
            "tell the story.\n"
            "PLACE: " + _flat(d.get("setting")) +
            "\nMOOD: " + _flat(d.get("mood")) +
            "\nCOLOUR FEELING: " + _flat(d.get("palette")) +
            "\n\n" + LAYOUT + "\n\n" + NOTEXT)


def art_prompt(d, art_key, strict=False):
    p = ("Front cover artwork for a children's book, vertical 3:4 portrait format, "
         "illustration filling the whole frame edge to edge.\n\n"
         "STYLE: " + ART[art_key] +
         "\n\nSCENE: " + _flat(d.get("subject")) +
         "\nCHARACTERS: " + _flat(d.get("characters")) +
         "\nSETTING: " + _flat(d.get("setting")) +
         "\nMOOD: " + _flat(d.get("mood")) +
         "\nCOLOUR FEELING: " + _flat(d.get("palette")) +
         "\n\nUse everything above only as a STARTING POINT, not as a picture to copy. "
         "Keep the main character (or main subject) and the overall feeling of the book "
         "recognisable, but freely reinvent the composition, the camera angle, the pose, "
         "the setting details and any secondary elements. The result must read as a "
         "different illustrator's own independent interpretation of the same book — "
         "clearly the same story, clearly not the same picture.\n\n" +
         LAYOUT + "\n\n" + NOTEXT)
    if strict:
        p += ("\n\nThe previous attempt put important detail in the top band. "
              "This time leave the top band almost completely empty.")
    return p


class BlockedError(RuntimeError):
    """AI chizishdan bosh tortdi (odatda mashhur personaj)."""


def make_art(prompt):
    r = _retry(lambda: client.models.generate_content(
        model=IMAGE_MODEL, contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="3:4"))))
    for part in r.candidates[0].content.parts:
        if getattr(part, "inline_data", None) and part.inline_data.data:
            return Image.open(io.BytesIO(part.inline_data.data)).convert("RGB"), r.usage_metadata
    reason = str(r.candidates[0].finish_reason)
    if "PROHIBITED" in reason:
        raise BlockedError(reason)
    raise RuntimeError("rasm qaytmadi (%s)" % reason)


def band_is_clear(im):
    """Yuqoridagi bo‘lak matn uchun bo‘shmi — AI ning o‘zidan so‘raymiz."""
    buf = io.BytesIO()
    im.save(buf, "PNG")
    try:
        r = client.models.generate_content(
            model=DESCRIBE_MODEL,
            contents=[types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"),
                      CHECK.format(pc=int(TOP_BAND * 100))],
            config=types.GenerateContentConfig(response_mime_type="application/json"))
        return bool(json.loads(r.text).get("clear")), r.usage_metadata
    except Exception:
        return True, None      # tekshiruv ishlamasa, ishni to‘xtatmaymiz


# ==========================================================
# 5-QISM — SARLAVHA VA MUALLIFNI YOZISH
# ==========================================================
def _f(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def _wrap(d, text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit(d, text, fname, maxw, max_lines, hi, lo=17):
    for sz in range(hi, lo - 1, -1):
        f = _f(fname, sz)
        ls = _wrap(d, text, f, maxw)
        if len(ls) <= max_lines and all(d.textlength(l, font=f) <= maxw for l in ls):
            return f, ls
    f = _f(fname, lo)
    return f, _wrap(d, text, f, maxw)


def draw_text(im, title, author, font_key):
    """Sarlavha KATTA HARFLARDA, muallif esa bosh harflari bilan (ega qarori)."""
    tfile, afile = FONTS[font_key]
    im = im.convert("RGB").resize((W, H), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    pad = int(W * 0.075)
    maxw = W - 2 * pad

    tf, lines = _fit(d, title.upper(), tfile, maxw, 3, int(W * 0.125))
    # Uch qatorli uzun sarlavha juda baland blok yasab, muallifni rasm
    # ustiga itarib yuborardi — shunday holatda harf kichraytiriladi.
    if len(lines) == 3 and tf.size > int(W * 0.098):
        tf, lines = _fit(d, title.upper(), tfile, maxw, 3, int(W * 0.098))
    af = _f(afile, int(W * 0.054))
    lh = int(tf.size * 1.10)
    margin = int(H * 0.100)   # ega tanlagan balandlik («B»)
    title_end = margin + len(lines) * lh
    y_author = title_end + int(H * 0.018)
    block_end = y_author + int(af.size * 1.25)

    # MATN ORTIDAGI FON. Ega talabi: «orqaga bir xilda xira qora fon berib
    # yuborish g‘alati». Shuning uchun:
    #   1) rang RASMNING O‘ZIDAN olinadi (kulrang plastinka emas) — shu joyning
    #      o‘rtacha rangi to‘qlashtiriladi, ya'ni fon rasmga singib ketadi;
    #   2) shakli — keng, kuchli xiralashtirilgan dog‘, TO‘G‘RI CHIZIQLI
    #      chegarasi yo‘q (avval gorizontal chiziq ko‘rinib qolgandi);
    #   3) kuchi rasmga qarab o‘zgaradi — yorug‘ joyda ko‘proq, qorong‘ida
    #      deyarli yo‘q. Qorong‘i muqovaga fon qo‘yish shart emas.
    band = im.crop((0, max(0, margin - 10), W, min(H, block_end + 10)))
    r_, g_, b_ = ImageStat.Stat(band).mean[:3]
    lum = 0.299 * r_ + 0.587 * g_ + 0.114 * b_
    tint = (int(r_ * 0.24), int(g_ * 0.24), int(b_ * 0.26))
    strength = max(0.18, min(0.78, (lum - 35) / 145.0))

    # Parda SARLAVHA ostida to‘liq kuchda, muallif qatorida so‘nib bitadi.
    # Ega talabi: uzun (uch qatorli) sarlavhada parda bolaning YUZIGACHA
    # tushib ketgandi. Endi ikki tomonlama chegara bor: so‘nish sarlavha
    # tugashi bilan boshlanadi va rasmning 45% idan pastga hech qachon
    # o‘tmaydi.
    full_to = title_end
    fade_end = min(int(H * 0.45), block_end + int(H * 0.05))
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        if y <= full_to:
            v = 1.0
        else:
            t = min(1.0, (y - full_to) / max(1, fade_end - full_to))
            v = 1.0 - (t * t * (3.0 - 2.0 * t))
        grad.putpixel((0, y), int(255 * strength * v))
    mask = grad.resize((W, H)).filter(ImageFilter.GaussianBlur(4))
    im = Image.composite(Image.new("RGB", (W, H), tint), im, mask)

    d = ImageDraw.Draw(im)

    def centred(text, font, y, fill):
        x = (W - d.textlength(text, font=font)) / 2
        # Soya — fon yengil bo‘lgani uchun harfni shu ushlab turadi.
        for dx, dy in ((0, 3), (0, 2)):
            d.text((x + dx, y + dy), text, font=font, fill=(8, 12, 22))
        d.text((x, y), text, font=font, fill=fill)

    y = margin
    for ln in lines:
        centred(ln, tf, y, (255, 255, 255))
        y += lh
    a = author_case(author)
    if a:
        centred(a, af, y_author, (232, 238, 248))
    return im


# ==========================================================
# 6-QISM — ASOSIY OQIM
# ==========================================================
def pick(desc, meta):
    """Yosh va kayfiyatga qarab rasm uslubi va shriftni tanlaydi."""
    group = BAND_GROUP.get(meta.get("age_band") or "", "")
    if not group:
        group = desc.get("audience") if desc.get("audience") in ("kichik", "orta", "katta") else "orta"

    tone = desc.get("tone")
    mood = (meta.get("mood") or "").lower()
    topics = (meta.get("topics") or "").lower()
    # Bazadagi o‘zbekcha kayfiyat AI taxminidan ustun turadi — u kitobning
    # to‘liq matni asosida yozilgan, muqova rasmi asosida emas.
    if "tarix" in mood or "tarix" in topics or "biograf" in topics:
        tone = "tarixiy"
    elif "kulgili" in mood or "hajviy" in mood:
        tone = "kulgili"
    elif "sarguzasht" in mood or "hayajon" in mood or "shiddat" in mood:
        tone = "sarguzasht"
    elif "hazin" in mood or "jiddiy" in mood:
        tone = "jiddiy"
    elif "iliq" in mood or "samimiy" in mood:
        tone = "yumshoq"
    if tone not in ("kulgili", "yumshoq", "sarguzasht", "jiddiy", "tarixiy"):
        tone = "yumshoq"
    return CHOICE.get((group, tone), ("ertak", "quicksand")) + (group, tone)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="vergul bilan: fayl nomlari (kengaytmasiz)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=OUT_DIR)
    ap.add_argument("--force", action="store_true", help="tayyorini ham qayta chizish")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    meta = book_meta()
    files = sorted(f for f in os.listdir(COVERS) if f.endswith(".webp"))
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        files = [f for f in files if os.path.splitext(f)[0] in want]
    files = [f for f in files if not any(f.startswith(s) for s in SKIP)]
    if args.limit:
        files = files[:args.limit]

    tin = tout = iin = nimg = 0
    done = skipped = failed = 0
    for i, fn in enumerate(files, 1):
        out_path = os.path.join(args.out, fn)
        if os.path.exists(out_path) and not args.force:
            skipped += 1
            continue
        m = meta.get(fn)
        if not m:
            print("%3d/%d  %-46s NOMI TOPILMADI" % (i, len(files), fn[:44]))
            failed += 1
            continue
        try:
            d, u = describe(os.path.join(COVERS, fn))
            tin += u.prompt_token_count
            tout += u.candidates_token_count
            art_key, font_key, group, tone = pick(d, m)

            note = ""
            try:
                im, u2 = make_art(art_prompt(d, art_key))
            except BlockedError:
                # Mashhur personaj — qahramonsiz manzara chizamiz.
                im, u2 = make_art(scene_prompt(d, art_key))
                note = " (manzara — personaj chizilmadi)"
            iin += u2.prompt_token_count
            nimg += 1
            clear, u3 = band_is_clear(im)
            if u3:
                tin += u3.prompt_token_count
                tout += u3.candidates_token_count
            if not clear:
                im, u2 = make_art(art_prompt(d, art_key, strict=True))
                iin += u2.prompt_token_count
                nimg += 1
                note += " (qayta chizildi)"

            # Xom (matnsiz) rasm webapp dan TASHQARIDA saqlanadi: u 1.3 MB
            # atrofida va ilova bilan birga tarqalmasligi kerak. Matn
            # joylashuvini keyin qayta yozish uchun kerak bo‘ladi.
            os.makedirs(RAW_DIR, exist_ok=True)
            im.save(os.path.join(RAW_DIR, fn.replace(".webp", ".png")))
            draw_text(im, m["title"], m["author"], font_key).save(
                out_path, "WEBP", quality=86, method=6)
            done += 1
            print("%3d/%d  %-40s %-6s %-10s %-10s%s" %
                  (i, len(files), m["title"][:38], group, tone, font_key, note))
        except Exception as e:
            failed += 1
            print("%3d/%d  %-46s XATO: %s" % (i, len(files), fn[:44], str(e)[:70]))

    cost = tin * 0.25e-6 + tout * 1.5e-6 + iin * 0.25e-6 + nimg * 0.0336
    print("\nTayyor: %d | o‘tkazildi: %d | xato: %d" % (done, skipped, failed))
    print("Rasm chizildi: %d ta | taxminiy sarf: $%.2f" % (nimg, cost))
    print("Natija:", args.out)


if __name__ == "__main__":
    main()
