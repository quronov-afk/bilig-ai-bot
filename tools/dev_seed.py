# -*- coding: utf-8 -*-
"""Mahalliy sinov uchun namunaviy baza yaratadi.

Ishlatish (loyiha ildizidan):
    rm -f bot_base.db
    DEV_MODE=1 python3 tools/dev_seed.py
    DEV_MODE=1 OWNER_ID=1001 PORT=8080 python3 webapp_api.py &

So‘ng brauzerda: http://localhost:8080/?dev_id=1001

Yaratiladi: ota-ona (1001) + 3 farzand (Ibrohim 9, Ismoil 7, Sadi 12).
Sadi to‘liq namoyish ma'lumoti bilan to‘ldiriladi.

Bundan tashqari BO‘SH ota-ona (1002) ham yaratiladi — hech qanday farzandi,
kitobi va sovg‘asi yo‘q. U barcha «bo‘sh ekran»larni ko‘rish uchun kerak:
    http://localhost:8080/?dev_id=1002
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DEV_MODE", "1")

import database                      # noqa: E402
database.init_db()
import webapp_api                    # noqa: E402
import demo_data                     # noqa: E402

conn, cursor = database.conn, database.cursor
app = webapp_api.app.test_client()

cursor.execute(
    "INSERT OR REPLACE INTO Users (user_id, role, name, is_approved) "
    "VALUES (1001, 'parent', 'Sadullo Quronov', 1)"
)
conn.commit()

for name, age, avatar in [("Ibrohim", 9, "lion"), ("Ismoil", 7, "penguin"), ("Sadi", 12, "fox")]:
    app.post("/api/parent/children?dev_id=1001",
             json={"name": name, "age": age, "avatar_id": avatar})

# Sadi (-3) — to‘liq namoyish
demo_data.fill_demo_child(1001, -3)

# Test natijalari (to‘g‘ri/xato sanog‘i bilan)
for i, (title, correct, total) in enumerate([
    ("Sariq devni minib", 18, 18),
    ("Tom Soyerning boshidan kechirganlari", 16, 18),
    ("Amir Temur haqida hikoyalar", 15, 17),
    ("Kapitan Grant bolalari", 14, 18),
]):
    row = cursor.execute("SELECT book_id FROM Plan_Books WHERE title = ?", (title,)).fetchone()
    if not row:
        continue
    pct = round(correct / total * 100)
    ts = (datetime.now() - timedelta(days=3 + i * 5)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, logic_score, "
        "conclusion_score, created_at, correct_count, total_count) VALUES (?, ?, 'test', ?, ?, ?, ?, ?, ?)",
        (-3, row[0], pct, pct, pct, ts, correct, total)
    )

# BO‘SH OTA-ONA (1002) — bo‘sh ekranlarni ko‘rish uchun. Farzandi ham,
# kitobi ham, do‘konda mahsuloti ham yo‘q.
cursor.execute(
    "INSERT OR REPLACE INTO Users (user_id, role, name, is_approved) "
    "VALUES (1002, 'parent', 'Yangi ota-ona', 1)"
)

# Ibrohim (-1) — eski uslubdagi nishon (migratsiyani sinash uchun)
cursor.execute("UPDATE Users SET badges = ? WHERE user_id = -1", ("🗣 Notiq",))
conn.commit()

kids = cursor.execute("SELECT user_id, name, child_code FROM Users WHERE role = 'child'").fetchall()
print("Namunaviy baza tayyor. Farzandlar:")
for uid, name, code in kids:
    print(f"   {name:10} id={uid}  ID kodi: {code}")
print("\nOching: http://localhost:8080/?dev_id=1001")
print("Bo‘sh ekranlar:  http://localhost:8080/?dev_id=1002")
