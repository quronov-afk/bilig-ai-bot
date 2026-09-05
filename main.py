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
    print("🚀 Bilig AI to‘liq pedagogik tizimi muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
