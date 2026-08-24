import asyncio
import threading
from datetime import datetime
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import init_db, cursor
from server import run_dummy_server
from handlers import main_router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Routerlarni ulash
dp.include_router(main_router)

# ==========================================
# KUNLIK AVTOMATIK SCHEDULER
# ==========================================
async def daily_reminder_scheduler(bot: Bot):
    while True:
        try:
            now = datetime.now()
            if now.hour == 19:
                today_str = now.strftime("%Y-%m-%d")
                cursor.execute("SELECT user_id, name, streak_days, last_read_date FROM Users WHERE role = 'child'")
                children = cursor.fetchall()
                for c in children:
                    c_id, c_name, streak, last_read = c
                    if last_read != today_str:
                        msg = (
                            f"👋 <b>Salom, Qahramon {c_name}!</b> 🦸‍♂️\n\n"
                            f"📚 Bugun hali kitob o'qimadingizmi? Kitoblar sizni kutmoqda!\n"
                            f"🔥 <b>Uzluksiz kunlaringiz (Streak):</b> {streak} kun!\n\n"
                            f"Bugun ham kamida 2 bet o'qib, olovni 🔥 o'chirmang! ✨"
                        )
                        try:
                            await bot.send_message(c_id, msg, parse_mode="HTML")
                        except Exception:
                            pass
                await asyncio.sleep(3600)
            else:
                await asyncio.sleep(1800)
        except Exception as e:
            print(f"Scheduler error: {e}")
            await asyncio.sleep(300)

# ==========================================
# BOTNI ISHGA TUSHIRISH
# ==========================================
async def main():
    init_db()
    threading.Thread(target=run_dummy_server, daemon=True).start()
    asyncio.create_task(daily_reminder_scheduler(bot))
    print("🚀 Bilig AI moduli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
