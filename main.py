import os
import sqlite3
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
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
    # Ota-onalar uchun koin kursini saqlash ustunini qo'shamiz (agar yo'q bo'lsa)
    try:
        cursor.execute("ALTER TABLE Users ADD COLUMN coin_rate INTEGER DEFAULT 500")
    except sqlite3.OperationalError:
        pass # Ustun allaqachon bor

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Family_Link (
            parent_id INTEGER,
            child_id INTEGER,
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

# Koin kursi uchun Inline tugmalar (Xabar tagida chiqadi)
def get_coin_rate_inline_keyboard():
    kb = [
        [InlineKeyboardButton(text="🪙 500 so'm", callback_data="rate_500"),
         InlineKeyboardButton(text="🪙 1,000 so'm", callback_data="rate_1000")],
        [InlineKeyboardButton(text="🪙 5,000 so'm", callback_data="rate_5000"),
         InlineKeyboardButton(text="🪙 10,000 so'm", callback_data="rate_10000")],
        [InlineKeyboardButton(text="✍️ Boshqa summa kiritish", callback_data="rate_custom")],
        [InlineKeyboardButton(text="🚫 Pul bilan rag'batlantirmaslik", callback_data="rate_0")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==========================================
# 4. FSM (HOLATLAR)
# ==========================================
class Registration(StatesGroup):
    waiting_for_parent_code = State()

class ParentSettings(StatesGroup):
    waiting_for_custom_rate = State()

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
            "👇 <i>Quyidagi tugmalar orqali botni boshqaring:</i>",
            parse_mode="HTML", reply_markup=get_parent_keyboard()
        )
        return
    elif user and user[0] == 'child':
        await message.answer(
            "<b>Asosiy menyuga xush kelibsiz, Qahramon!</b> 🦸‍♂️🦸‍♀️\n\n"
            "👇 <i>Quyidagi tugmalardan birini tanla:</i>",
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
        "<i>Iltimos, kim bo'lib kirmoqchi ekanligingizni tanlang:</i>", 
        parse_mode="HTML", reply_markup=keyboard
    )

@dp.message(F.text == "👨‍👩‍👦 Men Ota-onaman")
async def parent_handler(message: types.Message):
    cursor.execute("UPDATE Users SET role = 'parent' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    parent_code = f"BLG-{str(message.from_user.id)[-4:]}"
    await message.answer(f"Siz Ota-ona sifatida ro'yxatdan o'tdingiz! ✅\nFarzandingiz ulanishi uchun kodingiz: <b>{parent_code}</b>", parse_mode="HTML", reply_markup=get_parent_keyboard())

@dp.message(F.text == "👦👧 Men O'quvchiman")
async def child_handler(message: types.Message, state: FSMContext):
    cursor.execute("UPDATE Users SET role = 'child' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer("Iltimos, ota-onangiz bergan kodni kiriting (masalan, BLG-1234):", reply_markup=types.ReplyKeyboardRemove())
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
        try:
            cursor.execute("INSERT INTO Family_Link (parent_id, child_id) VALUES (?, ?)", (parent[0], message.from_user.id))
            conn.commit()
            await message.answer("Tabriklaymiz! Ota-onangiz bilan bog'landingiz! 🎉", reply_markup=get_child_keyboard())
            await bot.send_message(parent[0], f"Farzandingiz ({message.from_user.full_name}) profilingizga ulandi! ✅")
        except sqlite3.IntegrityError:
            await message.answer("Siz allaqachon bu ota-onaga ulangansiz!", reply_markup=get_child_keyboard())
        await state.clear()
    else:
        await message.answer("Bunday kodga ega ota-ona topilmadi. Qaytadan kiriting:")

# ==========================================
# KOIN KURSI MANTIG'I (YANGI QO'SHILGAN QISM)
# ==========================================
@dp.message(F.text == "⚙️ Koin kursi")
async def koin_kursi_handler(message: types.Message):
    text = (
        "⚙️ <b>Koin kursini belgilash</b>\n\n"
        "Farzandingiz o'qigan har bir kitobi uchun <b>BiligCoin (🪙)</b> ishlab topadi. "
        "Siz 1 ta BiligCoin necha so'mga teng ekanligini belgilashingiz mumkin.\n\n"
        "<i>Agar farzandingizni pul bilan rag'batlantirishni xohlamasangiz, eng pastdagi tugmani tanlang. Shunda u faqat reyting va nishonlar uchun o'qiydi.</i>\n\n"
        "👇 <b>Quyidagilardan birini tanlang:</b>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_coin_rate_inline_keyboard())

@dp.callback_query(F.data.startswith("rate_"))
async def process_rate_callback(callback: types.CallbackQuery, state: FSMContext):
    rate_val = callback.data.split("_")[1]
    
    # Agar "Boshqa summa" bosilsa
    if rate_val == "custom":
        await callback.message.edit_text("✍️ <b>Iltimos, 1 ta BiligCoin uchun summani raqamlarda kiriting:</b>\n<i>(Masalan: 2000)</i>", parse_mode="HTML")
        await state.set_state(ParentSettings.waiting_for_custom_rate)
        return
        
    rate = int(rate_val)
    # Bazaga saqlash
    cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, callback.from_user.id))
    conn.commit()
    
    if rate == 0:
        await callback.message.edit_text("✅ <b>Siz pul bilan rag'batlantirmaslik rejimini tanladingiz!</b>\n\nEndi farzandingiz faqat bilim, reyting va maxsus nishonlar uchun o'qiydi. Bu juda zo'r tanlov! 🧠", parse_mode="HTML")
    else:
        await callback.message.edit_text(f"✅ <b>Koin kursi muvaffaqiyatli o'rnatildi!</b>\n\nEndi 1 BiligCoin = {rate} so'm.", parse_mode="HTML")
        
    await callback.answer() # Tugma aylanishini to'xtatish

@dp.message(ParentSettings.waiting_for_custom_rate)
async def process_custom_rate(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting! (Masalan: 1500)")
        return
        
    rate = int(message.text)
    cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, message.from_user.id))
    conn.commit()
    
    await message.answer(f"✅ <b>Koin kursi muvaffaqiyatli o'rnatildi!</b>\n\nEndi 1 BiligCoin = {rate} so'm.", parse_mode="HTML")
    await state.clear()

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
