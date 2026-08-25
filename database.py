import os
import sqlite3
from datetime import datetime, timedelta

# Render.com doimiy diski yoki mahalliy baza yo'li
db_path = "/var/data/bot_base.db" if os.path.exists("/var/data") else "bot_base.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

def init_db():
    # 1. FOYDALANUVCHILAR JADVALI
    cursor.execute('''CREATE TABLE IF NOT EXISTS Users (
        user_id INTEGER PRIMARY KEY,
        role TEXT,
        name TEXT,
        balance_coins INTEGER DEFAULT 0,
        total_xp INTEGER DEFAULT 0,
        streak_days INTEGER DEFAULT 0,
        coin_rate INTEGER DEFAULT 500,
        badges TEXT DEFAULT '',
        is_approved INTEGER DEFAULT 1,
        last_read_date TEXT DEFAULT '',
        streak_freezes INTEGER DEFAULT 0,
        rank_title TEXT DEFAULT '🥉 Kitobxon Sayyoh',
        parent_pin TEXT DEFAULT ''
    )''')

    # 2. OILA VA FARZAND BOG'LANISHI
    cursor.execute('''CREATE TABLE IF NOT EXISTS Family_Link (
        parent_id INTEGER,
        child_id INTEGER,
        mutolaa_id TEXT,
        child_age INTEGER DEFAULT 10,
        UNIQUE(parent_id, child_id)
    )''')

    # 3. MUTOLAA REJALARI
    cursor.execute('''CREATE TABLE IF NOT EXISTS Reading_Plans (
        plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id INTEGER,
        child_id INTEGER,
        name TEXT,
        prize TEXT,
        deadline TEXT,
        status TEXT DEFAULT 'active',
        is_prize_skipped INTEGER DEFAULT 0
    )''')

    # 4. REJADAGI KITOBLAR VA TEST BOSQICHLARI
    cursor.execute('''CREATE TABLE IF NOT EXISTS Plan_Books (
        book_id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER,
        title TEXT,
        author TEXT,
        status TEXT DEFAULT 'pending',
        pages_read INTEGER DEFAULT 0,
        total_pages INTEGER DEFAULT 0,
        audio_count INTEGER DEFAULT 0,
        is_completed INTEGER DEFAULT 0,
        mid_test_1_done INTEGER DEFAULT 0,
        mid_test_2_done INTEGER DEFAULT 0,
        final_test_done INTEGER DEFAULT 0
    )''')

    # 5. AI SAVOLLAR BANKI (AyT)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Book_Tests (
        test_id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER UNIQUE,
        questions_json TEXT
    )''')

    # 6. SOVG'ALAR DO'KONI
    cursor.execute('''CREATE TABLE IF NOT EXISTS Store_Items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id INTEGER,
        name TEXT,
        price INTEGER
    )''')

    # 7. MUTOLAA JURNALI (LOGLAR)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Reading_Logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id INTEGER,
        book_id INTEGER,
        pages_added INTEGER,
        created_at TEXT
    )''')

    # 8. PEDAGOGIK DIAGNOSTIKA JURNALI (Kognitiv va Nutqiy tahlillar)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Diagnostic_Logs (
        diag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id INTEGER,
        book_id INTEGER,
        type TEXT,
        factual_score INTEGER DEFAULT 0,
        logic_score INTEGER DEFAULT 0,
        conclusion_score INTEGER DEFAULT 0,
        fluency_score INTEGER DEFAULT 0,
        vocabulary_score INTEGER DEFAULT 0,
        parent_note TEXT,
        convo_topic TEXT,
        created_at TEXT
    )''')

    # 9. TAKLIF HAVOLALARI (BETA TEST)
    cursor.execute('''CREATE TABLE IF NOT EXISTS Invite_Links (
        code TEXT PRIMARY KEY,
        is_used INTEGER DEFAULT 0,
        used_by INTEGER
    )''')

    # BAZANI XAVFSIZ MIGRATSIYA QILISH (Eski bazani buzmasdan yangi ustunlar qo'shish)
    migrations = [
        "ALTER TABLE Plan_Books ADD COLUMN pages_read INTEGER DEFAULT 0",
        "ALTER TABLE Family_Link ADD COLUMN child_age INTEGER DEFAULT 10",
        "ALTER TABLE Users ADD COLUMN badges TEXT DEFAULT ''",
        "ALTER TABLE Users ADD COLUMN is_approved INTEGER DEFAULT 1",
        "ALTER TABLE Plan_Books ADD COLUMN audio_count INTEGER DEFAULT 0",
        "ALTER TABLE Users ADD COLUMN last_read_date TEXT DEFAULT ''",
        "ALTER TABLE Plan_Books ADD COLUMN is_completed INTEGER DEFAULT 0",
        "ALTER TABLE Reading_Plans ADD COLUMN child_id INTEGER",
        "ALTER TABLE Plan_Books ADD COLUMN total_pages INTEGER DEFAULT 0",
        "ALTER TABLE Plan_Books ADD COLUMN mid_test_1_done INTEGER DEFAULT 0",
        "ALTER TABLE Plan_Books ADD COLUMN mid_test_2_done INTEGER DEFAULT 0",
        "ALTER TABLE Plan_Books ADD COLUMN final_test_done INTEGER DEFAULT 0",
        "ALTER TABLE Users ADD COLUMN streak_freezes INTEGER DEFAULT 0",
        "ALTER TABLE Users ADD COLUMN rank_title TEXT DEFAULT '🥉 Kitobxon Sayyoh'",
        "ALTER TABLE Users ADD COLUMN parent_pin TEXT DEFAULT ''",
        "ALTER TABLE Reading_Plans ADD COLUMN is_prize_skipped INTEGER DEFAULT 0"
    ]

    for query in migrations:
        try:
            cursor.execute(query)
        except Exception:
            pass

    conn.commit()

# ==========================================
# YORDAMCHI VA DIAGNOSTIK FUNKSIYALAR
# ==========================================

def get_parent_id(child_id):
    """Bolaga biriktirilgan ota-ona ID sini topish"""
    cursor.execute("SELECT parent_id FROM Family_Link WHERE child_id = ?", (child_id,))
    res = cursor.fetchone()
    return res[0] if res else None

def get_child_total_pages(child_id):
    """Bolaning barcha o'qigan jami sahifalari yig'indisi"""
    cursor.execute("""
        SELECT SUM(pages_read) FROM Plan_Books pb
        JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id
        WHERE rp.child_id = ?
    """, (child_id,))
    res = cursor.fetchone()[0]
    return res if res else 0

def calculate_and_update_rank(child_id):
    """Bolaning o'qigan betlariga qarab unvonini hisoblash va yangilash"""
    total_pages = get_child_total_pages(child_id)
    
    if total_pages >= 300:
        rank = "👑 Bilig Donishmandi"
    elif total_pages >= 150:
        rank = "🥇 Kitobxon Qahramon"
    elif total_pages >= 50:
        rank = "🥈 Kitobxon Iztopar"
    else:
        rank = "🥉 Kitobxon Sayyoh"

    cursor.execute("UPDATE Users SET rank_title = ? WHERE user_id = ?", (rank, child_id))
    conn.commit()
    return rank, total_pages

def update_streak(user_id):
    """Streak hisoblash va 'Olov qalqoni' (Streak Freeze 🛡) mexanizmi"""
    cursor.execute("SELECT streak_days, last_read_date, streak_freezes FROM Users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return 0, False
    
    streak, last_date_str, freezes = row
    today_str = datetime.now().strftime("%Y-%m-%d")
    today = datetime.strptime(today_str, "%Y-%m-%d").date()
    shield_used = False

    if last_date_str == today_str:
        return streak, shield_used

    if last_date_str:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        diff_days = (today - last_date).days

        if diff_days == 1:
            streak += 1
        elif diff_days == 2 and freezes > 0:
            # 1 kun qoldirilgan, lekin Olov qalqoni bor!
            freezes -= 1
            streak += 1
            shield_used = True
            cursor.execute("UPDATE Users SET streak_freezes = ? WHERE user_id = ?", (freezes, user_id))
        else:
            streak = 1
    else:
        streak = 1

    cursor.execute("UPDATE Users SET streak_days = ?, last_read_date = ? WHERE user_id = ?", (streak, today_str, user_id))
    conn.commit()
    return streak, shield_used

def generate_progress_bar(percent):
    """Foiz bo'yicha vizual progress bar chizish"""
    filled = min(5, max(0, int(percent // 20)))
    empty = 5 - filled
    return f"[{'🟩' * filled}{'⬜' * empty}] {percent}%"

def get_child_passport_data(child_id):
    """Oylik Kitobxon Pasporti uchun kognitiv va nutqiy diagnostika ma'lumotlarini to'plash"""
    cursor.execute("SELECT name, balance_coins, badges, streak_days, rank_title FROM Users WHERE user_id = ?", (child_id,))
    user = cursor.fetchone()
    if not user:
        return None

    name, coins, badges, streak, rank = user
    total_pages = get_child_total_pages(child_id)

    # Tugatilgan kitoblar soni
    cursor.execute("""
        SELECT COUNT(*) FROM Plan_Books pb
        JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id
        WHERE rp.child_id = ? AND pb.is_completed = 1
    """, (child_id,))
    completed_books = cursor.fetchone()[0]

    # Diagnostik o'rtacha ballarni olish (oxirgi 30 kun)
    cursor.execute("""
        SELECT 
            AVG(factual_score), 
            AVG(logic_score), 
            AVG(conclusion_score), 
            AVG(fluency_score),
            AVG(vocabulary_score)
        FROM Diagnostic_Logs 
        WHERE child_id = ?
    """, (child_id,))
    diag = cursor.fetchone()

    factual = int(diag[0]) if diag and diag[0] is not None else 85
    logic = int(diag[1]) if diag and diag[1] is not None else 75
    conclusion = int(diag[2]) if diag and diag[2] is not None else 70
    fluency = int(diag[3]) if diag and diag[3] is not None else 80

    return {
        "name": name,
        "rank": rank,
        "completed_books": completed_books,
        "total_pages": total_pages,
        "streak": streak,
        "coins": coins,
        "badges": badges if badges else "Hali nishonlar yo‘q",
        "factual_bar": generate_progress_bar(factual),
        "logic_bar": generate_progress_bar(logic),
        "conclusion_bar": generate_progress_bar(conclusion),
        "fluency_bar": generate_progress_bar(fluency)
    }

def generate_admin_stats_text():
    """Loyiha muallifi (Admin) uchun kengaytirilgan to'liq statistika"""
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

    cursor.execute("SELECT COUNT(*) FROM Diagnostic_Logs")
    total_diags = cursor.fetchone()[0]

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
        f"🧠 <b>AI DIAGNOSTIKA VA FAOLLIK:</b>\n"
        f"• Bolalardagi jami Biliglar: <b>{total_coins} 🔅</b>\n"
        f"• AI Savollar banki testlari: <b>{total_tests} ta</b>\n"
        f"• O‘tkazilgan pedagogik tahlillar: <b>{total_diags} ta</b>\n\n"
        f"🆕 <b>Oxirgi a'zo bo‘lganlar:</b>\n{recent_text}"
    )
    return text
