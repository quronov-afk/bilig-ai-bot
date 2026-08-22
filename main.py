import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

# Render'dan Tokenni olamiz
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# /start bosilganda ishlaydigan funksiya
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    # Tugmalarni yaratamiz
    kb = [
        [KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")],
        [KeyboardButton(text="👦👧 Men O'quvchiman")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer("Bilig AI - Aqlli kitobxonlar dunyosiga xush kelibsiz!\nKim bo'lib kirmoqchisiz?", reply_markup=keyboard)

# Render uchun soxta veb-server (Bot o'chib qolmasligi uchun)
async def handle(request):
    return web.Response(text="Bilig AI Bot ishlayapti!")

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Botni ishga tushirish
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
