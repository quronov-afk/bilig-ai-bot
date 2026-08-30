# -*- coding: utf-8 -*-
"""Test bazasini muharrir sifatida tekshirish (bir martalik ish).

NEGA KERAK: bazadagi savollar orasida mavjud bo‘lmagan so‘zlar, harfi
almashib ketgan so‘zlar va g‘aliz jumlalar bor edi. Bu skript har bir
kitobning savollarini Gemini'ga yuborib, FAQAT TILINI tuzattiradi.

XAVFSIZLIK QOIDASI: AI savol ma'nosini, variantlar sonini yoki to‘g‘ri
javobning o‘rnini o‘zgartira olmaydi. To‘g‘ri javob AI'ga umuman
ko‘rsatilmaydi — u raqam bo‘yicha shu yerda saqlanib turadi va ish
oxirida joyiga qaytariladi. Tekshiruvdan o‘tmagan javob rad etiladi va
kitobning eski savollari o‘zgarishsiz qoladi.

Ish to‘xtab qolsa, qaytadan ishga tushirilganda qolgan joyidan davom
etadi (tayyor natijalar alohida faylga yozib boriladi).
"""
import os
import sys
import json
import gzip
import asyncio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Maxfiy kalitlar odatda serverning o‘z sozlamalarida turadi. Bu skript
# esa shaxsiy kompyuterda ishlaydi — kalitni yonidagi .env faylidan olamiz.
_env = os.path.join(ROOT, ".env")
if os.path.exists(_env):
    for _line in open(_env, encoding="utf-8"):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

import ai_service                                    # noqa: E402

SEED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "books_seed.json.gz")
PROGRESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "edit_tests_progress.json")
PARALLEL = 3          # bir vaqtda nechta kitob — chegaraga urilmaslik uchun


def prompt_for(title, author, items):
    body = json.dumps(items, ensure_ascii=False, indent=1)
    return f"""Sen tajribali o‘zbek tili muharririsan. Quyida «{title}»
kitobi ({author or "muallif noma'lum"}) bo‘yicha bolalar uchun tuzilgan
test savollari berilgan.

{body}

VAZIFANG — FAQAT TILNI TUZATISH:
· Mavjud bo‘lmagan so‘zlarni to‘g‘ri so‘z bilan almashtir.
· Harfi tushib qolgan yoki almashib ketgan so‘zlarni tuzat.
· Grammatik xatolarni (kelishik, egalik, zamon qo‘shimchalari) tuzat.
· G‘aliz, tarjimaga o‘xshagan jumlani ravon o‘zbekcha jumlaga aylantir.
· Ruscha yoki inglizcha so‘z bo‘lsa — o‘zbekchasiga almashtir.
· O‘, o‘, G‘, g‘ harflari chapga qaragan jingalak belgi bilan yozilsin.
  Tutuq belgisi (ma'lumot, e'tibor) oddiy apostrof bilan qoladi.

QAT'IY TAQIQLAR:
· Savol MA'NOSINI o‘zgartirma. Yangi savol qo‘shma, birortasini o‘chirma.
· Variantlar SONINI o‘zgartirma va TARTIBINI almashtirma — qaysi variant
  nechanchi o‘rinda bo‘lsa, o‘sha o‘rinda qolsin.
· Har bir savolning "id" raqami o‘zgarmasin.
· Xato bo‘lmagan matnni «yaxshilash» uchun qayta yozma — o‘zgarishsiz qoldir.

Natijani FAQAT quyidagi JSON ro‘yxat formatida qaytar (boshqa hech narsa yozma):
[{{"id": 1, "question": "Savol matni?", "options": ["Birinchi", "Ikkinchi", "Uchinchi"]}}]"""


async def edit_book(book, sem, done):
    key = book.get("key")
    qs = book.get("questions") or []
    if not qs or key in done:
        return
    items = [{"id": q.get("id"), "question": q.get("question", ""),
              "options": list(q.get("options") or [])} for q in qs]
    # To‘g‘ri javob AI'ga ko‘rsatilmaydi — o‘rni raqam bilan shu yerda qoladi.
    answer_idx = []
    for q in qs:
        opts = q.get("options") or []
        try:
            answer_idx.append(opts.index(q.get("answer")))
        except ValueError:
            answer_idx.append(-1)

    async with sem:
        try:
            resp = await ai_service._ask("edit_tests", [prompt_for(
                book.get("title", ""), book.get("author", ""), items)],
                json_mode=True, attempts=2)
            fixed = json.loads(ai_service.clean_json(resp.text))
        except Exception as e:
            print("XATO  %-40s %r" % (book.get("title", "")[:40], e), flush=True)
            return

    if not isinstance(fixed, list) or len(fixed) != len(qs):
        print("RAD   %-40s savol soni mos emas" % book.get("title", "")[:40], flush=True)
        return

    by_id = {}
    for f in fixed:
        if isinstance(f, dict):
            by_id[str(f.get("id"))] = f

    out, changed = [], 0
    for i, q in enumerate(qs):
        f = by_id.get(str(q.get("id")))
        new_q = dict(q)
        old_opts = q.get("options") or []
        if f:
            nq = ai_service.tidy_uz((f.get("question") or "").strip(), "[muharrir]")
            nopts = [ai_service.tidy_uz(str(o).strip(), "[muharrir]")
                     for o in (f.get("options") or [])]
            # Tekshiruv: matn bo‘sh emas va variantlar soni o‘sha-o‘sha.
            if nq and len(nopts) == len(old_opts) and all(nopts):
                if nq != q.get("question") or nopts != old_opts:
                    changed += 1
                new_q["question"] = nq
                new_q["options"] = nopts
                if answer_idx[i] >= 0:
                    new_q["answer"] = nopts[answer_idx[i]]
        # Javob har doim variantlardan biri bo‘lishi SHART.
        if new_q.get("answer") not in (new_q.get("options") or []):
            new_q = dict(q)
        out.append(new_q)

    done[key] = out
    with open(PROGRESS, "w", encoding="utf-8") as f:
        json.dump(done, f, ensure_ascii=False)
    print("OK    %-40s %d ta savol, %d tasi tahrirlandi"
          % (book.get("title", "")[:40], len(out), changed), flush=True)


async def main():
    with gzip.open(SEED, "rt", encoding="utf-8") as f:
        data = json.load(f)
    books = data.get("books") or []

    done = {}
    if os.path.exists(PROGRESS):
        try:
            with open(PROGRESS, encoding="utf-8") as f:
                done = json.load(f)
        except Exception:
            done = {}
    print("Kitoblar: %d ta, avvaldan tayyor: %d ta" % (len(books), len(done)), flush=True)

    sem = asyncio.Semaphore(PARALLEL)
    await asyncio.gather(*[edit_book(b, sem, done) for b in books])

    fixed_books = 0
    for b in books:
        if b.get("key") in done:
            b["questions"] = done[b["key"]]
            fixed_books += 1
    with gzip.open(SEED, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print("\nTAYYOR: %d ta kitobning testi tahrirdan o‘tdi." % fixed_books, flush=True)


if __name__ == "__main__":
    asyncio.run(main())
