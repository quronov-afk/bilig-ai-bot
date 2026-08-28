#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kitoblar jadvali va holati.

Kitoblarni kunlarga TENG NARXDA taqsimlaydi (uzun kitob qimmat, qisqasi
arzon — shuning uchun soni emas, og‘irligi tenglashtiriladi) va qaysi
biri bajarilganini ko‘rsatadi.

Ishlatish:
    python3 tools/book_plan.py            # umumiy holat
    python3 tools/book_plan.py 1          # 1-kun ro‘yxati
    python3 tools/book_plan.py --kunlar 5 # jadvalni qayta bo‘lish
"""

import json
import os
import sys

WORK = os.path.join("tools", "book_work")
OUT = os.path.join("tools", "book_out")
INDEX = os.path.join(WORK, "index.json")

# «Teddi» o‘lchovi: 51 636 belgi ≈ 20 000 token. O‘zbekcha matnda
# taxminan 2,6 belgi = 1 token. 4000 — mening javobim (pasport + 30 test).
CHARS_PER_TOKEN = 2.6
ANSWER_TOKENS = 4000


def load():
    with open(INDEX, encoding="utf-8") as fh:
        books = json.load(fh)
    for b in books:
        b["tokens"] = int(b["sent_chars"] / CHARS_PER_TOKEN) + ANSWER_TOKENS
        b["done"] = os.path.exists(os.path.join(OUT, b["work_file"][:-4] + ".json"))
    return books


def split_days(books, days):
    """Kunlar orasida narxni tenglashtirib bo‘ladi (och qorin usuli)."""
    groups = [[] for _ in range(days)]
    for b in sorted(books, key=lambda x: -x["tokens"]):
        groups.sort(key=lambda g: sum(x["tokens"] for x in g))
        groups[0].append(b)
    for i, g in enumerate(groups, 1):
        g.sort(key=lambda x: x["tokens"])       # kun ichida arzondan boshlanadi
        for b in g:
            b["day"] = i
    return groups


def main():
    args = sys.argv[1:]
    days = 7
    if "--kunlar" in args:
        days = int(args[args.index("--kunlar") + 1])
        args = [a for a in args if a != "--kunlar" and a != str(days)]

    books = load()
    groups = split_days(books, days)

    with open(INDEX, "w", encoding="utf-8") as fh:
        json.dump(sorted(books, key=lambda b: (b["day"], b["tokens"])),
                  fh, ensure_ascii=False, indent=1)

    if args and args[0].isdigit():
        d = int(args[0])
        g = groups[d - 1]
        print("%d-KUN — %d ta kitob, ~%d ming token\n" % (d, len(g), sum(x["tokens"] for x in g) / 1000))
        for b in g:
            print("  %s %-44s %5.1fk token  %s" %
                  ("✓" if b["done"] else "·", b["title"][:44],
                   b["tokens"] / 1000, b["coverage"]))
        return 0

    done = sum(1 for b in books if b["done"])
    left = sum(b["tokens"] for b in books if not b["done"])
    print("UMUMIY HOLAT: %d / %d ta kitob tayyor" % (done, len(books)))
    print("Qolgan yuk  : ~%.2f mln token\n" % (left / 1e6))
    for i, g in enumerate(groups, 1):
        d = sum(1 for b in g if b["done"])
        print("  %d-kun: %2d ta kitob  ~%3.0f ming token   [%d tayyor]"
              % (i, len(g), sum(x["tokens"] for x in g) / 1000, d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
