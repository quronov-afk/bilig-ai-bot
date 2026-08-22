import os
import sqlite3
import asyncio
import threading
import traceback # XATONI ANIQ KO'RSATUVCHI KUTUBXONA
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
    kb = [[KeyboardButton(text="📝 Mutolaa rejasini tuzish"), KeyboardButton(text="📊 Farzandim natijalari")],
          [KeyboardButton(text="🎁 Mukofotlar")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_child_keyboard():
    kb = [[KeyboardButton(text="📖 Kitob o'qish")],
          [KeyboardButton(text="👤 Mening Qahramonim"), KeyboardButton(text="🏆 Reyting")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_add_book_keyboard():
    kb = [[InlineKeyboardButton(text="👶 Yosh bo'yicha tavsiyalar", callback_data="add_book_age")],
          [InlineKeyboardButton(text="✍️ Matn orqali qo'shish", callback_data="add_book_text")],
          [InlineKeyboardButton(text="📸 Rasm orqali (AI Vision)", callback_data="add_book_photo")]]
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

# ==========================================
# 5. TELEGRAM BOT MANTIG'I
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=TOKEN)
dp = Dispatcher()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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

@dp.callback_query(F.data == "rewards_store_edit")
async def rewards_store_callback(callback: types.CallbackQuery):
    await callback.answer("Tez kunda! Bu bo'lim orqali farzandingiz uchun maxsus sovg'alar do'konini yaratasiz.", show_alert=True)

@dp.callback_query(F.data.startswith("rate_"))
async def process_rate_callback(callback: types.CallbackQuery, state: FSMContext):
    rate_val = callback.data.split("_")[1]
    if rate_val == "custom":
        await callback.message.edit_text("✍️ <b>Iltimos, 1 ta Bilig (🟡) uchun summani raqamlarda kiriting:</b>\n<i>(Masalan: 2000)</i>", parse_mode="HTML")
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
    await message.answer(f"✅ <b>Bilig kursi muvaffaqiyatli o'rnatildi!</b>\n\nEndi 1 🟡 = {rate} so'm.", parse_mode="HTML")
    await state.clear()

# ==========================================
# MUTOLAA REJASINI TUZISH MANTIG'I
# ==========================================
@dp.message(F.text == "📝 Mutolaa rejasini tuzish")
async def create_plan_start(message: types.Message, state: FSMContext):
    text = (
        "📝 <b>Mutolaa rejasi nima?</b>\n\n"
        "Bu farzandingiz uchun maxsus <b>'Kitobxonlik marafoni'</b> dir. Siz unga o'qilishi kerak bo'lgan kitoblarni, muddatni va oxirida beriladigan Katta Mukofotni belgilaysiz.\n\n"
        "<i>Bu nima beradi?</i> Bola maqsadsiz emas, balki aniq bir marra (masalan, Velosiped yutish) sari intiladi.\n\n"
        "👇 <b>1-qadam:</b> Rejaga qanday nom berasiz?\n"
        "<i>(Masalan: 'Yozgi ta'til mutolaasi', 'Tug'ilgan kun sovg'asi uchun')</i>"
    )
    await message.answer(text, parse_mode="HTML")
    await state.set_state(PlanCreation.waiting_for_name)

@dp.message(PlanCreation.waiting_for_name)
async def plan_name_received(message: types.Message, state: FSMContext):
    await state.update_data(plan_name=message.text)
    text = (
        "🎁 <b>2-qadam: Katta Mukofot!</b>\n\n"
        "Bu reja to'liq tugatilganda farzandingiz qanday katta sovg'a oladi?\n"
        "<i>(Masalan: 'Velosiped', 'Parkka borish', '5000 🟡')</i>"
    )
    await message.answer(text, parse_mode="HTML")
    await state.set_state(PlanCreation.waiting_for_prize)

@dp.message(PlanCreation.waiting_for_prize)
async def plan_prize_received(message: types.Message, state: FSMContext):
    await state.update_data(plan_prize=message.text)
    text = (
        "⏳ <b>3-qadam: Muddat (Deadline)</b>\n\n"
        "Rejani qachongacha tugatish kerak?\n"
        "<i>(Masalan: '1 oyda', '31-Avgustgacha')</i>"
    )
    await message.answer(text, parse_mode="HTML")
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
    
    text = (
        f"✅ <b>Reja muvaffaqiyatli yaratildi!</b>\n\n"
        f"📌 <b>Nom:</b> {plan_name}\n"
        f"🎁 <b>Mukofot:</b> {plan_prize}\n"
        f"⏳ <b>Muddat:</b> {plan_deadline}\n\n"
        f"📚 <b>Endi bu rejaga kitoblar qo'shamiz!</b>\n"
        f"Siz qo'shgan kitoblar farzandingizning botida ro'yxat bo'lib ko'rinadi. U shu ro'yxatdan o'ziga yoqqanini tanlab, o'qishni boshlaydi. Xohlasangiz 1 ta, xohlasangiz 10 ta kitob qo'shishingiz mumkin.\n\n"
        f"👇 <i>Qaysi usuldan foydalanasiz?</i>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_add_book_keyboard())

# --- MATN ORQALI QO'SHISH ---
@dp.callback_query(F.data == "add_book_text")
async def add_book_text_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ <b>Matn orqali qo'shish</b>\n\nKitob nomi va muallifini nuqta bilan ajratib yozing:\n<i>Masalan: O'tkan kunlar. Abdulla Qodiriy</i>", parse_mode="HTML")
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
    await message.answer(f"📚 <b>'{title.strip()}'</b> kitobi rejangizga qo'shildi!\n\nYana kitob qo'shasizmi?", parse_mode="HTML", reply_markup=get_add_book_keyboard())

# --- RASM ORQALI QO'SHISH (GEMINI AI VISION) ---
@dp.callback_query(F.data == "add_book_photo")
async def add_book_photo_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📸 <b>Rasm orqali qo'shish</b>\n\nKitobning muqovasini (ustki qismini) rasmga olib yuboring. AI o'zi kitob nomi va muallifini aniqlaydi!", parse_mode="HTML")
    await state.set_state(PlanCreation.waiting_for_book_photo)
    await callback.answer()

@dp.message(PlanCreation.waiting_for_book_photo, F.photo)
async def process_book_photo(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>Gemini AI rasmni tahlil qilmoqda... Iltimos kuting.</i>", parse_mode="HTML")
    
    if not GEMINI_API_KEY:
        await processing_msg.edit_text("❌ GEMINI_API_KEY topilmadi. Iltimos Render sozlamalarini tekshiring.")
        return

    try:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        image_data = downloaded_file.read()
        
        # Siz aytgan aniq model nomini kiritdik
        model = genai.GenerativeModel('gemini-3.6-flash')
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
        
        await processing_msg.edit_text(f"✅ <b>AI muvaffaqiyatli aniqladi!</b>\n\n📚 <b>'{title.strip()}'</b> (Muallif: {author.strip()})\n\n<i>Kitob rejangizga qo'shildi! Yana kitob qo'shasizmi?</i>", parse_mode="HTML", reply_markup=get_add_book_keyboard())
    
    except Exception as e:
        # XATONI ANIQ KO'RSATUVCHI QISM
        error_traceback = traceback.format_exc()
        error_msg = (
            f"❌ <b>XATOLIK YUZ BERDI:</b>\n\n"
            f"<code>{str(e)}</code>\n\n"
            f"<b>Diagnostika logi:</b>\n"
            f"<code>{error_traceback[-800:]}</code>"
        )
        await processing_msg.edit_text(error_msg, parse_mode="HTML", reply_markup=get_add_book_keyboard())
        print(error_traceback)

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
