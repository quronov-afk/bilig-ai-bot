import os
import sqlite3
import asyncio
import threading
import traceback
import json
import uuid
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import google.generativeai as genai

# ==========================================
# LOYIHA MUALLIFI XAVFSIZLIK ID (RENDER ENV)
# ==========================================
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# ==========================================
# TAVSIYA ETILGAN ASARLAR MA'LUMOTLARI
# ==========================================
RECOMMENDED_BOOKS = {
    "3": [
        "O‘zbek xalq ertaklari",
        "Kuchukning hikoyasi. Anvar Obidjon.",
        "Buzoqning hikoyasi. Anvar Obidjon.",
        "Xorazmiy. 0 bilan tanishuv. Dinara Muminova.",
        "Beruniy. Sahrodagi qahramon. Saʼdullo Quronov.",
        "Ibn Sino. Oʻsimliklar bilan tanishuv. Nilufar Jabborova.",
        "Alisher. Maktabda birinchi kun. Dilnavoz Najimova.",
        "Toʻmaris. Tovuqni kim oʻgʻirladi?. Dinara Muminova.",
        "Bobur. Hindistonda. Gulnoz Tojiboyeva.",
        "Amir Temur. Qilichsiz gʻalaba. Qobiljon Shermatov.",
        "Forobiy. Gulnoz Tojiboyeva.",
        "Ulugʻbek. Kiyik ovida. Qobiljon Shermatov.",
        "Mushukchaning hikoyasi. Anvar Obidjon.",
        "Quyonchaning hikoyasi. Anvar Obidjon.",
        "Xoʻtikning hikoyasi. Anvar Obidjon.",
        "Toshbaqaning hikoyasi. Anvar Obidjon.",
        "Assalomu alaykum. Vasiliy Suxomlinskiy.",
        "Yetti qiz. Vasiliy Suxomlinskiy."
    ],
    "6": [
        "Joʻjaning hikoyasi. Anvar Obidjon.",
        "Tulkichaning hikoyasi. Anvar Obidjon.",
        "Choʻchqachaning hikoyasi. Anvar Obidjon.",
        "Hakkaning hikoyasi. Anvar Obidjon.",
        "Chumolining hikoyasi. Anvar Obidjon.",
        "Qurbaqaning hikoyasi. Anvar Obidjon.",
        "Uloqchaning hikoyasi. Anvar Obidjon.",
        "Bu sizga, oyijon. Yoqut Rahimova.",
        "Suv va daraxt. Zamira Ibrohimova.",
        "Bir bor ekan, pul bor ekan. Namoz Saʼdullayev.",
        "Bola va pul. Gʻiyosiddin Yusuf.",
        "Goʻzal xulqlar. Gʻiyosiddin Yusuf.",
        "Kundalik odoblar. Gʻiyosiddin Yusuf.",
        "Hayvonlar haqida hikoyalar. Aziz Nesin.",
        "Olmaxonning xotirasi. Mixail Prishvin.",
        "Jiblajibonning xatlari. Nikolay Sladkov.",
        "Assalomu alaykum. Vasiliy Suxomlinskiy.",
        "Odam boʻlish qiyin. Vasiliy Suxomlinskiy.",
        "Yetti qiz. Vasiliy Suxomlinskiy.",
        "Uzunquloq. Georgiy Skrebitskiy.",
        "Oʻgʻrivoy. Georgiy Skrebitskiy.",
        "Buyuk sayohatchilar. Mixail Zoshchenko.",
        "Pinokkioning boshidan kechirganlari. Karlo Kollodi.",
        "Maugli. Jozef Redyard Kipling.",
        "Bilmasvoy va doʻstlarining boshidan kechirganlari. Nikolay Nosov."
    ],
    "8": [
        "Oltin yurakli avtobola. Anvar Obidjon.",
        "Alamazon va uning piyodalari. Anvar Obidjon.",
        "0099 raqamli yolgʻonchi. Anvar Obidjon.",
        "Meshpolvonning janglari. Anvar Obidjon.",
        "Pashshavoyning boshidan kechirganlari. Anvar Obidjon.",
        "Futbol toʻpining sarguzashtlari. Anvar Obidjon.",
        "Moʻttivoymisan, Mittivoymisan?. Anvar Obidjon.",
        "Galaktikada bir kun 1-2-3. Saʼdulla Quronov.",
        "Shaytonvachchaning nayranglari. Erkin Malik.",
        "7-“A” da. Erkin Malik.",
        "Champo otli ilon. Erkin Malik.",
        "Qaldirgʻoch. Erkin Malik.",
        "Quyonlar saltanati. Xudoyberdi Toʻxtaboyev.",
        "Shirin qovunlar mamlakati. Xudoyberdi Toʻxtaboyev.",
        "Sehrli qalpoqcha. Xudoyberdi Toʻxtaboyev.",
        "Qaylardasan, bolaligim. Xudoyberdi Toʻxtaboyev.",
        "Changalzor iti. Normurod Norqobilov.",
        "Belbogʻ. Normurod Norqobilov.",
        "Paxmoq. Normurod Norqobilov.",
        "Amir Temur haqida hikoyalar. Toʻlqin Hayit.",
        "Olimjonning sarguzashtlari. Otabek Quvvatov.",
        "Ulugʻbek yulduzlar saltanatida. Otabek Quvvatov.",
        "Akramning sarguzashtlari. Pirimqul Qodirov.",
        "Ajab qishloq. Ergash Raimov.",
        "Chillak oʻyin. Shukur Xolmirzayev.",
        "Oqtosh. Shukur Xolmirzayev.",
        "Sulaymon ovchi va uning iti haqida. Sunnatulla Anorboyev.",
        "Yalpiz somsa. Oʻtkir Hoshimov.",
        "Shaytonni tutgan Shertoy. Abror Qoʻshnazarov.",
        "Boychechak. Abdusaid Koʻchimov.",
        "Hovlidagi maydoncha. Abdusaid Koʻchimov.",
        "Raqamlar sarguzashtlari. Saidqul Uspanov.",
        "Kichkina shahzoda. Antuan de Sent-Ekzyuperi.",
        "Yovvoyi yoʻrgʻa. Ernest Seton-Tompson.",
        "Domino. Ernest Seton-Tompson.",
        "Lobo. Ernest Seton-Tompson.",
        "Springfild tulkisi. Ernest Seton-Tompson.",
        "Chink. Ernest Seton-Tompson.",
        "Jonni laqabli ayiqcha. Ernest Seton-Tompson.",
        "Bingo. Ernest Seton-Tompson.",
        "Bugʻular izidan. Ernest Seton-Tompson.",
        "Snap. Ernest Seton-Tompson.",
        "Arno. Ernest Seton-Tompson.",
        "Bilmasvoy va doʻstlarining boshidan kechirganlari. Nikolay Nosov.",
        "Bilmasvoy quyosh shahrida. Nikolay Nosov.",
        "Pinokkioning boshidan kechirganlari. Karlo Kollodi.",
        "Buratino va uning sarguzashtlari. Aleksey Tolstoy.",
        "Tom Soyerning boshidan kechirganlari. Mark Tven.",
        "Tom Soyerning yangi sarguzashtlari. Mark Tven.",
        "Antiqa qurbaqa. Mark Tven.",
        "Alisaning sayohatlari. Kir Bulichev.",
        "Gʻaroyib bolalar. Aziz Nesin.",
        "Vinni Pux va uning sarguzashtlari. Alan Aleksandr Miln.",
        "Maugli. Jozef Redyard Kipling.",
        "Robinzonlar maktabi. Jyul Vern.",
        "Muzlar iskanjasida. Jyul Vern.",
        "Oʻqituvchi odam boʻlgan ekan. Ayzek Azimov.",
        "Men, buvim, Iliko va Illarion. Nodar Dumbadze.",
        "Anton boʻrini uchratgan kecha. Edith Shrayber Vike.",
        "Teddi. Yuriy Kazakov.",
        "Hikoyalar. Jek London.",
        "Baron Myunxauzenning sarguzashtlari. Erix Raspe.",
        "Maysajonning sarguzashtlari. Sergey Rozanov.",
        "Lider bola. Gʻiyosiddin Yusuf.",
        "Kundalik odoblar. Gʻiyosiddin Yusuf.",
        "Stiv Jobs. Navroʻz Ergash oʻgʻli.",
        "Muhammad Ali. Navroʻz Ergash oʻgʻli.",
        "Leonardo da Vinchi. Navroʻz Ergash oʻgʻli.",
        "Motsart. Navroʻz Ergash oʻgʻli.",
        "Albert Eynshteyn. Navroʻz Ergash oʻgʻli."
    ],
    "12": [
        "Sariq devni minib. Xudoyberdi Toʻxtaboyev.",
        "Qasoskorning oltin boshi. Xudoyberdi Toʻxtaboyev.",
        "Besh bolali yigitcha. Xudoyberdi Toʻxtaboyev.",
        "Shum bola. Gʻafur Gʻulom.",
        "Oʻtmishdan ertaklar. Abdulla Qahhor.",
        "Dunyoning ishlari. Oʻtkir Hoshimov.",
        "Galaktikada bir kun 1-2-3. Saʼdulla Quronov.",
        "Ot kishnagan oqshom. Togʻay Murod.",
        "Bolalik xotiralarim. Oybek.",
        "Jayhun ustida bulutlar. Mirkarim Osim.",
        "Zulmat ichra nur. Mirkarim Osim.",
        "Nur va zulmat. Mirkarim Osim.",
        "Olmos jilosi. Hojiakbar Shayxov.",
        "Afandining qirq bir pashshasi. Zohir Aʼlam.",
        "Boʻsh kelma, Aliqulov!. Farhod Musajonov.",
        "Qaysar bolaning hayoti. Mirzakalon Ismoiliy.",
        "Yonar daryo. Hakim Nazir.",
        "Kenjatoy. Hakim Nazir.",
        "Eski maktab. Sadriddin Ayniy.",
        "Jadidlar. Abdulla Qodiriy. Bahodir Karimov.",
        "Jadidlar. Abdulhamid Choʻlpon. Dilmurod Quronov.",
        "Jadidlar. Abdurauf Fitrat. Hamidulla Boltaboyev.",
        "Jadidlar. Abdulla Avloniy. Olim Oltinbek.",
        "Jadidlar. Isʼhoqxon toʻra Ibrat. Ulugʻbek Dolimov.",
        "Uygʻonish. Abu Ali ibn Sino. Abdulqodir Zohidiy.",
        "Uygʻonish. Abu Rayhon Beruniy. Abror Xidirov.",
        "Uygʻonish. Ahmad al-Fargʻoniy. Ashraf Ahmedov.",
        "Uygʻonish. Muso al-Xorazmiy. Ashraf Ahmedov.",
        "Kichkina shahzoda. Antuan de Sent-Ekzyuperi.",
        "Oʻn besh yoshli kapitan. Jyul Vern.",
        "Kapitan Grant bolalari. Jyul Vern.",
        "Klodius Bombarnak. Jyul Vern.",
        "Robinzonlar maktabi. Jyul Vern.",
        "Oliver Tvistning boshidan kechirganlari. Charlz Dikkens.",
        "Shahzoda va gado. Mark Tven.",
        "Tom Soyerning boshidan kechirganlari. Mark Tven.",
        "Gulliverning sayohatlari. Jonatan Svift.",
        "Merosxoʻr. Robert Luis Stivenson.",
        "Kapitan Vrungelning sarguzashtlari. Andrey Nekrasov.",
        "Birinchi muallim. Chingiz Aytmatov.",
        "Bolaligim. Chingiz Aytmatov.",
        "Fransuz tili saboqlari. Valentin Rasputin.",
        "Bir kunlik yoz. Rey Bredberi.",
        "Kavkaz asiri. Lev Tolstoy.",
        "Quyoshni koʻryapman. Nodar Dumbadze.",
        "Men, buvim, Iliko va Illarion. Nodar Dumbadze.",
        "Eski telefon. Pol Villard.",
        "Yoz bilan xayrlashuv. Konstantin Paustovskiy.",
        "Vaqtni qoʻyib yuboring!. Janni Rodari.",
        "Maktab alamlari va zavqlari. Orxan Pamuk.",
        "Marko Poloning ajoyib va gʻaroyib sarguzashtlari. Villi Maynk.",
        "Yovvoyi yoʻrgʻa. Ernest Seton-Tompson.",
        "Domino. Ernest Seton-Tompson.",
        "Lobo. Ernest Seton-Tompson."
    ]
}

MUTOLAA_NOTE = "\n\n💡 <i>Izoh: Agarda ushbu kitoblarni bosma shaklda topa olmasangiz, ularni 'Mutolaa' ilovasida elektron o'qish yoki tinglash shaklida topishingiz mumkin.</i>"

WELCOME_TEXT = (
    "👋 <b>Bilig AI ga xush kelibsiz!</b>\n\n"
    "Ushbu bot bolalar yozuvchisi <b>Sa'dullo Quronov</b> tomonidan farzandiga kitob o'qitishda qiynalayotgan ota-onalarga yordam berish uchun yaratildi.\n\n"
    "🎯 <b>Qanday ishlaydi?</b>\n"
    "📖 <b>Bola o'qiydi</b> ➡️ 🤖 <b>AI tekshirib \"Bilig\" (🔅 oltin tanga) beradi</b> ➡️ 🎁 <b>Bola tangalariga siz belgilagan sovg'alarni oladi!</b>\n\n"
    "Kitob o'qish endi urush-janjal emas, qiziqarli o'yin! 🚀\n\n"
    "👇 <b>Boshlash uchun kimsiz?</b>"
)

# GEMINI MODELI NOMI
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

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
    cursor.execute('''CREATE TABLE IF NOT EXISTS Reading_Logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT, child_id INTEGER, book_id INTEGER, pages_added INTEGER, created_at TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS Invite_Links (
        code TEXT PRIMARY KEY, is_used INTEGER DEFAULT 0, used_by INTEGER)''')
    
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
    try: cursor.execute("ALTER TABLE Reading_Plans ADD COLUMN child_id INTEGER")
    except: pass
    
    conn.commit()

def clean_json(text):
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    elif text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()

# ==========================================
# ADMIN STATISTIKA MATNINI GENERATSIYA QILISH
# ==========================================
def generate_admin_stats_text():
    cursor.execute("SELECT COUNT(*) FROM Users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Users WHERE role = 'parent'")
    total_parents = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Users WHERE role = 'child'")
    total_children = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Family_Link")
    total_families = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Reading_Plans")
    total_plans = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Reading_Plans WHERE status = 'completed'")
    completed_plans = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Plan_Books")
    total_books = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Plan_Books WHERE is_completed = 1")
    completed_books = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(pages_read) FROM Plan_Books")
    res_pages = cursor.fetchone()[0]
    total_pages = res_pages if res_pages else 0

    cursor.execute("SELECT SUM(balance_coins) FROM Users WHERE role = 'child'")
    res_coins = cursor.fetchone()[0]
    total_coins = res_coins if res_coins else 0

    cursor.execute("SELECT COUNT(*) FROM Book_Tests")
    total_tests = cursor.fetchone()[0]

    cursor.execute("SELECT user_id, name, role FROM Users WHERE role IS NOT NULL ORDER BY user_id DESC LIMIT 5")
    recent_users = cursor.fetchall()
    recent_text = ""
    for u in recent_users:
        r_icon = "👨‍👩‍👦" if u[2] == 'parent' else ("👦👧" if u[2] == 'child' else "👤")
        recent_text += f"• {r_icon} <b>{u[1]}</b> (ID: <code>{u[0]}</code>)\n"

    if not recent_text:
        recent_text = "• Hozircha foydalanuvchilar yo'q.\n"

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    text = (
        f"👑 <b>LOYIHA MUALLIFI STATISTIKASI</b>\n"
        f"<i>Bilig AI platformasi ko'rsatkichlari ({now_str})</i>\n\n"
        f"👥 <b>FOYDALANUVCHILAR:</b>\n"
        f"• Jami foydalanuvchilar: <b>{total_users} ta</b>\n"
        f"  └ 👨‍👩‍👦 Ota-onalar: <b>{total_parents} ta</b>\n"
        f"  └ 👦👧 O'quvchilar: <b>{total_children} ta</b>\n"
        f"  └ 🔗 Bog'langan oilalar: <b>{total_families} ta</b>\n\n"
        f"📖 <b>MUTOLAA VA KITOBLAR:</b>\n"
        f"• Jami mutolaa rejalari: <b>{total_plans} ta</b> (Tugatilgan: {completed_plans})\n"
        f"• Rejalardagi kitoblar: <b>{total_books} ta</b> (Tugatilgan: {completed_books})\n"
        f"• 📚 Jami o'qilgan sahifalar: <b>{total_pages} bet</b>\n\n"
        f"🔅 <b>FAOLLIK VA BILIG:</b>\n"
        f"• Bolalardagi jami Biliglar: <b>{total_coins} 🔅</b>\n"
        f"• AI orqali tuzilgan testlar: <b>{total_tests} ta</b>\n\n"
        f"🆕 <b>Oxirgi a'zo bo'lganlar:</b>\n{recent_text}"
    )
    return text

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
          [KeyboardButton(text="📊 Farzandim natijalari"), KeyboardButton(text="🎁 Mukofotlar")],
          [KeyboardButton(text="📞 Qayta aloqa")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_child_keyboard():
    kb = [[KeyboardButton(text="📖 Kitob o'qish")],
          [KeyboardButton(text="🎁 Sovrinlarim"), KeyboardButton(text="🏆 Reyting")],
          [KeyboardButton(text="📞 Qayta aloqa")]]
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
        [InlineKeyboardButton(text="🔅 Bilig kursini belgilash", callback_data="rewards_bilig_rate")],
        [InlineKeyboardButton(text="🛍 Sovg'alar do'konini tahrirlash", callback_data="rewards_store_edit")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_bilig_rate_inline_keyboard():
    kb = [
        [InlineKeyboardButton(text="🔅 500 so'm", callback_data="rate_500"),
         InlineKeyboardButton(text="🔅 1,000 so'm", callback_data="rate_1000")],
        [InlineKeyboardButton(text="🔅 5,000 so'm", callback_data="rate_5000"),
         InlineKeyboardButton(text="🔅 10,000 so'm", callback_data="rate_10000")],
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
    waiting_for_coin_deduction = State()
class PlanCreation(StatesGroup):
    waiting_for_child = State()
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
class Feedback(StatesGroup):
    waiting_for_message = State()

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

def get_parent_id(child_id):
    cursor.execute("SELECT parent_id FROM Family_Link WHERE child_id = ?", (child_id,))
    res = cursor.fetchone()
    return res[0] if res else None

def update_streak(user_id):
    cursor.execute("SELECT streak_days, last_read_date FROM Users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row: return 0
    streak, last_date_str = row
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    today = datetime.strptime(today_str, "%Y-%m-%d").date()

    if last_date_str == today_str:
        return streak 
        
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

# ==========================================
# KUNLIK AVTOMATIK MOTIVATSIYA VA SCHEDULER
# ==========================================
async def daily_reminder_scheduler():
    while True:
        try:
            now = datetime.now()
            # Har kuni kechqurun soat 19:00 da tekshiradi
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
                            f"Bugun ham kamida 2 bet o'qib, olovni 🔥 o'chirmaslikka harakat qiling va yangi 🔅 Biliglar ishlang! ✨"
                        )
                        try:
                            await bot.send_message(c_id, msg, parse_mode="HTML")
                        except Exception:
                            pass
                # Qayta jo'natmaslik uchun 1 soat uxlaydi
                await asyncio.sleep(3600)
            else:
                await asyncio.sleep(1800) # 30 minutda bir soatni tekshiradi
        except Exception as e:
            print(f"Scheduler error: {e}")
            await asyncio.sleep(300)

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
# ADMIN BUYRUQLARI (/stats, /invite, /reply)
# ==========================================
@dp.message(Command("stats"))
@dp.message(Command("admin"))
async def admin_stats_handler(message: types.Message):
    user_id = message.from_user.id
    if OWNER_ID != 0 and user_id != OWNER_ID:
        return  

    stats_text = generate_admin_stats_text()
    if OWNER_ID == 0:
        stats_text += f"\n\n⚙️ <i>Eslatma: Xavfsizlik uchun Render.com'da Environment Variables qismiga <b>OWNER_ID={user_id}</b> o'zgaruvchisini qo'shing.</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh_stats")]
    ])
    await message.answer(stats_text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(F.data == "admin_refresh_stats")
async def refresh_admin_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if OWNER_ID != 0 and user_id != OWNER_ID:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return
        
    stats_text = generate_admin_stats_text()
    if OWNER_ID == 0:
        stats_text += f"\n\n⚙️ <i>Eslatma: Xavfsizlik uchun Render.com'da Environment Variables qismiga <b>OWNER_ID={user_id}</b> o'zgaruvchisini qo'shing.</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh_stats")]
    ])
    
    try:
        await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer("Statistika yangilandi!")

@dp.message(Command("invite"))
async def generate_invite_link(message: types.Message):
    if OWNER_ID != 0 and message.from_user.id != OWNER_ID:
        return
        
    code = str(uuid.uuid4())[:8]
    cursor.execute("INSERT INTO Invite_Links (code) VALUES (?)", (code,))
    conn.commit()
    
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"
    
    await message.answer(f"🔗 <b>Bir martalik taklif havolasi yaratildi:</b>\n\n<code>{link}</code>\n\n<i>Ushbu havola orqali faqat 1 kishi ro'yxatdan o'ta oladi.</i>", parse_mode="HTML")

@dp.message(Command("reply"))
async def admin_reply_handler(message: types.Message, command: CommandObject):
    if OWNER_ID != 0 and message.from_user.id != OWNER_ID:
        return
        
    if not command.args:
        await message.answer("⚠️ <b>Foydalanish:</b> /reply <foydalanuvchi_id> <matn>", parse_mode="HTML")
        return
        
    parts = command.args.split(" ", 1)
    if len(parts) < 2:
        await message.answer("⚠️ <b>Foydalanish:</b> /reply <foydalanuvchi_id> <matn>", parse_mode="HTML")
        return
        
    user_id, text = parts[0], parts[1]
    
    try:
        await bot.send_message(int(user_id), f"👨‍💻 <b>Admindan javob:</b>\n\n{text}", parse_mode="HTML")
        await message.answer("✅ Javob muvaffaqiyatli yuborildi!")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}")

# ==========================================
# QAYTA ALOQA (FEEDBACK) TIZIMI
# ==========================================
@dp.message(F.text == "📞 Qayta aloqa")
async def feedback_start(message: types.Message, state: FSMContext):
    await message.answer("✍️ <b>Qayta aloqa</b>\n\nBot haqida fikrlaringiz, takliflaringiz yoki xatoliklar bo'lsa, shu yerda yozib qoldiring (rasm yoki video ham yuborishingiz mumkin).\n\nXabaringiz to'g'ridan-to'g'ri loyiha muallifiga yuboriladi.", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(Feedback.waiting_for_message)

@dp.message(Feedback.waiting_for_message)
async def feedback_receive(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await cancel_handler(message, state)
        return
        
    if OWNER_ID == 0:
        await message.answer("⚠️ Adminga xabar yuborish sozlanmagan (OWNER_ID kiritilmagan).")
        await state.clear()
        return
        
    cursor.execute("SELECT role FROM Users WHERE user_id = ?", (message.from_user.id,))
    role_row = cursor.fetchone()
    role = role_row[0] if role_row else "Noma'lum"
    
    user_info = f"📩 <b>YANGI XABAR (Qayta aloqa)</b>\n\n"
    user_info += f"👤 <b>Yuboruvchi:</b> {message.from_user.full_name}\n"
    user_info += f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
    user_info += f"🎭 <b>Rol:</b> {role}\n\n"
    user_info += f"<i>Javob yozish uchun:</i>\n<code>/reply {message.from_user.id} matn</code>"
    
    try:
        await bot.send_message(OWNER_ID, user_info, parse_mode="HTML")
        await message.copy_to(OWNER_ID)
        
        kb = get_parent_keyboard() if role == 'parent' else get_child_keyboard()
        await message.answer("✅ Xabaringiz adminga muvaffaqiyatli yuborildi! Fikringiz uchun rahmat!", reply_markup=kb)
    except Exception as e:
        await message.answer("❌ Xabar yuborishda xatolik yuz berdi.")
        
    await state.clear()

# ==========================================
# START VA YOPIQ TEST RUXSATI
# ==========================================
@dp.message(CommandStart())
async def start_handler(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
    
    # 1. DEEP-LINK (Bir martalik havola) ORQALI KIRISHNI TEKSHIRISH
    if command.args:
        code = command.args
        cursor.execute("SELECT is_used FROM Invite_Links WHERE code = ?", (code,))
        link_row = cursor.fetchone()
        if link_row:
            if link_row[0] == 0:
                # Havola to'g'ri va ishlatilmagan
                cursor.execute("UPDATE Invite_Links SET is_used = 1, used_by = ? WHERE code = ?", (message.from_user.id, code))
                cursor.execute("INSERT OR IGNORE INTO Users (user_id, name, is_approved) VALUES (?, ?, 1)", (message.from_user.id, message.from_user.full_name))
                cursor.execute("UPDATE Users SET is_approved = 1 WHERE user_id = ?", (message.from_user.id,))
                conn.commit()
                
                kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O'quvchiman")]]
                await message.answer(f"✅ <b>Maxsus taklif havolasi qabul qilindi!</b>\n\n{WELCOME_TEXT}", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
                return
            else:
                await message.answer("❌ Bu taklif havolasi allaqachon ishlatilgan!")
                return
    
    # 2. ODATIY KIRISH (Bazada bor-yo'qligini tekshirish)
    cursor.execute("SELECT role, is_approved FROM Users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if user and user[1] == 1:
        if user[0] == 'parent':
            await message.answer("<b>Asosiy menyuga xush kelibsiz!</b> 👨‍👩‍👦", parse_mode="HTML", reply_markup=get_parent_keyboard())
        elif user[0] == 'child':
            await message.answer("<b>Asosiy menyuga xush kelibsiz, Qahramon!</b> 🦸‍♂️🦸‍♀️", parse_mode="HTML", reply_markup=get_child_keyboard())
        else:
            kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O'quvchiman")]]
            await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
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
        await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
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
    text = "🔅 <b>Bilig kursini belgilash</b>\n\n1 ta Bilig (🔅) necha so'mga teng ekanligini tanlang."
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_bilig_rate_inline_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("rate_"))
async def process_rate_callback(callback: types.CallbackQuery, state: FSMContext):
    rate_val = callback.data.split("_")[1]
    if rate_val == "custom":
        await callback.message.delete()
        await bot.send_message(callback.from_user.id, "✍️ <b>Iltimos, 1 ta Bilig (🔅) uchun summani kiriting:</b>\n<i>(Masalan: 1000, 5000)</i>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
        await state.set_state(ParentSettings.waiting_for_custom_rate)
        return
    rate = int(rate_val)
    cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, callback.from_user.id))
    conn.commit()
    
    if rate == 0:
        await callback.message.edit_text("✅ <b>Siz pul bilan rag'batlantirmaslik rejimini tanladingiz!</b>\n\nEndi farzandingiz faqat nishonlar, reyting va bilim uchun o'qiydi. Bu juda zo'r tanlov! 🧠", parse_mode="HTML", reply_markup=get_rewards_main_keyboard())
    else:
        await callback.message.edit_text(f"✅ <b>Bilig kursi o'rnatildi!</b>\n1 🔅 = {rate} so'm.", parse_mode="HTML", reply_markup=get_rewards_main_keyboard())
    await callback.answer()

@dp.message(ParentSettings.waiting_for_custom_rate)
async def process_custom_rate(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return
    rate = int(message.text)
    cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, message.from_user.id))
    conn.commit()
    await message.answer(f"✅ <b>Bilig kursi o'rnatildi!</b>\n1 🔅 = {rate} so'm.", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await state.clear()

# DO'KONNI TAHRIRLASH
@dp.callback_query(F.data == "rewards_store_edit")
async def store_edit_callback(callback: types.CallbackQuery):
    cursor.execute("SELECT item_id, name, price FROM Store_Items WHERE parent_id = ?", (callback.from_user.id,))
    items = cursor.fetchall()
    
    kb = []
    for item in items:
        kb.append([InlineKeyboardButton(text=f"❌ {item[1]} ({item[2]} 🔅)", callback_data=f"delitem_{item[0]}")])
        
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
    try: await callback.message.delete()
    except Exception: pass
    await bot.send_message(callback.from_user.id, "✍️ <b>Sovg'a nomini kiriting:</b>\n<i>(Masalan: Muzqaymoq, Parkka borish)</i>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(StoreSettings.waiting_for_item_name)
    await callback.answer()

@dp.message(StoreSettings.waiting_for_item_name)
async def store_item_name(message: types.Message, state: FSMContext):
    await state.update_data(item_name=message.text)
    await message.answer("💰 <b>Bu sovg'a necha Bilig (🔅) turadi?</b>\nFaqat raqam kiriting:\n<i>(Masalan: 50, 100)</i>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(StoreSettings.waiting_for_item_price)

@dp.message(StoreSettings.waiting_for_item_price)
async def store_item_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return
    data = await state.get_data()
    cursor.execute("INSERT INTO Store_Items (parent_id, name, price) VALUES (?, ?, ?)", (message.from_user.id, data['item_name'], int(message.text)))
    conn.commit()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yana sovg'a qo'shish", callback_data="add_store_item")],
        [InlineKeyboardButton(text="🔙 Do'konga qaytish", callback_data="rewards_store_edit")]
    ])
    await message.answer(f"✅ <b>{data['item_name']}</b> do'konga qo'shildi!\n\nYana sovg'a qo'shasizmi?", parse_mode="HTML", reply_markup=kb)
    await state.clear()

# ==========================================
# MUTOLAA REJASINI TUZISH MANTIG'I
# ==========================================
@dp.message(F.text == "📝 Mutolaa rejasini tuzish")
async def create_plan_start(message: types.Message, state: FSMContext):
    cursor.execute("SELECT child_id FROM Family_Link WHERE parent_id = ?", (message.from_user.id,))
    children = cursor.fetchall()
    
    if not children:
        await message.answer("⚠️ Sizga hali hech qaysi farzand ulanmagan. Iltimos, avval farzandingizni ulang.")
        return
        
    if len(children) == 1:
        await state.update_data(plan_child_id=children[0][0])
        text = "📝 <b>Mutolaa rejasi nima?</b>\n\n👇 <b>1-qadam:</b> Rejaga qanday nom berasiz?\n<i>(Masalan: 'Yozgi ta'til mutolaasi', 'Tug'ilgan kun sovg'asi uchun')</i>"
        await message.answer(text, parse_mode="HTML", reply_markup=get_back_reply_keyboard())
        await state.set_state(PlanCreation.waiting_for_name)
    else:
        kb = []
        for c in children:
            cursor.execute("SELECT name FROM Users WHERE user_id = ?", (c[0],))
            c_name_row = cursor.fetchone()
            if c_name_row:
                kb.append([InlineKeyboardButton(text=f"👦👧 {c_name_row[0]}", callback_data=f"planfor_{c[0]}")])
        
        await message.answer("📝 <b>Mutolaa rejasi tuzish</b>\n\nQaysi farzandingiz uchun reja tuzyapsiz?", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await state.set_state(PlanCreation.waiting_for_child)

@dp.callback_query(PlanCreation.waiting_for_child, F.data.startswith("planfor_"))
async def plan_child_selected(callback: types.CallbackQuery, state: FSMContext):
    child_id = int(callback.data.split("_")[1])
    await state.update_data(plan_child_id=child_id)
    await callback.message.delete()
    text = "📝 <b>Mutolaa rejasi nima?</b>\n\n👇 <b>1-qadam:</b> Rejaga qanday nom berasiz?\n<i>(Masalan: 'Yozgi ta'til mutolaasi', 'Tug'ilgan kun sovg'asi uchun')</i>"
    await bot.send_message(callback.from_user.id, text, parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(PlanCreation.waiting_for_name)
    await callback.answer()

@dp.message(PlanCreation.waiting_for_name)
async def plan_name_received(message: types.Message, state: FSMContext):
    await state.update_data(plan_name=message.text)
    await message.answer("🎁 <b>2-qadam: Katta Mukofot!</b>\n\nBu reja to'liq tugatilganda farzandingiz qanday katta sovg'a oladi?\n<i>(Masalan: 'Velosiped', '100 🔅 Bilig', 'Muzqaymoq')</i>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(PlanCreation.waiting_for_prize)

@dp.message(PlanCreation.waiting_for_prize)
async def plan_prize_received(message: types.Message, state: FSMContext):
    await state.update_data(plan_prize=message.text)
    await message.answer("⏳ <b>3-qadam: Muddat (Deadline)</b>\n\nRejani qachongacha tugatish kerak?\n<i>(Masalan: '1 oy', '31-Avgustgacha')</i>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(PlanCreation.waiting_for_deadline)

@dp.message(PlanCreation.waiting_for_deadline)
async def plan_deadline_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    child_id = data.get('plan_child_id')
    
    cursor.execute("INSERT INTO Reading_Plans (parent_id, child_id, name, prize, deadline) VALUES (?, ?, ?, ?, ?)",
                   (message.from_user.id, child_id, data['plan_name'], data['plan_prize'], message.text))
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
    await bot.send_message(callback.from_user.id, "✍️ <b>Matn orqali qo'shish</b>\n\nKitob nomi va muallifini nuqta bilan ajratib yozing:\n<i>(Masalan: O'tkan kunlar. Abdulla Qodiriy)</i>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
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
        
        model = genai.GenerativeModel(GEMINI_MODEL)
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
# YOSH BO'YICHA TAVSIYALAR
# ==========================================
@dp.callback_query(F.data == "add_book_age")
async def show_age_recommendation_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="👶 3+ yosh", callback_data="rec_age_3"), InlineKeyboardButton(text="👦 6+ yosh", callback_data="rec_age_6")],
        [InlineKeyboardButton(text="🧒 8+ yosh", callback_data="rec_age_8"), InlineKeyboardButton(text="🧑 12+ yosh", callback_data="rec_age_12")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="finish_plan")]
    ]
    await callback.message.edit_text("👶 <b>Farzandingiz yosh toifasini tanlang:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@dp.callback_query(F.data.startswith("rec_age_"))
async def show_recommended_books_list(callback: types.CallbackQuery):
    age_group = callback.data.split("_")[2]
    books_list = RECOMMENDED_BOOKS.get(age_group, [])
    
    text = f"📚 <b>{age_group}+ yoshli bolalar uchun tavsiya etilgan asarlar ro'yxati:</b>\n\n"
    for idx, b_name in enumerate(books_list, 1):
        text += f"{idx}. {b_name}\n"
        
    text += MUTOLAA_NOTE
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Yosh toifalariga qaytish", callback_data="add_book_age")]
    ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

# ==========================================
# OTA-ONA UCHUN FAOL REJALAR VA TEST TUZISH
# ==========================================
async def show_parent_plans(message_or_callback, user_id):
    cursor.execute("SELECT rp.plan_id, rp.name, rp.prize, rp.deadline, u.name FROM Reading_Plans rp LEFT JOIN Users u ON rp.child_id = u.user_id WHERE rp.parent_id = ? AND rp.status = 'active'", (user_id,))
    plans = cursor.fetchall()
    if not plans:
        text = "Sizda hozircha faol rejalar yo'q."
        if isinstance(message_or_callback, types.Message): await message_or_callback.answer(text, reply_markup=get_parent_keyboard())
        else: await message_or_callback.message.edit_text(text)
        return
        
    kb = []
    for p in plans:
        cursor.execute("SELECT COUNT(*) FROM Plan_Books WHERE plan_id = ?", (p[0],))
        book_count = cursor.fetchone()[0]
        child_name = f" ({p[4]})" if p[4] else ""
        kb.append([InlineKeyboardButton(text=f"🎯 {p[1]}{child_name} ({book_count} ta kitob)", callback_data=f"showplan_{p[0]}")])
        
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
# AI TEST TUZISH MANTIG'I (KAMIDA 3 TA RASM)
# ==========================================
@dp.callback_query(F.data.startswith("aitest_"))
async def ask_for_test_photo(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    await state.update_data(test_book_id=book_id, photos=[])
    await callback.message.delete()
    
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="✅ Testni tuzish")],
        [KeyboardButton(text="🔙 Orqaga")]
    ], resize_keyboard=True)
    
    await bot.send_message(
        callback.from_user.id,
        "📸 <b>AI Test tuzish uchun kamida 3 ta sahifa rasmini yuboring!</b>\n\n"
        "1-sahifa, 2-sahifa va 3-sahifalarni ketma-ket rasmga olib yuboring.\n\n"
        "Barcha rasmlarni yuborgach, pastdagi <b>'✅ Testni tuzish'</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=kb
    )
    await state.set_state(AITestCreation.waiting_for_page_photo)
    await callback.answer()

@dp.message(AITestCreation.waiting_for_page_photo, F.photo)
async def collect_test_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    image_bytes = downloaded_file.read()
    
    data = await state.get_data()
    photos = data.get('photos', [])
    photos.append(image_bytes)
    await state.update_data(photos=photos)
    
    photo_count = len(photos)
    if photo_count < 3:
        await message.answer(f"📸 <b>{photo_count}-sahifa rasmi qabul qilindi!</b>\n\nYana kamida {3 - photo_count} ta sahifa rasmini yuboring.")
    else:
        await message.answer(f"📸 <b>{photo_count}-sahifa rasmi qabul qilindi!</b>\n\nYetarli rasmlar yig'ildi. Testni tuzish uchun pastdagi <b>'✅ Testni tuzish'</b> tugmasini bosing.")

@dp.message(AITestCreation.waiting_for_page_photo, F.text == "✅ Testni tuzish")
async def generate_ai_test_multi(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    book_id = data.get('test_book_id')
    
    if len(photos) < 3:
        await message.answer(f"⚠️ <b>Kamida 3 ta sahifa rasmini yuborishingiz kerak!</b>\nHozircha {len(photos)} ta rasm yubordingiz. Yana {3 - len(photos)} ta rasm yuboring.")
        return
        
    processing_msg = await message.answer(f"⏳ <i>Gemini AI {len(photos)} ta sahifani tahlil qilib, test tuzmoqda... Iltimos kuting.</i>", parse_mode="HTML")
    
    try:
        prompt = f"""Bu bolalar kitobining {len(photos)} ta sahifasi rasmlari. Shu matnlar va sahifalar mazmuni asosida bolalar uchun 5 ta sifatli test savoli tuz. 
        DIQQAT: Savollar faqat quruq xotirani emas, balki bolaning fikrlashini, mantiqini va asar mohiyatini tushunganini sinaydigan bo'lsin.
        Har bir savolda 3 ta variant (A, B, C) bo'lsin. 
        Natijani FAQAT VA FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday so'z qo'shma:
        [ {{"question": "Savol matni?", "options": ["A) variant", "B) variant", "C) variant"], "answer": "A) variant"}} ]"""
        
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        contents = [prompt]
        for img_bytes in photos:
            contents.append({"mime_type": "image/jpeg", "data": img_bytes})
            
        response = await model.generate_content_async(contents)
        
        ai_result = clean_json(response.text)
        questions = json.loads(ai_result)
        
        cursor.execute("INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)", (book_id, ai_result))
        conn.commit()
        
        test_text = f"✅ <b>AI Test {len(photos)} ta sahifa asosida muvaffaqiyatli tuzildi!</b>\n\n<i>Quyidagi savollar bazaga saqlandi:</i>\n\n"
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
        
    cursor.execute("SELECT plan_id, name, prize FROM Reading_Plans WHERE parent_id = ? AND (child_id = ? OR child_id IS NULL) AND status = 'active'", (link[0], user_id))
    plans = cursor.fetchall()
    
    kb, has_books, text = [], False, "🦸‍♂️ <b>Qahramon! Ota-onang senga ajoyib reja tuzgan.</b>\n\n"
    for p in plans:
        cursor.execute("SELECT book_id, title, pages_read, is_completed FROM Plan_Books WHERE plan_id = ?", (p[0],))
        books = cursor.fetchall()
        if books:
            text += f"🎯 <b>{p[1]}</b> (Mukofot: {p[2]})\n"
            for b in books:
                if b[3] == 0: 
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
    
    test_btn = InlineKeyboardButton(text="📝 Testni ishlash (Bilig 🔅)", callback_data=f"taketest_{book_id}_0_0") if cursor.fetchone() else InlineKeyboardButton(text="🔒 Test (Hozircha mavjud emas)", callback_data="no_test_alert")
        
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
        
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = await model.generate_content_async([prompt, {"mime_type": "image/jpeg", "data": downloaded_file.read()}])
        
        ai_result = json.loads(clean_json(response.text))
        
        try: await message.delete()
        except Exception: pass 
        
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
        
        # LOGLAR BAZASIGA YOZISH (HAFTALIK HISOBOT UCHUN)
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO Reading_Logs (child_id, book_id, pages_added, created_at) VALUES (?, ?, ?, ?)",
                       (child_id, book_id, pages_read_now, now_ts))
        
        streak = update_streak(child_id) 
        
        # HAFTALIK TAQQOSLASH MATNINI TAYYORLASH
        now_dt = datetime.now()
        w1_start = (now_dt - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        w2_start = (now_dt - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("SELECT SUM(pages_added) FROM Reading_Logs WHERE child_id = ? AND created_at >= ?", (child_id, w1_start))
        res_w1 = cursor.fetchone()[0]
        this_week = res_w1 if res_w1 else 0

        cursor.execute("SELECT SUM(pages_added) FROM Reading_Logs WHERE child_id = ? AND created_at >= ? AND created_at < ?", (child_id, w2_start, w1_start))
        res_w2 = cursor.fetchone()[0]
        last_week = res_w2 if res_w2 else 0

        comp_text = ""
        if last_week > 0:
            diff = this_week - last_week
            if diff > 0:
                comp_text = f"\n📈 <b>Barakalla!</b> Siz ushbu haftada o'tgan haftaga nisbatan <b>+{diff} bet ko'p</b> o'qidingiz! Ajoyib natija! 🚀"
            elif diff < 0:
                comp_text = f"\n📊 <b>G'ayrat qiling!</b> O'tgan haftada nisbatan biroz kamroq o'qiyapsiz, sur'atni oshiramiz! 💪"
            else:
                comp_text = f"\n📊 <b>Ajoyib!</b> O'tgan haftadagi kabi barqaror o'qishda davom etyapsiz!"

        if earned_bilig > 0:
            cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (earned_bilig, child_id))
            reply_text = f"🎉 <b>Qoyilmaqom!</b> Sen {pages_read_now} bet o'qiding va <b>{earned_bilig} 🔅 Bilig</b> ishlab olding!{comp_text}\n🔥 Streak: {streak} kun!\n<i>(Jami o'qilgan: {new_page_num} bet)</i>"
        else:
            reply_text = f"👍 <b>Barakalla!</b> Sen {pages_read_now} bet o'qiding. Yana {5 - (new_page_num % 5)} bet o'qisang, yangi Bilig 🔅 olasan!{comp_text}\n🔥 Streak: {streak} kun!"
            
        conn.commit()
        await processing_msg.delete()
        await message.answer(reply_text, parse_mode="HTML", reply_markup=get_child_keyboard())
        await state.clear()
        
        parent_id = get_parent_id(child_id)
        if parent_id:
            await bot.send_message(parent_id, f"📖 Farzandingiz hozirgina <b>'{book_title}'</b> kitobidan {pages_read_now} bet o'qidi. (Jami: {new_page_num} bet).", parse_mode="HTML")
        
    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"❌ Xatolik yuz berdi. Qaytadan urinib ko'r.", reply_markup=get_child_keyboard())
        await state.clear()

# ==========================================
# 2-BOSQICH: AUDIO XULOSA, BOLA VA OTA UCHUN BOHOLASH
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
        
    await state.update_data(audio_book_id=book_id, is_retry=False)
    await callback.message.delete()
    await bot.send_message(callback.from_user.id, "🎤 <b>Ovozli xabar yubor!</b>\n\nKitobda nimalar bo'lganini o'z so'zlaring bilan aytib ber. AI Adabiyotshunos seni eshitib, baho beradi!", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ChildReading.waiting_for_audio)
    await callback.answer()

@dp.callback_query(F.data.startswith("retryaudio_"))
async def retry_audio_summary(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    await state.update_data(audio_book_id=book_id, is_retry=True)
    await callback.message.delete()
    await bot.send_message(callback.fromuser.id, "🎤 <b>Qayta ovozli xabar yubor!</b>\n\nBu safar adabiyotshunos maslahat berganidek, chiroyliroq va batafsilroq gapirishga harakat qil. Omadingni sinab ko'r! 🚀", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ChildReading.waiting_for_audio)
    await callback.answer()

@dp.message(ChildReading.waiting_for_audio, F.voice)
async def process_audio_summary(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>Adabiyotshunos va o'qituvchi seni eshitmoqda...</i>", parse_mode="HTML")
    try:
        file_info = await bot.get_file(message.voice.file_id)
        downloaded_file = await bot.download_file(file_info.file_path)
        
        data = await state.get_data()
        book_id = data.get('audio_book_id')
        is_retry = data.get('is_retry', False)
        
        cursor.execute("SELECT child_age FROM Family_Link WHERE child_id = ?", (message.from_user.id,))
        age_row = cursor.fetchone()
        age = age_row[0] if age_row else 10
        
        cursor.execute("SELECT title FROM Plan_Books WHERE book_id = ?", (book_id,))
        book_row = cursor.fetchone()
        book_title = book_row[0] if book_row else "Kitob"
        
        prompt = f"""Sen mehribon va talabchan Adabiyotshunos hamda maktab o'qituvchisisan. Bu {age} yoshli bolaning '{book_title}' kitobi bo'yicha yuborgan audio xulosasi.

        Tahlilni ikkita alohida qismga bo'lib, FAQAT quyidagi JSON formatida qaytar:

        {{
            "bonus_bilig": 3,
            "give_badge": false,
            "child_feedback": "Bola uchun sodda xabar matni...",
            "parent_report": {{
                "summary": "Audioning qisqacha matni va mazmuni...",
                "focused_points": "Bola e'tibor qaratgan asosiy masalalar va voqealar...",
                "strengths": "Bolaning yutuqlari (so'z boyligi, his-tuyg'ular, mantiq)...",
                "weaknesses": "Kamchiliklari va rivojlantirish kerak bo'lgan jihatlari..."
            }}
        }}

        TALABLAR:
        1. "bonus_bilig": 1 dan 5 gacha butun raqam (sifatiga qarab).
        2. "child_feedback": Bolaga yuboriladigan matn. Bolaga mos sodda tilda yoz. Agar Bilig kam (1, 2, 3) berilgan bo'lsa, xafa qilmasdan sababini tushuntir. Nutq so'zlash texnikasini o'rgat: "Gapirganda bunday gapir...", "Keyingi safar mana bu so'zlardan foydalan..." deb sodda o'rgat. Unga yana 1 ta imkoniyat va qolgan Biliglarni ishlash imkoniyati borligini aytib ruhlantir.
        3. "parent_report": Otaga yuboriladigan HAQQONIY va OBYEKTIV pedagogik tahlil. Audiodagi kamchiliklar va yutuqlarni ro'y-rost ko'rsat.
        4. "give_badge": boolean (juda ajoyib nutq bo'lsa true)."""
        
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = await model.generate_content_async([prompt, {"mime_type": "audio/ogg", "data": downloaded_file.read()}])
        
        ai_result = json.loads(clean_json(response.text))
        bonus = int(ai_result.get("bonus_bilig", 1))
        give_badge = ai_result.get("give_badge", False)
        child_feedback = ai_result.get("child_feedback", "Ajoyib xulosa!")
        parent_rep = ai_result.get("parent_report", {})
        
        if not is_retry:
            cursor.execute("UPDATE Plan_Books SET audio_count = audio_count + 1 WHERE book_id = ?", (book_id,))
            
        cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (bonus, message.from_user.id))
        update_streak(message.from_user.id)
        
        badge_text = ""
        if give_badge:
            cursor.execute("SELECT badges FROM Users WHERE user_id = ?", (message.from_user.id,))
            current_badges = cursor.fetchone()[0]
            if "Notiq" not in current_badges:
                new_badges = current_badges + " 🗣 Notiq" if current_badges else "🗣 Notiq"
                cursor.execute("UPDATE Users SET badges = ? WHERE user_id = ?", (new_badges, message.from_user.id))
                badge_text = "\n\n🏅 <b>TABRIKLAYMIZ! Sen 'Notiq' nishonini qo'lga kiritding!</b>"
                
        conn.commit()
        
        kb_child = None
        if bonus < 5:
            remaining = 5 - bonus
            kb_child = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"🎤 Qayta aytib berish (+{remaining} 🔅 Bilig)", callback_data=f"retryaudio_{book_id}")]
            ])
            
        reply_text = f"👨‍🏫 <b>Adabiyotshunos:</b>\n\n{child_feedback}\n\n🎁 <b>Olgan mukofoting:</b> {bonus} 🔅 Bilig!{badge_text}"
        await processing_msg.delete()
        await message.answer(reply_text, parse_mode="HTML", reply_markup=kb_child if kb_child else get_child_keyboard())
        await state.clear()
        
        # OTA-ONA UCHUN BATAHSIL PEDAGOGIK HISOBOT
        parent_id = get_parent_id(message.from_user.id)
        if parent_id:
            cursor.execute("SELECT name FROM Users WHERE user_id = ?", (message.from_user.id,))
            child_name = cursor.fetchone()[0]
            
            p_summary = parent_rep.get("summary", "Ko'rsatilmadi")
            p_focused = parent_rep.get("focused_points", "Ko'rsatilmadi")
            p_strengths = parent_rep.get("strengths", "Ko'rsatilmadi")
            p_weaknesses = parent_rep.get("weaknesses", "Ko'rsatilmadi")
            
            parent_text = (
                f"📊 <b>FARZANDINGIZNING AUDIO XULOSA TAHLILI</b>\n"
                f"<i>(O'qituvchi va adabiyotshunos haqqoniy bahosi)</i>\n\n"
                f"👦 <b>Farzand:</b> {child_name}\n"
                f"📘 <b>Kitob:</b> {book_title}\n"
                f"🎁 <b>Berilgan Bilig:</b> {bonus}/5 🔅\n\n"
                f"📝 <b>Audio mazmuni:</b>\n<i>{p_summary}</i>\n\n"
                f"🎯 <b>Bola e'tibor qilgan masalalar:</b>\n{p_focused}\n\n"
                f"✅ <b>Yutuqlari:</b>\n{p_strengths}\n\n"
                f"⚠️ <b>Kamchiliklar va rivojlantirish kerak bo'lgan jihatlar:</b>\n{p_weaknesses}"
            )
            await bot.send_message(parent_id, parent_text, parse_mode="HTML")
            
    except Exception as e:
        await processing_msg.delete()
        await message.answer(f"❌ Xatolik yuz berdi. Qaytadan urinib ko'r.", reply_markup=get_child_keyboard())
        await state.clear()

# ==========================================
# 3-BOSQICH: AI TEST YECHISH VA OTA-ONAGA HISOBOT
# ==========================================
@dp.callback_query(F.data.startswith("taketest_"))
async def execute_test(callback: types.CallbackQuery):
    try:
        parts = callback.data.split("_")
        book_id, q_idx, correct_count = int(parts[1]), int(parts[2]), int(parts[3])
        
        cursor.execute("SELECT questions_json FROM Book_Tests WHERE book_id = ?", (book_id,))
        test_row = cursor.fetchone()
        if not test_row:
            await callback.answer("🔒 Test topilmadi yoki allaqachon yechilgan!", show_alert=True)
            return
            
        questions = json.loads(test_row[0])
        
        if q_idx >= len(questions):
            cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (correct_count, callback.from_user.id))
            cursor.execute("DELETE FROM Book_Tests WHERE book_id = ?", (book_id,))
            conn.commit()
            
            text = f"🏁 <b>Test yakunlandi!</b>\n\n✅ To'g'ri javoblar: {correct_count} ta\n🎁 Sen <b>{correct_count} 🔅 Bilig</b> yutib olding! Barakalla, aqlli Qahramon! 🧠"
            await callback.message.edit_text(text, parse_mode="HTML")
            
            parent_id = get_parent_id(callback.from_user.id)
            if parent_id:
                cursor.execute("SELECT name FROM Users WHERE user_id = ?", (callback.from_user.id,))
                c_name = cursor.fetchone()[0]
                cursor.execute("SELECT title FROM Plan_Books WHERE book_id = ?", (book_id,))
                b_title = cursor.fetchone()[0]
                
                pct = int((correct_count / len(questions)) * 100)
                parent_test_text = (
                    f"📝 <b>FARZANDINGIZ TEST NATIJASI</b>\n\n"
                    f"👦 <b>Farzand:</b> {c_name}\n"
                    f"📘 <b>Kitob:</b> {b_title}\n"
                    f"🎯 <b>Natija:</b> {correct_count}/{len(questions)} ta to'g'ri ({pct}%)\n"
                    f"🎁 <b>Ajarilgan Bilig:</b> +{correct_count} 🔅\n\n"
                    f"💡 <i>Izoh: Test savollari mantiqiy fikrlash va diqqatni sinashga qaratilgan edi.</i>"
                )
                await bot.send_message(parent_id, parent_test_text, parse_mode="HTML")
            await callback.answer()
            return
            
        q = questions[q_idx]
        kb = []
        for i, opt in enumerate(q['options']):
            is_correct = 1 if opt.strip() == q['answer'].strip() else 0
            kb.append([InlineKeyboardButton(text=opt, callback_data=f"tans_{book_id}_{q_idx+1}_{correct_count}_{is_correct}")])
            
        kb.append([InlineKeyboardButton(text="🔙 Orqaga (Testni to'xtatish)", callback_data=f"cread_{book_id}")])
            
        text = f"📝 <b>{q_idx + 1}-savol:</b>\n\n{q['question']}"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await callback.answer()
    except Exception as e:
        await callback.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.", show_alert=True)

@dp.callback_query(F.data.startswith("tans_"))
async def process_test_answer(callback: types.CallbackQuery):
    try:
        parts = callback.data.split("_")
        _, book_id, next_q_idx, correct_count, is_correct = parts
        new_correct_count = int(correct_count) + int(is_correct)
        callback.data = f"taketest_{book_id}_{next_q_idx}_{new_correct_count}"
        await execute_test(callback)
    except Exception as e:
        await callback.answer("❌ Xatolik yuz berdi.", show_alert=True)

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
        f"🔅 <b>Biliglar:</b> {balance} ta\n"
        f"🔥 <b>Uzluksiz o'qish:</b> {streak} kun\n"
        f"🏅 <b>Nishonlar:</b> {badges}\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Do'konga kirish", callback_data="child_store")]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

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
        kb.append([InlineKeyboardButton(text=f"🎁 {item[1]} - {item[2]} 🔅", callback_data=f"buyitem_{item[0]}")])
        
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
        await callback.answer(f"Sizda yetarli Bilig yo'q! Yana {item[1] - balance} 🔅 yig'ishingiz kerak.", show_alert=True)
        return
        
    cursor.execute("UPDATE Users SET balance_coins = balance_coins - ? WHERE user_id = ?", (item[1], callback.from_user.id))
    conn.commit()
    
    await callback.message.edit_text(f"🎉 <b>Tabriklaymiz!</b> Sen <b>{item[0]}</b> sotib olding!\nOta-onangga xabar yuborildi.", parse_mode="HTML")
    await bot.send_message(item[2], f"🛍 <b>Diqqat!</b> Farzandingiz do'kondan <b>'{item[0]}'</b> sotib oldi! Iltimos, va'da qilingan sovg'ani olib bering.", parse_mode="HTML")
    await callback.answer()

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
        text += f"{medal} <b>{user[0]}</b> - {user[1]} 🔅\n"
        
    await message.answer(text, parse_mode="HTML")

# ==========================================
# FARZAND NATIJALARINI KO'RISH VA HAFTALIK TAHLIL
# ==========================================
async def show_single_child_result(message_or_call, child_id, parent_id):
    cursor.execute("SELECT child_age FROM Family_Link WHERE child_id = ? AND parent_id = ?", (child_id, parent_id))
    row = cursor.fetchone()
    child_age = row[0] if row else "Noma'lum"
    
    cursor.execute("SELECT name, balance_coins, badges, streak_days FROM Users WHERE user_id = ?", (child_id,))
    child = cursor.fetchone()
    if not child: return
    child_name, balance, badges, streak = child
    badges_text = badges if badges else "Hali nishonlar yo'q"
    
    cursor.execute("""
        SELECT pb.title, pb.pages_read, pb.is_completed 
        FROM Plan_Books pb 
        JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id 
        WHERE rp.parent_id = ? AND (rp.child_id = ? OR rp.child_id IS NULL)
    """, (parent_id, child_id))
    books = cursor.fetchall()
    
    total_pages = sum([b[1] for b in books]) if books else 0
    
    text = (
        f"📊 <b>{child_name}ning natijalari:</b>\n\n"
        f"👦 Yoshi: {child_age}\n"
        f"🔅 Yig'ilgan Biliglar: <b>{balance} ta</b>\n"
        f"🔥 Uzluksiz o'qish: {streak} kun\n"
        f"🏅 Nishonlar: {badges_text}\n\n"
        f"📖 <b>Jami o'qilgan: {total_pages} bet</b>\n"
    )
    
    if books:
        text += "\n📚 <b>Kitoblar bo'yicha:</b>\n"
        for b in books:
            status = "✅" if b[2] else "⏳"
            text += f" ➖ <i>{b[0]}</i>: {b[1]} bet {status}\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Haftalik hisobot va AI Tahlil", callback_data=f"weeklyrep_{child_id}")],
        [InlineKeyboardButton(text="➖ Bilig ayirish / Nolga tushirish", callback_data=f"deduct_coins_{child_id}")],
        [InlineKeyboardButton(text="➕ Boshqa farzand qo'shish", callback_data="add_child_info")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="parent_results_main")]
    ])
    
    if isinstance(message_or_call, types.Message):
        await message_or_call.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message_or_call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

# OTA-ONA UCHUN HAFTALIK TAHLIL HISOBOTI
@dp.callback_query(F.data.startswith("weeklyrep_"))
async def weekly_report_handler(callback: types.CallbackQuery):
    child_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT name FROM Users WHERE user_id = ?", (child_id,))
    c_name = cursor.fetchone()[0]

    now_dt = datetime.now()
    w1_start = (now_dt - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    w2_start = (now_dt - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT SUM(pages_added) FROM Reading_Logs WHERE child_id = ? AND created_at >= ?", (child_id, w1_start))
    res_w1 = cursor.fetchone()[0]
    this_week = res_w1 if res_w1 else 0

    cursor.execute("SELECT SUM(pages_added) FROM Reading_Logs WHERE child_id = ? AND created_at >= ? AND created_at < ?", (child_id, w2_start, w1_start))
    res_w2 = cursor.fetchone()[0]
    last_week = res_w2 if res_w2 else 0

    diff = this_week - last_week
    if last_week == 0:
        pct_text = "Yangi ko'rsatkich 🚀"
        dynamic_icon = "📈"
    elif diff > 0:
        pct = int((diff / last_week) * 100)
        pct_text = f"+{pct}% ga oshgan 🚀"
        dynamic_icon = "📈"
    elif diff < 0:
        pct = int((abs(diff) / last_week) * 100)
        pct_text = f"-{pct}% ga pasaygan 📉"
        dynamic_icon = "📉"
    else:
        pct_text = "Bir xil barqaror ⏸"
        dynamic_icon = "📊"

    report_text = (
        f"📈 <b>{c_name}ning HAFTALIK MUTOLAA HISOBOTI</b>\n\n"
        f"🗓 <b>Shu hafta o'qildi:</b> {this_week} bet\n"
        f"🗓 <b>O'tgan hafta o'qilgan edi:</b> {last_week} bet\n"
        f"{dynamic_icon} <b>Dinamika:</b> {pct_text}\n\n"
        f"🧠 <b>AI Pedagogik Tavsiyasi:</b>\n"
    )

    if diff >= 0:
        report_text += f"<i>Farzandingiz shu haftada juda faol bo'ldi! Sur'atni saqlab qolish uchun uni do'kondagi kichik sovg'alar yoki iliq so'zlar bilan rag'batlantiring.</i>"
    else:
        report_text += f"<i>Farzandingiz bu hafta o'tgan haftaga nisbatan biroz kamroq o me'yorida o'qidi. Unga yangi qiziqarli kitob tavsiya qilish yoki birgalikda o'qishni yo'lga qo'yish foydali bo'ladi.</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Farzand natijalariga qaytish", callback_data=f"childres_{child_id}")]
    ])

    await callback.message.edit_text(report_text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

async def show_parent_results_menu(message_or_call, parent_id):
    cursor.execute("SELECT child_id FROM Family_Link WHERE parent_id = ?", (parent_id,))
    links = cursor.fetchall()
    
    if not links:
        parent_code = f"BLG-{str(parent_id)[-4:]}"
        text = f"Sizga hali hech qaysi farzand ulanmagan.\n\nFarzandingiz botga kirib <b>'👦👧 Men O'quvchiman'</b> bo'limini tanlasin va kodingizni kiritsin:\n\n🔑 Kodingiz: <b>{parent_code}</b>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Farzand qo'shish yo'riqnomasi", callback_data="add_child_info")]])
        if isinstance(message_or_call, types.Message): await message_or_call.answer(text, parse_mode="HTML", reply_markup=kb)
        else: await message_or_call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        return
        
    kb = []
    for link in links:
        c_id = link[0]
        cursor.execute("SELECT name FROM Users WHERE user_id = ?", (c_id,))
        c_name_row = cursor.fetchone()
        if c_name_row:
            kb.append([InlineKeyboardButton(text=f"👦👧 {c_name_row[0]}", callback_data=f"childres_{c_id}")])
            
    kb.append([InlineKeyboardButton(text="➕ Boshqa farzand qo'shish", callback_data="add_child_info")])
    
    text = "📊 <b>Qaysi farzandingizning natijasini ko'rmoqchisiz?</b>"
    if isinstance(message_or_call, types.Message):
        await message_or_call.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await message_or_call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.message(F.text == "📊 Farzandim natijalari")
async def parent_results_handler(message: types.Message):
    await show_parent_results_menu(message, message.from_user.id)

@dp.callback_query(F.data == "parent_results_main")
async def parent_results_main_callback(callback: types.CallbackQuery):
    await show_parent_results_menu(callback, callback.from_user.id)
    await callback.answer()

@dp.callback_query(F.data.startswith("childres_"))
async def childres_callback(callback: types.CallbackQuery):
    child_id = int(callback.data.split("_")[1])
    await show_single_child_result(callback, child_id, callback.from_user.id)
    await callback.answer()

# ==========================================
# BILIG AYIRISH VA NOLGA TUSHIRISH MANTIG'I
# ==========================================
@dp.callback_query(F.data.startswith("deduct_coins_"))
async def deduct_coins_menu(callback: types.CallbackQuery):
    child_id = int(callback.data.split("_")[2])
    cursor.execute("SELECT name, balance_coins FROM Users WHERE user_id = ?", (child_id,))
    child = cursor.fetchone()
    if not child: return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Summa kiritish (Masalan: 10)", callback_data=f"dedcustom_{child_id}")],
        [InlineKeyboardButton(text="🔄 Hisobni 0 ga tushirish", callback_data=f"dedzero_{child_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"childres_{child_id}")]
    ])
    
    text = (
        f"➖ <b>{child[0]}ning hisobidan Bilig (🔅) ayirish</b>\n\n"
        f"Hozirgi balans: <b>{child[1]} 🔅</b>\n\n"
        f"<i>Farzandingizga naqd pul bergandingizda yoki sovg'a olib bergandingizdan so'ng hisobidan Biliglarini ayirish uchun kerakli usulni tanlang:</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("dedzero_"))
async def deduct_zero_handler(callback: types.CallbackQuery):
    child_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT name, balance_coins FROM Users WHERE user_id = ?", (child_id,))
    child = cursor.fetchone()
    
    cursor.execute("UPDATE Users SET balance_coins = 0 WHERE user_id = ?", (child_id,))
    conn.commit()
    
    await callback.answer(f"{child[0]}ning balansi 0 ga tushirildi!", show_alert=True)
    await show_single_child_result(callback, child_id, callback.from_user.id)
    
    try:
        await bot.send_message(child_id, f"ℹ️ <b>Ota-onangiz hisobingizdagi Biliglarni nolga tushirdi.</b>\n<i>(Berilgan pul yoki mukofotlar hisobiga)</i>\n\nHozirgi balansingiz: <b>0 🔅</b>", parse_mode="HTML")
    except Exception:
        pass

@dp.callback_query(F.data.startswith("dedcustom_"))
async def deduct_custom_start(callback: types.CallbackQuery, state: FSMContext):
    child_id = int(callback.data.split("_")[1])
    await state.update_data(target_deduct_child_id=child_id)
    
    await callback.message.delete()
    await bot.send_message(
        callback.from_user.id,
        "✍️ <b>Farzandingiz hisobidan necha Bilig (🔅) ayirmoqchisiz?</b>\n\nFaqat raqam kiriting (Masalan: 10 yoki 20):",
        parse_mode="HTML",
        reply_markup=get_back_reply_keyboard()
    )
    await state.set_state(ParentSettings.waiting_for_coin_deduction)
    await callback.answer()

@dp.message(ParentSettings.waiting_for_coin_deduction)
async def process_coin_deduction(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting! (Masalan: 10)")
        return
        
    amount = int(message.text)
    data = await state.get_data()
    child_id = data.get('target_deduct_child_id')
    
    cursor.execute("SELECT name, balance_coins FROM Users WHERE user_id = ?", (child_id,))
    child = cursor.fetchone()
    if not child:
        await state.clear()
        return
        
    old_balance = child[1]
    new_balance = max(0, old_balance - amount)
    
    cursor.execute("UPDATE Users SET balance_coins = ? WHERE user_id = ?", (new_balance, child_id))
    conn.commit()
    
    await message.answer(
        f"✅ <b>{child[0]}ning hisobidan {amount} 🔅 ayirildi!</b>\n\nYangi balans: <b>{new_balance} 🔅</b>",
        parse_mode="HTML",
        reply_markup=get_parent_keyboard()
    )
    await state.clear()
    
    try:
        await bot.send_message(child_id, f"ℹ️ <b>Ota-onangiz hisobingizdan {amount} 🔅 ayirdi.</b>\n<i>(Berilgan pul/sovg'a hisobiga)</i>\n\nHozirgi balansingiz: <b>{new_balance} 🔅</b>", parse_mode="HTML")
    except Exception:
        pass

# ==========================================
# FARZAND QO'SHISH YO'RIQNOMASI
# ==========================================
@dp.callback_query(F.data == "add_child_info")
async def add_child_info_handler(callback: types.CallbackQuery):
    parent_code = f"BLG-{str(callback.from_user.id)[-4:]}"
    text = (
        f"➕ <b>Yangi farzand qo'shish yo'riqnomasi:</b>\n\n"
        f"1. Farzandingiz telefonida ushbu botni oching va <b>'👦👧 Men O'quvchiman'</b> tugmasini bosing.\n"
        f"2. Bot undan ota-ona kodini so'raganda, quyidagi kodingizni kiritsin:\n\n"
        f"🔑 Sizning kodingiz: <b>{parent_code}</b>\n\n"
        f"<i>Farzandingiz ulangan zahoti sizga Telegram orqali avtomatik xabar boradi!</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="parent_results_main")]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

# ==========================================
# 6. ASOSIY ISHGA TUSHIRISH FUNKSIYASI
# ==========================================
async def main():
    init_db()
    threading.Thread(target=run_dummy_server, daemon=True).start()
    asyncio.create_task(daily_reminder_scheduler()) # Avtomatik kunlik eslatmalarni yoqish
    print("Telegram bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
