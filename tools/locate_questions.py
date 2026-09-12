#!/usr/bin/env python3
# ==========================================================
# tools/locate_questions.py
# ----------------------------------------------------------
# Har bir test savolining javobi kitobning QAYERIDA ekanini topadi
# (0-100 foiz) va tools/question_pos.json ga yozadi.
#
# NEGA KERAK (ega topgan xato, 2026-09-13): savollar Word matndan
# tuzilgan, bosma kitob esa boshqacha sahifalanadi; ustiga-ustak
# katta kitoblarda AI matnni parchalab o‘qigan va «boshi/o‘rtasi/oxiri»
# belgisini taxminan qo‘ygan. Natijada 1-oraliq testda bola hali
# o‘qimagan joydan savol tushishi mumkin edi.
#
# USUL (AI'siz, tekin): savol va to‘g‘ri javobdagi kamyob so‘zlar
# to‘liq matnning qaysi bo‘lagida birga uchrashi izlanadi. O‘rin
# ishonchli topilmasa — null (bunday savol faqat yakuniy testga tushadi).
# Foiz bet raqamiga bog‘liq emas, shuning uchun bosma nashr qanday
# sahifalanganining farqi yo‘q.
#
# Ishlatish:  python3 tools/locate_questions.py
# ==========================================================
import bisect
import collections
import glob
import json
import math
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from extract_books import read_paragraphs      # noqa: E402
from build_book_seed import book_key           # noqa: E402

WORD_DIRS = [os.environ.get("BILIG_WORD_DIR", ""),
             os.path.expanduser("~/Мой диск/BOT/BILIG/Mutolaa Word 28.08.2026"),
             os.path.expanduser("~/Desktop/Mutolaa Word 28.08.2026")]
SOURCES = [("tools/book_out", "tools/book_work/index.json"),
           ("tools/book_out2", "tools/book_work2/index.json")]
OUT_FILE = os.path.join(ROOT, "tools", "question_pos.json")

# Ishonch mezoni. 2026-09-13 da besh variant sinaldi (197 kitob, 5580 savol):
# 0.50/0.85 — 2416 ta o‘rin, AI «1-qism» deganlarining 92 % i ≤33 %;
# 0.40/0.90 — 2893 ta, 90 %; 0.30/0.95 — 3414 ta, 86 %. O‘rtachasi tanlandi:
# qamrov 20 % oshadi, aniqlik deyarli pasaymaydi.
RATIO_MIN = 0.40   # topilgan so‘zlar «og‘irligi» savolnikining kamida shuncha qismi
AMBIG_MAX = 0.90   # boshqa joyda deyarli shunday moslik bo‘lsa — o‘rin noaniq

APOS = str.maketrans({"‘": "'", "’": "'", "ʻ": "'", "`": "'", "ʼ": "'"})
WORD = re.compile(r"[a-zа-яёқғўҳ']+")
OPT_PREFIX = re.compile(r"^\s*[A-DА-Г]\)\s*")

# Savol so‘zlari va ko‘p uchraydigan yordamchi so‘zlar — joy ko‘rsatmaydi.
STOP = set("""
bilan uchun keyin qaysi nima nimaga nimani nimadan nimada nega qanday qancha
kimga kimni kimning kimdan qachon qayerda qayerga qayerdan shunda ushbu ular
uning ularning ekan emas bo'ldi bo'lib bo'lgan bo'ladi qildi qilib qilgan
qiladi dedi degan kabi juda yana hamma barcha biror hech endi hali faqat
lekin ammo biroq chunki sababli tufayli orqali haqida o'zi o'zini sizni
sening menga mening bizning ularni boshqa birinchi ikkinchi oxirida boshida
paytda vaqtda keldi ketdi berdi oldi turdi hikoya kitob kitobda asar asarda
qahramon qahramoni muallif voqea voqeada so'radi aytdi boshladi nimalar
yordam o'rniga o'rtasida davomida natijada sabab sababi uchun ekanligi
""".split())
STOP_STEMS = {w[:5] for w in STOP}


def stems(text):
    t = unicodedata.normalize("NFC", text or "").lower().translate(APOS)
    out = []
    for m in WORD.finditer(t):
        w = m.group(0).strip("'")
        if len(w) < 4 or w in STOP:
            continue
        s = w[:5]
        if s in STOP_STEMS:
            continue
        out.append(s)
    return out


def word_dir():
    for d in WORD_DIRS:
        if d and os.path.isdir(d):
            return d
    sys.exit("Word papkasi topilmadi (BILIG_WORD_DIR bilan ko‘rsating)")


def book_text(path):
    return "\n".join(t for t, _ in read_paragraphs(path))


class Book:
    def __init__(self, text):
        self.tok = stems(text)
        self.n = len(self.tok)
        self.W = 250 if self.n >= 5000 else max(40, self.n // 10)
        self.occ = collections.defaultdict(list)
        for i, s in enumerate(self.tok):
            self.occ[s].append(i)
        nwin = max(1, -(-self.n // self.W))
        self.idf = {}
        for s, lst in self.occ.items():
            df = len({i // self.W for i in lst})
            v = math.log((nwin + 1.0) / (df + 0.5))
            self.idf[s] = v if v > 0.2 else 0.0

    def locate(self, qtext):
        q = [s for s in dict.fromkeys(stems(qtext)) if self.idf.get(s, 0) > 0]
        if len(q) < 2:
            return None
        total = sum(self.idf[s] for s in q)
        rare = sorted(q, key=lambda s: len(self.occ[s]))[:2]
        half = self.W // 2
        cands = []
        for s in rare:
            for p in self.occ[s]:
                score, hits = 0.0, []
                for t in q:
                    lst = self.occ[t]
                    j = bisect.bisect_left(lst, p - half)
                    if j < len(lst) and lst[j] <= p + half:
                        score += self.idf[t]
                        hits.append(lst[j])
                if len(hits) >= 2:
                    hits.sort()
                    cands.append((score, hits[len(hits) // 2]))
        if not cands:
            return None
        cands.sort(key=lambda c: (-c[0], c[1]))
        best, bpos = cands[0]
        second = max((c[0] for c in cands if abs(c[1] - bpos) > self.W), default=0.0)
        if best / total < RATIO_MIN or second >= AMBIG_MAX * best:
            return None
        return int(round(100.0 * bpos / max(1, self.n - 1)))


def main():
    wd = word_dir()
    files = {unicodedata.normalize("NFC", f): f for f in os.listdir(wd)}
    result, st = {}, collections.Counter()
    risky_examples = []
    for out_dir, index_path in SOURCES:
        items = json.load(open(os.path.join(ROOT, index_path), encoding="utf-8"))
        items = items if isinstance(items, list) else list(items.values())
        by_title = {(i["title"], i["author"]): i for i in items}
        for path in sorted(glob.glob(os.path.join(ROOT, out_dir, "*.json"))):
            d = json.load(open(path, encoding="utf-8"))
            qs = d.get("questions") or []
            if not qs:
                continue
            it = by_title.get((d.get("title"), d.get("author")))
            real = files.get(unicodedata.normalize("NFC", it["file"])) if it else None
            if not real:
                st["kitob_fayli_yoq"] += 1
                continue
            bk = Book(book_text(os.path.join(wd, real)))
            st["kitob"] += 1
            positions = {}
            per_part = collections.defaultdict(int)
            for q in qs:
                st["savol"] += 1
                part = int(q.get("part") or 0) if str(q.get("part", "")).isdigit() else 0
                per_part[part] += 1
                served_mid = part in (1, 2) and per_part[part] <= 7   # eski tizimda oraliqqa tushgan
                if q.get("category") == "conclusion":
                    pos = None
                    st["xulosa_faqat_yakuniy"] += 1
                else:
                    ans = OPT_PREFIX.sub("", str(q.get("answer") or ""))
                    pos = bk.locate(str(q.get("question") or "") + " " + ans)
                if pos is None:
                    st["orni_noaniq"] += 1
                else:
                    st["orni_topildi"] += 1
                    bucket = 1 if pos <= 33 else (2 if pos <= 67 else 3)
                    st["ai_bilan_mos" if bucket == part else "ai_bilan_farq"] += 1
                    if served_mid and ((part == 1 and pos > 33) or (part == 2 and pos > 67)):
                        st["xavfli_eski_oraliq"] += 1
                        if len(risky_examples) < 4:
                            risky_examples.append((d["title"], part, pos, q.get("question")))
                positions[str(q.get("question"))] = pos
            result[book_key(d["title"], d["author"])] = positions
    json.dump(result, open(OUT_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    located = st["orni_topildi"]
    print("Kitoblar: %d | savollar: %d" % (st["kitob"], st["savol"]))
    print("O‘rni topildi: %d (%.0f%%) | noaniq: %d | xulosa savoli (faqat yakuniy): %d"
          % (located, 100.0 * located / max(1, st["savol"]), st["orni_noaniq"], st["xulosa_faqat_yakuniy"]))
    print("AI belgisi bilan mos: %d | farq: %d" % (st["ai_bilan_mos"], st["ai_bilan_farq"]))
    print("ESKI TIZIMDA o‘qilmagan joydan oraliq testga tushgan savollar: %d" % st["xavfli_eski_oraliq"])
    if st["kitob_fayli_yoq"]:
        print("Word fayli topilmagan kitob: %d" % st["kitob_fayli_yoq"])
    for t, p, pos, qq in risky_examples:
        print("  misol: «%s» — AI %d-qism degan, aslida %d%%: %s" % (t, p, pos, qq))
    print("Yozildi:", OUT_FILE)


if __name__ == "__main__":
    main()
