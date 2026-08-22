import os
import sqlite3
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ==========================================
# 1. MA'LUMOTLAR BAZASI (SQLITE) SOZLAMALARI
# ==========================================
db_path = "/var/data/bot_base.db" if os.path.exists("/var/data") else "bot_base.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

def init_db():
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
    def log_message(self, format, *args):
        pass

class ReusableTCPServer(HTTPServer):
    allow_reuse_address = True

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = ReusableTCPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ==========================================
# 3. FSM (HOLATLAR) - Bot kutib turishi uchun
# ==========================================
class Registration(StatesGroup):
    waiting_for_parent_code = State()

# ==========================================
# 4. TELEGRAM BOT MANTIG'I
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear() # Har ehtimolga qarshi eski holatlarni tozalaymiz
    cursor.execute("INSERT OR IGNORE INTO Users (user_id, name) VALUES (?, ?)", 
                   (message.from_user.id, message.from_user.full_name))
    conn.commit()
    
    kb = [
        [KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")],
        [KeyboardButton(text="👦👧 Men O'quvchiman")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer("Bilig AI - Aqlli kitobxonlar dunyosiga xush kelibsiz!\nKim bo'lib kirmoqchisiz?", reply_markup=keyboard)

@dp.message(F.text == "👨‍👩‍👦 Men Ota-onaman")
async def parent_handler(message: types.Message):
    cursor.execute("UPDATE Users SET role = 'parent' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    
    parent_code = f"BLG-{str(message.from_user.id)[-4:]}"
    await message.answer(f"Siz Ota-ona sifatida ro'yxatdan o'tdingiz! ✅\n\nFarzandingiz botga kirganda kiritishi uchun kodingiz: <b>{parent_code}</b>", parse_mode="HTML")

@dp.message(F.text == "👦👧 Men O'quvchiman")
async def child_handler(message: types.Message, state: FSMContext):
    cursor.execute("UPDATE Users SET role = 'child' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    
    await message.answer("Siz O'quvchi sifatida ro'yxatdan o'tdingiz! 👦👧\n\nIltimos, ota-onangiz bergan kodni kiriting (masalan, BLG-1234):")
    # Bot endi boladan kod kutish rejimiga o'tadi
    await state.set_state(Registration.waiting_for_parent_code)

# Bola kodni yozganda ishlaydigan funksiya
@dp.message(Registration.waiting_for_parent_code)
async def process_parent_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    
    if not code.startswith("BLG-"):
        await message.answer("Kod xato formatda! Iltimos, 'BLG-1234' ko'rinishidagi kodni kiriting.")
        return
        
    parent_suffix = code.replace("BLG-", "")
    
    # Bazadan shu kodga ega ota-onani qidiramiz
    cursor.execute("SELECT user_id FROM Users WHERE role = 'parent' AND CAST(user_id AS TEXT) LIKE ?", ('%' + parent_suffix,))
    parent = cursor.fetchone()
    
    if parent:
        parent_id = parent[0]
        child_id = message.from_user.id
        
        try:
            # Ota-ona va bolani Family_Link jadvaliga qo'shamiz
            cursor.execute("INSERT INTO Family_Link (parent_id, child_id) VALUES (?, ?)", (parent_id, child_id))
            conn.commit()
            
            await message.answer("Tabriklaymiz! Ota-onangiz bilan muvaffaqiyatli bog'landingiz! 🎉\n\nEndi kitob o'qishni boshlashingiz mumkin.")
            
            # Ota-onaga xabar yuboramiz
            await bot.send_message(parent_id, f"Farzandingiz ({message.from_user.full_name}) profilingizga muvaffaqiyatli ulandi! ✅")
            
        except sqlite3.IntegrityError:
            await message.answer("Siz allaqachon bu ota-onaga ulangansiz!")
            
        # Kutish rejimini o'chiramiz
        await state.clear()
    else:
        await message.answer("Bunday kodga ega ota-ona topilmadi. Kodingizni tekshirib, qaytadan kiriting:")

# ==========================================
# 5. ASOSIY ISHGA TUSHIRISH FUNKSIYASI
# ==========================================
async def main():
    init_db()
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Telegram bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
