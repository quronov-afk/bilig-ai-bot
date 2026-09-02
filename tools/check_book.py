#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kitob pasporti va testini tekshirish — sifat nazorati.

Har bir tayyor kitob shu tekshiruvdan o‘tadi. O‘tmasa — qayta yoziladi.
Tekshiriladiganlar:

  · pasportning barcha maydonlari to‘ldirilganmi
  · qisqa asarda test emas, og‘zaki savol bo‘lishi
  · savollar soni kitob uzunligiga mos (20 / 30 ta)
  · kitob qismlariga to‘g‘ri bo‘linganmi
  · Barrett taksonomiyasi nisbati saqlanganmi (40% xotira + 60% tushunish)
  · to‘g‘ri javob variantlar orasida AYNAN turibdimi
  · har savolda 3 yoki 4 ta variant bormi
  · imlo: O‘, o‘, G‘, g‘ to‘g‘ri belgi bilan yozilganmi

Ishlatish:
    python3 tools/check_book.py                  # hammasini
    python3 tools/check_book.py teddi.json       # bittasini
"""

import json
import os
import re
import sys

OUT_DIR = os.path.join("tools", "book_out")

# Ega belgilagan pasport tuzilmasi (2026-08-28). Ertaga ota-ona AI ustozdan
# «bu kitob nima haqida?» deb so‘raganda javob shu maydonlardan olinadi.
PASSPORT_FIELDS = ["age_band", "age_hint", "topics", "theme", "summary",
                   "characters", "conclusion", "difficulty", "mood", "for_whom"]

# Ega belgilagan yosh toifalari (2026-08-28). «3 yosh» toifasi bekor
# qilindi — eng kichik asarlar ham 4 yoshdan boshlanadi.
AGE_BANDS = ("4-6", "7-8", "9-10", "11-13", "14-16", "17-19")

# Uzunlik chegaralari — ega belgilagan
# Ega qarori (2026-09-01): pasport kengaytirildi. Sabab — eski chegara
# bilan kelajakda yangi test kerak bo‘lganda kitobni qaytadan o‘qishga
# to‘g‘ri kelardi. Endi pasportning o‘zi yetadi.
THEME_MAX = 500        # g‘oyasi
SUMMARY_MAX = 3000     # qisqacha syujeti
EVENTS_MIN = 15        # voqealar tafsiloti (qisqa asarda 6)
EVENTS_MIN_SHORT = 6
QUOTES_MIN = 4         # asl matndan olingan muhim jumlalar

# Barrett taksonomiyasi — o‘qib tushunishni baholash uchun tayyor metod.
# «literal» — xotira (40%), qolgan to‘rttasi — tushunish (60%).
#
# Savollar soni KITOB UZUNLIGIGA qarab o‘zgaradi. Bir sahifalik hikoyadan
# 30 ta savol chiqarib bo‘lmaydi — AI matndan so‘z terib, bo‘sh savollar
# yozishga majbur bo‘ladi. Har bir o‘lchamda 40/60 nisbati saqlanadi.
PROFILES = {
    10: {"parts": {1: 3, 2: 3, 3: 4},
         "barrett": {"literal": 4, "reorganization": 1, "inferential": 3,
                     "evaluation": 1, "appreciation": 1}},
    20: {"parts": {1: 7, 2: 7, 3: 6},
         "barrett": {"literal": 8, "reorganization": 3, "inferential": 5,
                     "evaluation": 2, "appreciation": 2}},
    30: {"parts": {1: 10, 2: 10, 3: 10},
         "barrett": {"literal": 12, "reorganization": 4, "inferential": 6,
                     "evaluation": 4, "appreciation": 4}},
}


# Ega qarori (2026-08-28), SAHIFA soni bo‘yicha:
#   5 sahifagacha  — test tuzilmaydi, og‘zaki xulosa so‘raladi
#   30 sahifagacha — 20 ta test
#   undan ortiq    — 30 ta test
# Sahifa soni Word faylining o‘zidan olinadi (docProps/app.xml).
SHORT_PAGES = 5
MID_PAGES = 30
# Sahifa soni noma'lum bo‘lsa, belgidan chamalanadi. O‘lchandi: bu
# to‘plamda bir sahifada o‘rtacha 2 253 belgi.
CHARS_PER_PAGE = 2_253


# Ega qarori: 7 yoshgacha bolaga test berilmaydi — ular uchun kitob o‘yin
# va suhbat, imtihon emas. Ya'ni "4-6" toifasidagi asarga test tuzilmaydi.
#
# DIQQAT: buni KATALOGDAGI yosh guruhiga qarab hal qilmaymiz — u ishonchsiz
# (masalan 277 betlik «Amir Temur» katalogda 3 yosh guruhida turgan edi).
# Qarorni AI o‘zi qabul qiladi: asarni o‘qib, toifasini belgilaydi va
# "4-6" bo‘lsa test o‘rniga og‘zaki savol yozadi.
NO_TEST_BAND = "4-6"


def profile_for(chars, pages=0, age_group=None):
    """Asar hajmiga mos savollar soni. 0 — test umuman tuzilmaydi."""
    if not pages:
        pages = max(1, round(chars / CHARS_PER_PAGE))
    if pages <= SHORT_PAGES:
        return 0
    if pages <= MID_PAGES:
        return 20
    return 30


CATEGORIES = {"factual", "logic", "conclusion"}

# Noto‘g‘ri tutuq belgilari: o'/o`/o’ — hammasi o‘ bo‘lishi kerak
BAD_APOS = re.compile(r"[oOgG]['`’]")


# BEGONA TIL. AI ba'zan inglizcha yoki ruscha so‘zni tarjima qilmay
# qoldiradi («…sayyora astronomers aytishi bo‘yicha…»). Bunday matn
# bolaga ko‘rsatilmasligi kerak.
CYRILLIC = re.compile(r"[\u0400-\u04FF]")
FOREIGN_WORDS = (
    "the", "and", "with", "which", "there", "about", "people", "because",
    "through", "however", "therefore", "between", "different", "astronomer",
    "astronomers", "chapter", "story", "children", "little", "prince",
    "author", "however",
)
FOREIGN = re.compile(r"\b(" + "|".join(FOREIGN_WORDS) + r")\b", re.I)


def text_values(obj, out=None):
    """Faqat MATN qiymatlarini yig‘adi — JSON kalitlari tekshirilmaydi."""
    if out is None:
        out = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            text_values(v, out)
    elif isinstance(obj, list):
        for v in obj:
            text_values(v, out)
    return out


def language_errors(d):
    """Imlo va begona til xatolari."""
    errs = []
    for txt in text_values(d):
        for m in BAD_APOS.finditer(txt):
            errs.append("imlo xatosi: %r" % txt[max(0, m.start() - 20):m.end() + 20])
        for m in CYRILLIC.finditer(txt):
            errs.append("kirill harfi: %r" % txt[max(0, m.start() - 25):m.start() + 15])
        for m in FOREIGN.finditer(txt):
            errs.append("begona so‘z «%s»: %r"
                        % (m.group(1), txt[max(0, m.start() - 30):m.end() + 20]))
    return errs


def check(path):
    """Xatolar ro‘yxatini qaytaradi (bo‘sh bo‘lsa — toza)."""
    errs = []
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
    except Exception as e:
        return ["JSON o‘qilmadi: %s" % e]

    for key in ("title", "author", "genre", "age_group", "coverage"):
        if not str(d.get(key, "")).strip():
            errs.append("«%s» maydoni bo‘sh" % key)

    p = d.get("passport") or {}
    for key in PASSPORT_FIELDS:
        val = p.get(key)
        if not val or (isinstance(val, str) and len(val.strip()) < 3):
            errs.append("pasportda «%s» yo‘q yoki juda qisqa" % key)
    if isinstance(p.get("topics"), list) and len(p["topics"]) < 3:
        errs.append("mavzular 3 tadan kam")
    # Kengaytirilgan pasport faqat YANGI ro‘yxatda (book_out2) majburiy —
    # eski 130 ta kitob boshqa qolipda tayyorlangan.
    new_format = ("book_out2" in path.replace("\\", "/"))
    ev = p.get("events")
    if new_format and not isinstance(ev, list):
        errs.append("«events» (voqealar tafsiloti) ro‘yxat emas")
    elif new_format:
        need = EVENTS_MIN_SHORT if d.get("short_form") else EVENTS_MIN
        if len(ev) < need:
            errs.append("voqealar tafsiloti %d ta band (kamida %d bo‘lsin)"
                        % (len(ev), need))
        if any(len(str(x).strip()) < 15 for x in ev):
            errs.append("voqealar tafsilotida juda kalta band bor")
    qt = p.get("quotes")
    if new_format and (not isinstance(qt, list) or len(qt) < QUOTES_MIN):
        errs.append("muhim parchalar %s ta (kamida %d bo‘lsin)"
                    % (len(qt) if isinstance(qt, list) else "?", QUOTES_MIN))
    if p.get("age_band") not in AGE_BANDS:
        errs.append("yosh toifasi noto‘g‘ri (%r) — %s dan biri bo‘lsin"
                    % (p.get("age_band"), "/".join(AGE_BANDS)))
    theme = p.get("theme") or ""
    if len(theme) > THEME_MAX:
        errs.append("g‘oyasi %d belgi (%d dan oshmasin)" % (len(theme), THEME_MAX))
    summ = p.get("summary") or ""
    if len(summ) > SUMMARY_MAX:
        errs.append("syujeti %d belgi (%d dan oshmasin)" % (len(summ), SUMMARY_MAX))
    if len(summ) < 200:
        errs.append("syujeti juda kalta (200 belgidan kam)")
    if len((p.get("conclusion") or "")) < 60:
        errs.append("xulosasi yo‘q yoki juda kalta")

    qs = d.get("questions") or []

    # Ega qarori (2026-09-01): DINIY-MA'RIFIY kitobdan test tuzilmaydi —
    # AI diniy matnni talqin qilishda xato qilishi mumkin. O‘rniga aniq
    # parchaga tayangan ochiq savollar beriladi.
    if d.get("no_test"):
        if qs:
            errs.append("diniy kitobga test tuzilmasligi kerak edi (%d ta savol)" % len(qs))
        tqs = d.get("talk_questions") or []
        if len(tqs) < 3:
            errs.append("ochiq savollar %d ta (kamida 3 ta bo‘lsin)" % len(tqs))
        for i, t in enumerate(tqs, 1):
            ctx = str((t or {}).get("context", "")).strip()
            qq = str((t or {}).get("question", "")).strip()
            if len(ctx) < 40:
                errs.append("%d-savol: parcha (context) yo‘q yoki juda kalta" % i)
            if len(qq) < 25 or "?" not in qq:
                errs.append("%d-savol: savol yo‘q yoki savol shaklida emas" % i)
        errs += language_errors(d)
        return errs

    # Test o‘rniga og‘zaki savol beriladigan holatlar:
    #   · asar 5 betdan qisqa, yoki
    #   · AI uni "4-6" yosh toifasiga kiritgan (7 yoshgacha test yo‘q)
    if d.get("short_form") or p.get("age_band") == NO_TEST_BAND:
        if qs:
            errs.append("qisqa asarga test tuzilmasligi kerak edi (%d ta savol bor)" % len(qs))
        tq = (d.get("talk_question") or "").strip()
        if len(tq) < 25:
            errs.append("og‘zaki savol yo‘q yoki juda kalta")
        elif "?" not in tq:
            errs.append("og‘zaki savol savol shaklida emas")
        errs += language_errors(d)
        return errs

    if len(qs) not in PROFILES:
        errs.append("savollar soni %d ta (10, 20 yoki 30 bo‘lishi kerak)" % len(qs))
        return errs
    prof = PROFILES[len(qs)]

    parts, layers, ids = {}, {}, set()
    for q in qs:
        qid = q.get("id")
        if qid in ids:
            errs.append("takroriy id: %s" % qid)
        ids.add(qid)

        part = q.get("part")
        if part not in (1, 2, 3):
            errs.append("%s-savol: qism belgisi noto‘g‘ri (%r)" % (qid, part))
        parts[part] = parts.get(part, 0) + 1

        lay = q.get("barrett")
        if lay not in prof["barrett"]:
            errs.append("%s-savol: Barrett qatlami noto‘g‘ri (%r)" % (qid, lay))
        layers[lay] = layers.get(lay, 0) + 1

        if q.get("category") not in CATEGORIES:
            errs.append("%s-savol: category noto‘g‘ri (%r)" % (qid, q.get("category")))

        opts = q.get("options") or []
        if not 3 <= len(opts) <= 4:
            errs.append("%s-savol: variantlar soni %d ta" % (qid, len(opts)))
        # Soddalik chegarasi: uzun savol bolani javobdan emas, O‘QISHDAN
        # qiynaydi. Ko‘rsatmada 12/6 so‘z so‘raladi, bu yerda biroz erkinlik.
        # Ega qoidasi: mayda tafsilot so‘ralmasin («nechta edi», «necha yoshda»)
        if re.search(r"\bnecha", (q.get("question") or ""), re.I):
            errs.append("%s-savol: mayda tafsilot so‘ralgan («necha...»): %r"
                        % (qid, (q.get("question") or "")[:50]))
        nw = len((q.get("question") or "").split())
        if nw > 16:
            errs.append("%s-savol: %d so‘z — juda uzun (16 dan oshmasin)" % (qid, nw))
        for o in opts:
            if len(o.split()) > 9:
                errs.append("%s-savol: variant %d so‘z — juda uzun: %r"
                            % (qid, len(o.split()), o[:45]))
        if q.get("answer") not in opts:
            errs.append("%s-savol: to‘g‘ri javob variantlar orasida yo‘q" % qid)
        if len(set(opts)) != len(opts):
            errs.append("%s-savol: bir xil variant takrorlangan" % qid)
        if len((q.get("question") or "").strip()) < 10:
            errs.append("%s-savol: savol matni juda kalta" % qid)

    for part in (1, 2, 3):
        need = prof["parts"][part]
        if parts.get(part, 0) != need:
            errs.append("%d-qismda %d ta savol (%d bo‘lishi kerak)"
                        % (part, parts.get(part, 0), need))
    for lay, need in prof["barrett"].items():
        if layers.get(lay, 0) != need:
            errs.append("«%s» qatlami: %d ta (%d bo‘lishi kerak)"
                        % (lay, layers.get(lay, 0), need))

    errs += language_errors(d)
    return errs


def main():
    if len(sys.argv) > 1:
        names = sys.argv[1:]
    else:
        names = sorted(f for f in os.listdir(OUT_DIR) if f.endswith(".json"))
    bad = 0
    for name in names:
        errs = check(os.path.join(OUT_DIR, name))
        if errs:
            bad += 1
            print("✗ %s" % name)
            for e in errs[:12]:
                print("    ·", e)
        else:
            print("✓ %s" % name)
    print("\nTekshirildi: %d ta, xatoli: %d ta" % (len(names), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
