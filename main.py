import os
import sqlite3
import asyncio
import threading
import traceback
import json
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
    
    try:
        cursor.execute("ALTER TABLE Plan_Books ADD COLUMN pages_read INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    cursor.execute('''CREATE TABLE IF NOT EXISTS Book_Tests (
        test_id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER UNIQUE, questions_json TEXT)''')
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

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True)

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
class Registration(StatesGroup): waiting_for_parent_code = State()
class ParentSettings(StatesGroup): waiting_for_custom_rate = State()
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

# ==========================================
# 5. TELEGRAM BOT MANTIG'I
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@dp.message(F.text == "❌ Bekor qilish")
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

@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    cursor.execute("SELECT role FROM Users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if user and user[0] == 'parent':
        await message.answer("<b>Asosiy menyuga xush kelibsiz!</b> 👨‍👩‍👦", parse_mode="HTML", reply_markup=get_parent_keyboard())
        return
    elif user and user[0] == 'child':
        await message.answer("<b>Asosiy menyuga xush kelibsiz, Qahramon!</b> 🦸‍♂️🦸‍♀️", parse_mode="HTML", reply_markup=get_child_keyboard())
        return

    cursor.execute("INSERT OR IGNORE INTO Users (user_id, name) VALUES (?, ?)", (message.from_user.id, message.from_user.full_name))
    conn.commit()
    kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O'quvchiman")]]
    await message.answer("👋 <b>Bilig AI - Aqlli kitobxonlar dunyosiga xush kelibsiz!</b>\n\n<i>Kim bo'lib kirmoqchisiz?</i>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.text == "👨‍👩‍👦 Men Ota-onaman")
async def parent_handler(message: types.Message):
    cursor.execute("UPDATE Users SET role = 'parent' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer(f"Siz Ota-ona sifatida ro'yxatdan o'tdingiz! ✅\nFarzandingiz ulanishi uchun kodingiz: <b>BLG-{str(message.from_user.id)[-4:]}</b>", parse_mode="HTML", reply_markup=get_parent_keyboard())

@dp.message(F.text == "👦👧 Men O'quvchiman")
async def child_handler(message: types.Message, state: FSMContext):
    cursor.execute("UPDATE Users SET role = 'child' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer("Iltimos, ota-onangiz bergan kodni kiriting (masalan, BLG-1234):", reply_markup=get_cancel_keyboard())
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
# MUKOFOTLAR VA BILIG KURSI MANTIG'I
# ==========================================
def get_rewards_text():
    return (
        "🎁 <b>Mukofotlar va Motivatsiya bo'limi</b>\n\n"
        "Bu bo'lim orqali farzandingiz uchun o'qishni qiziqarli o'yinga aylantirasiz!\n\n"
        "🟡 <b>Bilig (Oltin tanga) nima?</b>\n"
        "Farzandingiz o'qigan har bir sahifasi va yechgan testlari uchun virtual oltin tangalar (Bilig) yig'adi. "
        "Siz bu tangalarning haqiqiy puldagi qiymatini belgilashingiz mumkin (Masalan: 1 🟡 = 1000 so'm).\n\n"
        "🛍 <b>Sovg'alar do'koni:</b>\n"
        "Farzandingiz yig'gan tangalariga nimalar sotib olishi mumkinligini o'zingiz kiritasiz (Masalan: 'Parkka borish' - 50 🟡).\n\n"
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
    text = (
        "🟡 <b>Bilig kursini belgilash</b>\n\n"
        "1 ta Bilig (🟡) necha so'mga teng ekanligini tanlang.\n\n"
        "<i>⚠️ Agar farzandingizni pul bilan rag'batlantirishni xohlamasangiz, eng pastdagi 'Pul bilan rag'batlantirmaslik' tugmasini tanlang. "
        "Shunda u faqat reyting, bilim va maxsus nishonlar uchun o'qiydi.</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_bilig_rate_inline_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("rate_"))
async def process_rate_callback(callback: types.CallbackQuery, state: FSMContext):
    rate_val = callback.data.split("_")[1]
    if rate_val == "custom":
        await callback.message.delete()
        await bot.send_message(callback.from_user.id, "✍️ <b>Iltimos, 1 ta Bilig (🟡) uchun summani raqamlarda kiriting:</b>\n<i>(Masalan: 2000)</i>", parse_mode="HTML", reply_markup=get_cancel_keyboard())
        await state.set_state(ParentSettings.waiting_for_custom_rate)
        return
    
    rate = int(rate_val)
    cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, callback.from_user.id))
    conn.commit()
    
    if rate == 0:
        await callback.message.edit_text("✅ <b>Siz pul bilan rag'batlantirmaslik rejimini tanladingiz!</b>\n\nEndi farzandingiz faqat bilim, reyting va maxsus nishonlar uchun o'qiydi. Bu juda zo'r tanlov! 🧠", parse_mode="HTML", reply_markup=get_rewards_main_keyboard())
    else:
        await callback.message.edit_text(f"✅ <b>Bilig kursi muvaffaqiyatli o'rnatildi!</b>\n\nEndi 1 🟡 = {rate} so'm.", parse_mode="HTML", reply_markup=get_rewards_main_keyboard())
    await callback.answer()

@dp.message(ParentSettings.waiting_for_custom_rate)
async def process_custom_rate(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting! (Masalan: 1500)")
        return
    rate = int(message.text)
    cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, message.from_user.id))
    conn.commit()
    await message.answer(f"✅ <b>Bilig kursi muvaffaqiyatli o'rnatildi!</b>\n\nEndi 1 🟡 = {rate} so'm.", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await state.clear()

# ==========================================
# MUTOLAA REJASINI TUZISH MANTIG'I
# ==========================================
@dp.message(F.text == "📝 Mutolaa rejasini tuzish")
async def create_plan_start(message: types.Message, state: FSMContext):
    text = (
        "📝 <b>Mutolaa rejasi nima?</b>\n\n"
        "Bu farzandingiz uchun maxsus <b>'Kitobxonlik marafoni'</b> dir. Siz unga o'qilishi kerak bo'lgan kitoblarni, muddatni va oxirida beriladigan Katta Mukofotni belgilaysiz.\n\n"
        "👇 <b>1-qadam:</b> Rejaga qanday nom berasiz?\n"
        "<i>(Masalan: 'Yozgi ta'til mutolaasi', 'Tug'ilgan kun sovg'asi uchun')</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await state.set_state(PlanCreation.waiting_for_name)

@dp.message(PlanCreation.waiting_for_name)
async def plan_name_received(message: types.Message, state: FSMContext):
    await state.update_data(plan_name=message.text)
    await message.answer("🎁 <b>2-qadam: Katta Mukofot!</b>\n\nBu reja to'liq tugatilganda farzandingiz qanday katta sovg'a oladi?\n<i>(Masalan: 'Velosiped', 'Parkka borish', '5000 🟡')</i>", parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await state.set_state(PlanCreation.waiting_for_prize)

@dp.message(PlanCreation.waiting_for_prize)
async def plan_prize_received(message: types.Message, state: FSMContext):
    await state.update_data(plan_prize=message.text)
    await message.answer("⏳ <b>3-qadam: Muddat (Deadline)</b>\n\nRejani qachongacha tugatish kerak?\n<i>(Masalan: '1 oyda', '31-Avgustgacha')</i>", parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await state.set_state(PlanCreation.waiting_for_deadline)

@dp.message(PlanCreation.waiting_for_deadline)
async def plan_deadline_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    plan_name = data['plan_name']
    plan_prize = data['plan_prize']
    plan_deadline = message.text
    
    cursor.execute("INSERT INTO Reading_Plans (parent_id, name, prize, deadline) VALUES (?, ?, ?, ?)",
                   (message.from_user.id, plan_name, plan_prize, plan_deadline))
    plan_id = cursor.lastrowid
    conn.commit()
    
    await state.update_data(current_plan_id=plan_id)
    await message.answer(f"✅ <b>Reja muvaffaqiyatli yaratildi!</b>\n\n📌 <b>Nom:</b> {plan_name}\n🎁 <b>Mukofot:</b> {plan_prize}\n⏳ <b>Muddat:</b> {plan_deadline}", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await message.answer("📚 <b>Endi bu rejaga kitoblar qo'shamiz!</b>\n👇 <i>Qaysi usuldan foydalanasiz?</i>", parse_mode="HTML", reply_markup=get_add_book_keyboard())

@dp.callback_query(F.data == "finish_plan")
async def finish_plan_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("✅ <b>Mutolaa rejasi to'liq saqlandi va yopildi!</b>\n\nFarzandingiz endi bu kitoblarni o'z menyusida ko'radi va o'qishni boshlashi mumkin.", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "add_book_text")
async def add_book_text_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "✍️ <b>Matn orqali qo'shish</b>\n\nKitob nomi va muallifini nuqta bilan ajratib yozing:\n<i>Masalan: O'tkan kunlar. Abdulla Qodiriy</i>", parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await state.set_state(PlanCreation.waiting_for_book_text)
    await callback.answer()

@dp.message(PlanCreation.waiting_for_book_text)
async def process_book_text(message: types.Message, state: FSMContext):
    if "." not in message.text:
        await message.answer("⚠️ Iltimos, kitob nomi va muallifini nuqta (.) bilan ajrating.")
        return
    title, author = message.text.split(".", 1)
    data = await state.get_data()
    plan_id = data.get('current_plan_id')
    cursor.execute("INSERT INTO Plan_Books (plan_id, title, author) VALUES (?, ?, ?)", (plan_id, title.strip(), author.strip()))
    conn.commit()
    
    await message.answer(f"📚 <b>'{title.strip()}'</b> kitobi rejangizga qo'shildi!", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await message.answer("Yana kitob qo'shasizmi yoki rejani yakunlaysizmi?", reply_markup=get_add_book_keyboard())

@dp.callback_query(F.data == "add_book_photo")
async def add_book_photo_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "📸 <b>Rasm orqali qo'shish</b>\n\nKitobning muqovasini (ustki qismini) rasmga olib yuboring. AI o'zi kitob nomi va muallifini aniqlaydi!", parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await state.set_state(PlanCreation.waiting_for_book_photo)
    await callback.answer()

@dp.message(PlanCreation.waiting_for_book_photo, F.photo)
async def process_book_photo(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>Gemini AI rasmni tahlil qilmoqda... Iltimos kuting.</i>", parse_mode="HTML")
    if not GEMINI_API_KEY:
        await processing_msg.edit_text("❌ GEMINI_API_KEY topilmadi.")
        return
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        image_data = downloaded_file.read()
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = "Bu kitob muqovasining rasmi. Menga faqat kitobning nomi va muallifini quyidagi formatda yozib ber: 'Kitob nomi. Muallif'. Boshqa hech qanday so'z qo'shma. Agar muallif ko'rinmasa, 'Noma'lum muallif' deb yoz."
        contents = [prompt, {"mime_type": "image/jpeg", "data": image_data}]
        response = await model.generate_content_async(contents)
        ai_result = response.text.strip()
        
        if "." in ai_result:
            title, author = ai_result.split(".", 1)
        else:
            title = ai_result
            author = "Noma'lum muallif"
            
        data = await state.get_data()
        plan_id = data.get('current_plan_id')
        cursor.execute("INSERT INTO Plan_Books (plan_id, title, author) VALUES (?, ?, ?)", (plan_id, title.strip(), author.strip()))
        conn.commit()
        
        await processing_msg.delete()
        await message.answer(f"✅ <b>AI muvaffaqiyatli aniqladi!</b>\n\n📚 <b>'{title.strip()}'</b> (Muallif: {author.strip()})\n\n<i>Kitob rejangizga qo'shildi!</i>", parse_mode="HTML", reply_markup=get_parent_keyboard())
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
        text = "Sizda hozircha faol rejalar yo'q. Yangi reja tuzish tugmasidan foydalaning."
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(text, reply_markup=get_parent_keyboard())
        else:
            await message_or_callback.message.edit_text(text)
        return
        
    kb = []
    for p in plans:
        cursor.execute("SELECT COUNT(*) FROM Plan_Books WHERE plan_id = ?", (p[0],))
        b_count = cursor.fetchone()[0]
        kb.append([InlineKeyboardButton(text=f"🎯 {p[1]} ({b_count} ta kitob)", callback_data=f"showplan_{p[0]}")])
        
    text = "📚 <b>Sizning faol rejalaringiz.</b>\nQaysi birini ko'rmoqchisiz?"
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)

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
    
    cursor.execute("SELECT book_id, title, author FROM Plan_Books WHERE plan_id = ?", (plan_id,))
    books = cursor.fetchall()
    
    kb = []
    for b in books:
        kb.append([InlineKeyboardButton(text=f"📘 {b[1]}", callback_data=f"showbook_{b[0]}")])
        
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
    await callback.answer("✅ Reja va uning kitoblari o'chirildi!", show_alert=True)
    await show_parent_plans(callback, callback.from_user.id)

@dp.callback_query(F.data.startswith("showbook_"))
async def show_book_details(callback: types.CallbackQuery):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT plan_id, title, author, pages_read FROM Plan_Books WHERE book_id = ?", (book_id,))
    book = cursor.fetchone()
    plan_id = book[0]
    
    kb = [
        [InlineKeyboardButton(text="📝 AI Test tuzish (Rasm orqali)", callback_data=f"aitest_{book_id}")],
        [InlineKeyboardButton(text="🗑 Kitobni o'chirish", callback_data=f"delbook_{book_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"showplan_{plan_id}")]
    ]
    
    text = f"📘 <b>{book[1]}</b>\n✍️ Muallif: {book[2]}\n📖 Farzandingiz o'qidi: {book[3]} bet"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

# ==========================================
# AI TEST TUZISH MANTIG'I (OTA-ONA)
# ==========================================
@dp.callback_query(F.data.startswith("aitest_"))
async def ask_for_test_photo(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    await state.update_data(test_book_id=book_id)
    await callback.message.delete()
    
    text = (
        "📸 <b>AI Test tuzish</b>\n\n"
        "Kitobning ixtiyoriy sahifasini rasmga olib yuboring. "
        "AI ushbu sahifa matnini o'qib, farzandingiz uchun 5 ta qiziqarli test savoli tuzadi."
    )
    await bot.send_message(callback.from_user.id, text, parse_mode="HTML", reply_markup=get_cancel_keyboard())
    await state.set_state(AITestCreation.waiting_for_page_photo)
    await callback.answer()

@dp.message(AITestCreation.waiting_for_page_photo, F.photo)
async def generate_ai_test(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>Gemini AI sahifani o'qib, test tuzmoqda... Iltimos kuting.</i>", parse_mode="HTML")
    
    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        image_data = downloaded_file.read()
        
        prompt = """Bu bolalar kitobining sahifasi. Shu matn asosida bolalar uchun 5 ta oddiy va qiziqarli test savoli tuz. 
        Har bir savolda 3 ta variant (A, B, C) bo'lsin. 
        Natijani FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday so'z qo'shma:
        [
          {"question": "Savol matni?", "options": ["A) variant", "B) variant", "C) variant"], "answer": "A) variant"}
        ]"""
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        contents = [prompt, {"mime_type": "image/jpeg", "data": image_data}]
        response = await model.generate_content_async(contents)
        
        ai_result = response.text.strip()
        if ai_result.startswith("```json"):
            ai_result = ai_result[7:-3].strip()
            
        json.loads(ai_result) 
        
        data = await state.get_data()
        book_id = data.get('test_book_id')
        
        cursor.execute("INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)", (book_id, ai_result))
        conn.commit()
        
        await processing_msg.delete()
        await message.answer("✅ <b>AI Test muvaffaqiyatli tuzildi va bazaga saqlandi!</b>\n\nFarzandingiz ushbu kitobni o'qiyotganda testni yechib, qo'shimcha Bilig 🟡 olishi mumkin.", parse_mode="HTML", reply_markup=get_parent_keyboard())
        await state.clear()
        
    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"❌ <b>Xatolik yuz berdi:</b>\n\nAI test tuza olmadi. Iltimos rasmni tiniqroq oling va qayta urinib ko'ring.\n<code>{str(e)}</code>", parse_mode="HTML", reply_markup=get_parent_keyboard())
        await state.clear()

# ==========================================
# FARZAND UCHUN KITOB O'QISH MENYUSI
# ==========================================
async def show_child_books(message_or_callback, user_id):
    cursor.execute("SELECT parent_id FROM Family_Link WHERE child_id = ?", (user_id,))
    link = cursor.fetchone()
    if not link:
        text = "Siz hali ota-onangizga ulanmagansiz! Iltimos kodni kiriting."
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(text)
        return
        
    parent_id = link[0]
    cursor.execute("SELECT plan_id, name, prize FROM Reading_Plans WHERE parent_id = ? AND status = 'active'", (parent_id,))
    plans = cursor.fetchall()
    
    if not plans:
        text = "Hozircha ota-onangiz sizga reja tuzmagan. Biroz kuting! 😊"
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(text)
        else:
            await message_or_callback.message.edit_text(text)
        return
        
    kb = []
    text = "🦸‍♂️ <b>Qahramon! Ota-onang senga ajoyib reja tuzgan.</b>\n\n"
    has_books = False
    
    for p in plans:
        cursor.execute("SELECT book_id, title, pages_read FROM Plan_Books WHERE plan_id = ?", (p[0],))
        books = cursor.fetchall()
        
        if books:
            text += f"🎯 <b>{p[1]}</b> (Mukofot: {p[2]})\n"
            for b in books:
                kb.append([InlineKeyboardButton(text=f"📘 {b[1]} ({b[2]} bet)", callback_data=f"cread_{b[0]}")])
                has_books = True
            text += "\n"
            
    if not has_books:
        text = "Ota-onangiz reja tuzgan, lekin unga hali kitob qo'shmagan. Iltimos, ota-onangizga ayting, rejaga kitob qo'shsinlar! 😊"
        markup = None
    else:
        text += "👇 Qaysi kitobni o'qishni davom ettiramiz?"
        markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)

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
    test_exists = cursor.fetchone()
    
    if test_exists:
        test_btn = InlineKeyboardButton(text="📝 Testni ishlash (Bilig 🟡)", callback_data=f"take_test_{book_id}")
    else:
        test_btn = InlineKeyboardButton(text="🔒 Test (Hozircha mavjud emas)", callback_data="no_test_alert")
        
    kb = [
        [InlineKeyboardButton(text="📸 Sahifani rasmga olib yuborish", callback_data=f"send_page_{book_id}")],
        [InlineKeyboardButton(text="🎤 Audio xulosa yuborish", callback_data=f"send_audio_{book_id}")],
        [test_btn],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="child_books_main")]
    ]
    
    text = "Ajoyib tanlov! O'qishni boshla. To'xtagan joyingda menga sahifani rasmga olib yubor. Istasang, asar xulosasini so'zlab ber."
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data == "no_test_alert")
async def no_test_alert(callback: types.CallbackQuery):
    await callback.answer("🔒 Ota-onangiz bu kitob uchun hali test tuzmagan. O'qishda davom eting!", show_alert=True)

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
