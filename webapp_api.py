# ==========================================================
# webapp_api.py
# ------------------------------------------------------------
# BU FAYL — "Bilig AI" Telegram Mini App uchun BACKEND (API).
# Botdagi barcha funksiyalar (kitob qo‘shish, o‘qish, testlar,
# do‘kon, reyting, natijalar, admin statistikasi) shu yerda
# WEB so‘rovlari (HTTP so‘rovlar) sifatida qayta ishlanadi.
#
# MUHIM: bu fayl botning o‘zidagi database.py, config.py va
# ai_service.py fayllaridan FOYDALANADI (ularni qayta yozmaydi).
# Shuning uchun bu faylni loyihaning ASOSIY papkasiga
# (main.py bilan bir joyga) qo‘yish kerak.
# ==========================================================

import os
import io
import re
import json
import time
import hmac
import hashlib
import asyncio
import threading
import traceback
import uuid
import urllib.parse
from datetime import datetime, date, timedelta

import requests
from flask import Flask, request, jsonify, send_from_directory, g, Response

from config import BOT_TOKEN, OWNER_ID, RECOMMENDED_BOOKS
from database import (
    conn, cursor, get_parent_id, update_streak,
    calculate_and_update_rank, get_child_total_pages,
    get_child_passport_data, generate_admin_stats_text,
    generate_progress_bar, get_badges
)
import ai_service
import badges_engine

# ------------------------------------------------------------
# Kichik ma'lumotlar bazasi yangilanishi (migratsiya):
# Users jadvaliga bola avatarini va "profil to‘ldirilganmi" belgisini
# saqlash uchun 2 ta yangi ustun qo‘shamiz. database.py faylini
# qayta yozmaslik uchun shu yerda, xavfsiz tarzda (agar ustun
# allaqachon mavjud bo‘lsa xatoni e'tiborsiz qoldirib) qo‘shiladi.
# ------------------------------------------------------------
for _col_sql in (
    "ALTER TABLE Users ADD COLUMN avatar_id TEXT DEFAULT 'fox'",
    "ALTER TABLE Users ADD COLUMN profile_done INTEGER DEFAULT 0",
    # Ovozli xulosa uchun AI bergan Bilig bahosi (bosh sahifada ko‘rsatiladi)
    "ALTER TABLE Diagnostic_Logs ADD COLUMN bonus_bilig INTEGER DEFAULT 0",
    # Reja turi: 'quick' — bir martalik kitob, 'marathon' — bir nechta kitobli marafon.
    # Eski rejalar 'quick' bo‘lib qoladi, chunki ular odatda bitta kitobdan iborat.
    "ALTER TABLE Reading_Plans ADD COLUMN plan_type TEXT DEFAULT 'quick'",
    # Farzandning shaxsiy ulanish kodi (8 xonali). Ota-ona farzandni o‘z
    # kabinetidan yaratganda beriladi; farzand keyinchalik o‘z telefonidan
    # kirmoqchi bo‘lsa, aynan shu kodni kiritadi.
    "ALTER TABLE Users ADD COLUMN child_code TEXT",
    # AI ustozning bolaning o‘ziga aytgan iliq xabari (ota-ona hisoboti alohida)
    "ALTER TABLE Diagnostic_Logs ADD COLUMN child_note TEXT",
    # Testda nechta savol bo‘lgani va nechtasiga to‘g‘ri javob berilgani.
    # Ilgari faqat umumiy foiz saqlanardi, sanoq esa yo‘qolib ketardi.
    "ALTER TABLE Diagnostic_Logs ADD COLUMN correct_count INTEGER",
    "ALTER TABLE Diagnostic_Logs ADD COLUMN total_count INTEGER",
    # Bolaga ko‘rsatilgan nishonlar soni. Bundan ortig‘i — u hali ko‘rmagan
    # nishonlar; ilovaga kirganda tipratikan ularni yetkazadi.
    "ALTER TABLE Users ADD COLUMN badges_seen INTEGER DEFAULT 0",
    # Ota-onaga oxirgi marta 3 kunlik xulosa yuborilgan vaqt
    "ALTER TABLE Users ADD COLUMN last_summary_at TEXT",
    # AI ustoz savoliga javob berilganmi (kitob boshi va oxiri uchun).
    "ALTER TABLE Plan_Books ADD COLUMN talk_start_done INTEGER DEFAULT 0",
    "ALTER TABLE Plan_Books ADD COLUMN talk_end_done INTEGER DEFAULT 0",
    # Oxirgi ovozli xulosa yuborilganda kitob nechanchi betda edi.
    # Keyingi xulosa uchun bola yana 15 bet o‘qishi kerak.
    "ALTER TABLE Plan_Books ADD COLUMN voice_last_page INTEGER DEFAULT 0",
    # Qisqa asar: test tuzilmaydi, o‘rniga og‘zaki xulosa so‘raladi.
    "ALTER TABLE Book_Base ADD COLUMN short_form INTEGER DEFAULT 0",
    # Asar xulosasi — ota-onaga «bu kitob farzandimga nima beradi?» javobi.
    "ALTER TABLE Book_Base ADD COLUMN conclusion TEXT",
    # Yosh toifasi: 4-6 | 7-8 | 9-10 | 11-13 | 14-16
    "ALTER TABLE Book_Base ADD COLUMN age_band TEXT",
    # Mavzu teglari (JSON ro‘yxat) — AI ustoz kitob tavsiya qilishda ishlatadi
    "ALTER TABLE Book_Base ADD COLUMN topics TEXT",
    # Qanday bolaga mos kelishi — tavsiya uchun eng muhim maydon
    "ALTER TABLE Book_Base ADD COLUMN for_whom TEXT",
    "ALTER TABLE Book_Base ADD COLUMN difficulty TEXT",
    "ALTER TABLE Book_Base ADD COLUMN mood TEXT",
    # Ota-ona kitob muqovasini rasmga olsa — o‘sha rasm fayli nomi.
    # Bo‘sh bo‘lsa, muqova katalogdan nomi bo‘yicha topiladi.
    "ALTER TABLE Plan_Books ADD COLUMN cover_file TEXT",

    # Bankdagi test qayerdan kelgan: 1 — o‘qish davomida yig‘ilgan sahifa
    # yozuvlaridan. Bunday test faqat YAKUNIY test sifatida ishlatiladi.
    "ALTER TABLE Test_Bank ADD COLUMN from_notes INTEGER DEFAULT 0",
):
    try:
        cursor.execute(_col_sql)
        conn.commit()
    except Exception:
        pass

# ------------------------------------------------------------
# ESKI NISHONLARNI YANGI TIZIMGA O‘TKAZISH (bir martalik)
# ------------------------------------------------------------
# Ilgari faqat 3 ta nishon bor edi va ular bo‘shliq bilan, emoji bilan
# saqlanardi. Endi 29 talik tizim ishlaydi: nomlar vergul bilan ajratiladi
# va webapp/badges/ dagi chizma nomlariga aynan mos keladi.
# Eski nishonlar aynan shu ko‘rinishda saqlangan edi (emoji bilan).
# Aynan shu satrlar qidiriladi — «Zukko kitobxon» kabi yangi nomlar
# tasodifan o‘zgarib ketmasligi uchun.
_OLD_BADGE_MAP = {
    "🔥 Charchamas Kitobxon": "Tengsiz qahramon",
    "🗣 Notiq": "Ilm notig‘i",
    "🧠 Zukko": "Zukko kitobxon",
}


def _migrate_old_badges():
    try:
        cursor.execute("SELECT user_id, badges FROM Users WHERE badges IS NOT NULL AND badges != ''")
        rows = cursor.fetchall()
    except Exception:
        return
    changed = 0
    for uid, raw in rows:
        text = raw or ""
        if not any(old in text for old in _OLD_BADGE_MAP):
            continue
        names = []
        for old, new in _OLD_BADGE_MAP.items():
            if old in text:
                text = text.replace(old, ",")
                if new not in names:
                    names.append(new)
        # Eski yozuvda boshqa nomlar ham qolgan bo‘lsa, ular saqlanadi
        for part in text.split(","):
            part = part.strip()
            if part and part not in names:
                names.append(part)
        try:
            cursor.execute("UPDATE Users SET badges = ? WHERE user_id = ?", (",".join(names), uid))
            changed += 1
        except Exception:
            pass
    if changed:
        conn.commit()
        print(f"[webapp_api] {changed} ta foydalanuvchining eski nishonlari yangilandi")


_migrate_old_badges()

# ------------------------------------------------------------
# NISHON NOMI O‘ZGARGANDA BAZANI KO‘CHIRISH
# ------------------------------------------------------------
# Nishonlar bazada NOMI bo‘yicha saqlanadi (Users.badges). Nom
# o‘zgartirilsa, bolalar qo‘lga kiritgan nishon yo‘qolib qolmasligi
# uchun eski nom yangisiga ko‘chiriladi. Ro‘yxat o‘sib boradi;
# ikki marta ishga tushsa ham zarari yo‘q.
# ------------------------------------------------------------
_BADGE_RENAMES = [
    ("Ming betlik dovon", "Ming bir sahifa"),
    ("Kitoblar ummoni", "Kitob ummoni"),
    ("Yengilmas qahramon", "Tengsiz qahramon"),
    ("Kichik kutubxonachi", "Yosh kutubxonachi"),
    ("Bilim notig‘i", "Ilm notig‘i"),
    ("Bilim akademiyasi", "Bilimdon"),
]


def _migrate_badge_renames():
    if not _BADGE_RENAMES:
        return
    table = dict(_BADGE_RENAMES)
    try:
        cursor.execute("SELECT user_id, badges FROM Users "
                       "WHERE badges IS NOT NULL AND badges != ''")
        rows = cursor.fetchall()
    except Exception:
        return
    changed = 0
    for uid, raw in rows:
        names = [b.strip() for b in (raw or "").split(",") if b.strip()]
        new_names = []
        for b in names:
            b = table.get(b, b)
            if b not in new_names:
                new_names.append(b)
        if new_names != names:
            try:
                cursor.execute("UPDATE Users SET badges = ? WHERE user_id = ?",
                               (",".join(new_names), uid))
                changed += 1
            except Exception:
                pass
    if changed:
        conn.commit()
        print(f"[webapp_api] {changed} ta foydalanuvchining nishon nomlari ko‘chirildi")


_migrate_badge_renames()

# 10 ta bolalar avatari — cho‘chqa ISTISNO qilingan
AVATAR_IDS = ["fox", "bear", "penguin", "rabbit", "cat", "owl", "panda", "lion", "elephant", "dog"]

# ------------------------------------------------------------
# Flask ilovasi. Mini App fayllari (index.html, app.js, style.css)
# shu webapp_api.py bilan BIR XIL papkada turgan "webapp" papkasidan
# xizmat qiladi (masalan: /project/webapp_api.py va /project/webapp/index.html).
# Agar shu joyda topilmasa, ehtiyot chorasi sifatida bir qavat yuqoridan
# ham qidiradi — turli papka joylashuvlarida ham ishlashi uchun.
# ------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_CANDIDATES = [
    os.path.join(_HERE, "webapp"),                              # webapp_api.py bilan bir papkada
    os.path.join(os.path.dirname(_HERE), "webapp"),              # webapp_api.py bir qavat pastki papkada bo‘lsa
]
WEBAPP_DIR = next((p for p in _CANDIDATES if os.path.isdir(p)), _CANDIDATES[0])
print(f"[webapp_api] Mini App fayllari shu papkadan xizmat qiladi: {WEBAPP_DIR}")

app = Flask(__name__, static_folder=WEBAPP_DIR, static_url_path="")

# SQLite bir vaqtda ko‘p yozuvlarda xato bermasligi uchun oddiy qulf (lock)
db_lock = threading.Lock()

# ------------------------------------------------------------
# AI SARFINI TEJAYDIGAN JADVALLAR
# ------------------------------------------------------------
# 1) Test_Bank — bir xil kitobga test FAQAT BIR MARTA tuziladi. Keyin
#    o‘sha kitobni qo‘shgan har bir oila tayyor testni bepul oladi.
#    Bu — eng qimmat AI chaqiruvi, shuning uchun tejash ham eng katta.
# 2) Page_Check_Cache — aynan bir xil sahifa rasmi qayta yuborilsa,
#    AI qayta chaqirilmaydi, oldingi javob ishlatiladi.
# 3) Page_Check_Log — kunlik chegarani hisoblash uchun.
# ------------------------------------------------------------
for _tbl_sql in (
    """CREATE TABLE IF NOT EXISTS Test_Bank (
        book_key TEXT PRIMARY KEY,
        title TEXT,
        author TEXT,
        questions_json TEXT,
        use_count INTEGER DEFAULT 0,
        created_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS Page_Check_Cache (
        img_hash TEXT PRIMARY KEY,
        result_json TEXT,
        created_at TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS Page_Check_Log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id INTEGER,
        img_hash TEXT,
        from_cache INTEGER DEFAULT 0,
        created_at TEXT
    )""",
    # Bola o‘qish davomida yuborgan har bir sahifaning qisqa mazmuni.
    # AI rasmni baribir o‘qiydi — biz shunchaki ko‘rganini saqlab qolamiz.
    """CREATE TABLE IF NOT EXISTS Book_Page_Notes (
        book_id INTEGER,
        page_number INTEGER,
        note TEXT,
        created_at TEXT,
        PRIMARY KEY (book_id, page_number)
    )""",
    # Shu kitob uchun test yozuvlardan tuzilganmi va nechta yozuv ishlatilgan.
    # Ota-ona qo‘lda tuzgan yoki umumiy bankdan kelgan testni BUZMASLIK uchun
    # kerak: bu jadvalda yozuvi yo‘q testga biz tegmaymiz.
    """CREATE TABLE IF NOT EXISTS Auto_Test_State (
        book_id INTEGER PRIMARY KEY,
        notes_used INTEGER DEFAULT 0,
        updated_at TEXT
    )""",
    # UMUMIY KITOB BAZASI. Katalogda yo‘q kitoblar ham shu yerda yig‘iladi.
    # AI test uchun rasmlarni baribir o‘qiydi — o‘sha o‘qiganini saqlab
    # qolamiz. Ertaga boshqa oila shu kitobni qo‘shsa, mazmuni TAYYOR
    # turadi va AI umuman chaqirilmaydi.
    # AI USTOZ SAVOLLARI — bola ovozda javob beradigan ochiq savollar.
    # Kalit bo‘yicha saqlanadi, ya'ni bir marta tuzilsa hamma oilaga yetadi.
    """CREATE TABLE IF NOT EXISTS Book_Talk_Questions (
        book_key TEXT,
        stage TEXT,
        question TEXT,
        created_at TEXT,
        PRIMARY KEY (book_key, stage)
    )""",
    """CREATE TABLE IF NOT EXISTS Book_Base (
        book_key TEXT PRIMARY KEY,
        title TEXT,
        author TEXT,
        summary TEXT,
        characters TEXT,
        theme TEXT,
        age_hint TEXT,
        source TEXT,
        use_count INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    )""",
):
    try:
        cursor.execute(_tbl_sql)
        conn.commit()
    except Exception:
        pass

# ------------------------------------------------------------
# FOYDALANUVCHI YUKLAGAN RASMLAR (avatar va kitob muqovasi)
# ------------------------------------------------------------
# Rasm telefonning O‘ZIDA kichraytirilib, WebP formatiga o‘tkaziladi —
# serverga tayyor, kichkina fayl keladi. Shuning uchun bu yerda rasm
# bilan ishlaydigan kutubxona kerak emas.
#
# Disk: avatar ~8 KB, muqova ~20 KB. Ming bola + ming muqova = ~28 MB.
# O‘smasligi uchun uch qoida: qat'iy hajm chegarasi, bir xil fayl ikki
# marta saqlanmaydi (mazmuni bo‘yicha), eskisi ishlatilmasa o‘chiriladi.
# ------------------------------------------------------------
UPLOAD_DIR = "/var/data/uploads" if os.path.isdir("/var/data") else \
    os.path.join(_HERE, "uploads")
AVATAR_MAX_BYTES = 40 * 1024
COVER_MAX_BYTES = 80 * 1024

for _sub in ("av", "cv"):
    try:
        os.makedirs(os.path.join(UPLOAD_DIR, _sub), exist_ok=True)
    except Exception as e:
        print(f"[webapp_api] yuklamalar papkasini yaratib bo‘lmadi: {e}")


def _image_kind(data: bytes):
    """Rasm turini baytlaridan aniqlaydi. Rasm bo‘lmasa None."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def save_upload(sub: str, data: bytes, max_bytes: int):
    """Rasmni diskka saqlaydi va fayl nomini qaytaradi.

    Bir xil rasm ikki marta saqlanmaydi — nom mazmun yig‘indisidan olinadi.
    Xato bo‘lsa (rasm emas yoki juda katta) — (None, sabab) qaytaradi.
    """
    if not data:
        return None, "Rasm bo‘sh"
    if len(data) > max_bytes:
        return None, "Rasm juda katta (%d KB, chegara %d KB)" % (
            len(data) // 1024, max_bytes // 1024)
    kind = _image_kind(data)
    if not kind:
        return None, "Bu rasm emas"
    name = hashlib.sha1(data).hexdigest()[:16] + "." + kind
    path = os.path.join(UPLOAD_DIR, sub, name)
    if not os.path.exists(path):
        try:
            with io.open(path, "wb") as fh:
                fh.write(data)
        except Exception as e:
            return None, "Saqlab bo‘lmadi: %s" % e
    return name, None


def drop_upload_if_unused(sub: str, name: str, column: str, table: str = "Users"):
    """Eski rasm boshqa hech kimda ishlatilmasa — o‘chiriladi."""
    if not name:
        return
    try:
        cursor.execute("SELECT COUNT(*) FROM %s WHERE %s = ?" % (table, column),
                       ("up:" + name,))
        if cursor.fetchone()[0] > 0:
            return
        path = os.path.join(UPLOAD_DIR, sub, name)
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass


@app.route("/uploads/<path:path>")
def serve_upload(path):
    """Yuklangan rasmlar. Ular loyiha papkasidan tashqarida (doimiy diskda)."""
    safe = os.path.normpath(path).replace("\\", "/").lstrip("/")
    if safe.startswith("..") or "/../" in safe:
        return ("Noto‘g‘ri yo‘l", 400)
    full = os.path.join(UPLOAD_DIR, safe)
    if not os.path.isfile(full):
        return ("Topilmadi", 404)
    return send_from_directory(UPLOAD_DIR, safe)


# Bitta bola bir kunda nechta sahifa rasmini AI'ga tekshirtira oladi.
# Chegaraga yetganda mutolaa TO‘XTAMAYDI — sahifa raqamini qo‘lda kiritish
# yo‘li ochiq qoladi, ya'ni sifat pasaymaydi, faqat ortiqcha sarf kesiladi.
PAGE_CHECK_DAILY_LIMIT = 20


def book_key(title, author):
    """Kitob nomi va muallifini solishtirish uchun yagona ko‘rinishga keltiradi.

    «Alpomish. Xalq dostoni», «alpomish - xalq dostoni» va «Alpomish.Xalq
    dostoni» — uchalasi ham bitta kalitga aylanadi.
    """
    def norm(t):
        t = (t or "").strip().lower()
        for ch in ("‘", "’", "`", "ʻ"):
            t = t.replace(ch, "'")
        t = re.sub(r"[^\w']+", " ", t, flags=re.UNICODE)
        return " ".join(t.split())

    a = norm(author)
    # Muallif noma'lum bo‘lsa — faqat kitob nomi bo‘yicha solishtiramiz
    if not a or "noma'lum" in a:
        a = ""
    return norm(title) + "|" + a


def _attach_test_from_bank(book_id, title, author):
    """Umumiy bankda shu kitobning testi bo‘lsa — AI'siz nusxalab beradi.

    Qaytaradi: savollar soni (bankda yo‘q bo‘lsa 0).
    """
    key = book_key(title, author)
    try:
        cursor.execute(
            "SELECT questions_json, book_key, from_notes FROM Test_Bank WHERE book_key = ?", (key,))
        row = cursor.fetchone()
        # Muallif noma'lum bo‘lsa, kalit "kitob nomi|" ko‘rinishida bo‘ladi —
        # bunda bankdagi ayni shu nomli kitobni muallifidan qat'i nazar topamiz.
        if not row and key.endswith("|"):
            cursor.execute(
                "SELECT questions_json, book_key, from_notes FROM Test_Bank "
                "WHERE book_key LIKE ? LIMIT 1", (key + "%",))
            row = cursor.fetchone()
    except Exception:
        return 0
    if not row or not row[0]:
        return 0
    key = row[1]
    try:
        count = len(json.loads(row[0]))
    except Exception:
        return 0
    if not count:
        return 0
    with db_lock:
        cursor.execute(
            "INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)",
            (book_id, row[0])
        )
        cursor.execute("UPDATE Test_Bank SET use_count = use_count + 1 WHERE book_key = ?", (key,))
        # Bankdagi test yozuvlardan tuzilgan bo‘lsa, bu kitobda ham faqat
        # yakuniy test sifatida chiqadi.
        if len(row) > 2 and row[2]:
            cursor.execute(
                "INSERT OR REPLACE INTO Auto_Test_State (book_id, notes_used, updated_at) "
                "VALUES (?, 0, ?)", (book_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        else:
            cursor.execute("DELETE FROM Auto_Test_State WHERE book_id = ?", (book_id,))
        conn.commit()
    return count


def _save_test_to_bank(title, author, raw_json, from_notes=0):
    """Yangi tuzilgan testni umumiy bankka qo‘shadi.

    from_notes=1 — test o‘qish davomida yig‘ilgan sahifa yozuvlaridan
    tuzilgan. Bunday test kitobning hamma joyini qamramaydi, shuning uchun
    oraliq testlarga bo‘linmaydi: faqat yakuniy test sifatida beriladi.
    Bu belgi bank orqali boshqa oilalarga ham o‘tadi.
    """
    key = book_key(title, author)
    with db_lock:
        # To‘liq (rasmlardan tuzilgan) testni yozuvlardan tuzilgani bilan
        # almashtirib yubormaymiz — sifatlisi ustun turadi.
        cursor.execute("SELECT from_notes FROM Test_Bank WHERE book_key = ?", (key,))
        row = cursor.fetchone()
        if row is not None and from_notes and not row[0]:
            return
        cursor.execute(
            "INSERT OR REPLACE INTO Test_Bank (book_key, title, author, questions_json, "
            "use_count, created_at, from_notes) VALUES (?, ?, ?, ?, 1, ?, ?)",
            (key, title, author, raw_json,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(from_notes))
        )
        conn.commit()


# ==========================================================
# TEST BOSQICHLARI — bolaning kelgan joyiga qarab
# ----------------------------------------------------------
# Ilgari uchala bosqich ham bir xil savollarni berardi: 20 tasining
# HAMMASINI. Shuning uchun 50-betda turgan bolaga 280-bet haqida savol
# tushardi. Endi savollar kitob qismlariga bo‘linadi va har bosqich
# faqat O‘QILGAN qismdan so‘raydi.
# ==========================================================
TEST_MID_COUNT = 7        # oraliq testda nechta savol
TEST_FINAL_COUNT = 10     # yakuniy testda nechta savol
STAGE_ORDER = ("mid_test_1", "mid_test_2", "final_test")


def _split_by_part(questions):
    """Savollarni kitobning uch qismiga ajratadi.

    AI yangi testlarda "part" (1/2/3) belgisini qo‘yadi. Eski testlarda
    bu belgi yo‘q — ular tartib bo‘yicha uchga bo‘linadi, chunki savollar
    odatda kitob voqealari ketma-ketligida tuziladi.
    """
    parts = {1: [], 2: [], 3: []}
    tagged = [q for q in questions if q.get("part") in (1, 2, 3, "1", "2", "3")]
    if len(tagged) >= max(3, len(questions) // 2):
        for q in questions:
            parts[int(q.get("part", 1) or 1)].append(q)
        if all(parts[i] for i in (1, 2, 3)):
            return parts
        parts = {1: [], 2: [], 3: []}
    third = max(1, len(questions) // 3)
    parts[1] = questions[:third]
    parts[2] = questions[third:third * 2]
    parts[3] = questions[third * 2:]
    return parts


def _take(pool, n, chosen):
    """Ro‘yxatdan n ta savol oladi, allaqachon tanlanganlarini o‘tkazib."""
    out = []
    for q in pool:
        if id(q) in chosen:
            continue
        out.append(q)
        chosen.add(id(q))
        if len(out) >= n:
            break
    return out


def stage_questions(questions, stage, done_stages=()):
    """Shu bosqichda beriladigan savollar.

    Tartib qat'iy: savol berishda va javobni tekshirishda AYNAN bir xil
    ro‘yxat chiqishi shart.

    `done_stages` — bola ALLAQACHON topshirgan oraliq bosqichlar. Yakuniy
    test o‘sha bosqichlarda ko‘rilgan savollarni takrorlamaydi: aks holda
    u bilimni emas, yaqinda ko‘rilgan javobning xotirasini tekshirardi.
    Oraliqlarni topshirmagan bolada esa (masalan, test faqat yakuniy
    bo‘lgan kitobda) butun bank ochiq qoladi.
    """
    parts = _split_by_part(questions)
    if stage == "mid_test_1":
        return parts[1][:TEST_MID_COUNT]
    if stage == "mid_test_2":
        return parts[2][:TEST_MID_COUNT]

    asked = set()
    if "mid_test_1" in done_stages:
        asked |= {id(q) for q in parts[1][:TEST_MID_COUNT]}
    if "mid_test_2" in done_stages:
        asked |= {id(q) for q in parts[2][:TEST_MID_COUNT]}

    fresh = {i: [q for q in parts[i] if id(q) not in asked] for i in (1, 2, 3)}
    # Yangi savollar yetarli bo‘lsa — takrorga umuman bormaymiz. Yetmasa
    # (eski, kichik banklarda) butun bankdan olamiz: savolsiz qolgandan
    # ko‘ra, bir-ikkitasi takrorlangani yaxshi.
    use = fresh if sum(len(fresh[i]) for i in (1, 2, 3)) >= 6 else parts

    chosen = set()
    picked = (_take(use[1], 3, chosen) +
              _take(use[2], 3, chosen) +
              _take(use[3], 4, chosen))
    if len(picked) < TEST_FINAL_COUNT:
        picked += _take(use[1] + use[2] + use[3],
                        TEST_FINAL_COUNT - len(picked), chosen)
    return picked[:TEST_FINAL_COUNT]


def _done_stages(book_id):
    """Bola qaysi oraliq bosqichlarni allaqachon topshirgan."""
    cursor.execute(
        "SELECT mid_test_1_done, mid_test_2_done FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    out = []
    if row and row[0]:
        out.append("mid_test_1")
    if row and row[1]:
        out.append("mid_test_2")
    return tuple(out)


def stage_gate(book_id, stage):
    """Bu bosqich hozir ochiqmi? Qaytaradi: (ochiqmi, yana necha bet kerak).

    1-oraliq — kitobning 1/3 qismi o‘qilganda,
    2-oraliq — 2/3 qismi o‘qilganda,
    yakuniy  — oxirigacha o‘qilganda ochiladi.
    Kitobning bet soni noma'lum bo‘lsa qulf ishlamaydi — hammasi ochiq.
    """
    cursor.execute("SELECT pages_read, total_pages FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row:
        return False, 0
    pages = row[0] or 0
    total = row[1] or 0
    if total <= 0:
        return True, 0
    # Yakuniy test uchun 100% talab qilinmaydi: bola oxirgi betni rasmga
    # olmasligi mumkin va test butunlay yopilib qolardi. 90% yetarli.
    need_at = {"mid_test_1": (total + 2) // 3,
               "mid_test_2": (total * 2 + 2) // 3,
               "final_test": max(1, total * 9 // 10)}.get(stage, total)
    return pages >= need_at, max(0, need_at - pages)


def save_book_base(title, author, info, source, short_form=0):
    """Kitob haqidagi ma'lumotni umumiy bazaga yozadi.

    `source`: 'photo' — ota-ona yuklagan sahifa rasmlaridan;
              'notes' — bola o‘qish davomida yuborgan sahifalardan.
    Rasmlardan olingani to‘liqroq, shuning uchun uni yozuvlardan
    olingani bilan almashtirmaymiz.
    """
    if not info or not (info.get("summary") or "").strip():
        return
    key = book_key(title, author)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with db_lock:
            cursor.execute("SELECT source FROM Book_Base WHERE book_key = ?", (key,))
            row = cursor.fetchone()
            if row is not None and source == "notes" and row[0] == "photo":
                return
            cursor.execute(
                "INSERT OR REPLACE INTO Book_Base (book_key, title, author, summary, "
                "characters, theme, conclusion, age_hint, age_band, topics, "
                "for_whom, difficulty, mood, source, short_form, "
                "use_count, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                "COALESCE((SELECT use_count FROM Book_Base WHERE book_key = ?), 0), "
                "COALESCE((SELECT created_at FROM Book_Base WHERE book_key = ?), ?), ?)",
                (key, title, author, (info.get("summary") or "").strip(),
                 (info.get("characters") or "").strip(), (info.get("theme") or "").strip(),
                 (info.get("conclusion") or "").strip(),
                 (info.get("age_hint") or "").strip(),
                 (info.get("age_band") or "").strip(),
                 json.dumps(info.get("topics") or [], ensure_ascii=False),
                 (info.get("for_whom") or "").strip(),
                 (info.get("difficulty") or "").strip(),
                 (info.get("mood") or "").strip(),
                 source, int(short_form),
                 key, key, now, now)
            )
            conn.commit()
        ai_service.log_line("[kitob_bazasi] «%s» saqlandi (%s)" % (title, source))
        # Mazmun bor — endi AI ustoz savollarini ham tayyorlab qo‘yamiz.
        prepare_talk_questions(title, author, info)
    except Exception:
        traceback.print_exc()


TALK_COINS = 5            # AI ustoz savoliga yaxshi javob uchun Bilig
TALK_STAGES = ("start", "end")


def talk_gate(book_id, stage):
    """AI ustoz savoli hozir ochiqmi. Qaytaradi: (ochiqmi, yana necha bet).

    «start» — kitobning uchdan biri o‘qilganda (1-oraliq test bilan bir vaqtda),
    «end»   — kitob oxirigacha o‘qilganda (yakuniy test bilan bir vaqtda).
    """
    return stage_gate(book_id, "mid_test_1" if stage == "start" else "final_test")


def get_talk_question(title, author, stage):
    """Tayyorlangan savolni bazadan oladi (bo‘lmasa None)."""
    key = book_key(title, author)
    try:
        cursor.execute(
            "SELECT question FROM Book_Talk_Questions WHERE book_key = ? AND stage = ?",
            (key, stage))
        row = cursor.fetchone()
    except Exception:
        return None
    return row[0] if row and row[0] else None


def save_talk_question(title, author, stage, question):
    if not question:
        return
    try:
        with db_lock:
            cursor.execute(
                "INSERT OR REPLACE INTO Book_Talk_Questions (book_key, stage, question, created_at) "
                "VALUES (?, ?, ?, ?)",
                (book_key(title, author), stage, question,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
    except Exception:
        traceback.print_exc()


def prepare_talk_questions(title, author, base):
    """Ikkala savolni oldindan tayyorlab qo‘yadi — bola bosganda kutmasin.

    Kitob bazasi to‘lgan zahoti fon rejimida chaqiriladi.
    """
    def worker():
        for stage in TALK_STAGES:
            try:
                # DIQQAT: `cursor` — butun ilovada YAGONA obyekt. Fon ipida
                # undan qulfsiz foydalanilsa, ayni paytda so‘rov bajarayotgan
                # asosiy ipning natijasi o‘chib ketadi («Recursive use of
                # cursors not allowed»). Shuning uchun O‘QISH ham qulf ostida.
                with db_lock:
                    mavjud = get_talk_question(title, author, stage)
                if mavjud:
                    continue
                q = run_async(ai_service.generate_talk_question(title, author, base, stage))
                save_talk_question(title, author, stage, q)
                ai_service.log_line("[savol] «%s» %s savoli tayyor" % (title, stage))
            except Exception:
                traceback.print_exc()

    threading.Thread(target=worker, daemon=True).start()


BASE_COLS = ("summary, characters, theme, age_hint, COALESCE(short_form, 0), "
             "COALESCE(conclusion, ''), COALESCE(age_band, ''), "
             "COALESCE(topics, ''), COALESCE(for_whom, ''), "
             "COALESCE(difficulty, ''), COALESCE(mood, '')")


def get_book_base(title, author):
    """Umumiy bazadan kitob haqidagi ma'lumotni oladi (bo‘lmasa None)."""
    key = book_key(title, author)
    try:
        cursor.execute(
            "SELECT %s FROM Book_Base WHERE book_key = ?" % BASE_COLS, (key,))
        row = cursor.fetchone()
        if not row and key.endswith("|"):
            cursor.execute(
                "SELECT %s FROM Book_Base WHERE book_key LIKE ? LIMIT 1" % BASE_COLS,
                (key + "%",))
            row = cursor.fetchone()
    except Exception:
        return None
    if not row:
        return None
    try:
        topics = json.loads(row[7]) if row[7] else []
    except Exception:
        topics = []
    return {"summary": row[0], "characters": row[1], "theme": row[2],
            "age_hint": row[3], "short_form": bool(row[4]), "conclusion": row[5],
            "age_band": row[6], "topics": topics, "for_whom": row[8],
            "difficulty": row[9], "mood": row[10]}


# ==========================================================
# «YASHIRIN» TEST TUZISH — o‘qish davomida o‘z-o‘zidan
# ----------------------------------------------------------
# Bola sahifani rasmga olganda AI uni baribir o‘qiydi. Endi biz o‘sha
# o‘qiganini saqlab boramiz. Yozuvlar yetarli bo‘lgach, test fon
# rejimida jimgina tuziladi — hech kim qo‘shimcha ish qilmaydi.
#
# NEGA ARZON: test tuzishda RASM QAYTA YUBORILMAYDI, faqat qisqa
# matnlar. Ya'ni eng qimmat qismi allaqachon to‘langan.
# ==========================================================
AUTO_TEST_MIN_NOTES = 3      # shundan kam yozuvda test tuzilmaydi
AUTO_TEST_STEP = 3           # har 3 ta yangi yozuvda test boyitiladi
AUTO_TEST_BANK_MIN = 6       # umumiy bankka faqat shundan ko‘p yozuvda qo‘shiladi


def _save_page_note(book_id, page_number, note):
    """Sahifa mazmunini saqlaydi. Bir sahifa uchun bitta yozuv."""
    if not note or page_number <= 0:
        return
    try:
        with db_lock:
            cursor.execute(
                "INSERT OR REPLACE INTO Book_Page_Notes (book_id, page_number, note, created_at) "
                "VALUES (?, ?, ?, ?)",
                (book_id, page_number, note, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
    except Exception:
        traceback.print_exc()


def _auto_test_allowed(book_id):
    """Bu kitobning testiga tegishimiz mumkinmi?

    Tegmaymiz, agar:
      - test bor, lekin uni BIZ tuzmagan bo‘lsak (ota-ona yoki umumiy bank);
      - bola allaqachon biror bosqichni topshirgan bo‘lsa — savollar
        o‘rtada almashib qolmasin.
    """
    cursor.execute("SELECT test_id FROM Book_Tests WHERE book_id = ?", (book_id,))
    has_test = cursor.fetchone() is not None
    cursor.execute("SELECT notes_used FROM Auto_Test_State WHERE book_id = ?", (book_id,))
    state = cursor.fetchone()
    if has_test and not state:
        return False, 0
    cursor.execute(
        "SELECT mid_test_1_done, mid_test_2_done, final_test_done FROM Plan_Books WHERE book_id = ?",
        (book_id,)
    )
    row = cursor.fetchone()
    if row and any(row):
        return False, 0
    return True, (state[0] if state else 0)


def _maybe_build_test_from_notes(book_id):
    """Yozuvlar yetarli bo‘lsa, fon rejimida test tuzadi. Xatolar jim yutiladi —
    bu qo‘shimcha imkoniyat, bolaning o‘qishini hech qachon to‘xtatmasligi kerak."""
    try:
        allowed, used = _auto_test_allowed(book_id)
        if not allowed:
            return
        cursor.execute(
            "SELECT page_number, note FROM Book_Page_Notes WHERE book_id = ? "
            "AND note != '' ORDER BY page_number", (book_id,)
        )
        notes = cursor.fetchall()
        if len(notes) < AUTO_TEST_MIN_NOTES:
            return
        if used and len(notes) < used + AUTO_TEST_STEP:
            return          # oldingi safardan beri yetarli yangi yozuv yig‘ilmagan

        cursor.execute("SELECT title, author, total_pages FROM Plan_Books WHERE book_id = ?",
                       (book_id,))
        row = cursor.fetchone()
        if not row:
            return
        title, author, total_pages = row[0], row[1], (row[2] or 0)

        def worker():
            try:
                questions, raw_json = run_async(
                    ai_service.generate_test_from_notes(title, author, list(notes), total_pages)
                )
                if not questions:
                    return
                with db_lock:
                    cursor.execute(
                        "INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)",
                        (book_id, raw_json)
                    )
                    cursor.execute(
                        "INSERT OR REPLACE INTO Auto_Test_State (book_id, notes_used, updated_at) "
                        "VALUES (?, ?, ?)",
                        (book_id, len(notes), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
                    conn.commit()
                # Umumiy bankka faqat yetarlicha to‘liq test tushsin — aks holda
                # boshqa oilalar ham chala testni olib qoladi.
                if len(notes) >= AUTO_TEST_BANK_MIN:
                    _save_test_to_bank(title, author, raw_json, from_notes=1)
                    # Yozuvlar yetarli — kitob mazmuni ham tuzilib, umumiy
                    # bazaga qo‘shiladi. Rasm yuborilmaydi, ya'ni arzon.
                    try:
                        info = run_async(
                            ai_service.summarize_book_from_notes(title, author, list(notes)))
                        save_book_base(title, author, info, "notes")
                    except Exception:
                        traceback.print_exc()
                ai_service.log_line("[auto_test] «%s» uchun %d ta savol tuzildi (%d ta yozuvdan)"
                                    % (title, len(questions), len(notes)))
            except Exception:
                traceback.print_exc()

        threading.Thread(target=worker, daemon=True).start()
    except Exception:
        traceback.print_exc()


def _mark_celebrated(child_id, shown, later):
    """Darrov tabriklangan nishonlarni «ko‘rilgan» deb belgilaydi.

    Bo‘lmasa bola ularni ikki marta ko‘rardi: avval natija oynasida,
    keyin yana tipratikanli kutib olish kartochkasida.

    `badges_seen` — sanoq (ro‘yxatning nechtasi ko‘rilgan). Nishonlar
    shu tartibda beriladi: [eskilar..., darrov ko‘rsatilganlar..., keyingilar...].
    Shuning uchun sanoqni «eskilar + ko‘rsatilganlar» ga surish yetarli —
    keyingilari «ko‘rilmagan» bo‘lib qoladi.

    Ilgaridan ko‘rilmagan nishon turgan bo‘lsa, sanoqqa umuman tegmaymiz:
    aks holda bola ularni umuman ko‘rmay qolardi.
    """
    if not shown:
        return
    try:
        total = len(get_badges(child_id))
        before = total - len(shown) - len(later or [])
        cursor.execute("SELECT badges_seen FROM Users WHERE user_id = ?", (child_id,))
        row = cursor.fetchone()
        seen = int(row[0]) if row and row[0] else 0
        if seen != before:
            return          # ilgaridan ko‘rilmaganlari bor — sanoqqa tegmaymiz
        with db_lock:
            cursor.execute("UPDATE Users SET badges_seen = ? WHERE user_id = ?",
                           (before + len(shown), child_id))
            conn.commit()
    except Exception:
        pass


def _final_only_book_ids():
    """Testi sahifa yozuvlaridan tuzilgan kitoblar — ularda oraliq test yo‘q."""
    try:
        cursor.execute("SELECT book_id FROM Auto_Test_State")
        return {r[0] for r in cursor.fetchall()}
    except Exception:
        return set()


def _page_checks_today(child_id):
    """Bugun shu bola uchun AI nechta rasmni tekshirgani (keshdan olinganlari sanalmaydi)."""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM Page_Check_Log WHERE child_id = ? "
            "AND substr(created_at, 1, 10) = ? AND from_cache = 0", (child_id, today))
        return cursor.fetchone()[0]
    except Exception:
        return 0


def run_async(coro):
    """ai_service.py dagi funksiyalar 'async def' bo‘lgani uchun,
    ularni oddiy (sync) Flask ichida shunday chaqiramiz."""
    return asyncio.run(coro)


# ==========================================================
# 1) TELEGRAM MINI APP FOYDALANUVCHISINI TEKSHIRISH (AUTH)
# ------------------------------------------------------------
# Telegram Mini App ochilganda telefon/brauzer "initData" degan
# imzolangan ma'lumot yuboradi. Biz shu imzoni BOT_TOKEN yordamida
# tekshirib, "bu haqiqatan shu botning foydalanuvchisimi" deb
# ishonch hosil qilamiz. Shu orqali login/parol kerak bo‘lmaydi —
# odam Telegram'da botni ochgani uchun avtomatik tanilib qoladi.
# ==========================================================

def validate_init_data(init_data: str):
    if not init_data or not BOT_TOKEN:
        return None
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calc_hash != received_hash:
            return None
        auth_date = int(parsed.get("auth_date", "0"))
        if time.time() - auth_date > 86400:  # 24 soatdan eski bo‘lsa - rad etamiz
            return None
        user = json.loads(parsed.get("user", "{}"))
        return user
    except Exception:
        return None


def require_auth(f):
    """Har bir API funksiyasi oldida ishlaydi: foydalanuvchini aniqlaydi."""
    def wrapper(*args, **kwargs):
        init_data = request.headers.get("X-Telegram-Init-Data", "")
        user = validate_init_data(init_data)

        # DEV_MODE: agar .env da DEV_MODE=1 bo‘lsa, brauzerda sinash uchun
        # tekshiruvsiz ruxsat beriladi (?dev_id=123 orqali).
        if not user and os.getenv("DEV_MODE") == "1":
            dev_id = request.args.get("dev_id") or request.headers.get("X-Dev-Id")
            if dev_id:
                user = {"id": int(dev_id), "first_name": "Test"}

        if not user:
            return jsonify({"error": "unauthorized", "message": "Telegram orqali ochilmagan"}), 401

        g.tg_user = user
        g.user_id = int(user["id"])
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


def send_telegram_message(chat_id: int, text: str):
    """Botdan foydalanuvchiga oddiy Telegram xabari yuborish (masalan,
    ota-onaga 'farzandingiz sovg‘a so‘radi' degan bildirishnoma)."""
    if not BOT_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=5
        )
    except Exception as e:
        print("Telegram xabar yuborishda xatolik:", e)


def notify_parent(child_id: int, text: str):
    """Farzandning ota-onasiga xabar yuboradi.

    HOZIR bu Telegram orqali ketadi. Kelajakda o‘z ilovamiz chiqqanda
    faqat shu funksiya ichini almashtirish kifoya — chaqiruv joylari
    o‘zgarmaydi.
    """
    try:
        parent_id = get_parent_id(child_id)
        if parent_id:
            send_telegram_message(parent_id, text)
    except Exception:
        pass


def child_name_of(child_id: int) -> str:
    try:
        cursor.execute("SELECT name FROM Users WHERE user_id = ?", (child_id,))
        row = cursor.fetchone()
        return row[0] if row and row[0] else "Farzandingiz"
    except Exception:
        return "Farzandingiz"


_BADGE_META_CACHE = None


def badge_meta():
    """webapp/badges/index.json — nishon nomi, sharti va matni."""
    global _BADGE_META_CACHE
    if _BADGE_META_CACHE is None:
        try:
            with io.open(os.path.join(WEBAPP_DIR, "badges", "index.json"),
                         encoding="utf-8") as fh:
                _BADGE_META_CACHE = json.load(fh)
        except Exception:
            _BADGE_META_CACHE = {}
    return _BADGE_META_CACHE


def badge_cond(name: str) -> str:
    for meta in badge_meta().values():
        if meta.get("name") == name:
            return meta.get("cond", "")
    return ""


def announce_badges(child_id: int, names):
    """Yangi nishonlar haqida ota-onaga xabar beradi.

    DIQQAT: ilgari bu funksiya nishonlarni «bolaga ko‘rsatilgan» deb ham
    belgilardi. Endi bunday emas — hamma nishon ham darrov ko‘rsatilmaydi.
    Ko‘rsatilganini `_mark_celebrated()` belgilaydi, qolganlari esa
    «ko‘rilmagan» bo‘lib qoladi va tipratikan ularni keyinroq yetkazadi.
    """
    if not names:
        return
    name = child_name_of(child_id)
    if len(names) == 1:
        cond = badge_cond(names[0])
        notify_parent(child_id, f"🏅 <b>{name}</b> «{names[0]}» nishonini qo‘lga kiritdi.\n"
                                f"{cond}. Bugun uni bir maqtab qo‘ying.")
    else:
        lst = "\n".join("• " + n for n in names)
        notify_parent(child_id, f"🏅 <b>{name}</b> birdaniga {len(names)} ta nishon oldi:\n{lst}")


def unseen_badges(child_id: int):
    """Bola hali tabrigini ko‘rmagan nishonlar.

    Nishon ota-ona «Bolaxona» rejimida ishlaganda yoki bot orqali
    berilgan bo‘lishi mumkin — bunda bola tabrikni ko‘rmay qoladi.
    Ilovaga kirganda tipratikan ularni yetkazadi.
    """
    have = get_badges(child_id)
    try:
        cursor.execute("SELECT badges_seen FROM Users WHERE user_id = ?", (child_id,))
        row = cursor.fetchone()
        seen = int(row[0]) if row and row[0] else 0
    except Exception:
        seen = 0
    return have[seen:] if len(have) > seen else []


def get_age_category_key(age: int) -> str:
    if age <= 5:
        return "3"
    elif age <= 7:
        return "6"
    elif age <= 11:
        return "8"
    else:
        return "12"


def has_voice_report(child_id: int, book_id: int) -> bool:
    """Shu kitob uchun bola ovozli xulosa yuborib, AI tahlil qilganmi - tekshiradi."""
    cursor.execute(
        "SELECT 1 FROM Diagnostic_Logs WHERE child_id = ? AND book_id = ? AND type = 'voice' LIMIT 1",
        (child_id, book_id)
    )
    return cursor.fetchone() is not None


# ==========================================================
# RAG‘BAT QOIDALARI (ega qarori, 2026-08-28)
# ----------------------------------------------------------
#   • Test  — har bosqich uchun natija 70% va undan yuqori bo‘lsa 3 Bilig.
#   • Ovoz  — har 15 betga bitta xulosa; yaxshi so‘zlab bersa 3 Bilig.
# Ikkalasida ham bir xil o‘lchov ishlatiladi — bola uchun qoida sodda
# va tushunarli bo‘lsin.
# ==========================================================
REWARD_PERCENT = 70       # «yaxshi» deb hisoblanadigan eng past natija
REWARD_COINS = 3          # yaxshi natija uchun beriladigan Bilig
VOICE_EVERY_PAGES = 15    # necha betga bitta ovozli xulosa


def voice_quota(book_id: int):
    """Shu kitob uchun ovozli xulosa hozir ochiqmi — shuni hisoblaydi.

    Qoida: oxirgi ovozli xulosadan beri kamida 15 bet o‘qilgan bo‘lsin.
    Birinchisi uchun — kitob boshidan 15 bet.

    Hisob «o‘qilgan betlar ÷ 15» tarzida qilinmaydi: unda 143 bet o‘qigan
    bola 9 ta huquqni birdan to‘plab, ketma-ket yuborib tanga yig‘a olardi.

    Qaytaradi: (ochiqmi, keyingisiga necha bet qolgani).
    """
    cursor.execute("SELECT pages_read, voice_last_page, total_pages "
                   "FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row:
        return False, VOICE_EVERY_PAGES
    pages = row[0] or 0
    last = row[1] or 0
    total = row[2] or 0
    need = max(0, last + VOICE_EVERY_PAGES - pages)
    # QISQA ASARLAR. Bir sahifalik hikoyada 15 bet hech qachon yig‘ilmaydi —
    # ilgari bunday kitobda ovozli xulosa umuman ochilmasdi. Endi kitob
    # oxirigacha o‘qilgan bo‘lsa, bitta xulosa beriladi. `last < total`
    # sharti buni BIR MARTA qiladi: xulosa yuborilgach, sanoq oxirgi betga
    # suriladi va qayta ochilmaydi.
    finished = total > 0 and pages >= total and last < total
    if finished:
        return True, 0
    # Kitobda 15 betdan kam qolgan bo‘lsa, «yana 15 bet o‘qi» deyish
    # noto‘g‘ri — bola oxirigacha o‘qisa bas.
    if total > 0:
        need = min(need, max(0, total - pages))
    return need == 0, need


# Daraja bosqichlari — database.py dagi calculate_and_update_rank bilan bir xil
RANK_STEPS = [(50, "Kitobxon Iztopar"), (150, "Kitobxon Qahramon"), (300, "Bilig Donishmandi")]

WEEKDAY_SHORT = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"]


def get_week_activity(child_id: int):
    """Oxirgi 7 kun: qaysi kunlari kitob o‘qilgan.

    Bosh sahifadagi haftalik chiziq uchun — bola uzluksizligini
    bir qarashda ko‘rsatadi.
    """
    today = date.today()
    first = today - timedelta(days=6)
    cursor.execute(
        "SELECT DISTINCT substr(created_at, 1, 10) FROM Reading_Logs "
        "WHERE child_id = ? AND substr(created_at, 1, 10) >= ?",
        (child_id, first.isoformat())
    )
    done = {r[0] for r in cursor.fetchall()}
    week = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        week.append({
            "label": WEEKDAY_SHORT[d.weekday()],
            "read": d.isoformat() in done,
            "today": i == 0,
        })
    return week


MONTH_NAMES = ["Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
               "Iyul", "Avgust", "Sentabr", "Oktabr", "Noyabr", "Dekabr"]


def get_reading_calendar(child_id: int, year: int = None, month: int = None):
    """Oylik mutolaa taqvimi: shu oyda qaysi kunlari o‘qilgan."""
    today = date.today()
    year = year or today.year
    month = month or today.month
    prefix = "%04d-%02d" % (year, month)
    cursor.execute(
        "SELECT DISTINCT substr(created_at, 1, 10) FROM Reading_Logs "
        "WHERE child_id = ? AND substr(created_at, 1, 7) = ?",
        (child_id, prefix)
    )
    days = sorted(r[0] for r in cursor.fetchall() if r[0])
    day_nums = sorted(int(d[8:10]) for d in days)

    # Shu oydagi eng uzun ketma-ket kunlar
    longest = run = 0
    prev = None
    for n in day_nums:
        run = run + 1 if prev is not None and n == prev + 1 else 1
        longest = max(longest, run)
        prev = n

    first = date(year, month, 1)
    nxt = date(year + (month == 12), (month % 12) + 1, 1)
    return {
        "year": year, "month": month, "month_name": MONTH_NAMES[month - 1],
        "days_in_month": (nxt - first).days,
        "first_weekday": first.weekday(),     # 0 = dushanba
        "read_days": day_nums,
        "read_count": len(day_nums),
        "longest": longest,
        "today": today.day if (today.year == year and today.month == month) else 0,
    }


def get_test_stats(child_id: int):
    """Testlar bo‘yicha umumiy natija: nechta test, nechta to‘g‘ri/xato."""
    cursor.execute(
        "SELECT COUNT(*), SUM(COALESCE(correct_count, 0)), SUM(COALESCE(total_count, 0)), "
        "AVG(factual_score) FROM Diagnostic_Logs WHERE child_id = ? AND type = 'test'",
        (child_id,)
    )
    row = cursor.fetchone() or (0, 0, 0, None)
    count = row[0] or 0
    correct = row[1] or 0
    total = row[2] or 0
    avg_pct = int(row[3]) if row[3] is not None else 0

    cursor.execute(
        "SELECT pb.title, d.factual_score FROM Diagnostic_Logs d "
        "JOIN Plan_Books pb ON d.book_id = pb.book_id "
        "WHERE d.child_id = ? AND d.type = 'test' ORDER BY d.factual_score DESC LIMIT 1",
        (child_id,)
    )
    b = cursor.fetchone()
    return {
        "count": count,
        "correct": correct,
        "total": total,
        "wrong": max(0, total - correct),
        "avg_pct": avg_pct,
        "best": {"title": b[0], "pct": int(b[1] or 0)} if b else None,
    }


# Bolaga ko‘rsatiladigan kuchli tomon — foiz emas, maqtov
STRENGTH_TEXT = {
    "factual": ("Faktik xotira", "kitobdagi tafsilotlarni juda yaxshi eslab qolasan"),
    "logic": ("Sabab-oqibat mantiqi", "voqealar nima uchun sodir bo‘lganini yaxshi tushunasan"),
    "conclusion": ("Asar xulosasi", "muallif nima demoqchi bo‘lganini teran anglaysan"),
    "fluency": ("Nutq ravonligi", "fikringni ravon va ishonchli bayon qilasan"),
    "vocabulary": ("So‘z boyligi", "go‘zal va boy so‘zlardan foydalanasan"),
}


def get_strength(child_id: int):
    """Bolaning eng kuchli ko‘nikmasi (unga maqtov sifatida ko‘rsatiladi)."""
    cursor.execute(
        "SELECT AVG(factual_score), AVG(logic_score), AVG(conclusion_score), "
        "AVG(fluency_score), AVG(vocabulary_score) FROM Diagnostic_Logs WHERE child_id = ?",
        (child_id,)
    )
    row = cursor.fetchone()
    if not row or all(v is None for v in row):
        return None
    keys = ["factual", "logic", "conclusion", "fluency", "vocabulary"]
    scores = [(k, v or 0) for k, v in zip(keys, row)]
    best = max(scores, key=lambda x: x[1])
    if best[1] <= 0:
        return None
    label, text = STRENGTH_TEXT[best[0]]
    return {"label": label, "text": text}


def get_shelf_books(child_id: int, parent_id: int = None):
    """Kitoblar javoni: rejadagi BARCHA kitoblar, tugatilganlari ham.

    Javon — bu kolleksiya: bola nima yig‘ganini ko‘rsin. Avval hozir
    o‘qilayotganlari (eng ko‘p o‘qilgani birinchi), keyin tugatilganlari.
    """
    q = ("SELECT pb.book_id, pb.title, pb.author, pb.pages_read, pb.total_pages, pb.is_completed, pb.cover_file "
         "FROM Plan_Books pb JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
         "WHERE rp.child_id = ?")
    params = [child_id]
    if parent_id:
        q += " AND rp.parent_id = ?"
        params.append(parent_id)
    q += " ORDER BY pb.is_completed ASC, pb.pages_read DESC"
    cursor.execute(q, params)
    return [
        {"id": b[0], "title": b[1], "author": b[2], "pages_read": b[3],
         "total_pages": b[4], "completed": bool(b[5]), "cover_file": b[6]}
        for b in cursor.fetchall()
    ]


def get_next_rank(total_pages: int):
    """Keyingi darajagacha qancha bet qolgani — ilhomlantirish uchun."""
    for limit, title in RANK_STEPS:
        if total_pages < limit:
            return {
                "title": title,
                "pages_left": limit - total_pages,
                "progress": min(100, int(total_pages / limit * 100)),
            }
    return None


def get_current_book(child_id: int, parent_id: int = None):
    """Bolaning hozir o‘qiyotgan (tugallanmagan, eng ko‘p sahifasi o‘qilgan) kitobini topadi."""
    q = ("SELECT pb.book_id, pb.title, pb.author, pb.pages_read, pb.total_pages, pb.cover_file FROM Plan_Books pb "
         "JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
         "WHERE rp.child_id = ? AND pb.is_completed = 0")
    params = [child_id]
    if parent_id:
        q += " AND rp.parent_id = ?"
        params.append(parent_id)
    q += " ORDER BY pb.pages_read DESC LIMIT 1"
    cursor.execute(q, params)
    row = cursor.fetchone()
    if not row:
        return None
    return {"id": row[0], "title": row[1], "author": row[2], "pages_read": row[3],
            "total_pages": row[4], "cover_file": row[5]}


def get_latest_child_note(child_id: int):
    """AI ustozning bolaning o‘ziga aytgan so‘nggi iliq xabari."""
    cursor.execute(
        "SELECT child_note FROM Diagnostic_Logs WHERE child_id = ? AND child_note IS NOT NULL "
        "AND child_note != '' ORDER BY created_at DESC LIMIT 1",
        (child_id,)
    )
    row = cursor.fetchone()
    return row[0] if row else ""


def get_latest_report(child_id: int):
    """AI Ustozning shu bola uchun so‘nggi pedagogik xulosasini (ovozli tahlildan) qaytaradi."""
    cursor.execute(
        "SELECT parent_note, convo_topic FROM Diagnostic_Logs WHERE child_id = ? "
        "ORDER BY created_at DESC LIMIT 1",
        (child_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    try:
        report = json.loads(row[0]) if row[0] else {}
    except Exception:
        report = {}
    return {
        "summary": report.get("summary", ""),
        "conversation_topic": row[1] or report.get("conversation_topic", "")
    }


# ==========================================================
# 2) PROFIL / KIRISH OQIMI  ( /start bilan bir xil vazifa)
# ==========================================================

@app.route("/api/me", methods=["GET"])
@require_auth
def api_me():
    uid = g.user_id
    cursor.execute(
        "SELECT role, name, is_approved, balance_coins, streak_days, rank_title, avatar_id, profile_done "
        "FROM Users WHERE user_id = ?",
        (uid,)
    )
    row = cursor.fetchone()

    if not row:
        # Bazada umuman yo‘q — link orqali kirmagan, yopiq beta
        return jsonify({"exists": False, "approved": False})

    role, name, approved, coins, streak, rank, avatar_id, profile_done = row
    result = {
        "exists": True,
        # Ovoz uchun qaysi formatni AVVAL sinash kerak. Server oxirgi marta
        # nima ishlaganini eslab qoladi: birinchi foydalanuvchi aniqlaydi,
        # qolganlari darrov to‘g‘ri yo‘ldan boradi. «asl» — telefon yozgan
        # fayl (ancha yengil), «wav» — o‘girilgan nusxa.
        "voice_prefer": _voice_prefer[0],
        "approved": bool(approved),
        "role": role,
        "name": name or g.tg_user.get("first_name", ""),
        "coins": coins,
        "streak": streak,
        "rank": rank,
        "avatar_id": avatar_id or "fox",
    }

    if role == "parent":
        result["parent_code"] = f"BLG-{str(uid)[-4:]}"
    elif role == "child":
        parent_id = get_parent_id(uid)
        result["linked_to_parent"] = bool(parent_id)
        result["needs_profile"] = bool(parent_id) and not bool(profile_done)

    if uid == OWNER_ID:
        result["is_admin"] = True

    return jsonify(result)


@app.route("/api/register_role", methods=["POST"])
@require_auth
def api_register_role():
    """Foydalanuvchi 'Men Ota-onaman' yoki 'Men O‘quvchiman' tugmasini bosganda."""
    data = request.get_json(force=True) or {}
    role = data.get("role")
    if role not in ("parent", "child"):
        return jsonify({"error": "role noto‘g‘ri"}), 400

    uid = g.user_id
    name = g.tg_user.get("first_name", "Foydalanuvchi")
    with db_lock:
        cursor.execute(
            "INSERT OR IGNORE INTO Users (user_id, name, is_approved) VALUES (?, ?, 1)", (uid, name)
        )
        cursor.execute("UPDATE Users SET role = ? WHERE user_id = ?", (role, uid))
        conn.commit()

    resp = {"ok": True, "role": role}
    if role == "parent":
        resp["parent_code"] = f"BLG-{str(uid)[-4:]}"
    return jsonify(resp)


@app.route("/api/link_parent", methods=["POST"])
@require_auth
def api_link_parent():
    """Bola kodni kiritganda oila bog‘lanadi.

    Ikki xil kod qabul qilinadi:
      • 8 xonali farzand kodi — ota-ona uni kabinetida yaratib qo‘ygan,
        bola o‘z telefonidan kirganda tayyor profilini o‘ziga oladi;
      • BLG-1234 — ota-ona kodi (eski yo‘l): yangi profil ochiladi.
    """
    data = request.get_json(force=True) or {}
    code = (data.get("code") or "").strip().upper()
    uid = g.user_id

    # ---- 1-yo‘l: farzandning shaxsiy 8 xonali kodi ----
    digits = "".join(ch for ch in code if ch.isdigit())
    if len(digits) == 8 and not code.startswith("BLG-"):
        cursor.execute("SELECT user_id FROM Users WHERE child_code = ?", (digits,))
        found = cursor.fetchone()
        if not found:
            return jsonify({"error": "Bunday kodli farzand topilmadi"}), 404
        local_id = found[0]
        if local_id > 0:
            return jsonify({"error": "Bu koddan allaqachon foydalanilgan"}), 400

        cursor.execute("SELECT 1 FROM Family_Link WHERE child_id = ?", (uid,))
        if cursor.fetchone():
            return jsonify({"error": "Siz allaqachon ota-onaga ulangansiz"}), 400

        cursor.execute("SELECT parent_id FROM Family_Link WHERE child_id = ?", (local_id,))
        prow = cursor.fetchone()
        _bind_child_to_telegram(local_id, uid)

        cursor.execute("SELECT name FROM Users WHERE user_id = ?", (uid,))
        nrow = cursor.fetchone()
        if prow:
            send_telegram_message(
                prow[0],
                f"✅ Farzandingiz ({nrow[0] if nrow else ''}) o‘z telefonidan ulandi!"
            )
        return jsonify({"ok": True, "profile_ready": True})

    # ---- 2-yo‘l: ota-ona kodi ----
    if not code.startswith("BLG-"):
        return jsonify({"error": "Kodni tekshiring: 8 xonali farzand kodi yoki BLG-1234"}), 400

    suffix = code.replace("BLG-", "")
    cursor.execute(
        "SELECT user_id FROM Users WHERE role = 'parent' AND CAST(user_id AS TEXT) LIKE ?",
        ("%" + suffix,)
    )
    parent = cursor.fetchone()
    if not parent:
        return jsonify({"error": "Bunday kodli ota-ona topilmadi"}), 404

    try:
        with db_lock:
            cursor.execute(
                "INSERT INTO Family_Link (parent_id, child_id) VALUES (?, ?)", (parent[0], uid)
            )
            conn.commit()
    except Exception:
        return jsonify({"error": "Siz allaqachon shu ota-onaga ulangansiz"}), 400

    cursor.execute("SELECT name FROM Users WHERE user_id = ?", (uid,))
    child_name = cursor.fetchone()[0]
    send_telegram_message(
        parent[0],
        f"✅ Farzandingiz ({child_name}) Mini App orqali profilingizga ulandi!"
    )
    return jsonify({"ok": True})


@app.route("/api/child/profile", methods=["POST"])
@require_auth
def api_child_profile():
    """Bola (yoki ota-ona) ro‘yxatdan o‘tishda: avatar, ism va yoshni saqlaydi."""
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    age = data.get("age")
    avatar_id = data.get("avatar_id") or "fox"
    if avatar_id not in AVATAR_IDS:
        avatar_id = "fox"
    if not name:
        return jsonify({"error": "Ism kiritilishi shart"}), 400
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = None
    if not age or age < 3 or age > 17:
        return jsonify({"error": "Yoshni to‘g‘ri kiriting (3-17)"}), 400

    uid = g.user_id
    with db_lock:
        cursor.execute(
            "UPDATE Users SET name = ?, avatar_id = ?, profile_done = 1 WHERE user_id = ?",
            (name, avatar_id, uid)
        )
        parent_id = get_parent_id(uid)
        if parent_id:
            cursor.execute(
                "UPDATE Family_Link SET child_age = ? WHERE parent_id = ? AND child_id = ?",
                (age, parent_id, uid)
            )
        conn.commit()
    return jsonify({"ok": True})


# ==========================================================
# 3) OTA-ONA BO‘LIMI
# ==========================================================

@app.route("/api/parent/home/<int(signed=True):child_id>", methods=["GET"])
@require_auth
def parent_home(child_id):
    """Bosh sahifa (ota-ona) — tanlangan farzand bo‘yicha to‘liq holat: faoliyat, kitoblar, natijalar."""
    cursor.execute(
        "SELECT name, balance_coins, streak_days, badges FROM Users WHERE user_id = ?", (child_id,)
    )
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Farzand topilmadi"}), 404
    name, coins, streak, badges = row
    rank, total_pages = calculate_and_update_rank(child_id)
    last_badge = (badges or "").split(",")[-1].strip() if badges else None

    cursor.execute(
        "SELECT COUNT(*) FROM Plan_Books pb JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
        "WHERE rp.parent_id = ? AND rp.child_id = ? AND pb.is_completed = 1",
        (g.user_id, child_id)
    )
    completed_books = cursor.fetchone()[0]

    cursor.execute(
        "SELECT pb.book_id, pb.title, pb.author, pb.pages_read, pb.total_pages, pb.cover_file FROM Plan_Books pb "
        "JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
        "WHERE rp.parent_id = ? AND rp.child_id = ? AND pb.is_completed = 0 ORDER BY pb.pages_read DESC",
        (g.user_id, child_id)
    )
    active_books = [
        {"id": b[0], "title": b[1], "author": b[2], "pages_read": b[3],
         "total_pages": b[4], "cover_file": b[5]}
        for b in cursor.fetchall()
    ]

    cursor.execute(
        "SELECT pb.title, rl.pages_added, rl.created_at FROM Reading_Logs rl "
        "JOIN Plan_Books pb ON rl.book_id = pb.book_id "
        "WHERE rl.child_id = ? ORDER BY rl.created_at DESC LIMIT 6",
        (child_id,)
    )
    recent_activity = [
        {"title": a[0], "pages_added": a[1], "created_at": a[2]}
        for a in cursor.fetchall()
    ]

    current_book = get_current_book(child_id, parent_id=g.user_id)
    # Joriy kitob bo‘yicha nechta test ishlangani va nechta audio yuborilgani
    if current_book:
        cursor.execute(
            "SELECT mid_test_1_done, mid_test_2_done, final_test_done, audio_count "
            "FROM Plan_Books WHERE book_id = ?", (current_book["id"],)
        )
        r = cursor.fetchone()
        if r:
            current_book["tests_done"] = int(r[0] or 0) + int(r[1] or 0) + int(r[2] or 0)
            current_book["audio_count"] = int(r[3] or 0)

    # Oxirgi ovozli xulosa uchun AI bergan Bilig bahosi
    cursor.execute(
        "SELECT bonus_bilig FROM Diagnostic_Logs WHERE child_id = ? AND type = 'voice' "
        "ORDER BY created_at DESC LIMIT 1", (child_id,)
    )
    r = cursor.fetchone()
    last_audio_score = int(r[0]) if r and r[0] else None

    last_report = get_latest_report(child_id)
    return jsonify({
        "name": name, "coins": coins, "streak": streak, "rank": rank,
        "total_pages": total_pages, "completed_books": completed_books,
        "current_book": current_book, "active_books": active_books,
        "recent_activity": recent_activity, "last_report": last_report,
        "last_badge": last_badge, "last_audio_score": last_audio_score,
        "week": get_week_activity(child_id), "next_rank": get_next_rank(total_pages),
        "badges": badges or "", "shelf_books": get_shelf_books(child_id, g.user_id)
    })


def _new_child_code():
    """Farzand uchun 8 xonali, takrorlanmas ulanish kodi."""
    import random
    for _ in range(50):
        code = "".join(random.choice("0123456789") for _ in range(8))
        cursor.execute("SELECT 1 FROM Users WHERE child_code = ?", (code,))
        if not cursor.fetchone():
            return code
    return None


def _new_local_child_id():
    """Ota-ona yaratgan farzand uchun ichki raqam.

    Telegram raqamlari doim musbat bo‘lgani uchun manfiy raqam tanlanadi —
    shunda hech qachon to‘qnashuv bo‘lmaydi. Farzand keyin o‘z telefonidan
    ulanganda bu raqam uning haqiqiy Telegram raqamiga almashtiriladi.
    """
    cursor.execute("SELECT MIN(user_id) FROM Users")
    row = cursor.fetchone()
    lowest = row[0] if row and row[0] is not None else 0
    return min(-1, lowest - 1)


def _bind_child_to_telegram(local_id, telegram_id):
    """Ota-ona yaratgan farzand profilini haqiqiy Telegram hisobiga bog‘lash.

    Farzandning barcha yozuvlari (kitoblar, o‘qish tarixi, testlar, Bilig)
    saqlanib qoladi — faqat raqami almashadi.
    """
    cursor.execute("SELECT is_approved FROM Users WHERE user_id = ?", (telegram_id,))
    row = cursor.fetchone()
    approved = row[0] if row else 1
    with db_lock:
        # Telegram foydalanuvchisining bo‘sh yozuvi o‘rnini profil egallaydi
        cursor.execute("DELETE FROM Users WHERE user_id = ?", (telegram_id,))
        cursor.execute(
            "UPDATE Users SET user_id = ?, is_approved = ?, role = 'child', profile_done = 1 "
            "WHERE user_id = ?",
            (telegram_id, approved, local_id)
        )
        for table in ("Family_Link", "Reading_Plans", "Reading_Logs", "Diagnostic_Logs"):
            cursor.execute(
                "UPDATE %s SET child_id = ? WHERE child_id = ?" % table,
                (telegram_id, local_id)
            )
        conn.commit()


@app.route("/api/admin/demo", methods=["POST"])
@require_auth
def admin_demo():
    """Namoyish ma'lumoti — faqat loyiha egasi uchun.

    Tanlangan farzand profilini investorlarga ko‘rsatish uchun to‘liq,
    haqiqiyga o‘xshash natijalar bilan to‘ldiradi yoki tozalaydi.
    """
    if g.user_id != OWNER_ID:
        return jsonify({"error": "Ruxsat yo‘q"}), 403

    data = request.get_json(force=True) or {}
    child_id = data.get("child_id")
    action = data.get("action") or "fill"
    if not child_id:
        return jsonify({"error": "child_id kerak"}), 400

    cursor.execute(
        "SELECT 1 FROM Family_Link WHERE parent_id = ? AND child_id = ?", (g.user_id, child_id)
    )
    if not cursor.fetchone():
        return jsonify({"error": "Bu farzand sizga tegishli emas"}), 403

    import demo_data
    with db_lock:
        if action == "clear":
            demo_data.clear_demo_child(int(child_id))
            return jsonify({"ok": True, "cleared": True})
        result = demo_data.fill_demo_child(g.user_id, int(child_id))
    return jsonify({"ok": True, **result})


@app.route("/api/parent/children", methods=["POST"])
@require_auth
def parent_add_child():
    """Ota-ona farzandni to‘liq o‘zi qo‘shadi (ism, yosh, avatar).

    Uyda bitta telefon bo‘lishi mumkin — shuning uchun farzandning alohida
    Telegram hisobi bo‘lishi shart emas. Unga 8 xonali kod beriladi:
    keyinchalik o‘z telefonidan kirmoqchi bo‘lsa, shu kodni kiritadi.
    """
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    avatar_id = data.get("avatar_id") or "fox"
    if avatar_id not in AVATAR_IDS:
        avatar_id = "fox"
    if not name:
        return jsonify({"error": "Ism kiritilishi shart"}), 400
    try:
        age = int(data.get("age"))
    except (TypeError, ValueError):
        age = 0
    if age < 3 or age > 17:
        return jsonify({"error": "Yoshni to‘g‘ri kiriting (3-17)"}), 400

    code = _new_child_code()
    if not code:
        return jsonify({"error": "Kod yaratib bo‘lmadi, qaytadan urinib ko‘ring"}), 500

    with db_lock:
        child_id = _new_local_child_id()
        cursor.execute(
            "INSERT INTO Users (user_id, role, name, is_approved, avatar_id, profile_done, child_code) "
            "VALUES (?, 'child', ?, 1, ?, 1, ?)",
            (child_id, name, avatar_id, code)
        )
        cursor.execute(
            "INSERT INTO Family_Link (parent_id, child_id, child_age) VALUES (?, ?, ?)",
            (g.user_id, child_id, age)
        )
        conn.commit()

    return jsonify({"ok": True, "id": child_id, "name": name, "age": age,
                    "avatar_id": avatar_id, "child_code": code, "linked": False})


@app.route("/api/parent/children", methods=["GET"])
@require_auth
def parent_children():
    cursor.execute(
        "SELECT fl.child_id, u.name, fl.child_age, u.avatar_id, u.child_code FROM Family_Link fl "
        "JOIN Users u ON fl.child_id = u.user_id WHERE fl.parent_id = ? "
        "ORDER BY fl.rowid",   # qo‘shilgan tartibda — har safar joyi almashmasin
        (g.user_id,)
    )
    rows = cursor.fetchall()
    # linked=True — farzand o‘z telefonidan ham kirgan (raqami musbat Telegram raqami)
    return jsonify([{"id": r[0], "name": r[1], "age": r[2] or 10, "avatar_id": r[3] or "fox",
                     "child_code": r[4] or "", "linked": r[0] > 0} for r in rows])


@app.route("/api/parent/children/<int(signed=True):child_id>/age", methods=["POST"])
@require_auth
def parent_set_child_age(child_id):
    data = request.get_json(force=True) or {}
    age = int(data.get("age", 10))
    with db_lock:
        cursor.execute(
            "UPDATE Family_Link SET child_age = ? WHERE child_id = ? AND parent_id = ?",
            (age, child_id, g.user_id)
        )
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/parent/children/<int(signed=True):child_id>/profile", methods=["POST"])
@require_auth
def parent_edit_child_profile(child_id):
    """Ota-ona farzandning ismi, yoshi va avatarini o‘zi tahrirlashi (Bolaxona bo‘limidan)."""
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    age = data.get("age")
    avatar_id = data.get("avatar_id")
    if avatar_id and avatar_id not in AVATAR_IDS:
        avatar_id = None
    with db_lock:
        if name:
            cursor.execute("UPDATE Users SET name = ? WHERE user_id = ?", (name, child_id))
        if avatar_id:
            cursor.execute("UPDATE Users SET avatar_id = ?, profile_done = 1 WHERE user_id = ?", (avatar_id, child_id))
        if age:
            cursor.execute(
                "UPDATE Family_Link SET child_age = ? WHERE child_id = ? AND parent_id = ?",
                (int(age), child_id, g.user_id)
            )
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/parent/recommended_books", methods=["GET"])
@require_auth
def parent_recommended_books():
    age = int(request.args.get("age", 10))
    key = get_age_category_key(age)
    return jsonify(RECOMMENDED_BOOKS.get(key, []))


@app.route("/api/parent/catalog", methods=["GET"])
@require_auth
def parent_catalog():
    """Kitoblar katalogi — nomi va muallifi alohida ajratilgan holda.

    Ota-ona kitobni shu ro‘yxatdan tanlaydi: nom, muallif va muqova tayyor,
    ya'ni AI umuman chaqirilmaydi. Ro‘yxat kichik bo‘lgani uchun bir marta
    to‘liq beriladi, qidiruv va yosh bo‘yicha saralash ilovaning o‘zida bo‘ladi.
    """
    books = []
    for age_key, titles in RECOMMENDED_BOOKS.items():
        for raw in titles:
            text = (raw or "").strip().rstrip(".")
            if not text:
                continue
            if "." in text:
                title, author = text.split(".", 1)
            else:
                title, author = text, ""
            books.append({
                "title": title.strip(),
                "author": author.strip(),
                "age": age_key,
            })
    return jsonify(books)


@app.route("/api/parent/plans", methods=["GET"])
@require_auth
def parent_plans():
    child_id = request.args.get("child_id", type=int)
    q = ("SELECT plan_id, name, prize, status, child_id, COALESCE(plan_type, 'quick') "
         "FROM Reading_Plans WHERE parent_id = ?")
    params = [g.user_id]
    if child_id:
        q += " AND child_id = ?"
        params.append(child_id)
    # DIQQAT: bu yordamchi ham shu cursor'dan foydalanadi, shuning uchun
    # asosiy so‘rovdan OLDIN chaqiriladi — aks holda natija o‘chib ketadi.
    _final_only = _final_only_book_ids()
    cursor.execute(q, params)
    plans = []
    for plan_id, name, prize, status, cid, plan_type in cursor.fetchall():
        cursor.execute(
            "SELECT book_id, title, author, pages_read, total_pages, is_completed, "
            "mid_test_1_done, mid_test_2_done, final_test_done, cover_file "
            "FROM Plan_Books WHERE plan_id = ?",
            (plan_id,)
        )
        books = [
            {"id": b[0], "title": b[1], "author": b[2], "pages_read": b[3],
             "total_pages": b[4], "completed": bool(b[5]),
             "test_final_only": b[0] in _final_only,
             "mid_test_1_done": bool(b[6]),
             "mid_test_2_done": bool(b[7]), "final_test_done": bool(b[8]),
             "cover_file": b[9], "has_voice": has_voice_report(cid, b[0])}
            for b in cursor.fetchall()
        ]
        plans.append({
            "id": plan_id, "name": name, "prize": prize, "status": status,
            "child_id": cid, "type": plan_type, "books": books
        })
    return jsonify(plans)


@app.route("/api/parent/plans", methods=["POST"])
@require_auth
def parent_create_plan():
    """Yangi mutolaa rejasi (Tezkor mutolaa yoki Marafon) yaratish."""
    data = request.get_json(force=True) or {}
    child_id = data.get("child_id")
    name = data.get("name") or "Mutolaa rejasi"
    prize = data.get("prize") or ""
    plan_type = "marathon" if data.get("type") == "marathon" else "quick"
    if not child_id:
        return jsonify({"error": "child_id kerak"}), 400

    with db_lock:
        cursor.execute(
            "INSERT INTO Reading_Plans (parent_id, child_id, name, prize, status, plan_type) "
            "VALUES (?, ?, ?, ?, 'active', ?)",
            (g.user_id, child_id, name, prize, plan_type)
        )
        conn.commit()
        plan_id = cursor.lastrowid
    return jsonify({"ok": True, "plan_id": plan_id})


@app.route("/api/parent/plans/<int:plan_id>/books", methods=["POST"])
@require_auth
def parent_add_book_text(plan_id):
    """Kitobni matn shaklida qo‘shish — AI nomi/muallifini avtomatik tozalaydi."""
    data = request.get_json(force=True) or {}
    raw_text = (data.get("text") or "").strip()
    total_pages = int(data.get("total_pages") or 0)

    # Katalogdan, tavsiyalardan yoki muqova tasdig‘idan kelgan kitobda nom va
    # muallif allaqachon aniq — bunda AI umuman chaqirilmaydi (tez va tekin).
    exact_title = (data.get("title") or "").strip()
    exact_author = (data.get("author") or "").strip()
    if exact_title:
        title = exact_title
        author = exact_author or "Noma'lum muallif"
    else:
        if not raw_text:
            return jsonify({"error": "Kitob nomini kiriting"}), 400
        title, author = run_async(ai_service.normalize_book_input(raw_text))

    with db_lock:
        cursor.execute(
            "INSERT INTO Plan_Books (plan_id, title, author, total_pages) VALUES (?, ?, ?, ?)",
            (plan_id, title, author, total_pages)
        )
        conn.commit()
        book_id = cursor.lastrowid
    test_count = _attach_test_from_bank(book_id, title, author)
    return jsonify({"ok": True, "book_id": book_id, "title": title, "author": author,
                    "test_ready": bool(test_count)})


@app.route("/api/parent/cover_read", methods=["POST"])
@require_auth
def parent_cover_read():
    """Muqova rasmidan nom va muallifni o‘qiydi, LEKIN bazaga yozmaydi.

    Rangba-rang muqovalarda AI adashishi mumkin, shuning uchun natija avval
    ota-onaga tasdiqlash uchun ko‘rsatiladi — u yerda tuzatib, keyin saqlanadi.
    """
    if "photo" not in request.files:
        return jsonify({"error": "Rasm topilmadi"}), 400
    image_bytes = request.files["photo"].read()
    title, author = run_async(ai_service.analyze_book_cover(image_bytes))
    return jsonify({"title": title, "author": author})


@app.route("/api/parent/plans/<int:plan_id>/books/photo", methods=["POST"])
@require_auth
def parent_add_book_photo(plan_id):
    """Kitob muqovasini rasmga olib yuborish — AI Vision nomi/muallifini o‘qiydi."""
    if "photo" not in request.files:
        return jsonify({"error": "Rasm topilmadi"}), 400
    image_bytes = request.files["photo"].read()
    title, author = run_async(ai_service.analyze_book_cover(image_bytes))

    with db_lock:
        cursor.execute(
            "INSERT INTO Plan_Books (plan_id, title, author) VALUES (?, ?, ?)",
            (plan_id, title, author)
        )
        conn.commit()
        book_id = cursor.lastrowid
    test_count = _attach_test_from_bank(book_id, title, author)
    return jsonify({"ok": True, "book_id": book_id, "title": title, "author": author,
                    "test_ready": bool(test_count)})


@app.route("/api/parent/books/<int:book_id>", methods=["DELETE"])
@require_auth
def parent_delete_book(book_id):
    with db_lock:
        cursor.execute("DELETE FROM Book_Tests WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM Plan_Books WHERE book_id = ?", (book_id,))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/parent/books/<int:book_id>/generate_test", methods=["POST"])
@require_auth
def parent_generate_test(book_id):
    """5-10 ta sahifa surati asosida AI Savollar banki (test) tuzish.

    AVVAL umumiy bank tekshiriladi: bu kitobga test allaqachon tuzilgan
    bo‘lsa, AI umuman chaqirilmaydi va test bir zumda beriladi.
    """
    cursor.execute("SELECT title, author FROM Plan_Books WHERE book_id = ?", (book_id,))
    _row = cursor.fetchone()
    title = _row[0] if _row else ""
    author = _row[1] if _row else ""

    count = _attach_test_from_bank(book_id, title, author)
    if count:
        return jsonify({"ok": True, "count": count, "from_bank": True})

    files = request.files.getlist("photos")
    if not files:
        return jsonify({"error": "Kamida 1 ta sahifa rasmi kerak"}), 400
    photos_bytes = [f.read() for f in files]

    # AI 5-10 ta sahifani o‘qib, 15-20 ta savol tuzishi 1-2 DAQIQA davom etadi.
    # Ilgari telefon shuncha vaqt javob kutib turardi va aloqa uzilib,
    # foydalanuvchi «Testni tuzib bo‘lmadi» degan tushunarsiz xabarni ko‘rardi.
    # Endi ish fon rejimida bajariladi: telefon darrov «kvitansiya» oladi va
    # vaqti-vaqti bilan «tayyor bo‘ldimi?» deb so‘rab turadi.
    job_id = _start_test_job(book_id, title, author, photos_bytes)
    return jsonify({"ok": True, "job_id": job_id, "from_bank": False})


# ==========================================================
# TEST TUZISH — FON REJIMIDAGI ISH
# ----------------------------------------------------------
# Har bir ish uchun bitta yozuv: holati, natijasi yoki xatosi.
# Xotirada saqlanadi — server qayta ishga tushsa yo‘qoladi, bu normal:
# foydalanuvchi shunchaki qaytadan urinadi.
# ==========================================================
_test_jobs = {}
_test_jobs_lock = threading.Lock()
TEST_JOB_TTL = 1800          # yarim soatdan keyin eski yozuvlar tozalanadi


def _set_test_job(job_id, **fields):
    with _test_jobs_lock:
        job = _test_jobs.setdefault(job_id, {})
        job.update(fields)
        job["at"] = time.time()


def _start_test_job(book_id, title, author, photos_bytes):
    job_id = uuid.uuid4().hex[:12]
    _set_test_job(job_id, status="ishlanmoqda", book_id=book_id, count=0, error=None)

    def worker():
        try:
            questions, raw_json, book_info = run_async(
                ai_service.generate_test_bank_from_photos(photos_bytes)
            )
            if not questions:
                raise ValueError("AI birorta ham savol tuza olmadi")
            with db_lock:
                cursor.execute(
                    "INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)",
                    (book_id, raw_json)
                )
                # Ota-ona rasmlardan tuzgan test TO‘LIQ hisoblanadi — u oraliq
                # testlarga ham bo‘linadi. Shuning uchun «faqat yakuniy»
                # belgisini olib tashlaymiz.
                cursor.execute("DELETE FROM Auto_Test_State WHERE book_id = ?", (book_id,))
                conn.commit()
            _save_test_to_bank(title, author, raw_json)
            # AI bu rasmlarni baribir o‘qidi — kitob haqida bilganini
            # umumiy bazaga qo‘shib qo‘yamiz.
            save_book_base(title, author, book_info, "photo")
            _set_test_job(job_id, status="tayyor", count=len(questions))
        except Exception as e:
            # Xatoni YASHIRMAYMIZ: jurnalga to‘liq yozamiz va qisqartirilgan
            # holini foydalanuvchiga ham ko‘rsatamiz. Aks holda nima
            # bo‘lganini na ega, na biz bilamiz.
            traceback.print_exc()
            ai_service.log_line("[test_job] XATO kitob=%s: %r" % (book_id, e))
            _set_test_job(job_id, status="xato", error=ai_service.human_error(e))

    threading.Thread(target=worker, daemon=True).start()
    return job_id


@app.route("/api/parent/test_job/<job_id>", methods=["GET"])
@require_auth
def parent_test_job(job_id):
    """Telefon shu manzilga «tayyor bo‘ldimi?» deb so‘rab turadi."""
    now = time.time()
    with _test_jobs_lock:
        for k in [k for k, v in _test_jobs.items() if now - v.get("at", 0) > TEST_JOB_TTL]:
            _test_jobs.pop(k, None)
        job = _test_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Bu ish topilmadi — qaytadan urinib ko‘ring"}), 404
    return jsonify({"status": job["status"], "count": job.get("count", 0),
                    "error": job.get("error")})


@app.route("/api/parent/results/<int(signed=True):child_id>", methods=["GET"])
@require_auth
def parent_child_results(child_id):
    """'📊 Farzandim natijalari' — bitta farzand bo‘yicha to‘liq hisobot."""
    rank, total_pages = calculate_and_update_rank(child_id)
    cursor.execute(
        "SELECT name, balance_coins, badges, streak_days FROM Users WHERE user_id = ?", (child_id,)
    )
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Farzand topilmadi"}), 404
    name, coins, badges, streak = row

    cursor.execute(
        "SELECT pb.title, pb.pages_read, pb.total_pages, pb.is_completed FROM Plan_Books pb "
        "JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id WHERE rp.parent_id = ? AND rp.child_id = ?",
        (g.user_id, child_id)
    )
    books = [
        {"title": b[0], "pages_read": b[1], "total_pages": b[2], "completed": bool(b[3])}
        for b in cursor.fetchall()
    ]

    return jsonify({
        "name": name, "rank": rank, "coins": coins, "streak": streak,
        "badges": badges or "Hali nishonlar yo‘q", "total_pages": total_pages,
        "books": books
    })


def _enrich_passport(child_id, data):
    """Shaxsiy natija sahifasi uchun qo‘shimcha ma'lumot."""
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    data["calendar"] = get_reading_calendar(child_id, year, month)
    data["books"] = get_shelf_books(child_id)
    data["tests"] = get_test_stats(child_id)
    data["strength"] = get_strength(child_id)
    data["next_rank"] = get_next_rank(data.get("total_pages", 0))
    return data


@app.route("/api/parent/passport/<int(signed=True):child_id>", methods=["GET"])
@require_auth
def parent_child_passport(child_id):
    """'Oylik Kitobxon Pasporti' — kognitiv/nutqiy diagnostika."""
    data = get_child_passport_data(child_id)
    if not data:
        return jsonify({"error": "Farzand topilmadi"}), 404
    return jsonify(_enrich_passport(child_id, data))


@app.route("/api/parent/coins/<int(signed=True):child_id>", methods=["POST"])
@require_auth
def parent_manage_coins(child_id):
    """Ota-ona farzandiga qo‘lda Bilig (tanga) qo‘shishi/ayirishi."""
    data = request.get_json(force=True) or {}
    delta = int(data.get("delta", 0))
    with db_lock:
        cursor.execute(
            "UPDATE Users SET balance_coins = MAX(0, balance_coins + ?) WHERE user_id = ?",
            (delta, child_id)
        )
        conn.commit()
        cursor.execute("SELECT balance_coins FROM Users WHERE user_id = ?", (child_id,))
        new_balance = cursor.fetchone()[0]
    send_telegram_message(child_id, f"🔅 Ota-onangiz balansingizga o‘zgartirish kiritdi. Joriy balans: {new_balance}")
    return jsonify({"ok": True, "balance": new_balance})


# ---------------- OTA-ONA: SOVG‘ALAR DO‘KONI ----------------

@app.route("/api/parent/store", methods=["GET"])
@require_auth
def parent_store_list():
    cursor.execute("SELECT item_id, name, price FROM Store_Items WHERE parent_id = ?", (g.user_id,))
    return jsonify([{"id": r[0], "name": r[1], "price": r[2]} for r in cursor.fetchall()])


@app.route("/api/parent/store", methods=["POST"])
@require_auth
def parent_store_add():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    price = int(data.get("price") or 0)
    if not name or price <= 0:
        return jsonify({"error": "Nomi va narxini to‘g‘ri kiriting"}), 400
    with db_lock:
        cursor.execute(
            "INSERT INTO Store_Items (parent_id, name, price) VALUES (?, ?, ?)", (g.user_id, name, price)
        )
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/parent/store/<int:item_id>", methods=["DELETE"])
@require_auth
def parent_store_delete(item_id):
    with db_lock:
        cursor.execute("DELETE FROM Store_Items WHERE item_id = ? AND parent_id = ?", (item_id, g.user_id))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/parent/rate", methods=["POST"])
@require_auth
def parent_set_rate():
    """Bilig tangasining pul kursini belgilash (masalan 1 Bilig = 500 so‘m)."""
    data = request.get_json(force=True) or {}
    rate = int(data.get("rate", 0))
    with db_lock:
        cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, g.user_id))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/parent/contact", methods=["POST"])
@require_auth
def parent_contact():
    """'📞 Qayta aloqa' — ota-ona loyiha egasiga (admin) xabar yozadi."""
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Xabar bo‘sh bo‘lmasin"}), 400
    if OWNER_ID:
        cursor.execute("SELECT name FROM Users WHERE user_id = ?", (g.user_id,))
        row = cursor.fetchone()
        sender_name = row[0] if row else "Foydalanuvchi"
        send_telegram_message(
            OWNER_ID,
            f"📞 <b>Yangi murojaat (Mini App)</b>\n👤 {sender_name} (ID: <code>{g.user_id}</code>)\n\n{text}"
        )
    return jsonify({"ok": True})


# ==========================================================
# 4) BOLA (O‘QUVCHI) BO‘LIMI
# ==========================================================

def _resolve_active_child(request):
    """Bolaxona rejimida ota-ona ekranidan kirilgan bo‘lsa, aktiv bolani aniqlaydi.
    Mini App'da buni frontend ?as_child=ID query parametri orqali beradi.

    XAVFSIZLIK: ilgari bu yerda hech qanday tekshiruv yo‘q edi — istalgan
    foydalanuvchi ?as_child=<boshqa bolaning raqami> deb yozib, begona
    oilaning bolasini KO‘RA va uning natijalarini O‘ZGARTIRA olardi.
    Endi faqat o‘z farzandiga ruxsat beriladi.
    """
    as_child = request.args.get("as_child", type=int)
    if not as_child or as_child == g.user_id:
        return g.user_id
    try:
        cursor.execute(
            "SELECT 1 FROM Family_Link WHERE parent_id = ? AND child_id = ?",
            (g.user_id, as_child)
        )
        if cursor.fetchone():
            return as_child
    except Exception:
        pass
    # Ruxsat yo‘q — hech narsa ko‘rsatmaymiz, o‘z hisobiga qaytariladi.
    ai_service.log_line("[xavfsizlik] %s begona bola %s ga tegmoqchi bo‘ldi"
                        % (g.user_id, as_child))
    return g.user_id


class NeedChildMode(Exception):
    """Ota-ona farzand nomidan ish qilmoqchi, lekin Bolaxonaga kirmagan."""


@app.errorhandler(NeedChildMode)
def _need_child_mode(_e):
    return jsonify({"error": "Buni farzandingiz nomidan bajarish uchun avval "
                             "Bolaxonaga kiring."}), 403


def _require_child_actor(request):
    """Bola nomidan bajariladigan amallar uchun aktiv bolani aniqlaydi.

    Ega qarori (2026-08-28): ota-ona bunday amalni faqat **Bolaxonaga
    kirgan holda** bajara oladi. Ilgari Bolaxonasiz ham o‘tib ketardi va
    natija (bet, Bilig, test) ota-onaning O‘Z hisobiga yozilardi.
    """
    child_id = _resolve_active_child(request)
    if child_id == g.user_id:
        cursor.execute("SELECT role FROM Users WHERE user_id = ?", (g.user_id,))
        row = cursor.fetchone()
        if row and row[0] == "parent":
            raise NeedChildMode()
    return child_id


@app.route("/api/child/home", methods=["GET"])
@require_auth
def child_home():
    """🏠 Bosh sahifa (bola) — o‘zining qisqacha holati."""
    child_id = _resolve_active_child(request)
    cursor.execute(
        "SELECT name, balance_coins, streak_days, rank_title, badges FROM Users WHERE user_id = ?", (child_id,)
    )
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Topilmadi"}), 404
    name, coins, streak, rank, badges = row
    current_book = get_current_book(child_id)
    last_badge = (badges or "").split(",")[-1].strip() if badges else None
    rank, total_pages = calculate_and_update_rank(child_id)

    # Joriy kitob bo‘yicha test va audio soni
    if current_book:
        cursor.execute(
            "SELECT mid_test_1_done, mid_test_2_done, final_test_done, audio_count "
            "FROM Plan_Books WHERE book_id = ?", (current_book["id"],)
        )
        r = cursor.fetchone()
        if r:
            current_book["tests_done"] = int(r[0] or 0) + int(r[1] or 0) + int(r[2] or 0)
            current_book["audio_count"] = int(r[3] or 0)

    # Rejadagi kitoblar (bosh sahifada 3 tasi ko‘rsatiladi)
    cursor.execute(
        "SELECT pb.book_id, pb.title, pb.author, pb.pages_read, pb.total_pages, pb.cover_file FROM Plan_Books pb "
        "JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
        "WHERE rp.child_id = ? AND pb.is_completed = 0 ORDER BY pb.pages_read DESC",
        (child_id,)
    )
    active_books = [
        {"id": b[0], "title": b[1], "author": b[2], "pages_read": b[3],
         "total_pages": b[4], "cover_file": b[5]}
        for b in cursor.fetchall()
    ]

    cursor.execute(
        "SELECT COUNT(*) FROM Plan_Books pb JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
        "WHERE rp.child_id = ? AND pb.is_completed = 1", (child_id,)
    )
    completed_books = cursor.fetchone()[0]

    cursor.execute(
        "SELECT bonus_bilig FROM Diagnostic_Logs WHERE child_id = ? AND type = 'voice' "
        "ORDER BY created_at DESC LIMIT 1", (child_id,)
    )
    r = cursor.fetchone()
    last_audio_score = int(r[0]) if r and r[0] else None

    return jsonify({
        "name": name, "coins": coins, "streak": streak, "rank": rank,
        "current_book": current_book, "last_badge": last_badge,
        "week": get_week_activity(child_id), "next_rank": get_next_rank(total_pages),
        "badges": badges or "", "total_pages": total_pages,
        "completed_books": completed_books, "active_books": active_books,
        "shelf_books": get_shelf_books(child_id),
        "last_audio_score": last_audio_score,
        "child_note": get_latest_child_note(child_id),
        "unseen_badges": unseen_badges(child_id)
    })


@app.route("/api/upload/avatar", methods=["POST"])
@require_auth
def upload_avatar():
    """Foydalanuvchi o‘z rasmini avatar qilib qo‘yadi.

    Rasm telefonda 192x192 ga kichraytirilib, WebP ga o‘tkazilgan bo‘ladi.
    Ota-ona farzandi uchun ham yuklashi mumkin — `child_id` bilan.
    """
    if "photo" not in request.files:
        return jsonify({"error": "Rasm topilmadi"}), 400
    data = request.files["photo"].read()

    target = g.user_id
    raw_child = request.args.get("child_id") or (request.form.get("child_id"))
    if raw_child:
        try:
            cid = int(raw_child)
        except ValueError:
            return jsonify({"error": "Farzand tanlanmagan"}), 400
        cursor.execute("SELECT 1 FROM Family_Link WHERE parent_id = ? AND child_id = ?",
                       (g.user_id, cid))
        if not cursor.fetchone():
            return jsonify({"error": "Bu farzand sizniki emas"}), 403
        target = cid

    name, err = save_upload("av", data, AVATAR_MAX_BYTES)
    if err:
        return jsonify({"error": err}), 400

    cursor.execute("SELECT avatar_id FROM Users WHERE user_id = ?", (target,))
    row = cursor.fetchone()
    old = row[0] if row else ""

    with db_lock:
        cursor.execute("UPDATE Users SET avatar_id = ? WHERE user_id = ?",
                       ("up:" + name, target))
        conn.commit()

    # Eskisi endi hech kimda ishlatilmasa — diskdan o‘chiriladi
    if old and old.startswith("up:") and old != "up:" + name:
        drop_upload_if_unused("av", old[3:], "avatar_id")

    return jsonify({"ok": True, "avatar_id": "up:" + name})


@app.route("/api/parent/books/<int:book_id>/cover", methods=["POST"])
@require_auth
def upload_book_cover(book_id):
    """Kitob muqovasi rasmi. Faqat shu oilaga ko‘rinadi."""
    if "photo" not in request.files:
        return jsonify({"error": "Rasm topilmadi"}), 400
    cursor.execute(
        "SELECT 1 FROM Plan_Books pb JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
        "WHERE pb.book_id = ? AND rp.parent_id = ?", (book_id, g.user_id))
    if not cursor.fetchone():
        return jsonify({"error": "Bu kitob sizniki emas"}), 403

    data = request.files["photo"].read()
    name, err = save_upload("cv", data, COVER_MAX_BYTES)
    if err:
        return jsonify({"error": err}), 400

    cursor.execute("SELECT cover_file FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    old = row[0] if row else ""

    with db_lock:
        cursor.execute("UPDATE Plan_Books SET cover_file = ? WHERE book_id = ?",
                       ("up:" + name, book_id))
        conn.commit()

    if old and old.startswith("up:") and old != "up:" + name:
        drop_upload_if_unused("cv", old[3:], "cover_file", "Plan_Books")

    return jsonify({"ok": True, "cover_file": "up:" + name})


@app.route("/api/child/badges/seen", methods=["POST"])
@require_auth
def child_mark_badges_seen():
    """Bola nishonlarni ko‘rdi — endi kutib olish kartochkasi chiqmaydi."""
    child_id = _resolve_active_child(request)
    with db_lock:
        cursor.execute("UPDATE Users SET badges_seen = ? WHERE user_id = ?",
                       (len(get_badges(child_id)), child_id))
        conn.commit()
    return jsonify({"ok": True})


@app.route("/api/child/passport", methods=["GET"])
@require_auth
def child_passport_self():
    """📜 Shaxsiy natija — taqvim, kitoblar, testlar va ko‘nikmalar."""
    child_id = _resolve_active_child(request)
    data = get_child_passport_data(child_id)
    if not data:
        return jsonify({"error": "Topilmadi"}), 404
    return jsonify(_enrich_passport(child_id, data))


@app.route("/api/child/books", methods=["GET"])
@require_auth
def child_books():
    child_id = _resolve_active_child(request)
    parent_id = get_parent_id(child_id)
    if not parent_id:
        return jsonify({"error": "Ota-onaga ulanmagansiz"}), 400

    # Asosiy so‘rovdan OLDIN — yordamchi ham shu cursor'dan foydalanadi.
    _final_only = _final_only_book_ids()
    cursor.execute(
        "SELECT plan_id, name, prize FROM Reading_Plans WHERE parent_id = ? AND child_id = ? AND status = 'active'",
        (parent_id, child_id)
    )
    plans = []
    for plan_id, name, prize in cursor.fetchall():
        cursor.execute(
            "SELECT book_id, title, author, pages_read, total_pages, is_completed, "
            "mid_test_1_done, mid_test_2_done, final_test_done, cover_file "
            "FROM Plan_Books WHERE plan_id = ?",
            (plan_id,)
        )
        books = [
            {"id": b[0], "title": b[1], "author": b[2], "pages_read": b[3],
             "total_pages": b[4], "completed": bool(b[5]),
             "test_final_only": b[0] in _final_only,
             "mid_test_1_done": bool(b[6]),
             "mid_test_2_done": bool(b[7]), "final_test_done": bool(b[8]),
             "cover_file": b[9], "has_voice": has_voice_report(child_id, b[0])}
            for b in cursor.fetchall()
        ]
        if books:
            plans.append({"id": plan_id, "name": name, "prize": prize, "books": books})
    return jsonify(plans)


@app.route("/api/child/book/<int:book_id>", methods=["GET"])
@require_auth
def child_book_detail(book_id):
    child_id = _resolve_active_child(request)
    # Diqqat: `cursor` yagona obyekt — yordamchi so‘rovni asosiy
    # execute() dan OLDIN bajaramiz, aks holda natija o‘chib ketadi.
    voice_open, voice_need = voice_quota(book_id)
    voice_sent = has_voice_report(child_id, book_id)
    stages = {}
    for _st in STAGE_ORDER:
        _open, _need = stage_gate(book_id, _st)
        stages[_st] = {"open": _open, "need_pages": _need}
    talk = {}
    for _ts in TALK_STAGES:
        _open, _need, _done = _talk_state(book_id, _ts)
        talk[_ts] = {"open": _open, "need_pages": _need, "done": _done}
    cursor.execute(
        "SELECT title, author, pages_read, total_pages, is_completed, "
        "mid_test_1_done, mid_test_2_done, final_test_done FROM Plan_Books WHERE book_id = ?",
        (book_id,)
    )
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Kitob topilmadi"}), 404
    cursor.execute("SELECT test_id FROM Book_Tests WHERE book_id = ?", (book_id,))
    has_test = cursor.fetchone() is not None
    # Test o‘qish davomida yig‘ilgan yozuvlardan tuzilgan bo‘lsa, u kitobning
    # hamma joyini qamramaydi — shuning uchun oraliq testlarga bo‘linmaydi.
    # Bola «Kitobni yakunladim» deganda bitta yakuniy test beriladi.
    cursor.execute("SELECT book_id FROM Auto_Test_State WHERE book_id = ?", (book_id,))
    final_only = cursor.fetchone() is not None
    base = get_book_base(row[0], row[1])
    # Qisqa asarda test bo‘lmaydi — bola og‘zaki xulosa beradi (ega qarori).
    short_form = bool((base or {}).get("short_form"))
    # AI USTOZ SAVOLI faqat kitob haqida biror narsa BILGANDA beriladi.
    # Aks holda AI faqat nom va muallifni ko‘rib, istalgan kitobga
    # to‘g‘ri keladigan bo‘sh savol yozadi — bola uni o‘qimasdan ham
    # javob bera oladi. Bunday savoldan ko‘ra yo‘qligi yaxshi.
    talk_ready = bool((base or {}).get("summary")) or any(
        get_talk_question(row[0], row[1], _ts) for _ts in TALK_STAGES)
    return jsonify({
        "title": row[0], "author": row[1], "pages_read": row[2], "total_pages": row[3],
        "completed": bool(row[4]), "mid_test_1_done": bool(row[5]),
        "mid_test_2_done": bool(row[6]), "final_test_done": bool(row[7]),
        "has_test": has_test, "test_final_only": final_only,
        "has_voice": voice_sent,
        "voice_open": voice_open,
        "voice_need_pages": voice_need,
        "voice_every_pages": VOICE_EVERY_PAGES,
        "stages": stages,
        "talk": talk,
        "short_form": short_form,
        "talk_ready": talk_ready,
        "book_base": base
    })


@app.route("/api/child/book/<int:book_id>/page_photo", methods=["POST"])
@require_auth
def child_submit_page_photo(book_id):
    """Bola o‘qigan sahifasini rasmga olib yuboradi -> AI tekshiradi -> Bilig beriladi."""
    if "photo" not in request.files:
        return jsonify({"error": "Rasm topilmadi"}), 400
    image_bytes = request.files["photo"].read()
    child_id = _require_child_actor(request)

    # 1) Aynan shu rasm ilgari tekshirilganmi? Bo‘lsa — AI chaqirilmaydi.
    img_hash = hashlib.sha256(image_bytes).hexdigest()
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ai_result = None
    from_cache = 0
    try:
        cursor.execute("SELECT result_json FROM Page_Check_Cache WHERE img_hash = ?", (img_hash,))
        cached = cursor.fetchone()
        if cached and cached[0]:
            ai_result = json.loads(cached[0])
            from_cache = 1
    except Exception:
        ai_result = None

    # 2) Kesh bo‘sh bo‘lsa — kunlik chegarani tekshiramiz, so‘ng AI chaqiriladi
    if ai_result is None:
        if _page_checks_today(child_id) >= PAGE_CHECK_DAILY_LIMIT:
            return jsonify({"ok": False, "reason": "daily_limit",
                             "message": "Bugun rasm orqali tekshirish chegarasiga yetdingiz. "
                                        "Sahifa raqamini qo‘lda kiritsangiz bo‘ladi."})
        ai_result = run_async(ai_service.verify_page_photo(image_bytes))
        try:
            with db_lock:
                cursor.execute(
                    "INSERT OR REPLACE INTO Page_Check_Cache (img_hash, result_json, created_at) "
                    "VALUES (?, ?, ?)",
                    (img_hash, json.dumps(ai_result, ensure_ascii=False), now_ts)
                )
                conn.commit()
        except Exception:
            pass

    try:
        with db_lock:
            cursor.execute(
                "INSERT INTO Page_Check_Log (child_id, img_hash, from_cache, created_at) "
                "VALUES (?, ?, ?, ?)", (child_id, img_hash, from_cache, now_ts)
            )
            conn.commit()
    except Exception:
        pass

    if not ai_result.get("is_book_page"):
        return jsonify({"ok": False, "reason": "not_book_page",
                         "message": "Bu kitob sahifasiga o‘xshamayapti. Qaytadan urinib ko‘ring."})

    new_page = int(ai_result.get("page_number", 0))

    # AI sahifani o‘qiganda nimani ko‘rganini saqlab qolamiz. Bu bolaga
    # ko‘rinmaydi — keyinchalik shu yozuvlardan test o‘z-o‘zidan tuziladi.
    # Sahifa raqami noaniq bo‘lsa ham mazmun qimmatli, lekin uni qaysi
    # sahifaga bog‘lashni bilmaymiz — shuning uchun faqat raqam bor bo‘lsa.
    _save_page_note(book_id, new_page, ai_result.get("note") or "")

    if new_page <= 0:
        return jsonify({"ok": False, "reason": "page_unclear",
                         "message": "Sahifa raqami aniq ko‘rinmadi. Sahifa raqamini qo‘lda kiriting."})

    result = _apply_page_progress(book_id, child_id, new_page)
    _maybe_build_test_from_notes(book_id)
    return result


@app.route("/api/child/book/<int:book_id>/page_manual", methods=["POST"])
@require_auth
def child_submit_page_manual(book_id):
    """AI orqali emas, sahifa raqamini qo‘lda kiritish (zaxira variant)."""
    data = request.get_json(force=True) or {}
    new_page = int(data.get("page_number", 0))
    child_id = _require_child_actor(request)
    if new_page <= 0:
        return jsonify({"ok": False, "message": "Sahifa raqamini to‘g‘ri kiriting"}), 400
    return _apply_page_progress(book_id, child_id, new_page)


def _apply_page_progress(book_id, child_id, new_page):
    cursor.execute("SELECT pages_read, title, total_pages FROM Plan_Books WHERE book_id = ?",
                   (book_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Kitob topilmadi"}), 404
    old_pages, book_title, total_pages = row

    if new_page <= old_pages:
        return jsonify({"ok": False, "reason": "not_progress",
                         "message": f"Siz allaqachon {old_pages}-sahifagacha o‘qigansiz!"})

    # Kitobning jami sahifasidan oshib ketmasin. Ilgari tekshiruv yo‘q edi:
    # 5000 deb yozilsa qabul qilinardi va bola bir zumda minglab Bilig
    # hamda hamma nishonni olib qo‘yardi. AI bet raqamini noto‘g‘ri
    # o‘qib yuborsa ham xuddi shunday bo‘lardi.
    if total_pages and new_page > total_pages:
        return jsonify({"ok": False, "reason": "too_big",
                         "message": f"Bu kitobda {total_pages} bet bor. "
                                    f"Sahifa raqamini tekshirib qayta kiriting."})

    earned_bilig = (new_page // 5) - (old_pages // 5)
    pages_added = new_page - old_pages
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with db_lock:
        cursor.execute("UPDATE Plan_Books SET pages_read = ? WHERE book_id = ?", (new_page, book_id))
        cursor.execute(
            "INSERT INTO Reading_Logs (child_id, book_id, pages_added, created_at) VALUES (?, ?, ?, ?)",
            (child_id, book_id, pages_added, now_ts)
        )
        if earned_bilig > 0:
            cursor.execute(
                "UPDATE Users SET balance_coins = balance_coins + ?, total_xp = total_xp + ? WHERE user_id = ?",
                (earned_bilig, pages_added, child_id)
            )
        conn.commit()

    cursor.execute("SELECT streak_days FROM Users WHERE user_id = ?", (child_id,))
    _r = cursor.fetchone()
    old_streak = _r[0] if _r else 0
    streak, shield_used = update_streak(child_id)
    rank, total_pages = calculate_and_update_rank(child_id)

    with db_lock:
        new_badges, later_badges = badges_engine.check_badges(
            child_id, {"shield_used": shield_used}, action="page")
    _mark_celebrated(child_id, new_badges, later_badges)
    announce_badges(child_id, new_badges + later_badges)

    cursor.execute("SELECT balance_coins FROM Users WHERE user_id = ?", (child_id,))
    balance = cursor.fetchone()[0]

    return jsonify({
        "ok": True, "book_title": book_title, "new_page": new_page,
        "earned_bilig": max(0, earned_bilig), "balance": balance,
        "streak": streak, "shield_used": shield_used, "rank": rank, "total_pages": total_pages,
        "new_badges": new_badges, "streak_up": streak > old_streak
    })


@app.route("/api/child/book/<int:book_id>/voice", methods=["POST"])
@require_auth
def child_submit_voice(book_id):
    """Bola audio xulosa yuboradi -> AI Ustoz tahlil qiladi -> bonus Bilig + ota-onaga hisobot."""
    if "audio" not in request.files:
        return jsonify({"error": "Audio topilmadi"}), 400
    audio_bytes = request.files["audio"].read()
    # Nima kelganini AYNAN bilib turamiz: telefon qanday format yozdi,
    # o‘girish ishladimi, server baytlardan qanday format ko‘ryapti.
    kind = ai_service.audio_kind(audio_bytes)
    detail = "server: %s, %d KB" % (kind, len(audio_bytes) // 1024)
    ai_service.log_line("[voice] kitob=%s %s | telefon: %s"
                        % (book_id, detail, request.form.get("meta", "-")))
    if len(audio_bytes) < 2000:
        return jsonify({"error": "Ovoz juda qisqa yoki yozilmagan. "
                                 "Mikrofonni bosib, kamida 15 soniya gapiring."}), 400
    child_id = _require_child_actor(request)

    # Ega qarori: ovozli xulosa har 15 betda bir marta yuboriladi. Ilgari
    # cheklov yo‘q edi — bir xil xulosani qayta-qayta yuborib tanga yig‘sa
    # bo‘lardi. Endi yangi xulosa uchun avval o‘qish kerak.
    is_open, need = voice_quota(book_id)
    if not is_open:
        return jsonify({"error": "Ovozli xulosa har %d betda bir marta yuboriladi. "
                                 "Yana %d bet o‘qigach, yangisini yuborsang bo‘ladi."
                                 % (VOICE_EVERY_PAGES, need)}), 403

    cursor.execute("SELECT title FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    book_title = row[0] if row else "Kitob"

    cursor.execute(
        "SELECT fl.child_age FROM Family_Link fl WHERE fl.child_id = ?", (child_id,)
    )
    age_row = cursor.fetchone()
    age = age_row[0] if age_row and age_row[0] else 10

    # Uzun audioni tahlil qilish bir daqiqagacha cho‘zilishi mumkin. Agar
    # telefon shuncha vaqt javob kutib tursa, aloqa uzilib «xato» chiqadi —
    # egasi buni aniq payqadi: 15 soniyalik ovoz o‘tdi, 1 daqiqaligi yo‘q.
    # Shuning uchun ish fon rejimida bajariladi: telefon darrov «kvitansiya»
    # oladi va vaqti-vaqti bilan «tayyor bo‘ldimi?» deb so‘rab turadi.
    try:
        was_original = bool(json.loads(request.form.get("meta") or "{}").get("ogirilmagan"))
    except Exception:
        was_original = False
    job_id = _start_voice_job(book_id, child_id, book_title, age, audio_bytes, detail, was_original)
    return jsonify({"ok": True, "job_id": job_id})


# ==========================================================
# OVOZNI TAHLIL QILISH — FON REJIMIDA
# ==========================================================
_voice_jobs = {}
_voice_jobs_lock = threading.Lock()

# Oxirgi marta qaysi format ishlagani. Ro‘yxat ichida — ip'lar orasida
# oddiy o‘zgaruvchini almashtirish uchun eng sodda yo‘l.
_voice_prefer = ["wav"]


def _set_voice_job(job_id, **fields):
    with _voice_jobs_lock:
        job = _voice_jobs.setdefault(job_id, {})
        job.update(fields)
        job["at"] = time.time()


def _start_voice_job(book_id, child_id, book_title, age, audio_bytes, detail,
                     was_original=False, talk_stage=None, question=""):
    job_id = uuid.uuid4().hex[:12]
    _set_voice_job(job_id, status="ishlanmoqda", result=None, error=None, detail=detail)

    def worker():
        try:
            result = run_async(
                ai_service.evaluate_voice_summary(audio_bytes, age, book_title, question))
            if talk_stage:
                payload = _finish_talk(book_id, child_id, book_title, result,
                                       detail, talk_stage, question)
            else:
                payload = _finish_voice(book_id, child_id, book_title, result, detail)
            _set_voice_job(job_id, status="tayyor", result=payload)
            # Ishlagan formatni eslab qolamiz — keyingi safar shundan boshlanadi.
            new_pref = "asl" if was_original else "wav"
            if _voice_prefer[0] != new_pref:
                _voice_prefer[0] = new_pref
                ai_service.log_line("[voice] endi avval «%s» sinaladi" % new_pref)
            ai_service.log_line("[voice] TAYYOR kitob=%s (%s)" % (book_id, detail))
        except Exception as e:
            traceback.print_exc()
            ai_service.log_line("[voice] XATO kitob=%s bola=%s (%s): %r"
                                % (book_id, child_id, detail, e))
            _set_voice_job(job_id, status="xato", error=ai_service.human_error(e))

    threading.Thread(target=worker, daemon=True).start()
    return job_id


@app.route("/api/child/voice_job/<job_id>", methods=["GET"])
@require_auth
def child_voice_job(job_id):
    now = time.time()
    with _voice_jobs_lock:
        for k in [k for k, v in _voice_jobs.items() if now - v.get("at", 0) > TEST_JOB_TTL]:
            _voice_jobs.pop(k, None)
        job = _voice_jobs.get(job_id)
    if not job:
        return jsonify({"error": "Bu ish topilmadi — qaytadan urinib ko‘ring"}), 404
    out = {"status": job["status"]}
    if job["status"] == "tayyor":
        out["result"] = job.get("result")
    if job["status"] == "xato":
        out["error"] = job.get("error")
    return jsonify(out)


def _finish_voice(book_id, child_id, book_title, result, detail):
    diag = result.get("diagnostic_scores", {})
    # Ega qarori: ovoz uchun ham test bilan bir xil o‘lchov — yaxshi so‘zlab
    # bersa 3 Bilig, aks holda tanga yo‘q (lekin iliq maslahat baribir bor).
    marks = [diag.get(k, 0) for k in ("factual_score", "logic_score",
                                      "conclusion_score", "fluency_score",
                                      "vocabulary_score")]
    average = sum(marks) / len(marks) if marks else 0
    bonus = REWARD_COINS if average >= REWARD_PERCENT else 0
    new_badges = []
    with db_lock:
        if bonus > 0:
            cursor.execute(
                "UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (bonus, child_id)
            )
        cursor.execute(
            "INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, logic_score, "
            "conclusion_score, fluency_score, vocabulary_score, parent_note, convo_topic, created_at, bonus_bilig, child_note) "
            "VALUES (?, ?, 'voice', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (child_id, book_id,
             diag.get("factual_score", 0), diag.get("logic_score", 0), diag.get("conclusion_score", 0),
             diag.get("fluency_score", 0), diag.get("vocabulary_score", 0),
             json.dumps(result.get("parent_report", {}), ensure_ascii=False),
             result.get("parent_report", {}).get("conversation_topic", ""),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), bonus,
             result.get("child_feedback", ""))
        )
        # Keyingi ovozli xulosa uchun sanoq shu betdan boshlanadi.
        # Bu AI tahlili MUVAFFAQIYATLI tugagandagina bajariladi — aks holda
        # xatolikdan keyingi qayta yuborish ham to‘silib qolardi.
        cursor.execute(
            "UPDATE Plan_Books SET voice_last_page = pages_read WHERE book_id = ?",
            (book_id,)
        )
        conn.commit()
        new_badges, later_badges = badges_engine.check_badges(
            child_id, {"ezgulik": bool(result.get("badge_ezgulik", False))},
            action="voice")

    _mark_celebrated(child_id, new_badges, later_badges)
    announce_badges(child_id, new_badges + later_badges)

    # Bu funksiya FON IPIDA ishlaydi, `cursor` esa yagona obyekt —
    # o‘qishni ham qulf ostida qilamiz, aks holda ayni paytdagi so‘rovning
    # natijasi o‘chib ketadi.
    with db_lock:
        parent_id = get_parent_id(child_id)
    if parent_id:
        pr = result.get("parent_report", {})
        send_telegram_message(
            parent_id,
            f"🎙 <b>{book_title}</b> bo‘yicha farzandingizning ovozli hisobotini AI tahlil qildi!\n\n"
            f"📌 {pr.get('summary', '')}\n\n✅ {pr.get('strengths', '')}\n🌱 {pr.get('weaknesses', '')}\n\n"
            f"{pr.get('conversation_topic', '')}"
        )

    return {
        "ok": True, "bonus_bilig": bonus,
        "feedback": result.get("child_feedback", ""),
        "give_badge": bool(result.get("give_badge", False)),
        "new_badges": new_badges
    }


# ==========================================================
# AI USTOZ SAVOLI — ovozda javob beriladigan ochiq savol
# ----------------------------------------------------------
# Kitobning boshida (uchdan biri o‘qilganda) va oxirida bittadan savol
# beriladi. Savol FAKTIK EMAS: bola o‘qiganini o‘z so‘zi bilan gapirib
# bera olishini, tushunganini va munosabatini ochadi. Javob ovozli
# yuboriladi, ota-onaga to‘liq hisobot boradi.
# ==========================================================
def _talk_state(book_id, stage):
    """(ochiqmi, yana necha bet, topshirilganmi) — bitta so‘rovda."""
    is_open, need = talk_gate(book_id, stage)
    column = "talk_start_done" if stage == "start" else "talk_end_done"
    cursor.execute("SELECT %s FROM Plan_Books WHERE book_id = ?" % column, (book_id,))
    row = cursor.fetchone()
    return is_open, need, bool(row and row[0])


@app.route("/api/child/book/<int:book_id>/talk", methods=["GET"])
@require_auth
def child_get_talk(book_id):
    """Shu bosqichdagi AI ustoz savolini olish."""
    stage = request.args.get("stage") or "start"
    if stage not in TALK_STAGES:
        stage = "start"

    is_open, need, done = _talk_state(book_id, stage)
    cursor.execute("SELECT title, author FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Kitob topilmadi"}), 404
    title, author = row[0], row[1]

    if not is_open:
        return jsonify({"open": False, "need_pages": need, "done": done, "question": None})

    question = get_talk_question(title, author, stage)
    if not question:
        base = get_book_base(title, author) or {}
        if not (base.get("summary") or "").strip():
            # Kitob haqida hech narsa bilmaymiz. Nomidan savol tuzsak,
            # u istalgan kitobga to‘g‘ri keladigan bo‘sh savol bo‘ladi.
            return jsonify({"open": False, "not_ready": True, "done": done,
                            "need_pages": 0, "question": None})
        # Oldindan tayyorlanmagan — shu yerda tuzamiz. Bu faqat matn, tez.
        try:
            question = run_async(
                ai_service.generate_talk_question(title, author, base, stage))
            save_talk_question(title, author, stage, question)
        except Exception as e:
            ai_service.log_line("[savol] XATO kitob=%s: %r" % (book_id, e))
            return jsonify({"error": ai_service.human_error(e)}), 500

    return jsonify({"open": True, "need_pages": 0, "done": done, "question": question})


@app.route("/api/child/book/<int:book_id>/talk", methods=["POST"])
@require_auth
def child_submit_talk(book_id):
    """Bola AI ustoz savoliga ovozli javob yuboradi."""
    stage = request.args.get("stage") or "start"
    if stage not in TALK_STAGES:
        stage = "start"
    if "audio" not in request.files:
        return jsonify({"error": "Audio topilmadi"}), 400
    audio_bytes = request.files["audio"].read()
    kind = ai_service.audio_kind(audio_bytes)
    detail = "server: %s, %d KB" % (kind, len(audio_bytes) // 1024)
    ai_service.log_line("[talk] kitob=%s bosqich=%s %s" % (book_id, stage, detail))
    if len(audio_bytes) < 2000:
        return jsonify({"error": "Ovoz juda qisqa yoki yozilmagan. "
                                 "Mikrofonni bosib, kamida 30 soniya gapiring."}), 400

    child_id = _require_child_actor(request)
    is_open, need, done = _talk_state(book_id, stage)
    if not is_open:
        return jsonify({"error": "Bu savolga hali erta. Yana %d bet o‘qi." % need}), 403
    if done:
        return jsonify({"error": "Bu savolga allaqachon javob bergansan."}), 403

    cursor.execute("SELECT title, author FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    title = row[0] if row else "Kitob"
    author = row[1] if row else ""

    cursor.execute("SELECT child_age FROM Family_Link WHERE child_id = ?", (child_id,))
    age_row = cursor.fetchone()
    age = age_row[0] if age_row and age_row[0] else 10

    question = get_talk_question(title, author, stage) or ""
    try:
        was_original = bool(json.loads(request.form.get("meta") or "{}").get("ogirilmagan"))
    except Exception:
        was_original = False
    job_id = _start_voice_job(book_id, child_id, title, age, audio_bytes, detail,
                              was_original, talk_stage=stage, question=question)
    return jsonify({"ok": True, "job_id": job_id})


def _finish_talk(book_id, child_id, book_title, result, detail, stage, question):
    """AI ustoz savoliga javobni yakunlaydi: Bilig, yozuv, ota-onaga hisobot."""
    diag = result.get("diagnostic_scores", {})
    marks = [diag.get(k, 0) for k in ("factual_score", "logic_score",
                                      "conclusion_score", "fluency_score",
                                      "vocabulary_score")]
    average = sum(marks) / len(marks) if marks else 0
    bonus = TALK_COINS if average >= REWARD_PERCENT else 0

    pr = dict(result.get("parent_report", {}))
    pr["question"] = question          # ota-ona qaysi savolga javob berilganini ko‘rsin
    column = "talk_start_done" if stage == "start" else "talk_end_done"

    with db_lock:
        if bonus > 0:
            cursor.execute(
                "UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?",
                (bonus, child_id))
        cursor.execute(
            "INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, logic_score, "
            "conclusion_score, fluency_score, vocabulary_score, parent_note, convo_topic, "
            "created_at, bonus_bilig, child_note) "
            "VALUES (?, ?, 'talk', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (child_id, book_id,
             diag.get("factual_score", 0), diag.get("logic_score", 0),
             diag.get("conclusion_score", 0), diag.get("fluency_score", 0),
             diag.get("vocabulary_score", 0),
             json.dumps(pr, ensure_ascii=False),
             pr.get("conversation_topic", ""),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), bonus,
             result.get("child_feedback", ""))
        )
        cursor.execute("UPDATE Plan_Books SET %s = 1 WHERE book_id = ?" % column, (book_id,))
        conn.commit()
        new_badges, later_badges = badges_engine.check_badges(
            child_id, {"ezgulik": bool(result.get("badge_ezgulik", False))},
            action="voice")

    _mark_celebrated(child_id, new_badges, later_badges)
    announce_badges(child_id, new_badges + later_badges)

    with db_lock:
        parent_id = get_parent_id(child_id)
    if parent_id:
        nom = "kitob boshi" if stage == "start" else "kitob yakuni"
        send_telegram_message(
            parent_id,
            f"🎓 <b>{book_title}</b> — AI ustoz savoli ({nom})\n\n"
            f"❓ <i>{question}</i>\n\n"
            f"📌 {pr.get('summary', '')}\n\n"
            f"✅ {pr.get('strengths', '')}\n🌱 {pr.get('weaknesses', '')}\n\n"
            f"{pr.get('conversation_topic', '')}"
        )

    return {
        "ok": True, "bonus_bilig": bonus,
        "feedback": result.get("child_feedback", ""),
        "new_badges": new_badges
    }


@app.route("/api/child/book/<int:book_id>/test", methods=["GET"])
@require_auth
def child_get_test(book_id):
    """Bosqich savollarini olish (to‘g‘ri javob YASHIRIB yuboriladi).

    Savollar bolaning kelgan joyiga qarab beriladi: 1-oraliqda faqat
    kitobning birinchi uchdan bir qismidan so‘raladi. Ilgari uchala
    bosqich ham butun kitobdan so‘rardi — o‘qilmagan sahifalar ham.
    """
    stage = request.args.get("stage") or "mid_test_1"
    if stage not in STAGE_ORDER:
        stage = "mid_test_1"

    cursor.execute("SELECT book_id FROM Auto_Test_State WHERE book_id = ?", (book_id,))
    if cursor.fetchone() is not None:
        stage = "final_test"

    is_open, need = stage_gate(book_id, stage)
    if not is_open:
        return jsonify({"error": "Bu testga hali erta. Yana %d bet o‘qi." % need}), 403

    done_stages = _done_stages(book_id)
    cursor.execute("SELECT questions_json FROM Book_Tests WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Bu kitob uchun test hali tuzilmagan"}), 404
    try:
        questions = json.loads(row[0])
    except Exception:
        return jsonify({"error": "Test ma'lumotida xatolik"}), 500

    safe_questions = [
        {"id": q.get("id"), "category": q.get("category"), "question": q.get("question"), "options": q.get("options")}
        for q in stage_questions(questions, stage, done_stages)
    ]
    if not safe_questions:
        return jsonify({"error": "Bu bosqich uchun savollar topilmadi"}), 404
    return jsonify(safe_questions)


@app.route("/api/child/book/<int:book_id>/test/submit", methods=["POST"])
@require_auth
def child_submit_test(book_id):
    """Test javoblarini tekshirish, ballash va Bilig berish."""
    data = request.get_json(force=True) or {}
    stage = data.get("stage", "mid_test_1")  # mid_test_1 | mid_test_2 | final_test
    answers = data.get("answers", {})  # {"1": "A) ...", ...}
    child_id = _require_child_actor(request)

    # Test o‘qish davomida yig‘ilgan yozuvlardan tuzilgan bo‘lsa, u faqat
    # yakuniy test sifatida beriladi — oraliq bosqichlarga bo‘linmaydi.
    cursor.execute("SELECT book_id FROM Auto_Test_State WHERE book_id = ?", (book_id,))
    if cursor.fetchone() is not None:
        stage = "final_test"

    cursor.execute("SELECT questions_json FROM Book_Tests WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Test topilmadi"}), 404
    questions = json.loads(row[0])

    # Bosqich hali ochilmagan bo‘lsa, javob qabul qilinmaydi — aks holda
    # bola savollarni ko‘rmasdan turib ham natija yubora olardi.
    is_open, need = stage_gate(book_id, stage)
    if not is_open:
        return jsonify({"error": "Bu testga hali erta. Yana %d bet o‘qi." % need}), 403

    # AYNAN savol berilgan ro‘yxat bo‘yicha tekshiramiz — butun bank
    # bo‘yicha emas, aks holda berilmagan savollar ham «xato» sanalardi.
    asked = stage_questions(questions, stage, _done_stages(book_id))
    correct = 0
    for q in asked:
        qid = str(q.get("id"))
        if qid in answers and answers[qid] == q.get("answer"):
            correct += 1
    total = len(asked) if asked else 1
    percent = round((correct / total) * 100)
    # Ega qarori: har bosqich (1-oraliq, 2-oraliq, yakuniy) uchun natija
    # 70% va undan yuqori bo‘lsa 3 Bilig; pastroq bo‘lsa tanga berilmaydi.
    earned = REWARD_COINS if percent >= REWARD_PERCENT else 0

    column_map = {
        "mid_test_1": "mid_test_1_done", "mid_test_2": "mid_test_2_done", "final_test": "final_test_done"
    }
    column = column_map.get(stage, "mid_test_1_done")

    # Bir testni ikki marta topshirib, Bilig yig‘ib olishning oldini olamiz.
    # Ilgari tekshiruv yo‘q edi: bir xil testni qayta-qayta topshirib,
    # har safar tanga olish mumkin edi.
    cursor.execute("SELECT %s FROM Plan_Books WHERE book_id = ?" % column, (book_id,))
    _done = cursor.fetchone()
    if _done and _done[0]:
        return jsonify({"ok": False, "reason": "already_done", "already_done": True,
                        "correct": correct, "total": total, "percent": percent,
                        "earned_bilig": 0, "new_badges": [],
                        "message": "Bu testni allaqachon topshirgansan. "
                                   "Natija saqlanib qolgan."})

    with db_lock:
        cursor.execute(f"UPDATE Plan_Books SET {column} = 1 WHERE book_id = ?", (book_id,))
        if stage == "final_test":
            cursor.execute("UPDATE Plan_Books SET is_completed = 1 WHERE book_id = ?", (book_id,))
        if earned:
            cursor.execute(
                "UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (earned, child_id)
            )
        # Test natijasi diagnostikaga yoziladi — ilgari Mini App'dagi testlar
        # umuman qayd etilmasdi, faqat botdagilari yozilardi.
        cursor.execute(
            "INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, logic_score, "
            "conclusion_score, created_at, correct_count, total_count) "
            "VALUES (?, ?, 'test', ?, ?, ?, ?, ?, ?)",
            (child_id, book_id, percent, percent, percent,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), correct, total)
        )
        conn.commit()
        new_badges, later_badges = badges_engine.check_badges(child_id, action="test")

    # Yakuniy test — kitob tugadi. Bu ota-ona kutayotgan xabar.
    if stage == "final_test":
        cursor.execute("SELECT title, pages_read FROM Plan_Books WHERE book_id = ?", (book_id,))
        brow = cursor.fetchone()
        if brow:
            cursor.execute(
                "SELECT COUNT(*) FROM Plan_Books pb JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
                "WHERE rp.child_id = ? AND pb.is_completed = 1", (child_id,))
            done = cursor.fetchone()[0]
            notify_parent(
                child_id,
                f"📖 <b>{child_name_of(child_id)}</b> «{brow[0]}» kitobini tugatdi.\n"
                f"{brow[1] or 0} bet. Javonida endi {done} ta tugatilgan kitob bor."
            )
    _mark_celebrated(child_id, new_badges, later_badges)
    announce_badges(child_id, new_badges + later_badges)

    return jsonify({"ok": True, "correct": correct, "total": total, "percent": percent,
                    "earned_bilig": earned, "new_badges": new_badges})


@app.route("/api/child/rewards", methods=["GET"])
@require_auth
def child_rewards():
    """'🎁 Sovrinlarim' — bola uchun bilig, nishonlar, daraja."""
    child_id = _resolve_active_child(request)
    cursor.execute(
        "SELECT balance_coins, badges, streak_days, rank_title FROM Users WHERE user_id = ?", (child_id,)
    )
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Topilmadi"}), 404
    coins, badges, streak, rank = row
    return jsonify({
        "coins": coins, "badges": (badges or "").split(",") if badges else [],
        "streak": streak, "rank": rank
    })


@app.route("/api/child/store", methods=["GET"])
@require_auth
def child_store():
    """'🛒 Do‘kon' — ota-ona kiritgan sovg‘alar ro‘yxati (bola sotib olishi mumkin)."""
    child_id = _resolve_active_child(request)
    parent_id = get_parent_id(child_id)
    if not parent_id:
        return jsonify([])
    cursor.execute("SELECT item_id, name, price FROM Store_Items WHERE parent_id = ?", (parent_id,))
    cursor.execute("SELECT balance_coins FROM Users WHERE user_id = ?", (child_id,))
    balance = cursor.fetchone()[0]
    cursor.execute("SELECT item_id, name, price FROM Store_Items WHERE parent_id = ?", (parent_id,))
    items = [{"id": r[0], "name": r[1], "price": r[2], "affordable": r[2] <= balance} for r in cursor.fetchall()]
    return jsonify({"balance": balance, "items": items})


@app.route("/api/child/store/<int:item_id>/buy", methods=["POST"])
@require_auth
def child_store_buy(item_id):
    child_id = _resolve_active_child(request)
    cursor.execute("SELECT balance_coins, name FROM Users WHERE user_id = ?", (child_id,))
    balance, child_name = cursor.fetchone()
    cursor.execute("SELECT name, price, parent_id FROM Store_Items WHERE item_id = ?", (item_id,))
    item = cursor.fetchone()
    if not item:
        return jsonify({"error": "Sovg‘a topilmadi"}), 404
    item_name, price, parent_id = item

    if balance < price:
        return jsonify({"ok": False, "message": "Bilig yetarli emas 😔"})

    with db_lock:
        cursor.execute("UPDATE Users SET balance_coins = balance_coins - ? WHERE user_id = ?", (price, child_id))
        conn.commit()

    send_telegram_message(
        parent_id,
        f"🛒 <b>{child_name}</b> do‘kondan <b>«{item_name}»</b> sovg‘asini {price} 🔅 ga sotib oldi. "
        f"Sovg‘ani berishni unutmang!"
    )
    return jsonify({"ok": True, "new_balance": balance - price})


@app.route("/api/child/rating", methods=["GET"])
@require_auth
def child_rating():
    """'🏆 Reyting' — bir xil ota-onaga bog‘langan barcha farzandlar orasida reyting
    (agar bitta bola bo‘lsa — umumiy TOP-10 orasida ko‘rsatiladi)."""
    child_id = _resolve_active_child(request)
    parent_id = get_parent_id(child_id)

    if parent_id:
        cursor.execute(
            "SELECT u.user_id, u.name, u.total_xp, u.rank_title FROM Family_Link fl "
            "JOIN Users u ON fl.child_id = u.user_id WHERE fl.parent_id = ? ORDER BY u.total_xp DESC",
            (parent_id,)
        )
        rows = cursor.fetchall()
        if len(rows) > 1:
            return jsonify({
                "scope": "oila",
                "list": [{"id": r[0], "name": r[1], "xp": r[2], "rank": r[3], "is_me": r[0] == child_id} for r in rows]
            })

    cursor.execute(
        "SELECT user_id, name, total_xp, rank_title FROM Users WHERE role = 'child' ORDER BY total_xp DESC LIMIT 10"
    )
    rows = cursor.fetchall()
    return jsonify({
        "scope": "umumiy",
        "list": [{"id": r[0], "name": r[1], "xp": r[2], "rank": r[3], "is_me": r[0] == child_id} for r in rows]
    })


# ==========================================================
# 5) ADMIN (loyiha egasi) — ixtiyoriy, /stats bilan bir xil
# ==========================================================

# ==========================================================
# 3 KUNLIK XULOSA — ota-onaga o‘z-o‘zidan boradigan yagona xabar
# ----------------------------------------------------------
# Qolgan barcha xabarlar bola biror amal qilganda yuboriladi.
# Bu esa «hech kim hech nima qilmaganda» ham ishlashi kerak,
# shuning uchun fon rejimidagi alohida ip (thread) kuzatib turadi.
# ==========================================================
SUMMARY_EVERY_DAYS = 3
SUMMARY_HOUR = 20          # kechqurun 20:00 dan keyin yuboriladi
_WEEKDAYS = ["dushanba", "seshanba", "chorshanba", "payshanba", "juma", "shanba", "yakshanba"]


def build_summary(child_id: int, days: int = SUMMARY_EVERY_DAYS):
    """Oxirgi N kundagi natijalar. Hech nima bo‘lmagan bo‘lsa — None."""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT SUM(pages_added), COUNT(DISTINCT substr(created_at, 1, 10)) "
                   "FROM Reading_Logs WHERE child_id = ? AND created_at >= ?", (child_id, since))
    row = cursor.fetchone()
    pages = row[0] or 0
    active_days = row[1] or 0

    cursor.execute("SELECT substr(created_at, 1, 10), SUM(pages_added) FROM Reading_Logs "
                   "WHERE child_id = ? AND created_at >= ? GROUP BY 1 ORDER BY 2 DESC LIMIT 1",
                   (child_id, since))
    best = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) FROM Diagnostic_Logs WHERE child_id = ? "
                   "AND type = 'test' AND created_at >= ?", (child_id, since))
    tests = cursor.fetchone()[0]

    cursor.execute("SELECT streak_days FROM Users WHERE user_id = ?", (child_id,))
    r = cursor.fetchone()
    streak = r[0] if r else 0

    name = child_name_of(child_id)
    if not pages and not tests:
        # Uch kun ichida hech nima bo‘lmadi — bu ham xabar, lekin boshqacha
        return (f"📕 <b>{name}</b> so‘nggi {days} kunda kitob ochmadi.\n"
                f"Ketma-ketligi yo‘qolib qolmasin — bugun eslatib qo‘ysangiz bo‘ladi.")

    lines = [f"📊 <b>{days} kunlik xulosa — {name}</b>", ""]
    if pages:
        lines.append(f"• {pages} bet o‘qildi ({active_days} kun faol)")
    if tests:
        lines.append(f"• {tests} ta test topshirdi")
    lines.append(f"• Ketma-ket {streak}-kun")
    if best and best[1]:
        try:
            wd = _WEEKDAYS[datetime.strptime(best[0], "%Y-%m-%d").weekday()]
            lines.append(f"\nEng faol kuni: {wd} — {best[1]} bet.")
        except Exception:
            pass
    return "\n".join(lines)


def _summary_due(child_id: int) -> bool:
    cursor.execute("SELECT last_summary_at FROM Users WHERE user_id = ?", (child_id,))
    row = cursor.fetchone()
    if not row or not row[0]:
        return True
    try:
        last = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return True
    return (datetime.now() - last).days >= SUMMARY_EVERY_DAYS


def send_due_summaries():
    """Muddati kelgan barcha xulosalarni yuboradi."""
    now = datetime.now()
    if now.hour < SUMMARY_HOUR:
        return 0
    try:
        cursor.execute("SELECT DISTINCT child_id FROM Family_Link")
        kids = [r[0] for r in cursor.fetchall()]
    except Exception:
        return 0
    sent = 0
    for child_id in kids:
        try:
            if not _summary_due(child_id):
                continue
            text = build_summary(child_id)
            if text:
                notify_parent(child_id, text)
            with db_lock:
                cursor.execute("UPDATE Users SET last_summary_at = ? WHERE user_id = ?",
                               (now.strftime("%Y-%m-%d %H:%M:%S"), child_id))
                conn.commit()
            sent += 1
        except Exception:
            continue
    return sent


def _summary_loop():
    while True:
        try:
            send_due_summaries()
        except Exception:
            pass
        time.sleep(1800)          # yarim soatda bir marta tekshiradi


def start_summary_worker():
    t = threading.Thread(target=_summary_loop, daemon=True)
    t.start()
    print("[webapp_api] 3 kunlik xulosa kuzatuvchisi ishga tushdi")


@app.route("/api/admin/summary_now", methods=["POST"])
@require_auth
def admin_summary_now():
    """Sinov uchun: xulosalarni darhol yuborish (faqat loyiha egasi)."""
    if OWNER_ID and g.user_id != OWNER_ID:
        return jsonify({"error": "Ruxsat yo‘q"}), 403
    return jsonify({"ok": True, "sent": send_due_summaries()})


@app.route("/api/admin/logs", methods=["GET"])
def admin_logs():
    """So‘nggi texnik yozuvlarni ko‘rsatadi — nosozlik sababini topish uchun.

    Render'dagi LOG_TOKEN sozlamasi qo‘yilmagan bo‘lsa, bu manzil umuman
    yo‘q (404). Ya'ni tasodifan ochilib qolmaydi. Yozuvlarda faqat texnik
    ma'lumot bo‘ladi: format, hajm, xato matni.
    """
    token = os.getenv("LOG_TOKEN", "")
    if not token or request.args.get("token") != token:
        return ("Topilmadi", 404)
    only = (request.args.get("q") or "").strip()
    lines = list(ai_service.LOG_RING)
    if only:
        lines = [x for x in lines if only in x]
    try:
        limit = max(1, min(400, int(request.args.get("n", 120))))
    except ValueError:
        limit = 120
    body = "\n".join(lines[-limit:]) or "(yozuv yo‘q)"
    return Response(body + "\n", mimetype="text/plain; charset=utf-8")


@app.route("/api/admin/stats", methods=["GET"])
@require_auth
def admin_stats():
    if OWNER_ID != 0 and g.user_id != OWNER_ID:
        return jsonify({"error": "Ruxsat yo‘q"}), 403
    text = generate_admin_stats_text()
    return jsonify({"html": text})


# ==========================================================
# 6) MINI APP FAYLLARINI (HTML/CSS/JS) TARQATISH
# ==========================================================

@app.route("/")
def serve_index():
    index_path = os.path.join(WEBAPP_DIR, "index.html")
    if not os.path.isfile(index_path):
        return (
            "<h3>webapp/index.html topilmadi</h3>"
            f"<p>Qidirilgan joy: <code>{index_path}</code></p>"
            "<p>webapp_api.py va webapp/ papkasi bir xil papkada (masalan, ikkalasi ham "
            "main.py bilan bir qatorda) turganini tekshiring.</p>",
            500,
        )
    html = io.open(index_path, encoding="utf-8").read()
    html = html.replace("__ASSET_V__", _asset_version())
    resp = Response(html, mimetype="text/html")
    return _no_cache(resp)


# ==========================================================
# BEZAK VA KOD FAYLLARINING VERSIYASI — O‘Z-O‘ZIDAN
# ----------------------------------------------------------
# Ilgari versiya raqami qo‘lda yozilardi: yangi kod chiqarilganda uni
# oshirish esdan chiqsa, telefon eski nusxani ko‘rsatib turaverardi.
# Endi raqam fayllarning o‘zidan hisoblanadi — fayl o‘zgarsa, raqam ham
# o‘zgaradi. Shuning uchun style.css va app.js ni telefonda BIR YIL
# saqlash xavfsiz: yangi nusxa chiqsa, manzili boshqacha bo‘ladi.
# ==========================================================
_asset_v_cache = None


def _asset_version():
    global _asset_v_cache
    # Mahalliy sinovda fayl tahrirlangani zahoti yangi raqam kerak,
    # serverda esa bir marta hisoblab qo‘yish kifoya (jarayon qayta
    # ishga tushganda o‘zi yangilanadi).
    if _asset_v_cache and os.getenv("DEV_MODE") != "1":
        return _asset_v_cache
    parts = []
    for name in ("app.js", "style.css", "index.html"):
        try:
            st = os.stat(os.path.join(WEBAPP_DIR, name))
            parts.append("%d-%d" % (st.st_size, int(st.st_mtime)))
        except OSError:
            parts.append("0")
    _asset_v_cache = hashlib.sha256("|".join(parts).encode()).hexdigest()[:10]
    return _asset_v_cache


def _no_cache(response):
    """Ilova fayllari har safar yangilanganini tekshirsin.

    Telegram Mini App fayllarni o‘z xotirasida uzoq saqlab qo‘yadi — natijada
    server yangilangan bo‘lsa ham, foydalanuvchi eski nusxani ko‘rib qolardi.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


# Muqova, nishon va maskot rasmlari o‘zgarmaydi — ular uzoq saqlanaveradi
_LONG_CACHE_DIRS = ("/covers/", "/badges/", "/mascots/", "/fonts/", "/uploads/")


@app.after_request
def _apply_cache_rules(response):
    """Kesh qoidalari — Flask o‘zi tarqatadigan fayllarga ham tegishli."""
    path = request.path or "/"
    # Rasmlar uzoq saqlanadi, lekin ular yonidagi ro‘yxat fayli (index.json)
    # o‘zgarib turadi — u har safar tekshirilishi kerak.
    if path.startswith(_LONG_CACHE_DIRS) and not path.endswith(".json"):
        response.headers["Cache-Control"] = "public, max-age=604800"
    elif path.startswith("/api/"):
        _no_cache(response)
    elif path.endswith((".css", ".js")) and request.args.get("v"):
        # Manzilida versiya raqami bor — aynan shu nusxa hech qachon
        # o‘zgarmaydi, shuning uchun telefonda bir yil saqlanaveradi.
        # Yangi kod chiqarilsa raqam o‘zgaradi va yangisi yuklanadi.
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    elif path == "/" or path.endswith((".html", ".js", ".css", ".json")):
        _no_cache(response)
    return response


# Bezak va kod fayllari — ular topilmasa index.html qaytarish MUMKIN EMAS
_ASSET_EXT = (".css", ".js", ".json", ".map", ".png", ".jpg", ".jpeg",
              ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf")


@app.route("/<path:path>")
def serve_static(path):
    full_path = os.path.join(WEBAPP_DIR, path)
    if os.path.isfile(full_path):
        return send_from_directory(WEBAPP_DIR, path)
    # Bezak yoki kod fayli topilmasa — ochiq 404. Ilgari bu yerda ham
    # index.html qaytarilardi: brauzer HTML ni CSS deb o‘qib, ilova
    # butunlay bezaksiz ko‘rinardi va bu javob keshga ham tushib qolardi.
    if path.lower().endswith(_ASSET_EXT):
        return ("Topilmadi: " + path, 404)
    # Qolgan yo‘llar uchun SPA odati: bosh sahifani ochamiz.
    return serve_index()


def run_webapp_server(port: int):
    """main.py / server.py ichidan thread sifatida chaqiriladi."""
    start_summary_worker()
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    run_webapp_server(int(os.getenv("PORT", 8080)))
