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
# AQLLI KUNLIK SCHEDULER & PEDAGOGIK TURTKI (NUDGE)
# ==========================================
async def daily_reminder_scheduler(bot: Bot):
    while True:
        try:
            now = datetime.now()
            # Har kuni kechki soat 19:30 da tekshiradi
            if now.hour == 19 and now.minute >= 30:
                today_str = now.strftime("%Y-%m-%d")
                day_before_yesterday = (now - timedelta(days=2)).strftime("%Y-%m-%d")

                cursor.execute("SELECT user_id, name, streak_days, last_read_date, rank_title FROM Users WHERE role = 'child' AND is_approved = 1")
                children = cursor.fetchall()

                for c in children:
                    c_id, c_name, streak, last_read, rank = c
                    
                    # 1. Bolaga eslatma (Agar bugun hali o'qimagan bo'lsa)
                    if last_read != today_str:
                        motivation = random.choice(REMINDER_MESSAGES)
                        msg = (
                            f"👋 <b>Salom, {c_name}!</b> 🦸‍♂️\n"
                            f"🎖 Darajangiz: <b>{rank}</b>\n\n"
                            f"{motivation}\n\n"
                            f"🔥 <b>Uzluksiz kunlaringiz (Streak):</b> {streak} kun!\n"
                            f"Bugun ham mutolaa qilib, olovingizni saqlab qoling! ⚡️"
                        )
                        try:
                            await bot.send_message(c_id, msg, parse_mode="HTML")
                        except Exception:
                            pass

                    # 2. Ota-onaga "Yumshoq pedagogik turtki" (Ketma-ket 2 kun o'qimasa)
                    if last_read and last_read <= day_before_yesterday:
                        parent_id = get_parent_id(c_id)
                        if parent_id:
                            parent_nudge = (
                                f"💡 <b>Farzand tarbiyasida kichik eslatma</b>\n\n"
                                f"Hurmatli ota-ona! Farzandingiz <b>{c_name}</b> oxirgi 2 kunda mutolaa qilmadi.\n\n"
                                f"🌱 <i>Pedagogik tavsiya: Farzandingiz bilan birgalikda 10 daqiqa kitob o‘qish yoki unga kitobdagi qiziq voqeani aytib berish orqali uning mutolaa ishtiyoqini osonlikcha qayta yoqishingiz mumkin.</i>"
                            )
                            try:
                                await bot.send_message(parent_id, parent_nudge, parse_mode="HTML")
                            except Exception:
                                pass

                # Bir kunda faqat bir marta yuborilishi uchun 1 soat uxlaydi
                await asyncio.sleep(3600)
            else:
                await asyncio.sleep(1800)
        except Exception as e:
            print(f"Scheduler xatoligi: {e}")
            await asyncio.sleep(300)

# ==========================================
# BOTNI ISHGA TUSHIRISH
# ==========================================
async def main():
    init_db()
    threading.Thread(target=run_dummy_server, daemon=True).start()
    asyncio.create_task(daily_reminder_scheduler(bot))
    print("🚀 Bilig AI to‘liq pedagogik tizimi muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
