import os
import sqlite3
import asyncio
import threading
import traceback
import json
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import google.generativeai as genai

# ==========================================
# 1. MA'LUMOTLAR BAZASI (SQLITE)
# ==========================================
db_path = "/var/data/bot_base.db" if os.path.exists("/var/data") else "bot_base.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.execute('''CREATE TABLE IF NOT EXISTS Users (
        user_id INTEGER PRIMARY KEY, role TEXT, name TEXT, balance_coins INTEGER DEFAULT 0, total_xp INTEGER DEFAULT 0, streak_days INTEGER DEFAULT 0, coin_rate INTEGER DEFAULT 500)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Family_Link (
        parent_id INTEGER, child_id INTEGER, mutolaa_id TEXT, UNIQUE(parent_id, child_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Reading_Plans (
        plan_id INTEGER PRIMARY KEY AUTOINCREMENT, parent_id INTEGER, name TEXT, prize TEXT, deadline TEXT, status TEXT DEFAULT 'active')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Plan_Books (
        book_id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id INTEGER, title TEXT, author TEXT, status TEXT DEFAULT 'pending')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Book_Tests (
        test_id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER UNIQUE, questions_json TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Store_Items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT, parent_id INTEGER, name TEXT, price INTEGER)''')
    
    # Yangi ustunlarni qo'shish (Xato bermasligi uchun try-except)
    try: cursor.execute("ALTER TABLE Plan_Books ADD COLUMN pages_read INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE Family_Link ADD COLUMN child_age INTEGER DEFAULT 10")
    except: pass
    try: cursor.execute("ALTER TABLE Users ADD COLUMN badges TEXT DEFAULT ''")
    except: pass
    try: cursor.execute("ALTER TABLE Users ADD COLUMN is_approved INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE Plan_Books ADD COLUMN audio_count INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE Users ADD COLUMN last_read_date TEXT DEFAULT ''")
    except: pass
    try: cursor.execute("ALTER TABLE Plan_Books ADD COLUMN is_completed INTEGER DEFAULT 0")
    except: pass
    
    conn.commit()

def clean_json(text):
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    elif text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()

# ==========================================
# 2. DUMMY HTTP SERVER
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args): pass

class ReusableTCPServer(HTTPServer): allow_reuse_address = True

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = ReusableTCPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# ==========================================
# 3. MENYULAR (KEYBOARDS)
# ==========================================
def get_parent_keyboard():
    kb = [[KeyboardButton(text="📝 Mutolaa rejasini tuzish"), KeyboardButton(text="📚 Faol rejalarim")],
          [KeyboardButton(text="📊 Farzandim natijalari"), KeyboardButton(text="🎁 Mukofotlar")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_child_keyboard():
    kb = [[KeyboardButton(text="📖 Kitob o'qish")],
          [KeyboardButton(text="🎁 Sovrinlarim"), KeyboardButton(text="🏆 Reyting")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_back_reply_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Orqaga")]], resize_keyboard=True)

def get_add_book_keyboard():
    kb = [[InlineKeyboardButton(text="👶 Yosh bo'yicha tavsiyalar", callback_data="add_book_age")],
          [InlineKeyboardButton(text="✍️ Matn orqali qo'shish", callback_data="add_book_text")],
          [InlineKeyboardButton(text="📸 Rasm orqali (AI Vision)", callback_data="add_book_photo")],
          [InlineKeyboardButton(text="✅ Rejani yakunlash", callback_data="finish_plan")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_rewards_main_keyboard():
    kb = [
        [InlineKeyboardButton(text="🟡 Bilig kursini belgilash", callback_data="rewards_bilig_rate")],
        [InlineKeyboardButton(text="🛍 Sovg'alar do'konini tahrirlash", callback_data="rewards_store_edit")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_bilig_rate_inline_keyboard():
    kb = [
        [InlineKeyboardButton(text="🟡 500 so'm", callback_data="rate_500"),
         InlineKeyboardButton(text="🟡 1,000 so'm", callback_data="rate_1000")],
        [InlineKeyboardButton(text="🟡 5,000 so'm", callback_data="rate_5000"),
         InlineKeyboardButton(text="🟡 10,000 so'm", callback_data="rate_10000")],
        [InlineKeyboardButton(text="✍️ Boshqa summa kiritish", callback_data="rate_custom")],
        [InlineKeyboardButton(text="🚫 Pul bilan rag'batlantirmaslik", callback_data="rate_0")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="rewards_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==========================================
# 4. FSM (HOLATLAR)
# ==========================================
class Access(StatesGroup): waiting_for_code = State()
class Registration(StatesGroup): waiting_for_parent_code = State()
class ParentSettings(StatesGroup): 
    waiting_for_custom_rate = State()
    waiting_for_child_age = State()
class PlanCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_prize = State()
    waiting_for_deadline = State()
    waiting_for_book_text = State()
    waiting_for_book_photo = State()
class AITestCreation(StatesGroup): waiting_for_page_photo = State()
class ChildReading(StatesGroup):
    waiting_for_page_photo = State()
    waiting_for_audio = State()
class StoreSettings(StatesGroup):
    waiting_for_item_name = State()
    waiting_for_item_price = State()

# ==========================================
# 5. TELEGRAM BOT MANTIG'I
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

ACCESS_CODE = os.getenv("ACCESS_CODE", "BILIG-TEST")

# Yordamchi funksiya: Ota-ona ID sini topish
def get_parent_id(child_id):
    cursor.execute("SELECT parent_id FROM Family_Link WHERE child_id = ?", (child_id,))
    res = cursor.fetchone()
    return res[0] if res else None

# Yordamchi funksiya: Streak (Uzluksiz o'qish) ni yangilash
def update_streak(user_id):
    cursor.execute("SELECT streak_days, last_read_date FROM Users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row: return 0
    streak, last_date_str = row
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    today = datetime.strptime(today_str, "%Y-%m-%d").date()

    if last_date_str == today_str:
        return streak # Bugun allaqachon o'qigan
        
    if last_date_str:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        if today - last_date == timedelta(days=1):
            streak += 1
        else:
            streak = 1
    else:
        streak = 1

    cursor.execute("UPDATE Users SET streak_days = ?, last_read_date = ? WHERE user_id = ?", (streak, today_str, user_id))
    conn.commit()
    return streak

@dp.message(F.text == "🔙 Orqaga")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    cursor.execute("SELECT role FROM Users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if user and user[0] == 'parent':
        await message.answer("🚫 Amaliyot bekor qilindi. Bosh menyudasiz.", reply_markup=get_parent_keyboard())
    elif user and user[0] == 'child':
        await message.answer("🚫 Amaliyot bekor qilindi. Bosh menyudasiz.", reply_markup=get_child_keyboard())
    else:
        kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O'quvchiman")]]
        await message.answer("🚫 Amaliyot bekor qilindi.", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# ==========================================
# START VA YOPIQ TEST RUXSATI
# ==========================================
@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    cursor.execute("SELECT role, is_approved FROM Users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if user and user[1] == 1:
        if user[0] == 'parent':
            await message.answer("<b>Asosiy menyuga xush kelibsiz!</b> 👨‍👩‍👦", parse_mode="HTML", reply_markup=get_parent_keyboard())
        elif user[0] == 'child':
            await message.answer("<b>Asosiy menyuga xush kelibsiz, Qahramon!</b> 🦸‍♂️🦸‍♀️", parse_mode="HTML", reply_markup=get_child_keyboard())
        else:
            kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O'quvchiman")]]
            await message.answer("👋 <b>Bilig AI - Aqlli kitobxonlar dunyosiga xush kelibsiz!</b>\n\n<i>Kim bo'lib kirmoqchisiz?</i>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return

    cursor.execute("INSERT OR IGNORE INTO Users (user_id, name, is_approved) VALUES (?, ?, 0)", (message.from_user.id, message.from_user.full_name))
    conn.commit()
    
    await message.answer(f"👋 <b>Bilig AI yopiq test rejimida ishlamoqda!</b>\n\nBotdan foydalanish uchun maxsus ruxsat kodingizni kiriting:", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Access.waiting_for_code)

@dp.message(Access.waiting_for_code)
async def process_access_code(message: types.Message, state: FSMContext):
    if message.text.strip() == ACCESS_CODE:
        cursor.execute("UPDATE Users SET is_approved = 1 WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        await state.clear()
        kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O'quvchiman")]]
        await message.answer("✅ <b>Kod qabul qilindi! Bilig AI ga xush kelibsiz!</b>\n\n<i>Kim bo'lib kirmoqchisiz?</i>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    else:
        await message.answer("❌ Noto'g'ri kod! Iltimos, qaytadan kiriting:")

@dp.message(F.text == "👨‍👩‍👦 Men Ota-onaman")
async def parent_handler(message: types.Message):
    cursor.execute("UPDATE Users SET role = 'parent' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer(f"Siz Ota-ona sifatida ro'yxatdan o'tdingiz! ✅\nFarzandingiz ulanishi uchun kodingiz: <b>BLG-{str(message.from_user.id)[-4:]}</b>", parse_mode="HTML", reply_markup=get_parent_keyboard())

@dp.message(F.text == "👦👧 Men O'quvchiman")
async def child_handler(message: types.Message, state: FSMContext):
    cursor.execute("UPDATE Users SET role = 'child' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer("Iltimos, ota-onangiz bergan kodni kiriting (masalan, BLG-1234):", reply_markup=get_back_reply_keyboard())
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
            
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👦👧 Farzand yoshini kiritish", callback_data=f"set_age_{message.from_user.id}")]])
            await bot.send_message(parent[0], f"Farzandingiz ({message.from_user.full_name}) profilingizga ulandi! ✅\n\nAI unga moslashishi uchun iltimos, farzandingizning yoshini kiriting:", reply_markup=kb)
        except sqlite3.IntegrityError:
            await message.answer("Siz allaqachon bu ota-onaga ulangansiz!", reply_markup=get_child_keyboard())
        await state.clear()
    else:
        await message.answer("Bunday kodga ega ota-ona topilmadi. Qaytadan kiriting:")

@dp.callback_query(F.data.startswith("set_age_"))
async def ask_child_age(callback: types.CallbackQuery, state: FSMContext):
    child_id = int(callback.data.split("_")[2])
    await state.update_data(target_child_id=child_id)
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "✍️ <b>Farzandingiz yoshini raqamda kiriting (masalan: 10):</b>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ParentSettings.waiting_for_child_age)
    await callback.answer()

@dp.message(ParentSettings.waiting_for_child_age)
async def save_child_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return
    age = int(message.text)
    data = await state.get_data()
    child_id = data.get('target_child_id')
    
    cursor.execute("UPDATE Family_Link SET child_age = ? WHERE child_id = ?", (age, child_id))
    conn.commit()
    
    await message.answer(f"✅ <b>Farzandingiz yoshi ({age}) saqlandi!</b>\nEndi AI uning yoshiga moslashib ishlaydi.", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await state.clear()

# ==========================================
# MUKOFOTLAR VA SOVG'ALAR DO'KONI (OTA-ONA)
# ==========================================
def get_rewards_text():
    return (
        "🎁 <b>Mukofotlar va Motivatsiya bo'limi</b>\n\n"
        "Bu bo'lim orqali farzandingiz uchun o'qishni qiziqarli o'yinga aylantirasiz!\n\n"
        "<i>👇 Quyidagi tugmalardan keraklisini tanlang:</i>"
    )

@dp.message(F.text == "🎁 Mukofotlar")
async def mukofotlar_handler(message: types.Message):
    await message.answer(get_rewards_text(), parse_mode="HTML", reply_markup=get_rewards_main_keyboard())

@dp.callback_query(F.data == "rewards_main")
async def rewards_main_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(get_rewards_text(), parse_mode="HTML", reply_markup=get_rewards_main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "rewards_bilig_rate")
async def rewards_bilig_rate_callback(callback: types.CallbackQuery):
    text = "🟡 <b>Bilig kursini belgilash</b>\n\n1 ta Bilig (🟡) necha so'mga teng ekanligini tanlang."
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_bilig_rate_inline_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("rate_"))
async def process_rate_callback(callback: types.CallbackQuery, state: FSMContext):
    rate_val = callback.data.split("_")[1]
    if rate_val == "custom":
        await callback.message.delete()
        await bot.send_message(callback.from_user.id, "✍️ <b>Iltimos, 1 ta Bilig (🟡) uchun summani kiritng:</b>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
        await state.set_state(ParentSettings.waiting_for_custom_rate)
        return
    rate = int(rate_val)
    cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, callback.from_user.id))
    conn.commit()
    await callback.message.edit_text(f"✅ <b>Bilig kursi o'rnatildi!</b>\n1 🟡 = {rate} so'm.", parse_mode="HTML", reply_markup=get_rewards_main_keyboard())
    await callback.answer()

@dp.message(ParentSettings.waiting_for_custom_rate)
async def process_custom_rate(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return
    rate = int(message.text)
    cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, message.from_user.id))
    conn.commit()
    await message.answer(f"✅ <b>Bilig kursi o'rnatildi!</b>\n1 🟡 = {rate} so'm.", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await state.clear()

# DO'KONNI TAHRIRLASH
@dp.callback_query(F.data == "rewards_store_edit")
async def store_edit_callback(callback: types.CallbackQuery):
    cursor.execute("SELECT item_id, name, price FROM Store_Items WHERE parent_id = ?", (callback.from_user.id,))
    items = cursor.fetchall()
    
    kb = []
    for item in items:
        kb.append([InlineKeyboardButton(text=f"❌ {item[1]} ({item[2]} 🟡)", callback_data=f"delitem_{item[0]}")])
        
    kb.append([InlineKeyboardButton(text="➕ Yangi sovg'a qo'shish", callback_data="add_store_item")])
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="rewards_main")])
    
    text = "🛍 <b>Sovg'alar do'koni</b>\n\nBu yerdagi sovg'alarni farzandingiz o'z Biliglariga sotib olishi mumkin. O'chirish uchun ❌ tugmasini bosing."
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("delitem_"))
async def delete_store_item(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[1])
    cursor.execute("DELETE FROM Store_Items WHERE item_id = ?", (item_id,))
    conn.commit()
    await store_edit_callback(callback)

@dp.callback_query(F.data == "add_store_item")
async def add_store_item_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "✍️ <b>Sovg'a nomini kiriting:</b>\n<i>(Masalan: Muzqaymoq, Parkka borish)</i>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(StoreSettings.waiting_for_item_name)
    await callback.answer()

@dp.message(StoreSettings.waiting_for_item_name)
async def store_item_name(message: types.Message, state: FSMContext):
    await state.update_data(item_name=message.text)
    await message.answer("💰 <b>Bu sovg'a necha Bilig (🟡) turadi?</b>\nFaqat raqam kiriting:", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(StoreSettings.waiting_for_item_price)

@dp.message(StoreSettings.waiting_for_item_price)
async def store_item_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return
    data = await state.get_data()
    cursor.execute("INSERT INTO Store_Items (parent_id, name, price) VALUES (?, ?, ?)", (message.from_user.id, data['item_name'], int(message.text)))
    conn.commit()
    await message.answer(f"✅ <b>{data['item_name']}</b> do'konga qo'shildi!", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await state.clear()

# ==========================================
# MUTOLAA REJASINI TUZISH MANTIG'I
# ==========================================
@dp.message(F.text == "📝 Mutolaa rejasini tuzish")
async def create_plan_start(message: types.Message, state: FSMContext):
    text = "📝 <b>Mutolaa rejasi nima?</b>\n\n👇 <b>1-qadam:</b> Rejaga qanday nom berasiz?\n<i>(Masalan: 'Yozgi ta'til mutolaasi')</i>"
    await message.answer(text, parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(PlanCreation.waiting_for_name)

@dp.message(PlanCreation.waiting_for_name)
async def plan_name_received(message: types.Message, state: FSMContext):
    await state.update_data(plan_name=message.text)
    await message.answer("🎁 <b>2-qadam: Katta Mukofot!</b>\n\nBu reja to'liq tugatilganda farzandingiz qanday katta sovg'a oladi?", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(PlanCreation.waiting_for_prize)

@dp.message(PlanCreation.waiting_for_prize)
async def plan_prize_received(message: types.Message, state: FSMContext):
    await state.update_data(plan_prize=message.text)
    await message.answer("⏳ <b>3-qadam: Muddat (Deadline)</b>\n\nRejani qachongacha tugatish kerak?", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(PlanCreation.waiting_for_deadline)

@dp.message(PlanCreation.waiting_for_deadline)
async def plan_deadline_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO Reading_Plans (parent_id, name, prize, deadline) VALUES (?, ?, ?, ?)",
                   (message.from_user.id, data['plan_name'], data['plan_prize'], message.text))
    plan_id = cursor.lastrowid
    conn.commit()
    await state.update_data(current_plan_id=plan_id)
    await message.answer(f"✅ <b>Reja muvaffaqiyatli yaratildi!</b>", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await message.answer("📚 <b>Endi bu rejaga kitoblar qo'shamiz!</b>\n👇 <i>Qaysi usuldan foydalanasiz?</i>", parse_mode="HTML", reply_markup=get_add_book_keyboard())

@dp.callback_query(F.data == "finish_plan")
async def finish_plan_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("✅ <b>Mutolaa rejasi to'liq saqlandi!</b>", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "add_book_text")
async def add_book_text_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "✍️ <b>Matn orqali qo'shish</b>\n\nKitob nomi va muallifini nuqta bilan ajratib yozing:", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(PlanCreation.waiting_for_book_text)
    await callback.answer()

@dp.message(PlanCreation.waiting_for_book_text)
async def process_book_text(message: types.Message, state: FSMContext):
    if "." not in message.text:
        await message.answer("⚠️ Iltimos, kitob nomi va muallifini nuqta (.) bilan ajrating.")
        return
    title, author = message.text.split(".", 1)
    data = await state.get_data()
    cursor.execute("INSERT INTO Plan_Books (plan_id, title, author) VALUES (?, ?, ?)", (data.get('current_plan_id'), title.strip(), author.strip()))
    conn.commit()
    await message.answer(f"📚 <b>'{title.strip()}'</b> kitobi rejangizga qo'shildi!", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await message.answer("Yana kitob qo'shasizmi yoki rejani yakunlaysizmi?", reply_markup=get_add_book_keyboard())

@dp.callback_query(F.data == "add_book_photo")
async def add_book_photo_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "📸 <b>Rasm orqali qo'shish</b>\n\nKitobning muqovasini rasmga olib yuboring.", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(PlanCreation.waiting_for_book_photo)
    await callback.answer()

@dp.message(PlanCreation.waiting_for_book_photo, F.photo)
async def process_book_photo(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>Gemini AI rasmni tahlil qilmoqda...</i>", parse_mode="HTML")
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        model = genai.GenerativeModel('gemini-3.6-flash')
        prompt = "Bu kitob muqovasining rasmi. Menga faqat kitobning nomi va muallifini quyidagi formatda yozib ber: 'Kitob nomi. Muallif'."
        response = await model.generate_content_async([prompt, {"mime_type": "image/jpeg", "data": downloaded_file.read()}])
        ai_result = response.text.strip()
        
        title, author = ai_result.split(".", 1) if "." in ai_result else (ai_result, "Noma'lum muallif")
        data = await state.get_data()
        cursor.execute("INSERT INTO Plan_Books (plan_id, title, author) VALUES (?, ?, ?)", (data.get('current_plan_id'), title.strip(), author.strip()))
        conn.commit()
        
        await processing_msg.delete()
        await message.answer(f"✅ <b>AI aniqladi!</b>\n📚 <b>'{title.strip()}'</b>\nKitob qo'shildi!", parse_mode="HTML", reply_markup=get_parent_keyboard())
        await message.answer("Yana kitob qo'shasizmi yoki rejani yakunlaysizmi?", reply_markup=get_add_book_keyboard())
    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"❌ <b>Xatolik:</b> {str(e)}", parse_mode="HTML", reply_markup=get_parent_keyboard())

# ==========================================
# OTA-ONA UCHUN FAOL REJALAR VA TEST TUZISH
# ==========================================
async def show_parent_plans(message_or_callback, user_id):
    cursor.execute("SELECT plan_id, name, prize, deadline FROM Reading_Plans WHERE parent_id = ? AND status = 'active'", (user_id,))
    plans = cursor.fetchall()
    if not plans:
        text = "Sizda hozircha faol rejalar yo'q."
        if isinstance(message_or_callback, types.Message): await message_or_callback.answer(text, reply_markup=get_parent_keyboard())
        else: await message_or_callback.message.edit_text(text)
        return
        
    kb = []
    for p in plans:
        cursor.execute("SELECT COUNT(*) FROM Plan_Books WHERE plan_id = ?", (p[0],))
        kb.append([InlineKeyboardButton(text=f"🎯 {p[1]} ({cursor.fetchone()[0]} ta kitob)", callback_data=f"showplan_{p[0]}")])
        
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    if isinstance(message_or_callback, types.Message): await message_or_callback.answer("📚 <b>Sizning faol rejalaringiz.</b>", parse_mode="HTML", reply_markup=markup)
    else: await message_or_callback.message.edit_text("📚 <b>Sizning faol rejalaringiz.</b>", parse_mode="HTML", reply_markup=markup)

@dp.message(F.text == "📚 Faol rejalarim")
async def parent_active_plans_msg(message: types.Message):
    await show_parent_plans(message, message.from_user.id)

@dp.callback_query(F.data == "parent_plans_main")
async def parent_active_plans_call(callback: types.CallbackQuery):
    await show_parent_plans(callback, callback.from_user.id)
    await callback.answer()

@dp.callback_query(F.data.startswith("showplan_"))
async def show_plan_details(callback: types.CallbackQuery):
    plan_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT name, prize, deadline FROM Reading_Plans WHERE plan_id = ?", (plan_id,))
    plan = cursor.fetchone()
    cursor.execute("SELECT book_id, title, is_completed FROM Plan_Books WHERE plan_id = ?", (plan_id,))
    
    kb = []
    for b in cursor.fetchall():
        status_icon = "✅" if b[2] == 1 else "📘"
        kb.append([InlineKeyboardButton(text=f"{status_icon} {b[1]}", callback_data=f"showbook_{b[0]}")])
        
    kb.append([InlineKeyboardButton(text="🗑 Rejani o'chirish", callback_data=f"delplan_{plan_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="parent_plans_main")])
    
    text = f"🎯 <b>{plan[0]}</b>\n🎁 Mukofot: {plan[1]}\n⏳ Muddat: {plan[2]}\n\n📚 <b>Kitoblar:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("delplan_"))
async def delete_plan_handler(callback: types.CallbackQuery):
    plan_id = int(callback.data.split("_")[1])
    cursor.execute("DELETE FROM Plan_Books WHERE plan_id = ?", (plan_id,))
    cursor.execute("DELETE FROM Reading_Plans WHERE plan_id = ?", (plan_id,))
    conn.commit()
    await callback.answer("✅ Reja o'chirildi!", show_alert=True)
    await show_parent_plans(callback, callback.from_user.id)

@dp.callback_query(F.data.startswith("showbook_"))
async def show_book_details(callback: types.CallbackQuery):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT plan_id, title, author, pages_read, is_completed FROM Plan_Books WHERE book_id = ?", (book_id,))
    book = cursor.fetchone()
    
    kb = [
        [InlineKeyboardButton(text="📝 AI Test tuzish (Rasm orqali)", callback_data=f"aitest_{book_id}")],
        [InlineKeyboardButton(text="🗑 Kitobni o'chirish", callback_data=f"delbook_{book_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"showplan_{book[0]}")]
    ]
    status_text = "Tugatilgan ✅" if book[4] == 1 else "O'qilmoqda ⏳"
    text = f"📘 <b>{book[1]}</b>\n✍️ Muallif: {book[2]}\n📖 O'qildi: {book[3]} bet\n holati: {status_text}"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

# ==========================================
# AI TEST TUZISH MANTIG'I (OTA-ONA)
# ==========================================
@dp.callback_query(F.data.startswith("aitest_"))
async def ask_for_test_photo(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(test_book_id=int(callback.data.split("_")[1]))
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "📸 <b>AI Test tuzish</b>\n\nKitobning ixtiyoriy sahifasini rasmga olib yuboring.", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(AITestCreation.waiting_for_page_photo)
    await callback.answer()

@dp.message(AITestCreation.waiting_for_page_photo, F.photo)
async def generate_ai_test(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>Gemini AI sahifani o'qib, sifatli test tuzmoqda...</i>", parse_mode="HTML")
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        prompt = """Bu bolalar kitobining sahifasi. Shu matn asosida bolalar uchun 5 ta sifatli test savoli tuz. 
        DIQQAT: Savollar faqat quruq xotirani emas, balki bolaning fikrlashini, mantiqini va asar mohiyatini tushunganini sinaydigan bo'lsin.
        Har bir savolda 3 ta variant (A, B, C) bo'lsin. 
        Natijani FAQAT VA FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday so'z qo'shma:
        [ {"question": "Savol matni?", "options": ["A) variant", "B) variant", "C) variant"], "answer": "A) variant"} ]"""
        
        model = genai.GenerativeModel('gemini-3.6-flash')
        response = await model.generate_content_async([prompt, {"mime_type": "image/jpeg", "data": downloaded_file.read()}])
        
        ai_result = clean_json(response.text)
        questions = json.loads(ai_result) # Validatsiya
        
        data = await state.get_data()
        cursor.execute("INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)", (data.get('test_book_id'), ai_result))
        conn.commit()
        
        # Ota-onaga tuzilgan testni ko'rsatish
        test_text = "✅ <b>AI Test muvaffaqiyatli tuzildi!</b>\n\n<i>Quyidagi savollar bazaga saqlandi:</i>\n\n"
        for i, q in enumerate(questions):
            test_text += f"<b>{i+1}. {q['question']}</b>\nJavob: {q['answer']}\n\n"
            
        await processing_msg.delete()
        await message.answer(test_text, parse_mode="HTML", reply_markup=get_parent_keyboard())
        await state.clear()
    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"❌ <b>Xatolik yuz berdi:</b>\n<code>{str(e)}</code>", parse_mode="HTML", reply_markup=get_parent_keyboard())
        await state.clear()

# ==========================================
# FARZAND UCHUN KITOB O'QISH MENYUSI
# ==========================================
async def show_child_books(message_or_callback, user_id):
    cursor.execute("SELECT parent_id FROM Family_Link WHERE child_id = ?", (user_id,))
    link = cursor.fetchone()
    if not link:
        if isinstance(message_or_callback, types.Message): await message_or_callback.answer("Siz hali ota-onangizga ulanmagansiz!")
        return
        
    cursor.execute("SELECT plan_id, name, prize FROM Reading_Plans WHERE parent_id = ? AND status = 'active'", (link[0],))
    plans = cursor.fetchall()
    
    kb, has_books, text = [], False, "🦸‍♂️ <b>Qahramon! Ota-onang senga ajoyib reja tuzgan.</b>\n\n"
    for p in plans:
        cursor.execute("SELECT book_id, title, pages_read, is_completed FROM Plan_Books WHERE plan_id = ?", (p[0],))
        books = cursor.fetchall()
        if books:
            text += f"🎯 <b>{p[1]}</b> (Mukofot: {p[2]})\n"
            for b in books:
                if b[3] == 0: # Faqat tugatilmagan kitoblar chiqadi
                    kb.append([InlineKeyboardButton(text=f"📘 {b[1]} ({b[2]} bet)", callback_data=f"cread_{b[0]}")])
                    has_books = True
            text += "\n"
            
    if not has_books:
        text = "Senda hozircha o'qilishi kerak bo'lgan kitoblar yo'q. 😊"
        markup = None
    else:
        text += "👇 Qaysi kitobni o'qishni davom ettiramiz?"
        markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    if isinstance(message_or_callback, types.Message): await message_or_callback.answer(text, parse_mode="HTML", reply_markup=markup)
    else: await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)

@dp.message(F.text == "📖 Kitob o'qish")
async def child_read_book_msg(message: types.Message):
    await show_child_books(message, message.from_user.id)

@dp.callback_query(F.data == "child_books_main")
async def child_read_book_call(callback: types.CallbackQuery):
    await show_child_books(callback, callback.from_user.id)
    await callback.answer()

@dp.callback_query(F.data.startswith("cread_"))
async def child_book_action(callback: types.CallbackQuery):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT test_id FROM Book_Tests WHERE book_id = ?", (book_id,))
    
    test_btn = InlineKeyboardButton(text="📝 Testni ishlash (Bilig 🟡)", callback_data=f"taketest_{book_id}_0_0") if cursor.fetchone() else InlineKeyboardButton(text="🔒 Test (Hozircha mavjud emas)", callback_data="no_test_alert")
        
    kb = [
        [InlineKeyboardButton(text="📸 Sahifani rasmga olib yuborish", callback_data=f"sendpage_{book_id}")],
        [InlineKeyboardButton(text="🎤 Audio xulosa yuborish", callback_data=f"sendaudio_{book_id}")],
        [test_btn],
        [InlineKeyboardButton(text="✅ Kitobni tugatdim", callback_data=f"finishbook_{book_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="child_books_main")]
    ]
    await callback.message.edit_text("Ajoyib tanlov! O'qishni boshla. To'xtagan joyingda menga sahifani rasmga olib yubor.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data == "no_test_alert")
async def no_test_alert(callback: types.CallbackQuery):
    await callback.answer("🔒 Ota-onangiz bu kitob uchun hali test tuzmagan. O'qishda davom eting!", show_alert=True)

# KITOBNI TUGATISH VA REJANI YAKUNLASH
@dp.callback_query(F.data.startswith("finishbook_"))
async def finish_book_handler(callback: types.CallbackQuery):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("UPDATE Plan_Books SET is_completed = 1 WHERE book_id = ?", (book_id,))
    
    cursor.execute("SELECT plan_id, title FROM Plan_Books WHERE book_id = ?", (book_id,))
    plan_id, book_title = cursor.fetchone()
    
    # Rejadagi qolgan kitoblarni tekshiramiz
    cursor.execute("SELECT COUNT(*) FROM Plan_Books WHERE plan_id = ? AND is_completed = 0", (plan_id,))
    remaining = cursor.fetchone()[0]
    
    parent_id = get_parent_id(callback.from_user.id)
    
    if remaining == 0:
        cursor.execute("UPDATE Reading_Plans SET status = 'completed' WHERE plan_id = ?", (plan_id,))
        cursor.execute("SELECT name, prize FROM Reading_Plans WHERE plan_id = ?", (plan_id,))
        plan_name, prize = cursor.fetchone()
        
        text_child = f"🎉 <b>URAA! MARAFON TUGADI!</b>\n\nSen '{plan_name}' rejasidagi barcha kitoblarni o'qib bo'lding!\nEndi ota-onangdan <b>'{prize}'</b> mukofotini so'rashing mumkin! Qahramon! 🦸‍♂️"
        await callback.message.edit_text(text_child, parse_mode="HTML")
        
        if parent_id:
            text_parent = f"🎉 <b>TABRIKLAYMIZ!</b>\n\nFarzandingiz '{plan_name}' rejasini to'liq yakunladi!\nUnga va'da qilingan <b>'{prize}'</b> mukofotini olib berish vaqti keldi! 🎁"
            await bot.send_message(parent_id, text_parent, parse_mode="HTML")
    else:
        await callback.message.edit_text(f"✅ <b>'{book_title}'</b> kitobini tugatding! Barakalla!\nRejada yana {remaining} ta kitob qoldi.", parse_mode="HTML")
        if parent_id:
            await bot.send_message(parent_id, f"📚 Farzandingiz <b>'{book_title}'</b> kitobini to'liq o'qib tugatdi! ✅", parse_mode="HTML")
            
    conn.commit()
    await callback.answer()

# ==========================================
# 1-BOSQICH: RASM YUBORISH VA SAHIFA RAQAMINI O'QISH
# ==========================================
@dp.callback_query(F.data.startswith("sendpage_"))
async def ask_page_photo(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    await state.update_data(reading_book_id=book_id)
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "📸 <b>O'qigan sahifangni rasmga olib yubor!</b>\n\n<i>(Rasm AI tomonidan tekshirilgach, darhol o'chirib tashlanadi)</i>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ChildReading.waiting_for_page_photo)
    await callback.answer()

@dp.message(ChildReading.waiting_for_page_photo, F.photo)
async def process_reading_photo(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>AI sahifani tekshirmoqda...</i>", parse_mode="HTML")
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        prompt = """Bu rasm foydalanuvchi yuborgan kitob sahifasi.
        1. Bu haqiqatan ham kitob sahifasimi? (true/false)
        2. Rasmda ko'rinib turgan eng katta sahifa raqamini top. Agar sahifa raqami umuman ko'rinmasa, 0 deb ber.
        Javobingni FAQAT JSON formatida ber: {"is_book_page": true, "page_number": 155}"""
        
        model = genai.GenerativeModel('gemini-3.6-flash')
        response = await model.generate_content_async([prompt, {"mime_type": "image/jpeg", "data": downloaded_file.read()}])
        
        ai_result = json.loads(clean_json(response.text))
        
        try: await message.delete()
        except: pass 
        
        if not ai_result.get("is_book_page"):
            await processing_msg.delete()
            await message.answer("🚫 Bu kitob sahifasiga o'xshamayapti. Iltimos, faqat kitobni rasmga olib yubor!", reply_markup=get_child_keyboard())
            await state.clear()
            return
            
        new_page_num = int(ai_result.get("page_number", 0))
        
        if new_page_num == 0:
            await processing_msg.delete()
            await message.answer("⚠️ Sahifa raqami ko'rinmadi! Iltimos, sahifa raqami aniq ko'rinadigan qilib rasmga olib yubor.", reply_markup=get_child_keyboard())
            await state.clear()
            return
            
        data = await state.get_data()
        book_id = data.get('reading_book_id')
        child_id = message.from_user.id
        
        cursor.execute("SELECT pages_read, title FROM Plan_Books WHERE book_id = ?", (book_id,))
        row = cursor.fetchone()
        old_pages = row[0] if row else 0
        book_title = row[1]
        
        if new_page_num <= old_pages:
            await processing_msg.delete()
            await message.answer(f"⚠️ Sen allaqachon {old_pages}-sahifagacha o'qigansan! Iltimos, yangiroq sahifani rasmga olib yubor.", reply_markup=get_child_keyboard())
            await state.clear()
            return
        
        cursor.execute("UPDATE Plan_Books SET pages_read = ? WHERE book_id = ?", (new_page_num, book_id))
        
        earned_bilig = (new_page_num // 5) - (old_pages // 5)
        pages_read_now = new_page_num - old_pages
        
        streak = update_streak(child_id) # STREAK YANGILASH
        
        if earned_bilig > 0:
            cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (earned_bilig, child_id))
            reply_text = f"🎉 <b>Qoyilmaqom!</b> Sen {pages_read_now} bet o'qiding va <b>{earned_bilig} 🟡 Bilig</b> ishlab olding!\n🔥 Streak: {streak} kun!\n<i>(Jami o'qilgan: {new_page_num} bet)</i>"
        else:
            reply_text = f"👍 <b>Barakalla!</b> Sen {pages_read_now} bet o'qiding. Yana {5 - (new_page_num % 5)} bet o'qisang, yangi Bilig 🟡 olasan!\n🔥 Streak: {streak} kun!"
            
        conn.commit()
        await processing_msg.delete()
        await message.answer(reply_text, parse_mode="HTML", reply_markup=get_child_keyboard())
        await state.clear()
        
        # Ota-onaga bildirishnoma
        parent_id = get_parent_id(child_id)
        if parent_id:
            await bot.send_message(parent_id, f"📖 Farzandingiz hozirgina <b>'{book_title}'</b> kitobidan {pages_read_now} bet o'qidi. (Jami: {new_page_num} bet).", parse_mode="HTML")
        
    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"❌ Xatolik yuz berdi. Qaytadan urinib ko'r.", reply_markup=get_child_keyboard())
        await state.clear()

# ==========================================
# 2-BOSQICH: AUDIO XULOSA VA ADABIYOTSHUNOS OLIM
# ==========================================
@dp.callback_query(F.data.startswith("sendaudio_"))
async def ask_audio_summary(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT pages_read, audio_count FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row: return
        
    pages_read, audio_count = row
    audio_count = audio_count if audio_count else 0
    required_pages = 10 if audio_count == 0 else 10 + (audio_count * 30)
    
    if pages_read < required_pages:
        await callback.answer(f"🔒 Audio xulosa yuborish uchun kamida {required_pages}-sahifagacha o'qishingiz kerak!\n\n(Hozir: {pages_read} bet o'qilgan)", show_alert=True)
        return
        
    await state.update_data(audio_book_id=book_id)
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "🎤 <b>Ovozli xabar yubor!</b>\n\nKitobda nimalar bo'lganini o'z so'zlaring bilan aytib ber. AI Adabiyotshunos olim seni eshitib, baho beradi!", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ChildReading.waiting_for_audio)
    await callback.answer()

@dp.message(ChildReading.waiting_for_audio, F.voice)
async def process_audio_summary(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>Adabiyotshunos olim seni eshitmoqda...</i>", parse_mode="HTML")
    try:
        file_info = await bot.get_file(message.voice.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        cursor.execute("SELECT child_age FROM Family_Link WHERE child_id = ?", (message.from_user.id,))
        age_row = cursor.fetchone()
        age = age_row[0] if age_row else 10
        
        prompt = f"""Sen mehribon va aqlli Adabiyotshunos olimsan. Bu {age} yoshli bolaning kitob bo'yicha audio xulosasi.
        Bolaning yoshini hisobga olib, uning fikrlashini, so'z boyligini tahlil qil. Unga motivatsiya beruvchi, maqtab, iliq fikr (feedback) yoz. Xulosa sifatiga qarab 1 dan 5 gacha bonus Bilig (tanga) ber.
        Javobni FAQAT JSON formatida ber: {{"feedback": "Sening xulosang juda zo'r...", "bonus_bilig": 3, "give_badge": true}}"""
        
        model = genai.GenerativeModel('gemini-3.6-flash')
        response = await model.generate_content_async([prompt, {"mime_type": "audio/ogg", "data": downloaded_file.read()}])
        
        ai_result = json.loads(clean_json(response.text))
        bonus = ai_result.get("bonus_bilig", 0)
        give_badge = ai_result.get("give_badge", False)
        feedback = ai_result.get("feedback", "Ajoyib xulosa!")
        
        data = await state.get_data()
        book_id = data.get('audio_book_id')
        
        cursor.execute("UPDATE Plan_Books SET audio_count = audio_count + 1 WHERE book_id = ?", (book_id,))
        cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (bonus, message.from_user.id))
        
        update_streak(message.from_user.id) # STREAK YANGILASH
        
        badge_text = ""
        if give_badge:
            cursor.execute("SELECT badges FROM Users WHERE user_id = ?", (message.from_user.id,))
            current_badges = cursor.fetchone()[0]
            if "Notiq" not in current_badges:
                new_badges = current_badges + " 🗣 Notiq" if current_badges else "🗣 Notiq"
                cursor.execute("UPDATE Users SET badges = ? WHERE user_id = ?", (new_badges, message.from_user.id))
                badge_text = "\n\n🏅 <b>TABRIKLAYMIZ! Sen 'Notiq' nishonini qo'lga kiritding!</b>"
                
        conn.commit()
        
        reply_text = f"👨‍🏫 <b>Adabiyotshunos olim:</b>\n<i>\"{feedback}\"</i>\n\n🎁 <b>Bonus:</b> {bonus} 🟡 Bilig!{badge_text}"
        await processing_msg.delete()
        await message.answer(reply_text, parse_mode="HTML", reply_markup=get_child_keyboard())
        await state.clear()
        
        # Ota-onaga bildirishnoma
        parent_id = get_parent_id(message.from_user.id)
        if parent_id:
            await bot.send_message(parent_id, f"🎤 Farzandingiz audio xulosa yubordi va <b>{bonus} 🟡 Bilig</b> ishladi!", parse_mode="HTML")
            
    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"❌ Xatolik yuz berdi. Qaytadan urinib ko'r.", reply_markup=get_child_keyboard())
        await state.clear()

# ==========================================
# 3-BOSQICH: AI TEST YECHISH
# ==========================================
@dp.callback_query(F.data.startswith("taketest_"))
async def execute_test(callback: types.CallbackQuery):
    _, book_id, q_idx, correct_count = callback.data.split("_")
    book_id, q_idx, correct_count = int(book_id), int(q_idx), int(correct_count)
    
    cursor.execute("SELECT questions_json FROM Book_Tests WHERE book_id = ?", (book_id,))
    test_row = cursor.fetchone()
    if not test_row: return
        
    questions = json.loads(test_row[0])
    
    if q_idx >= len(questions):
        cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (correct_count, callback.from_user.id))
        cursor.execute("DELETE FROM Book_Tests WHERE book_id = ?", (book_id,))
        conn.commit()
        
        text = f"🏁 <b>Test yakunlandi!</b>\n\n✅ To'g'ri javoblar: {correct_count} ta\n🎁 Sen <b>{correct_count} 🟡 Bilig</b> yutib olding! Barakalla, aqlli Qahramon! 🧠"
        await callback.message.edit_text(text, parse_mode="HTML")
        
        # Ota-onaga bildirishnoma
        parent_id = get_parent_id(callback.from_user.id)
        if parent_id:
            await bot.send_message(parent_id, f"📝 Farzandingiz test yechdi! Natija: <b>{correct_count}/5</b> to'g'ri.", parse_mode="HTML")
        await callback.answer()
        return
        
    q = questions[q_idx]
    kb = []
    for i, opt in enumerate(q['options']):
        is_correct = 1 if opt.strip() == q['answer'].strip() else 0
        kb.append([InlineKeyboardButton(text=opt, callback_data=f"tans_{book_id}_{q_idx+1}_{correct_count}_{is_correct}")])
        
    text = f"📝 <b>{q_idx + 1}-savol:</b>\n\n{q['question']}"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("tans_"))
async def process_test_answer(callback: types.CallbackQuery):
    _, book_id, next_q_idx, correct_count, is_correct = callback.data.split("_")
    new_correct_count = int(correct_count) + int(is_correct)
    callback.data = f"taketest_{book_id}_{next_q_idx}_{new_correct_count}"
    await execute_test(callback)

# ==========================================
# 4-BOSQICH: GAMIFIKATSIYA VA REYTING
# ==========================================
@dp.message(F.text == "🎁 Sovrinlarim")
async def show_rewards(message: types.Message):
    cursor.execute("SELECT balance_coins, badges, streak_days FROM Users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    balance = user[0]
    badges = user[1] if user[1] else "Hali nishonlar yo'q."
    streak = user[2]
    
    text = (
        f"🦸‍♂️ <b>Qahramon: {message.from_user.full_name}</b>\n\n"
        f"🟡 <b>Biliglar:</b> {balance} ta\n"
        f"🔥 <b>Uzluksiz o'qish:</b> {streak} kun\n"
        f"🏅 <b>Nishonlar:</b> {badges}\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Do'konga kirish", callback_data="child_store")]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

# BOLA UCHUN DO'KON
@dp.callback_query(F.data == "child_store")
async def child_store_handler(callback: types.CallbackQuery):
    parent_id = get_parent_id(callback.from_user.id)
    if not parent_id:
        await callback.answer("Siz hali ulanmagansiz!", show_alert=True)
        return
        
    cursor.execute("SELECT item_id, name, price FROM Store_Items WHERE parent_id = ?", (parent_id,))
    items = cursor.fetchall()
    
    if not items:
        await callback.message.edit_text("🛒 Do'konda hozircha sovg'alar yo'q. Ota-onangizga ayting, sovg'a qo'shsinlar!")
        return
        
    kb = []
    for item in items:
        kb.append([InlineKeyboardButton(text=f"🎁 {item[1]} - {item[2]} 🟡", callback_data=f"buyitem_{item[0]}")])
        
    await callback.message.edit_text("🛒 <b>Sovg'alar do'koni</b>\n\nYig'gan Biliglaringizga nima sotib olamiz?", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("buyitem_"))
async def buy_item_handler(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT name, price, parent_id FROM Store_Items WHERE item_id = ?", (item_id,))
    item = cursor.fetchone()
    
    cursor.execute("SELECT balance_coins FROM Users WHERE user_id = ?", (callback.from_user.id,))
    balance = cursor.fetchone()[0]
    
    if balance < item[1]:
        await callback.answer(f"Sizda yetarli Bilig yo'q! Yana {item[1] - balance} 🟡 yig'ishingiz kerak.", show_alert=True)
        return
        
    # Pulni yechish
    cursor.execute("UPDATE Users SET balance_coins = balance_coins - ? WHERE user_id = ?", (item[1], callback.from_user.id))
    conn.commit()
    
    await callback.message.edit_text(f"🎉 <b>Tabriklaymiz!</b> Sen <b>{item[0]}</b> sotib olding!\nOta-onangga xabar yuborildi.", parse_mode="HTML")
    
    # Ota-onaga xabar
    await bot.send_message(item[2], f"🛍 <b>Diqqat!</b> Farzandingiz do'kondan <b>'{item[0]}'</b> sotib oldi! Iltimos, va'da qilingan sovg'ani olib bering.", parse_mode="HTML")
    await callback.answer()

# REYTING (LEADERBOARD)
@dp.message(F.text == "🏆 Reyting")
async def show_leaderboard(message: types.Message):
    cursor.execute("SELECT name, balance_coins FROM Users WHERE role = 'child' ORDER BY balance_coins DESC LIMIT 10")
    top_users = cursor.fetchall()
    
    if not top_users:
        await message.answer("Hali reyting shakllanmadi.")
        return
        
    text = "🏆 <b>Eng ko'p Bilig yig'gan Qahramonlar:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, user in enumerate(top_users):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} <b>{user[0]}</b> - {user[1]} 🟡\n"
        
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "📊 Farzandim natijalari")
async def parent_results_handler(message: types.Message):
    cursor.execute("SELECT child_id, child_age FROM Family_Link WHERE parent_id = ?", (message.from_user.id,))
    link = cursor.fetchone()
    if not link: return
        
    child_id, child_age = link
    cursor.execute("SELECT name, balance_coins, badges, streak_days FROM Users WHERE user_id = ?", (child_id,))
    child = cursor.fetchone()
    if not child: return
        
    child_name, balance, badges, streak = child
    badges_text = badges if badges else "Hali nishonlar yo'q"
    
    cursor.execute("SELECT SUM(pages_read) FROM Plan_Books pb JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id WHERE rp.parent_id = ?", (message.from_user.id,))
    total_pages = cursor.fetchone()[0]
    total_pages = total_pages if total_pages else 0
    
    text = (
        f"📊 <b>{child_name}ning natijalari:</b>\n\n"
        f"👦 Yoshi: {child_age}\n"
        f"📖 Jami o'qilgan sahifalar: {total_pages} bet\n"
        f"🟡 Yig'ilgan Biliglar: {balance} ta\n"
        f"🔥 Uzluksiz o'qish: {streak} kun\n"
        f"🏅 Nishonlar: {badges_text}\n"
    )
    await message.answer(text, parse_mode="HTML")

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
