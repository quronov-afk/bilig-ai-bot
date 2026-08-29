# ==========================================================
# tools/build_book_seed.py
# ----------------------------------------------------------
# `tools/book_out/` dagi yuzlab alohida JSON faylni BITTA siqilgan
# faylga («books_seed.json.gz») yig‘adi. Server ishga tushganda
# ana shu bitta faylni o‘qib, kitob bazasini to‘ldiradi.
#
# NEGA BITTA FAYL: server har safar 130 ta faylni ochib o‘tirmasin,
# va GitHub'ga ham bitta ixcham fayl tushsin (1.6 MB → ~0.4 MB).
#
# Ishlatish:  python3 tools/build_book_seed.py
# ==========================================================
import glob
import gzip
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "tools", "book_out")
OUT_FILE = os.path.join(ROOT, "books_seed.json.gz")

# Pasportdan bazaga ko‘chiriladigan maydonlar (Book_Base ustunlari).
PASSPORT_FIELDS = ("summary", "characters", "theme", "conclusion", "age_hint",
                   "age_band", "topics", "for_whom", "difficulty", "mood")

# Savoldan bazaga ko‘chiriladigan maydonlar. Ortiqchasi (masalan
# «barrett») tashlanadi — fayl bekorga kattalashmasin.
Q_FIELDS = ("id", "part", "category", "question", "options", "answer")


def norm(t):
    """Kitob nomini solishtirish uchun sodda ko‘rinishga keltiradi.

    DIQQAT: bu `webapp_api.book_key()` bilan AYNAN bir xil ishlashi shart —
    aks holda bazaga tushgan kitobni ilova topa olmaydi.
    """
    t = (t or "").strip().lower()
    for ch in ("‘", "’", "`", "ʻ"):
        t = t.replace(ch, "'")
    t = re.sub(r"[^\w']+", " ", t, flags=re.UNICODE)
    return " ".join(t.split())


def book_key(title, author):
    a = norm(author)
    if not a or "noma'lum" in a:
        a = ""
    return norm(title) + "|" + a


def build():
    books = []
    skipped = []
    for path in sorted(glob.glob(os.path.join(SRC_DIR, "*.json"))):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            skipped.append((os.path.basename(path), "o‘qilmadi: %s" % e))
            continue

        title = (d.get("title") or "").strip()
        author = (d.get("author") or "").strip()
        passport = d.get("passport") or {}
        if not title or not (passport.get("summary") or "").strip():
            skipped.append((os.path.basename(path), "nomi yoki mazmuni yo‘q"))
            continue

        # Savollarni tozalaymiz: javobi variantlar ichida bo‘lmagan savol
        # bolaga hech qachon to‘g‘ri javob bermaydi — uni olib tashlaymiz.
        questions = []
        for q in (d.get("questions") or []):
            opts = q.get("options") or []
            if not q.get("question") or len(opts) < 2 or q.get("answer") not in opts:
                continue
            questions.append({k: q[k] for k in Q_FIELDS if k in q})

        books.append({
            "key": book_key(title, author),
            "title": title,
            "author": author,
            "short_form": 1 if d.get("short_form") else 0,
            "passport": {k: passport.get(k) for k in PASSPORT_FIELDS
                         if passport.get(k)},
            "questions": questions,
        })

    data = {"version": 1, "books": books}
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # mtime=0 — fayl har safar AYNAN bir xil chiqsin (o‘zgarmagan bo‘lsa
    # Git'da «o‘zgardi» bo‘lib ko‘rinmasin).
    with gzip.GzipFile(OUT_FILE, "wb", mtime=0) as f:
        f.write(raw)

    with_test = sum(1 for b in books if b["questions"])
    print("Kitoblar:      %d ta" % len(books))
    print("  testi bor:   %d ta" % with_test)
    print("  qisqa asar:  %d ta (test tuzilmaydi)" % sum(1 for b in books if b["short_form"]))
    print("Savollar jami: %d ta" % sum(len(b["questions"]) for b in books))
    print("Fayl:          %s (%.0f KB)" % (OUT_FILE, os.path.getsize(OUT_FILE) / 1024.0))
    if skipped:
        print("O‘tkazib yuborildi: %d ta" % len(skipped))
        for name, why in skipped:
            print("   %s — %s" % (name, why))


if __name__ == "__main__":
    build()
