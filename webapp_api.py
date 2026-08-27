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
import json
import time
import hmac
import hashlib
import asyncio
import threading
import urllib.parse
from datetime import datetime, date, timedelta

import requests
from flask import Flask, request, jsonify, send_from_directory, g

from config import BOT_TOKEN, OWNER_ID, RECOMMENDED_BOOKS
from database import (
    conn, cursor, get_parent_id, update_streak,
    calculate_and_update_rank, get_child_total_pages,
    get_child_passport_data, generate_admin_stats_text,
    generate_progress_bar
)
import ai_service

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
):
    try:
        cursor.execute(_col_sql)
        conn.commit()
    except Exception:
        pass

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


def get_shelf_books(child_id: int, parent_id: int = None):
    """Kitoblar javoni: rejadagi BARCHA kitoblar, tugatilganlari ham.

    Javon — bu kolleksiya: bola nima yig‘ganini ko‘rsin. Avval hozir
    o‘qilayotganlari (eng ko‘p o‘qilgani birinchi), keyin tugatilganlari.
    """
    q = ("SELECT pb.book_id, pb.title, pb.author, pb.pages_read, pb.total_pages, pb.is_completed "
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
         "total_pages": b[4], "completed": bool(b[5])}
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
    q = ("SELECT pb.book_id, pb.title, pb.author, pb.pages_read, pb.total_pages FROM Plan_Books pb "
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
    return {"id": row[0], "title": row[1], "author": row[2], "pages_read": row[3], "total_pages": row[4]}


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
        "SELECT pb.book_id, pb.title, pb.author, pb.pages_read, pb.total_pages FROM Plan_Books pb "
        "JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
        "WHERE rp.parent_id = ? AND rp.child_id = ? AND pb.is_completed = 0 ORDER BY pb.pages_read DESC",
        (g.user_id, child_id)
    )
    active_books = [
        {"id": b[0], "title": b[1], "author": b[2], "pages_read": b[3], "total_pages": b[4]}
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
    cursor.execute(q, params)
    plans = []
    for plan_id, name, prize, status, cid, plan_type in cursor.fetchall():
        cursor.execute(
            "SELECT book_id, title, author, pages_read, total_pages, is_completed, "
            "mid_test_1_done, mid_test_2_done, final_test_done FROM Plan_Books WHERE plan_id = ?",
            (plan_id,)
        )
        books = [
            {"id": b[0], "title": b[1], "author": b[2], "pages_read": b[3],
             "total_pages": b[4], "completed": bool(b[5]), "mid_test_1_done": bool(b[6]),
             "mid_test_2_done": bool(b[7]), "final_test_done": bool(b[8]),
             "has_voice": has_voice_report(cid, b[0])}
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
    return jsonify({"ok": True, "book_id": book_id, "title": title, "author": author})


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
    return jsonify({"ok": True, "book_id": book_id, "title": title, "author": author})


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
    """5-10 ta sahifa surati asosida AI Savollar banki (test) tuzish."""
    files = request.files.getlist("photos")
    if not files:
        return jsonify({"error": "Kamida 1 ta sahifa rasmi kerak"}), 400
    photos_bytes = [f.read() for f in files]

    questions, raw_json = run_async(ai_service.generate_test_bank_from_photos(photos_bytes))
    with db_lock:
        cursor.execute(
            "INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)",
            (book_id, raw_json)
        )
        conn.commit()
    return jsonify({"ok": True, "count": len(questions)})


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


@app.route("/api/parent/passport/<int(signed=True):child_id>", methods=["GET"])
@require_auth
def parent_child_passport(child_id):
    """'Oylik Kitobxon Pasporti' — kognitiv/nutqiy diagnostika."""
    data = get_child_passport_data(child_id)
    if not data:
        return jsonify({"error": "Farzand topilmadi"}), 404
    return jsonify(data)


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
    Mini App'da buni frontend ?as_child=ID query parametri orqali beradi."""
    as_child = request.args.get("as_child", type=int)
    return as_child or g.user_id


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
        "SELECT pb.book_id, pb.title, pb.author, pb.pages_read, pb.total_pages FROM Plan_Books pb "
        "JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
        "WHERE rp.child_id = ? AND pb.is_completed = 0 ORDER BY pb.pages_read DESC",
        (child_id,)
    )
    active_books = [
        {"id": b[0], "title": b[1], "author": b[2], "pages_read": b[3], "total_pages": b[4]}
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
        "child_note": get_latest_child_note(child_id)
    })


@app.route("/api/child/passport", methods=["GET"])
@require_auth
def child_passport_self():
    """📜 Shaxsiy Pasport — bolaning o‘zi o‘z diagnostikasini ko‘radi."""
    child_id = _resolve_active_child(request)
    data = get_child_passport_data(child_id)
    if not data:
        return jsonify({"error": "Topilmadi"}), 404
    return jsonify(data)


@app.route("/api/child/books", methods=["GET"])
@require_auth
def child_books():
    child_id = _resolve_active_child(request)
    parent_id = get_parent_id(child_id)
    if not parent_id:
        return jsonify({"error": "Ota-onaga ulanmagansiz"}), 400

    cursor.execute(
        "SELECT plan_id, name, prize FROM Reading_Plans WHERE parent_id = ? AND child_id = ? AND status = 'active'",
        (parent_id, child_id)
    )
    plans = []
    for plan_id, name, prize in cursor.fetchall():
        cursor.execute(
            "SELECT book_id, title, author, pages_read, total_pages, is_completed, "
            "mid_test_1_done, mid_test_2_done, final_test_done FROM Plan_Books WHERE plan_id = ?",
            (plan_id,)
        )
        books = [
            {"id": b[0], "title": b[1], "author": b[2], "pages_read": b[3],
             "total_pages": b[4], "completed": bool(b[5]), "mid_test_1_done": bool(b[6]),
             "mid_test_2_done": bool(b[7]), "final_test_done": bool(b[8]),
             "has_voice": has_voice_report(child_id, b[0])}
            for b in cursor.fetchall()
        ]
        if books:
            plans.append({"id": plan_id, "name": name, "prize": prize, "books": books})
    return jsonify(plans)


@app.route("/api/child/book/<int:book_id>", methods=["GET"])
@require_auth
def child_book_detail(book_id):
    child_id = _resolve_active_child(request)
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
    return jsonify({
        "title": row[0], "author": row[1], "pages_read": row[2], "total_pages": row[3],
        "completed": bool(row[4]), "mid_test_1_done": bool(row[5]),
        "mid_test_2_done": bool(row[6]), "final_test_done": bool(row[7]),
        "has_test": has_test, "has_voice": has_voice_report(child_id, book_id)
    })


@app.route("/api/child/book/<int:book_id>/page_photo", methods=["POST"])
@require_auth
def child_submit_page_photo(book_id):
    """Bola o‘qigan sahifasini rasmga olib yuboradi -> AI tekshiradi -> Bilig beriladi."""
    if "photo" not in request.files:
        return jsonify({"error": "Rasm topilmadi"}), 400
    image_bytes = request.files["photo"].read()
    child_id = _resolve_active_child(request)

    ai_result = run_async(ai_service.verify_page_photo(image_bytes))
    if not ai_result.get("is_book_page"):
        return jsonify({"ok": False, "reason": "not_book_page",
                         "message": "Bu kitob sahifasiga o‘xshamayapti. Qaytadan urinib ko‘ring."})

    new_page = int(ai_result.get("page_number", 0))
    if new_page <= 0:
        return jsonify({"ok": False, "reason": "page_unclear",
                         "message": "Sahifa raqami aniq ko‘rinmadi. Sahifa raqamini qo‘lda kiriting."})

    return _apply_page_progress(book_id, child_id, new_page)


@app.route("/api/child/book/<int:book_id>/page_manual", methods=["POST"])
@require_auth
def child_submit_page_manual(book_id):
    """AI orqali emas, sahifa raqamini qo‘lda kiritish (zaxira variant)."""
    data = request.get_json(force=True) or {}
    new_page = int(data.get("page_number", 0))
    child_id = _resolve_active_child(request)
    if new_page <= 0:
        return jsonify({"ok": False, "message": "Sahifa raqamini to‘g‘ri kiriting"}), 400
    return _apply_page_progress(book_id, child_id, new_page)


def _apply_page_progress(book_id, child_id, new_page):
    cursor.execute("SELECT pages_read, title FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Kitob topilmadi"}), 404
    old_pages, book_title = row

    if new_page <= old_pages:
        return jsonify({"ok": False, "reason": "not_progress",
                         "message": f"Siz allaqachon {old_pages}-sahifagacha o‘qigansiz!"})

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

    streak, shield_used = update_streak(child_id)
    rank, total_pages = calculate_and_update_rank(child_id)

    cursor.execute("SELECT balance_coins FROM Users WHERE user_id = ?", (child_id,))
    balance = cursor.fetchone()[0]

    return jsonify({
        "ok": True, "book_title": book_title, "new_page": new_page,
        "earned_bilig": max(0, earned_bilig), "balance": balance,
        "streak": streak, "shield_used": shield_used, "rank": rank, "total_pages": total_pages
    })


@app.route("/api/child/book/<int:book_id>/voice", methods=["POST"])
@require_auth
def child_submit_voice(book_id):
    """Bola audio xulosa yuboradi -> AI Ustoz tahlil qiladi -> bonus Bilig + ota-onaga hisobot."""
    if "audio" not in request.files:
        return jsonify({"error": "Audio topilmadi"}), 400
    audio_bytes = request.files["audio"].read()
    child_id = _resolve_active_child(request)

    cursor.execute("SELECT title FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    book_title = row[0] if row else "Kitob"

    cursor.execute(
        "SELECT fl.child_age FROM Family_Link fl WHERE fl.child_id = ?", (child_id,)
    )
    age_row = cursor.fetchone()
    age = age_row[0] if age_row and age_row[0] else 10

    result = run_async(ai_service.evaluate_voice_summary(audio_bytes, age, book_title))

    bonus = int(result.get("bonus_bilig", 0))
    diag = result.get("diagnostic_scores", {})
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
        conn.commit()

    parent_id = get_parent_id(child_id)
    if parent_id:
        pr = result.get("parent_report", {})
        send_telegram_message(
            parent_id,
            f"🎙 <b>{book_title}</b> bo‘yicha farzandingizning ovozli hisobotini AI tahlil qildi!\n\n"
            f"📌 {pr.get('summary', '')}\n\n✅ {pr.get('strengths', '')}\n🌱 {pr.get('weaknesses', '')}\n\n"
            f"{pr.get('conversation_topic', '')}"
        )

    return jsonify({
        "ok": True, "bonus_bilig": bonus,
        "feedback": result.get("child_feedback", ""),
        "give_badge": bool(result.get("give_badge", False))
    })


@app.route("/api/child/book/<int:book_id>/test", methods=["GET"])
@require_auth
def child_get_test(book_id):
    """Test savollarini olish (to‘g‘ri javob YASHIRIB yuboriladi)."""
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
        for q in questions
    ]
    return jsonify(safe_questions)


@app.route("/api/child/book/<int:book_id>/test/submit", methods=["POST"])
@require_auth
def child_submit_test(book_id):
    """Test javoblarini tekshirish, ballash va Bilig berish."""
    data = request.get_json(force=True) or {}
    stage = data.get("stage", "mid_test_1")  # mid_test_1 | mid_test_2 | final_test
    answers = data.get("answers", {})  # {"1": "A) ...", ...}
    child_id = _resolve_active_child(request)

    cursor.execute("SELECT questions_json FROM Book_Tests WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row:
        return jsonify({"error": "Test topilmadi"}), 404
    questions = json.loads(row[0])

    correct = 0
    for q in questions:
        qid = str(q.get("id"))
        if qid in answers and answers[qid] == q.get("answer"):
            correct += 1
    total = len(questions) if questions else 1
    percent = round((correct / total) * 100)
    earned = max(1, round(correct / 2))  # har 2 ta to‘g‘ri javob uchun 1 Bilig (kamida 1)

    column_map = {
        "mid_test_1": "mid_test_1_done", "mid_test_2": "mid_test_2_done", "final_test": "final_test_done"
    }
    column = column_map.get(stage, "mid_test_1_done")

    with db_lock:
        cursor.execute(f"UPDATE Plan_Books SET {column} = 1 WHERE book_id = ?", (book_id,))
        if stage == "final_test":
            cursor.execute("UPDATE Plan_Books SET is_completed = 1 WHERE book_id = ?", (book_id,))
        cursor.execute(
            "UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (earned, child_id)
        )
        conn.commit()

    return jsonify({"ok": True, "correct": correct, "total": total, "percent": percent, "earned_bilig": earned})


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
    return send_from_directory(WEBAPP_DIR, "index.html")


def _no_cache(response):
    """Ilova fayllari har safar yangilanganini tekshirsin.

    Telegram Mini App fayllarni o‘z xotirasida uzoq saqlab qo‘yadi — natijada
    server yangilangan bo‘lsa ham, foydalanuvchi eski nusxani ko‘rib qolardi.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


# Muqova, nishon va maskot rasmlari o‘zgarmaydi — ular uzoq saqlanaveradi
_LONG_CACHE_DIRS = ("/covers/", "/badges/", "/mascots/")


@app.after_request
def _apply_cache_rules(response):
    """Kesh qoidalari — Flask o‘zi tarqatadigan fayllarga ham tegishli."""
    path = request.path or "/"
    if path.startswith(_LONG_CACHE_DIRS):
        response.headers["Cache-Control"] = "public, max-age=604800"
    elif path.startswith("/api/"):
        _no_cache(response)
    elif path == "/" or path.endswith((".html", ".js", ".css", ".json")):
        _no_cache(response)
    return response


@app.route("/<path:path>")
def serve_static(path):
    # /api/... bo‘lmagan, lekin haqiqatda mavjud bo‘lmagan fayl so‘ralsa,
    # SPA odatiga ko‘ra bosh sahifaga (index.html) qaytaramiz — shunda
    # brauzer manzil satrida boshqa yo‘l bo‘lsa ham ilova ochiladi.
    full_path = os.path.join(WEBAPP_DIR, path)
    if os.path.isfile(full_path):
        return send_from_directory(WEBAPP_DIR, path)
    return serve_index()


def run_webapp_server(port: int):
    """main.py / server.py ichidan thread sifatida chaqiriladi."""
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)


if __name__ == "__main__":
    run_webapp_server(int(os.getenv("PORT", 8080)))
