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
# 1. MA'LUMOTLAR BAZASI (SQLITE)
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

# ==========================================
# 2. DUMMY HTTP SERVER
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args): pass

class ReusableTCPServer(HTTPServer):
    allow_reuse_address = True

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = ReusableTCPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ==========================================
# 3. MENYULAR (KEYBOARDS)
# ==========================================
def get_parent_keyboard():
    kb = [
        [KeyboardButton(text="📊 Farzandim natijalari")],
        [KeyboardButton(text="⚙️ Koin kursi"), KeyboardButton(text="🎁 Mukofotlar")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_child_keyboard():
    kb = [
        [KeyboardButton(text="📖 Kitob o'qish")],
        [KeyboardButton(text="👤 Mening Qahramonim"), KeyboardButton(text="🏆 Reyting")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ==========================================
# 4. FSM (HOLATLAR)
# ==========================================
class Registration(StatesGroup):
    waiting_for_parent_code = State()

# ==========================================
# 5. TELEGRAM BOT MANTIG'I
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    
    cursor.execute("SELECT role FROM Users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if user and user[0] == 'parent':
        await message.answer(
            "<b>Asosiy menyuga xush kelibsiz!</b> 👨‍👩‍👦\n\n"
            "👇 <i>Quyidagi tugmalar orqali botni boshqaring:</i>\n"
            "<b>📊 Farzandim natijalari</b> - O'qilgan kitoblar va ballarni ko'rish.\n"
            "<b>⚙️ Koin kursi</b> - 1 ta BiligCoin necha so'mga tengligini belgilash.\n"
            "<b>🎁 Mukofotlar</b> - Farzandingiz Koinlarga sotib olishi mumkin bo'lgan sovg'alarni qo'shish.",
            parse_mode="HTML", reply_markup=get_parent_keyboard()
        )
        return
    elif user and user[0] == 'child':
        await message.answer(
            "<b>Asosiy menyuga xush kelibsiz, Qahramon!</b> 🦸‍♂️🦸‍♀️\n\n"
            "👇 <i>Quyidagi tugmalardan birini tanla:</i>\n"
            "<b>📖 Kitob o'qish</b> - O'qishni boshlash va Koin ishlash.\n"
            "<b>👤 Mening Qahramonim</b> - Yig'gan ballaring va Koinlaringni ko'rish.\n"
            "<b>🏆 Reyting</b> - Boshqa o'quvchilar bilan bellashish.",
            parse_mode="HTML", reply_markup=get_child_keyboard()
        )
        return

    cursor.execute("INSERT OR IGNORE INTO Users (user_id, name) VALUES (?, ?)", 
                   (message.from_user.id, message.from_user.full_name))
    conn.commit()
    
    kb = [
        [KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")],
        [KeyboardButton(text="👦👧 Men O'quvchiman")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    await message.answer(
        "👋 <b>Bilig AI - Aqlli kitobxonlar dunyosiga xush kelibsiz!</b>\n\n"
        "Bu bot orqali kitob o'qish qiziqarli o'yinga aylanadi. Bolalar kitob o'qib virtual tangalar (Koinlar) yig'adi, ota-onalar esa bu tangalarni haqiqiy sovg'alarga almashtirib berishadi.\n\n"
        "<i>Iltimos, kim bo'lib kirmoqchi ekanligingizni tanlang:</i>", 
        parse_mode="HTML", reply_markup=keyboard
    )

@dp.message(F.text == "👨‍👩‍👦 Men Ota-onaman")
async def parent_handler(message: types.Message):
    cursor.execute("UPDATE Users SET role = 'parent' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    
    parent_code = f"BLG-{str(message.from_user.id)[-4:]}"
    
    instruction_text = (
        "🎉 <b>Tabriklaymiz! Siz Ota-ona sifatida ro'yxatdan o'tdingiz!</b>\n\n"
        "Sizning asosiy vazifangiz — farzandingizga motivatsiya berish. \n"
        "<b>Nima qilish kerak?</b>\n"
        "1️⃣ <b>Koin kursi:</b> 1 ta BiligCoin necha pulga tengligini belgilang.\n"
        "2️⃣ <b>Mukofotlar:</b> Farzandingiz qanday sovg'alar yutib olishi mumkinligini kiriting (Masalan: 'Parkka borish' - 100 Koin).\n"
        "3️⃣ <b>Tasdiqlash:</b> Farzandingiz kitob o'qiganini tasdiqlang va unga Koin bering.\n\n"
        f"Farzandingiz botga ulanishi uchun unga shu kodni bering: <b>{parent_code}</b>"
    )
    
    await message.answer(instruction_text, parse_mode="HTML", reply_markup=get_parent_keyboard())

@dp.message(F.text == "👦👧 Men O'quvchiman")
async def child_handler(message: types.Message, state: FSMContext):
    cursor.execute("UPDATE Users SET role = 'child' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    
    await message.answer(
        "Siz O'quvchi sifatida ro'yxatdan o'tdingiz! 👦👧\n\n"
        "Iltimos, ota-onangiz bergan kodni kiriting (masalan, BLG-1234):", 
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Registration.waiting_for_parent_code)

@dp.message(Registration.waiting_for_parent_code)
async def process_parent_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    
    if not code.startswith("BLG-"):
        await message.answer("Kod xato formatda! 'BLG-1234' ko'rinishida kiriting.")
        return
        
    parent_suffix = code.replace("BLG-", "")
    cursor.execute("SELECT user_id FROM Users WHERE role = 'parent' AND CAST(user_id AS TEXT) LIKE ?", ('%' + parent_suffix,))
    parent = cursor.fetchone()
    
    if parent:
        parent_id = parent[0]
        child_id = message.from_user.id
        
        try:
            cursor.execute("INSERT INTO Family_Link (parent_id, child_id) VALUES (?, ?)", (parent_id, child_id))
            conn.commit()
            
            child_instruction = (
                "🎉 <b>Tabriklaymiz! Ota-onangiz bilan bog'landingiz!</b>\n\n"
                "Seni <b>Bilig AI</b> qahramonlar dunyosi kutmoqda! 🦸‍♂️🦸‍♀️\n\n"
                "👇 <b>Qanday qilib tanga (Koin) ishlash mumkin?</b>\n"
                "1️⃣ <b>📖 Kitob o'qish</b> tugmasini bos va o'qiyotgan kitobingni rasmga olib yubor.\n"
                "2️⃣ O'qishni tugatgach, yana rasm yubor.\n"
                "3️⃣ Ota-onang tasdiqlagach, sen Koin (🪙) ishlaysan!\n\n"
                "Yig'ilgan Koinlarni ota-onangdan haqiqiy sovg'alarga almashtirib olishing mumkin! Qani, o'qishni boshladikmi?"
            )
            
            await message.answer(child_instruction, parse_mode="HTML", reply_markup=get_child_keyboard())
            await bot.send_message(parent_id, f"Farzandingiz ({message.from_user.full_name}) profilingizga ulandi! ✅\nEndi u kitob o'qishni boshlashi mumkin.")
            
        except sqlite3.IntegrityError:
            await message.answer("Siz allaqachon bu ota-onaga ulangansiz!", reply_markup=get_child_keyboard())
            
        await state.clear()
    else:
        await message.answer("Bunday kodga ega ota-ona topilmadi. Qaytadan kiriting:")

# ==========================================
# 6. ASOSIY ISHGA TUSHIRISH FUNKSIYASI
# ==========================================
async def main():
    init_db()
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Telegram bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
