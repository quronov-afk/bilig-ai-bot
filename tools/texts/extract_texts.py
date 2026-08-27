# -*- coding: utf-8 -*-
"""Ilovadagi BARCHA ko‘rinadigan matnlarni yig‘ib, tahrir uchun ro‘yxat tuzadi.

Ishlatish (loyiha ildizidan):
    python3 tools/texts/extract_texts.py

Natija: tools/texts/texts.json — har bir matn uchun:
    id     — barqaror belgi (fayl + tartib raqami)
    file   — qaysi faylda
    line   — nechanchi qatorda
    area   — ilovaning qaysi joyi (Bosh sahifa, Do‘kon, Nishonlar...)
    text   — matnning o‘zi

Matnlar HTML ichidan ham ajratib olinadi: '<p class="x">Salom</p>' dan
faqat «Salom» olinadi, teglar tegilmaydi.
"""
import hashlib
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "tools", "texts", "texts.json")

# Matn deb hisoblanmaydigan narsalar
SKIP_EXACT = {"", " ", "|", "/", "-", "—", ":", ".", ",", "?", "!", "&nbsp;"}

# Bular — kod, matn emas
TECH_RE = [
    re.compile(r"^[\s\d.,:;/|%+\-—→←]*$"),
    re.compile(r"^https?://"),
    re.compile(r"^/"),                                   # yo‘l: /api/..., /badges/...
    re.compile(r"^[#.][a-z][\w .#>:\[\]()-]*$", re.I),   # CSS tanlagich
    re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|ALTER TABLE|CREATE TABLE|"
               r"FROM|WHERE|JOIN|VALUES|GROUP BY|ORDER BY|LIMIT|COUNT\(|SUM\()\b"),
    re.compile(r"%[YmdHMS]"),                            # sana formati
    re.compile(r"data-[a-z]+=|class=|style=|href=|src=|viewBox|stroke|fill="),
    re.compile(r"^[a-z0-9_.-]+$", re.I),                 # bitta texnik so‘z
    re.compile(r"^[a-z_]+\s*[:=]\s*", re.I),             # kalit: qiymat
    re.compile(r"^\w+\.(js|css|html|json|py|webp|svg|db)\b", re.I),
    re.compile(r"^(application|image|audio|text)/"),      # mime
    re.compile(r"^(POST|GET|PUT|DELETE)\b"),
    re.compile(r"^[A-Z_]{3,}$"),                          # SABIT_NOM
    re.compile(r"gradient\(|rgba?\(|calc\(|translate|\d+px|\d+%,"),   # CSS
    re.compile(r'="'),                                    # yarim atribut qoldig‘i
    re.compile(r"^\[[a-z_]+\]"),                          # jurnal yozuvi: [webapp_api]
    re.compile(r"\b(webapp|tools|handlers)/"),             # fayl yo‘li
    re.compile(r"^(AND|OR|NOT)\s", re.I),                  # SQL bo‘lagi
    re.compile(r"[a-z-]+=\d"),                            # max-age=604800 kabi
    re.compile(r"^(🔥 Charchamas Kitobxon|🗣 Notiq|🧠 Zukko)$"),  # eski nishonlar
    re.compile(r"/[gimsu]*\s*,|\]/|\bfunction\s*\(|=>"),        # kod bo‘lagi
]

# Kod izohi / hujjat satri belgilari
DOC_HINT = re.compile(r"->|\bAI tekshiradi\b|\bchaqiriladi\b|\bqaytaradi\b|"
                      r"\bfunksiya\b|\bendpoint\b|\bjadval\b|\bustun\b|\bthread\b", re.I)

UZ_HINT = re.compile(
    r"[‘ʼ’]|\b(va|uchun|bilan|yo|kitob|bola|ota|ona|nishon|bet|sahifa|test|reja|"
    r"savol|javob|natija|kun|Bilig|hali|hozircha|yangi|tanlang|kiriting|yuboring|"
    r"bosing|sen|siz|sizning|sening|yo‘q|bor)\b", re.I)


def looks_like_text(t):
    t = t.strip()
    if t in SKIP_EXACT or len(t) < 3:
        return False
    for r in TECH_RE:
        if r.search(t):
            return False
    if DOC_HINT.search(t):
        return False
    if not re.search(r"[A-Za-z‘]", t):
        return False
    # Kamida 2 ta so‘z, yoki o‘zbekcha ko‘rinishdagi bitta so‘z
    return len(t.split()) >= 2 or bool(UZ_HINT.search(t))


def strip_html(s):
    """HTML bo‘lagidan faqat ko‘rinadigan matn parchalarini ajratadi."""
    # atributlar ichidagi matnni ham olamiz (placeholder, alt, title, aria-label)
    parts = []
    for m in re.finditer(r'(?:placeholder|title|aria-label|alt)="([^"]*)"', s):
        parts.append(m.group(1))
    # teglarni olib tashlaymiz
    body = re.sub(r"<[^>]*>", "\x00", s)
    parts.extend(body.split("\x00"))
    # Yarim qolgan teg qoldiqlarini kesamiz: '">Test tuzish' -> 'Test tuzish'
    clean = []
    for x in parts:
        x = re.sub(r'^[\s"\'>/]+', "", x)
        x = re.sub(r'[\s"\'</]+$', "", x)
        clean.append(x)
    return clean


def js_strings(path):
    """Bitta va ikkita tirnoq ichidagi satrlar (qator raqami bilan).

    Python hujjat satrlari (\"\"\"...\"\"\") butunlay o‘tkazib yuboriladi —
    ular kod izohi, foydalanuvchi ko‘rmaydi.
    """
    src = io.open(path, encoding="utf-8").read()
    if path.endswith(".py"):
        def _blank(m):
            return "\n" * m.group(0).count("\n")
        src = re.sub(r'"""[\s\S]*?"""', _blank, src)
        # «#» izohlari ham olib tashlanadi: o‘zbekcha izohdagi tutuq belgisi
        # (ma'lumot) aks holda satr boshi deb o‘qilib ketadi.
        src = "\n".join(re.sub(r"(?<!['\"])#.*$", "", ln) for ln in src.split("\n"))
        # Tarixiy ro‘yxatlar tahrir qilinmaydi: ular bazadagi ESKI nomlarni
        # saqlaydi, o‘zgartirilsa ko‘chirish buziladi.
        for name, close in (("_BADGE_RENAMES = [", "]"), ("_OLD_BADGE_MAP = {", "}")):
            while name in src:
                a = src.index(name)
                b = src.index("\n" + close, a) + len(close) + 1
                src = src[:a] + "\n" * src.count("\n", a, b) + src[b:]
    out = []
    line = 1
    i = 0
    n = len(src)
    in_line_comment = False
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1
            in_line_comment = False
            i += 1
            continue
        if in_line_comment:
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            in_line_comment = True
            i += 2
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            if j < 0:
                break
            line += src.count("\n", i, j)
            i = j + 2
            continue
        if c in "\"'":
            quote = c
            j = i + 1
            buf = []
            while j < n:
                if src[j] == "\\":
                    buf.append(src[j:j + 2])
                    j += 2
                    continue
                if src[j] == quote:
                    break
                if src[j] == "\n":
                    break
                buf.append(src[j])
                j += 1
            out.append((line, "".join(buf)))
            i = j + 1
            continue
        i += 1
    return out


def html_texts(path):
    src = io.open(path, encoding="utf-8").read()
    out = []
    for idx, raw in enumerate(src.split("\n"), 1):
        for piece in strip_html(raw):
            out.append((idx, piece))
    return out


# Ilovaning qaysi joyi ekanini funksiya nomidan taxmin qilamiz
AREA_MARKS = [
    ("renderParentHome", "Bosh sahifa — ota-ona"),
    ("renderChildHome", "Bosh sahifa — bola"),
    ("renderPlansTab", "Rejalar"),
    ("renderChildPlans", "Rejalar — bola"),
    ("renderStoreTab", "Do‘kon"),
    ("renderRatingTab", "Reyting"),
    ("renderResultScreen", "Natijalar"),
    ("badgeGridHtml", "Nishonlar"),
    ("Wizard", "Kitob qo‘shish"),
    ("openTestModal", "Test"),
    ("Test", "Test"),
    ("openVoiceModal", "Ovozli xulosa"),
    ("showPageResult", "Sahifa natijasi"),
    ("celebrate", "Nishon tabrigi"),
    ("mascotToast", "Maskot lentasi"),
    ("welcomeHtml", "Kutib olish"),
    ("emptyState", "Bo‘sh ekranlar"),
    ("api_link_parent", "Ro‘yxatdan o‘tish"),
    ("child_submit", "Bola amallari"),
    ("notify_parent", "Ota-onaga xabar"),
    ("announce_badges", "Ota-onaga xabar"),
    ("build_summary", "3 kunlik xulosa"),
]


def area_map(path):
    """Har bir qator uchun «qaysi bo‘lim» ekanini belgilaydi."""
    src = io.open(path, encoding="utf-8").read().split("\n")
    areas = {}
    cur = "Umumiy"
    for i, raw in enumerate(src, 1):
        if re.match(r"^\s*(async\s+)?function\s+\w+|^const\s+\w+\s*=\s*\{|^def\s+\w+", raw):
            for mark, name in AREA_MARKS:
                if mark in raw:
                    cur = name
                    break
            else:
                cur = "Umumiy"
        areas[i] = cur
    return areas


def collect():
    items = []
    seen = set()

    # Nishon matnlari — manbasi badge_defs.py. Ular app.js dagi BADGE_LIST da
    # ham takrorlanadi, shuning uchun avval shulardan boshlaymiz va keyin
    # fayllarda o‘sha matnlar qayta chiqmaydi.
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools", "badges"))
        from badge_defs import BADGES, MSG        # noqa
        for slug in BADGES:
            name, cond = BADGES[slug][0], BADGES[slug][1]
            for kind, val in (("nomi", name), ("sharti", cond), ("xabari", MSG.get(slug, ""))):
                if not val or val in seen:
                    continue
                seen.add(val)
                items.append({
                    "id": hashlib.sha1(("badge|" + slug + kind).encode("utf-8")).hexdigest()[:10],
                    "file": "tools/badges/badge_defs.py",
                    "line": 0,
                    "area": "Nishonlar — %s" % kind,
                    "text": val,
                })
    except Exception as e:
        print("Nishon matnlari olinmadi:", e)

    sources = [
        ("webapp/app.js", "js"),
        ("webapp/index.html", "html"),
        ("webapp_api.py", "js"),          # Python satrlari ham xuddi shunday olinadi
    ]
    for rel, kind in sources:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        areas = area_map(path)
        raw = js_strings(path) if kind == "js" else html_texts(path)
        for line, s in raw:
            pieces = strip_html(s) if ("<" in s and ">" in s) else [s]
            for piece in pieces:
                t = piece.strip()
                # JS ifodalari orasidagi qoldiqlarni tozalaymiz
                t = re.sub(r"\s+", " ", t)
                if not looks_like_text(t):
                    continue
                key = t
                if key in seen:
                    continue
                seen.add(key)
                items.append({
                    "id": hashlib.sha1((rel + "|" + t).encode("utf-8")).hexdigest()[:10],
                    "file": rel,
                    "line": line,
                    "area": areas.get(line, "Umumiy"),
                    "text": t,
                })

    return items


def main():
    items = collect()
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(items, ensure_ascii=False, indent=1))
    by_area = {}
    for it in items:
        by_area[it["area"]] = by_area.get(it["area"], 0) + 1
    print("Jami matn: %d\n" % len(items))
    for a in sorted(by_area, key=lambda x: -by_area[x]):
        print("  %-28s %d" % (a, by_area[a]))
    print("\nSaqlandi: %s" % OUT)


if __name__ == "__main__":
    main()
