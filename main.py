import asyncio
import random
import threading
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db, conn, cursor, get_parent_id
from server import run_dummy_server
from handlers import main_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# BIR MARTALIK TUZATISH (2026-09-13) — sahifa raqami cheksiz qabul
# qilingan eski xato (webapp_api.py'da tuzatildi) natijasida bir martada
# 99 betdan ko‘p (millionlab ham) yozilgan soxta yozuvlar. Ega tasdiqlab,
# o‘chirishga ruxsat berdi. `Seed_State` belgisi orqali faqat BIR MARTA
# ishlaydi — server qayta ko‘tarilganda TAKROR ishlamaydi.
# ==========================================
_STEP_MAX = 99
_BOOK_PAGES_MAX = 999


async def fix_corrupt_reading_logs_once():
    try:
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS Seed_State (
                name TEXT PRIMARY KEY, stamp TEXT, updated_at TEXT
            )""")
        conn.commit()
        cursor.execute("SELECT stamp FROM Seed_State WHERE name = 'fix_bad_pages_v2'")
        if cursor.fetchone():
            return
    except Exception:
        return

    try:
        # Namoyish bolalari (manfiy raqamli) tegilmaydi — ularda bir martada 40 betdan oshmaydi.
        cursor.execute(
            "SELECT log_id, child_id, book_id, pages_added, created_at FROM Reading_Logs "
            "WHERE pages_added > ? AND child_id > 0 ORDER BY log_id", (_STEP_MAX,))
        bad = cursor.fetchall()

        # Avval hammasini hisoblaymiz (hech narsa o‘chmasdan) — Bilig aynan
        # yozilgan paytdagi kabi chiqsin va hamyon tarixidagi yozuv topilsin.
        plan = []
        for log_id, child_id, book_id, pages_added, created_at in bad:
            cursor.execute(
                "SELECT COALESCE(SUM(pages_added), 0) FROM Reading_Logs "
                "WHERE book_id = ? AND log_id < ?", (book_id, log_id))
            old_pages = cursor.fetchone()[0]
            wrong_bilig = ((old_pages + pages_added) // 5) - (old_pages // 5)
            plan.append((log_id, child_id, book_id, pages_added, created_at, wrong_bilig))

        books = set()
        for log_id, child_id, book_id, pages_added, created_at, wrong_bilig in plan:
            cursor.execute(
                "UPDATE Users SET balance_coins = MAX(0, balance_coins - ?), "
                "total_xp = MAX(0, total_xp - ?) WHERE user_id = ?",
                (wrong_bilig, pages_added, child_id))
            cursor.execute(
                "DELETE FROM Coin_Ledger WHERE entry_id = ("
                "SELECT entry_id FROM Coin_Ledger WHERE child_id = ? AND kind = 'pages' "
                "AND amount = ? AND substr(replace(created_at, 'T', ' '), 1, 16) = substr(?, 1, 16) "
                "LIMIT 1)", (child_id, wrong_bilig, created_at))
            cursor.execute("DELETE FROM Reading_Logs WHERE log_id = ?", (log_id,))
            books.add(book_id)

        for book_id in books:
            cursor.execute(
                "UPDATE Plan_Books SET pages_read = (SELECT COALESCE(SUM(pages_added), 0) "
                "FROM Reading_Logs WHERE book_id = ?) WHERE book_id = ?", (book_id, book_id))
        cursor.execute("UPDATE Plan_Books SET total_pages = 0 WHERE total_pages > ?",
                       (_BOOK_PAGES_MAX,))
        conn.commit()
        cursor.execute(
            "INSERT OR REPLACE INTO Seed_State (name, stamp, updated_at) VALUES (?, ?, ?)",
            ("fix_bad_pages_v2", "done", datetime.now().isoformat()))
        conn.commit()
        print(f"Soxta sahifa yozuvlari tozalandi: {len(plan)} ta, {len(books)} ta kitob")
    except Exception as e:
        print("Tuzatishda xato:", e)


# Routerlarni ulash
dp.include_router(main_router)

# Turfa xil motivatsion xabarlar bazasi
REMINDER_MESSAGES = [
    "📚 Bugun hali kitob o‘qimadingizmi? Qahramonlar sizning davomingizni kutmoqda!",
    "✨ Bilim — bu eng qudratli kuch! Bugun kamida 2 bet o‘qib, o‘z kuchingizni oshiring!",
    "🚀 Har bir o‘qilgan sahifa sizni yangi unvonlar sari yetaklaydi. Olovni 🔥 o‘chirmang!",
    "🧠 Bugun kitob bilan 15 daqiqa o‘tkazishga nima deysiz? Yangi Biliglar sizni kutmoqda!"
]

# ==========================================
# KUNLIK ESLATMA — O‘CHIRILDI (2026-09-03)
# ------------------------------------------
# Bu yerda har kuni 19:30 da ishlaydigan eslatma bor edi: har bir
# bolaga «bugun o‘qimading» xabari, ota-onaga esa «farzandingiz 2 kun
# o‘qimadi» degan turtki. Ega e'tiroz bildirdi: «yana botdan xabar
# kelib jonga tegyapti».
#
# Ikki sabab bilan butunlay olib tashlandi:
#  1. TAKROR — bolaning parvozi haqidagi ogohlantirish `webapp_api.py`
#     dagi `check_streak_at_risk()` da allaqachon bor va u to‘g‘ri
#     qoidalar bilan ishlaydi: kuniga bir marta, tunda jim, chegara bilan.
#  2. QOIDA — ega qarori bo‘yicha botga faqat TO‘RT tur xabar boradi:
#     ota-onaga kitob tugatilgani va uch kunlik hisobot, bolaga parvoz
#     ogohlantirishi va guruhdan olqish. Ota-onaga kunlik turtki
#     yuborish bu ro‘yxatda yo‘q.
#
# Yangi xabar qo‘shish kerak bo‘lsa — `webapp_api.send_telegram_message`
# orqali qo‘shiladi, u yerda tunki jimlik va kunlik chegara ishlaydi.
# ==========================================

# ==========================================
# BOTNI ISHGA TUSHIRISH
# ==========================================
async def main():
    init_db()
    threading.Thread(target=run_dummy_server, daemon=True).start()
    await fix_corrupt_reading_logs_once()
    print("🚀 Bilig AI to‘liq pedagogik tizimi muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
