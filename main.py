import os
import sqlite3
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ==========================================
# 1. MA'LUMOTLAR BAZASI (SQLITE) SOZLAMALARI
# ==========================================
# Render Persistent Disk uchun yo'l
db_path = "/var/data/bot_base.db" if os.path.exists("/var/data") else "bot_base.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

def init_db():
    """Bot ishga tushganda kerakli jadvallarni yaratish"""
    # Foydalanuvchilar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY,
            role TEXT,
            name TEXT,
            balance_coins INTEGER DEFAULT 0,
            total_xp INTEGER DEFAULT 0,
            streak_days INTEGER DEFAULT 0
        )
    ''')
    # Oila (Ota-ona va bola) bog'lanish jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Family_Link (
            parent_id INTEGER,
            child_id INTEGER,
            coin_rate INTEGER DEFAULT 500,
            mutolaa_id TEXT,
            UNIQUE(parent_id, child_id)
        )
    ''')
    conn.commit()
    print(f"Ma'lumotlar bazasi ulandi: {db_path}")

# ==========================================
# 2. DUMMY HTTP SERVER (RENDER UCHUN)
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
        
    # Konsolni ortiqcha loglar bilan to'ldirmaslik uchun
    def log_message(self, format, *args):
        pass

class ReusableTCPServer(HTTPServer):
    allow_reuse_address = True

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = ReusableTCPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"Dummy Web Server {port}-portda ishga tushdi...")
    server.serve_forever()

# ==========================================
# 3. TELEGRAM BOT MANTIG'I
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    # Foydalanuvchini bazaga qo'shish (agar yo'q bo'lsa)
    cursor.execute("INSERT OR IGNORE INTO Users (user_id, name) VALUES (?, ?)", 
                   (message.from_user.id, message.from_user.full_name))
    conn.commit()
    
    # Tugmalarni yaratish
    kb = [
        [KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")],
        [KeyboardButton(text="👦👧 Men O'quvchiman")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer("Bilig AI - Aqlli kitobxonlar dunyosiga xush kelibsiz!\nKim bo'lib kirmoqchisiz?", reply_markup=keyboard)

@dp.message(F.text == "👨‍👩‍👦 Men Ota-onaman")
async def parent_handler(message: types.Message):
    # Rolni yangilash
    cursor.execute("UPDATE Users SET role = 'parent' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    
    # Ota-onaga ulanish kodini berish (ID ning oxirgi 4 ta raqami)
    parent_code = f"BLG-{str(message.from_user.id)[-4:]}"
    await message.answer(f"Siz Ota-ona sifatida ro'yxatdan o'tdingiz! ✅\n\nFarzandingiz botga kirganda kiritishi uchun kodingiz: <b>{parent_code}</b>", parse_mode="HTML")

@dp.message(F.text == "👦👧 Men O'quvchiman")
async def child_handler(message: types.Message):
    # Rolni yangilash
    cursor.execute("UPDATE Users SET role = 'child' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    
    await message.answer("Siz O'quvchi sifatida ro'yxatdan o'tdingiz! 👦👧\n\nIltimos, ota-onangiz bergan kodni kiriting:")

# ==========================================
# 4. ASOSIY ISHGA TUSHIRISH FUNKSIYASI
# ==========================================
async def main():
    # 1. Bazani tayyorlash
    init_db()
    
    # 2. Render uchun Dummy Serverni orqa fonda (Thread) ishga tushirish
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    # 3. Botni ishga tushirish
    print("Telegram bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
