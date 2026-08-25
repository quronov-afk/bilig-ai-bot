import os
import sqlite3
from datetime import datetime, timedelta

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
    try: cursor.execute("ALTER TABLE Users ADD COLUMN is_approved INTEGER DEFAULT 1")
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
        recent_text = "• Hozircha foydalanuvchilar yo‘q.\n"

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    text = (
        f"👑 <b>LOYIHA MUALLIFI STATISTIKASI</b>\n"
        f"<i>Bilig AI platformasi ko‘rsatkichlari ({now_str})</i>\n\n"
        f"👥 <b>FOYDALANUVCHILAR:</b>\n"
        f"• Jami foydalanuvchilar: <b>{total_users} ta</b>\n"
        f"  └ 👨‍👩‍👦 Ota-onalar: <b>{total_parents} ta</b>\n"
        f"  └ 👦👧 O‘quvchilar: <b>{total_children} ta</b>\n"
        f"  └ 🔗 Bog‘langan oilalar: <b>{total_families} ta</b>\n\n"
        f"📖 <b>MUTOLAA VA KITOBLAR:</b>\n"
        f"• Jami mutolaa rejalari: <b>{total_plans} ta</b> (Tugatilgan: {completed_plans})\n"
        f"• Rejalardagi kitoblar: <b>{total_books} ta</b> (Tugatilgan: {completed_books})\n"
        f"• 📚 Jami o‘qilgan sahifalar: <b>{total_pages} bet</b>\n\n"
        f"🔅 <b>FAOLLIK VA BILIG:</b>\n"
        f"• Bolalardagi jami Biliglar: <b>{total_coins} 🔅</b>\n"
        f"• AI orqali tuzilgan testlar: <b>{total_tests} ta</b>\n\n"
        f"🆕 <b>Oxirgi a'zo bo‘lganlar:</b>\n{recent_text}"
    )
    return text
