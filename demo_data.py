"""Namoyish (demo) ma'lumoti.

Loyihani investorlarga to‘liq ko‘rsatish uchun bitta farzand profilini
haqiqiyga o‘xshash natijalar bilan to‘ldiradi.

**QOIDA:** ilovaga yangi imkoniyat qo‘shilsa, SHU FAYLGA ham qo‘shiladi.
«To‘ldirish» tugmasi bosilganda ilovaning eng oxirgi holati to‘liq
ko‘rinishi kerak — bo‘sh ekran qolmasin.

Hozir to‘ldiriladi:
  · kitoblar, mutolaa tarixi, testlar, AI ustoz tahlillari, nishonlar
  · Bilig hisob daftari (hamyondagi harakatlar tarixi)
  · do‘kon sovg‘alari (belgilari bilan), xaridlar — berilgani va kutayotgani
  · orzu qilingan sovg‘a, Bilig kursi
  · ota-ona va bola uchun o‘qilmagan xabarnomalar (har turdan, shu
    jumladan «parvozing uzilmasin» ogohlantirishi)
  · kechki suhbat savoli — javob kutib turgan holatda

Faqat administrator (loyiha egasi) ishga tushira oladi.
"""

import json
from datetime import datetime, timedelta

from database import conn, cursor, calculate_and_update_rank


# Muqovasi ilovada mavjud kitoblar tanlandi — namoyishda javon chiroyli ko‘rinsin.
DEMO_BOOKS = [
    # (nom, muallif, jami bet, o‘qilgan bet, tugallanganmi, testlar, audio soni)
    ("Sariq devni minib", "Xudoyberdi To‘xtaboyev", 224, 224, True, (1, 1, 1), 2),
    ("Tom Soyerning boshidan kechirganlari", "Mark Tven", 208, 208, True, (1, 1, 1), 1),
    ("Kapitan Grant bolalari", "Jyul Vern", 320, 143, False, (1, 1, 0), 1),
]

DEMO_SINGLE_BOOKS = [
    ("Amir Temur haqida hikoyalar", "To‘lqin Hayit", 96, 96, True, (1, 1, 1), 1),
    ("Shum bola", "G‘afur G‘ulom", 180, 87, False, (1, 0, 0), 1),
]

# AI Ustozning ovozli xulosa bo‘yicha tahlillari
DEMO_REPORTS = [
    {
        "book": "Sariq devni minib",
        "days_ago": 3,
        "bonus": 3,
        "scores": (94, 92, 90, 89, 91),
        "summary": "Hoshimjonning sehrli qalpoqcha bilan boshlangan sarguzashtlarini "
                   "boshidan oxirigacha izchil so‘zlab berdi. Voqealar ketma-ketligini "
                   "chalkashtirmadi, qahramonlarning nomlarini aniq esladi.",
        "strengths": "Voqealarni o‘z his-tuyg‘ulari bilan bo‘yab gapirdi. "
                     "«Adolat» va «insof» kabi so‘zlarni o‘rinli ishlatdi.",
        "weaknesses": "Asar oxiridagi xulosani biroz shoshib aytdi — muallif nima "
                      "demoqchi bo‘lgani haqida ko‘proq o‘ylashi foydali bo‘ladi.",
        "convo": "Kechki suhbat uchun savol: «Agar senda ham sehrli qalpoqcha bo‘lsa, "
                 "uni birinchi navbatda nimaga ishlatgan bo‘larding?»",
        "child": "Barakalla! Hikoyani shunday jonli so‘zlab berdingki, men ham "
                 "Hoshimjon bilan birga sayohat qilgandek bo‘ldim. Ayniqsa «adolat» "
                 "so‘zini o‘rinli ishlatganing menga juda yoqdi. Shu zavq bilan "
                 "davom et — keyingi kitob seni yanada qiziqarli olamga olib boradi!",
    },
    {
        "book": "Amir Temur haqida hikoyalar",
        "days_ago": 9,
        "bonus": 2,
        "scores": (88, 82, 78, 85, 80),
        "summary": "Sohibqiron haqidagi hikoyalardan ikkitasini batafsil, qolganini "
                   "qisqacha so‘zlab berdi. Tarixiy joy nomlarini to‘g‘ri esladi.",
        "strengths": "Nutqi ravon, to‘xtalishlar deyarli yo‘q. Qahramonning "
                     "qarorlarini o‘z so‘zlari bilan izohlay oldi.",
        "weaknesses": "Ba'zi hikoyalarda voqealar sababini emas, faqat natijasini "
                      "aytdi. «Nima uchun shunday bo‘ldi?» degan savolga e'tibor bering.",
        "convo": "Kechki suhbat uchun savol: «Amir Temurning qaysi fazilati senga "
                 "eng ko‘p yoqdi va nima uchun?»",
        "child": "Zo‘r ish qilding! Tarixiy joy nomlarini xatosiz esladingiz — bu "
                 "diqqating kuchli ekanini bildiradi. Endi bir narsani sinab ko‘r: "
                 "har voqeadan keyin o‘zingga «nega shunday bo‘ldi?» deb savol ber. "
                 "Shunda hikoyalar yanada qiziqarli ochiladi.",
    },
    {
        "book": "Tom Soyerning boshidan kechirganlari",
        "days_ago": 18,
        "bonus": 2,
        "scores": (90, 91, 87, 88, 89),
        "summary": "Tom va Geklberri Finn do‘stligi haqida qiziqarli, jonli "
                   "hikoya qildi. O‘zini Tom o‘rniga qo‘yib ham fikr bildirdi.",
        "strengths": "Mustaqil xulosa chiqardi: «rostgo‘ylik qo‘rquvdan kuchliroq» "
                     "dedi. Bu yoshi uchun juda yaxshi tafakkur.",
        "weaknesses": "Ayrim ismlarni almashtirib yubordi — qayta o‘qishda "
                      "qahramonlar ro‘yxatini yozib qo‘yish yordam beradi.",
        "convo": "Kechki suhbat uchun savol: «Tom devorni bo‘yashni do‘stlariga "
                 "qanday qilib qiziqarli ish qilib ko‘rsatdi? Sen ham shunday "
                 "qilganmisan?»",
        "child": "«Rostgo‘ylik qo‘rquvdan kuchliroq» — buni o‘zing topding, va bu "
                 "juda teran fikr. Katta kitobxonlar ham shunday o‘ylaydi. "
                 "Qahramonlar ismini yozib borsang, hikoya yanada oson eslab qolinadi.",
    },
]

# Test natijalari: kitob nomi → uchta bosqichning foizi.
# Bosqich bajarilmagan bo‘lsa (DEMO_BOOKS dagi tests tuple da 0) — o‘tkazib
# yuboriladi. Savollar soni: oraliq testda 7 ta, yakuniyda 10 ta.
DEMO_TEST_PCT = {
    "Sariq devni minib": (86, 100, 90),
    "Tom Soyerning boshidan kechirganlari": (71, 86, 80),
    "Kapitan Grant bolalari": (86, 71, 0),
    "Amir Temur haqida hikoyalar": (100, 86, 90),
    "Shum bola": (71, 0, 0),
}
TEST_SIZES = (7, 7, 10)

# AI ustozning ochiq savollari va bolaning ovozli javoblari.
# (kitob, bosqich, necha kun oldin, savol, javob mazmuni)
DEMO_TALKS = [
    ("Sariq devni minib", "end", 4,
     "Hoshimjon boshidan kechirgan sinovlardan keyin o‘zgardimi? Nimasi bilan?",
     "Hoshimjon avval qo‘rqoqroq edi, keyin o‘zgardi — do‘stlari uchun "
     "javobgarlikni o‘z zimmasiga oldi, deb izohladi. Misol keltirdi."),
    ("Tom Soyerning boshidan kechirganlari", "start", 22,
     "Tom qanday bola? Uni bir jumlada tasvirlab bera olasanmi?",
     "«Sho‘x, lekin yuragi toza» dedi va buni devor bo‘yash voqeasi bilan "
     "asosladi. O‘z tengdoshlariga taqqosladi."),
]

# Do‘kon mahsulotlari — ota-ona farzandiga qo‘yadigan sovg‘alar
DEMO_STORE = [
    ("Muzqaymoq", 10, "\U0001F366"),
    ("Hot-dog", 15, "\U0001F32D"),
    ("Gamburger", 25, "\U0001F354"),
    ("Pizza", 60, "\U0001F355"),
    ("Kinoga borish", 120, "\U0001F3AC"),
    ("Yangi kitob", 150, "\U0001F4DA"),
    ("Smart soat", 400, "\u231A"),
]

# Xaridlar: (sovg‘a nomi, necha kun oldin, berilganmi)
# «Kinoga borish» ataylab 4 kun oldin va berilmagan — shunda ota-onaning
# bosh sahifasida «sovg‘a hali berilmadi» eslatmasi ham ko‘rinadi.
DEMO_PURCHASES = [
    ("Muzqaymoq", 12, True),
    ("Gamburger", 6, True),
    ("Kinoga borish", 4, False),
]

DEMO_GOAL = "Smart soat"          # bolaning orzusi
DEMO_COIN_RATE = 500              # 1 Bilig = 500 so‘m
DEMO_PARENT_BONUS = 60            # ota-ona qo‘lda qo‘shgan Bilig

DEMO_BADGES = [
    "Birinchi qadam", "Kitobxon sayyoh", "Kitoblar sultoni",
    "Olovli qanot", "Tengsiz qahramon", "Marra g‘olibi",
    "Zukko kitobxon", "Ilm notig‘i", "Tafakkur", "Chaqmoq kitobxon",
]


def _iso(days_ago, hour=19, minute=30):
    d = datetime.now() - timedelta(days=days_ago)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat(timespec="seconds")


def _add_book(plan_id, book):
    title, author, total, read, done, tests, audio = book
    cursor.execute(
        "INSERT INTO Plan_Books (plan_id, title, author, total_pages, pages_read, "
        "is_completed, mid_test_1_done, mid_test_2_done, final_test_done, audio_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (plan_id, title, author, total, read, 1 if done else 0,
         tests[0], tests[1], tests[2], audio)
    )
    return cursor.lastrowid


def clear_demo_child(child_id):
    """Farzandning barcha kitob, tarix va tahlillarini o‘chiradi."""
    cursor.execute("SELECT plan_id FROM Reading_Plans WHERE child_id = ?", (child_id,))
    plan_ids = [r[0] for r in cursor.fetchall()]
    for pid in plan_ids:
        cursor.execute("SELECT book_id FROM Plan_Books WHERE plan_id = ?", (pid,))
        for (bid,) in cursor.fetchall():
            cursor.execute("DELETE FROM Book_Tests WHERE book_id = ?", (bid,))
        cursor.execute("DELETE FROM Plan_Books WHERE plan_id = ?", (pid,))
    cursor.execute("DELETE FROM Reading_Plans WHERE child_id = ?", (child_id,))
    cursor.execute("DELETE FROM Reading_Logs WHERE child_id = ?", (child_id,))
    cursor.execute("DELETE FROM Diagnostic_Logs WHERE child_id = ?", (child_id,))
    # Yangi bo‘limlar: hamyon, xaridlar, xabarnomalar, kechki suhbat
    for sql in (
        "DELETE FROM Coin_Ledger WHERE child_id = ?",
        "DELETE FROM Purchases WHERE child_id = ?",
        "DELETE FROM Notifications WHERE child_id = ?",
        "DELETE FROM Talk_Checks WHERE child_id = ?",
        "DELETE FROM Group_Members WHERE child_id = ?",
        "DELETE FROM Group_Requests WHERE child_id = ?",
        "DELETE FROM Group_Task_Members WHERE child_id = ?",
        "DELETE FROM Group_Kudos WHERE to_child = ?",
        "DELETE FROM Group_Kudos WHERE from_child = ?",
    ):
        try:
            cursor.execute(sql, (child_id,))
        except Exception:
            pass          # jadval hali yaratilmagan bo‘lsa — e'tiborsiz
    # A'zosi qolmagan namoyish guruhi ham o‘chadi — «To‘ldirish» qayta
    # bosilganda guruh takrorlanib ketmasligi uchun.
    try:
        cursor.execute(
            "DELETE FROM Groups WHERE group_id NOT IN (SELECT group_id FROM Group_Members)")
        cursor.execute(
            "DELETE FROM Group_Tasks WHERE group_id NOT IN (SELECT group_id FROM Groups)")
        cursor.execute(
            "DELETE FROM Group_Task_Members WHERE task_id NOT IN (SELECT task_id FROM Group_Tasks)")
    except Exception:
        pass
    cursor.execute(
        "UPDATE Users SET balance_coins = 0, streak_days = 0, total_xp = 0, badges = '', "
        "badges_seen = 0, goal_item_id = NULL, streak_freezes = 0 WHERE user_id = ?",
        (child_id,)
    )
    conn.commit()


# Har sinfdoshda: raqami, ismi, avatari, tugatgan kitoblari soni va
# shu haftadagi kunlik betlari (dushanbadan bugungacha aylanma tarzda
# olinadi). Raqamlar QAT'IY — «To‘ldirish» qayta bosilsa ham reyting
# aynan bir xil chiqadi.
DEMO_MATES = [
    (-9001, "Doniyor", "bear", 6, [34, 28, 40, 22, 36, 30, 26], 9),
    (-9002, "Nilufar", "owl", 5, [26, 31, 18, 29, 24, 33, 20], 8),
    (-9003, "Javohir", "lion", 4, [22, 0, 27, 19, 25, 0, 30], 7),
    (-9004, "Zilola", "rabbit", 3, [18, 21, 0, 24, 16, 22, 0], 6),
    (-9005, "Bekzod", "dog", 2, [12, 0, 0, 15, 0, 18, 0], 4),
]
DEMO_MATE_REQ = (-9006, "Shohrux", "fox", 3, [20, 17, 0, 23, 0, 19, 21], 6)
DEMO_GROUP_NAME = "4-maktab, 7-B sinf"
DEMO_MATE_BOOKS = [
    ("Alpomish", "Xalq dostoni", 96),
    ("Shum bola", "G‘afur G‘ulom", 128),
    ("Bolalikning oltin daftari", "Xudoyberdi To‘xtaboyev", 112),
    ("Sariq devni minib", "Xudoyberdi To‘xtaboyev", 176),
    ("Kichkina shahzoda", "Antuan de Sent-Ekzyuperi", 88),
    ("Robinzon Kruzo", "Daniel Defo", 148),
]


def _week_days():
    """Shu haftaning dushanbasidan bugungacha bo‘lgan kunlar."""
    today = datetime.now()
    start = today - timedelta(days=today.weekday())
    out = []
    d = start
    while d.date() <= today.date():
        out.append(d)
        d = d + timedelta(days=1)
    return out


def _demo_mate(uid, mate_name, avatar, books, week_pages=None, correct=0):
    """Namoyish uchun sinfdosh profili va uning tugatgan kitoblari."""
    cursor.execute(
        "INSERT OR REPLACE INTO Users (user_id, role, name, is_approved, avatar_id, profile_done) "
        "VALUES (?, 'child', ?, 1, ?, 1)", (uid, mate_name, avatar)
    )
    cursor.execute("SELECT plan_id FROM Reading_Plans WHERE child_id = ?", (uid,))
    for (pid,) in cursor.fetchall():
        cursor.execute("DELETE FROM Plan_Books WHERE plan_id = ?", (pid,))
    cursor.execute("DELETE FROM Reading_Plans WHERE child_id = ?", (uid,))
    cursor.execute(
        "INSERT INTO Reading_Plans (parent_id, child_id, name, status, plan_type) "
        "VALUES (?, ?, ?, 'active', 'quick')", (uid, uid, "Sinf ro‘yxati")
    )
    pid = cursor.lastrowid
    book_id = None
    for i in range(books):
        title, author, total = DEMO_MATE_BOOKS[i % len(DEMO_MATE_BOOKS)]
        cursor.execute(
            "INSERT INTO Plan_Books (plan_id, title, author, total_pages, pages_read, is_completed) "
            "VALUES (?, ?, ?, ?, ?, 1)", (pid, title, author, total, total)
        )
        book_id = cursor.lastrowid

    # Haftalik reyting shu yozuvlardan hisoblanadi — busiz «Haftalik»
    # ro‘yxati bo‘sh ko‘rinardi.
    cursor.execute("DELETE FROM Reading_Logs WHERE child_id = ?", (uid,))
    cursor.execute("DELETE FROM Diagnostic_Logs WHERE child_id = ?", (uid,))
    # Shu hafta va undan oldingi uch hafta — «Oylik» va «Umumiy»
    # ro‘yxatlar ham haqiqiyga o‘xshab ko‘rinishi uchun.
    for week_back in range(4):
        for i, day in enumerate(_week_days()):
            d = day - timedelta(days=7 * week_back)
            pages = (week_pages or [0])[(i + week_back) % len(week_pages or [0])]
            if not pages:
                continue
            cursor.execute(
                "INSERT INTO Reading_Logs (child_id, book_id, pages_added, created_at) "
                "VALUES (?, ?, ?, ?)",
                (uid, book_id, pages, d.replace(hour=18, minute=0, second=0,
                                                microsecond=0).strftime("%Y-%m-%d %H:%M:%S"))
            )
    if correct:
        last = _week_days()[-1]
        cursor.execute(
            "INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, "
            "logic_score, conclusion_score, created_at, correct_count, total_count) "
            "VALUES (?, ?, 'test', 80, 80, 80, ?, ?, 10)",
            (uid, book_id, last.replace(hour=19, minute=0, second=0,
                                        microsecond=0).strftime("%Y-%m-%d %H:%M:%S"), correct)
        )


DEMO_TASK_BOOK = ("Sariq devni minib", "Xudoyberdi To‘xtaboyev", 176)
DEMO_TASK_QUESTIONS = [
    {"question": "Hoshimjon sehrli qalpoqni qayerdan topib oladi?",
     "options": ["Bog‘dan", "G‘ordan", "Maktabdan", "Bozordan"], "answer": "G‘ordan"},
    {"question": "Hoshimjon sariq devni nima bilan yengadi?",
     "options": ["Aql va topqirlik bilan", "Kuch bilan", "Sehrli qilich bilan"],
     "answer": "Aql va topqirlik bilan"},
    {"question": "Asar qahramoni dastlab qanday o‘quvchi edi?",
     "options": ["Dangasa", "A‘lochi", "Sportchi"], "answer": "Dangasa"},
    {"question": "Hoshimjonga eng ko‘p kim yordam beradi?",
     "options": ["Do‘stlari", "Hech kim", "Sariq dev"], "answer": "Do‘stlari"},
    {"question": "Asarning asosiy g‘oyasi nima?",
     "options": ["Mehnat va aql g‘alaba keltiradi", "Kuchli bo‘lgan yutadi",
                 "Omad hal qiladi"], "answer": "Mehnat va aql g‘alaba keltiradi"},
]
# OTA-ONA TAHRIRLAYDIGAN TAYYOR TEST (2026-09-02 imkoniyati).
# Namoyishda ota-ona kitob oynasidan «Savollarni ko‘rish va tahrirlash» ni
# bossa, bo‘sh emas — tayyor 12 ta savol chiqadi va ularni tuzatib ko‘rsatadi.
# Qolgan kitoblarga test umumiy bankdan olinadi (pastdagi halqa).
DEMO_BOOK_TEST_TITLE = "Tom Soyerning boshidan kechirganlari"
DEMO_BOOK_TEST = [
    {"id": 1, "part": 1, "category": "factual",
     "question": "Tom kim bilan birga yashaydi?",
     "options": ["Polli xolasi bilan", "Otasi bilan", "Yolg‘iz"],
     "answer": "Polli xolasi bilan"},
    {"id": 2, "part": 1, "category": "logic",
     "question": "Tom devor bo‘yashni qanday qildirib oldi?",
     "options": ["Ishni qiziqarli ko‘rsatib", "Pul berib", "Yig‘lab"],
     "answer": "Ishni qiziqarli ko‘rsatib"},
    {"id": 3, "part": 1, "category": "factual",
     "question": "Tomning eng yaqin do‘sti kim?",
     "options": ["Geklberri Finn", "O‘qituvchisi", "Polli xola"],
     "answer": "Geklberri Finn"},
    {"id": 4, "part": 1, "category": "factual",
     "question": "Tom maktabda kimni yoqtirib qoladi?",
     "options": ["Bekkini", "Polli xolani", "Hech kimni"],
     "answer": "Bekkini"},
    {"id": 5, "part": 2, "category": "factual",
     "question": "Tom va do‘stlari qayerga qochib ketishadi?",
     "options": ["Orolga", "Tog‘ga", "Boshqa shaharga"],
     "answer": "Orolga"},
    {"id": 6, "part": 2, "category": "logic",
     "question": "Bolalar yo‘qolganda shahar nima deb o‘ylaydi?",
     "options": ["Halok bo‘lishgan deb", "Uxlab qolishgan deb", "Sayohatga ketishgan deb"],
     "answer": "Halok bo‘lishgan deb"},
    {"id": 7, "part": 2, "category": "factual",
     "question": "Tom o‘z motam marosimida nima qiladi?",
     "options": ["Tirik holda paydo bo‘ladi", "Yashirinib qoladi", "Uyga qaytmaydi"],
     "answer": "Tirik holda paydo bo‘ladi"},
    {"id": 8, "part": 2, "category": "conclusion",
     "question": "Sudda Tom nima qilishga jur\'at qildi?",
     "options": ["Haqiqatni aytdi", "Jim turdi", "Qochib ketdi"],
     "answer": "Haqiqatni aytdi"},
    {"id": 9, "part": 3, "category": "factual",
     "question": "Tom va Bekki qayerda adashib qolishadi?",
     "options": ["G‘orda", "O‘rmonda", "Daryoda"],
     "answer": "G‘orda"},
    {"id": 10, "part": 3, "category": "logic",
     "question": "Tom Bekkini qanday qutqaradi?",
     "options": ["Chiqish yo‘lini topib", "Baqirib chaqirib", "Kutib o‘tirib"],
     "answer": "Chiqish yo‘lini topib"},
    {"id": 11, "part": 3, "category": "factual",
     "question": "Bolalar oxirida nimani topib olishadi?",
     "options": ["Xazinani", "Kemani", "Xatni"],
     "answer": "Xazinani"},
    {"id": 12, "part": 3, "category": "conclusion",
     "question": "Asar o‘quvchiga nimani o‘rgatadi?",
     "options": ["Jasorat va halollikni", "Boylik izlashni", "Dangasalikni"],
     "answer": "Jasorat va halollikni"},
]

# Namoyishda musobaqa yarim yo‘lda turadi: kimdir tugatgan, kimdir o‘qiyapti.
# (raqami, o‘qigan beti, tugatganmi, testdagi to‘g‘ri javob, ovozli xulosa Biligi)
DEMO_TASK_RACERS = [(-9001, 176, 1, 4, 3), (-9002, 138, 0, 3, 2),
                    (-9003, 96, 0, 2, 0), (-9004, 54, 0, 0, 0)]


def _fill_demo_task(gid, child_id, parent_id):
    """Namoyish uchun ochiq musobaqa: sovg‘asi, muddati va qatnashchilari bilan."""
    title, author, pages = DEMO_TASK_BOOK
    now = datetime.now()
    cursor.execute(
        "INSERT INTO Group_Tasks (group_id, kind, title, author, total_pages, goal_kind, "
        "goal_value, prize, deadline, final_count, questions_json, checked_by, status, "
        "created_by, created_at, published_at) VALUES (?, 'book', ?, ?, ?, 'books', 0, ?, ?, "
        "?, ?, ?, 'open', ?, ?, ?)",
        (gid, title, author, pages, "Velosiped",
         (now + timedelta(days=9)).strftime("%Y-%m-%d"), len(DEMO_TASK_QUESTIONS),
         json.dumps(DEMO_TASK_QUESTIONS, ensure_ascii=False), "Nodira opa",
         parent_id,
         now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S"))
    )
    tid = cursor.lastrowid
    joined = (now - timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S")

    def _put(uid, read, done, correct=0, voice=0):
        cursor.execute(
            "SELECT plan_id FROM Reading_Plans WHERE child_id = ? ORDER BY plan_id LIMIT 1", (uid,))
        r = cursor.fetchone()
        if not r:
            return
        cursor.execute(
            "INSERT INTO Plan_Books (plan_id, title, author, total_pages, pages_read, is_completed, "
            "last_read_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (r[0], title, author, pages, read, done, now.strftime("%Y-%m-%d %H:%M:%S"))
        )
        bid = cursor.lastrowid
        cursor.execute(
            "INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)",
            (bid, json.dumps(DEMO_TASK_QUESTIONS, ensure_ascii=False)))
        # Musobaqa ballari shu yozuvlardan hisoblanadi: test javoblari,
        # ovozli xulosa va AI ustoz savoli.
        seconds = 0
        if correct:
            cursor.execute(
                "INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, logic_score, "
                "conclusion_score, created_at, correct_count, total_count) "
                "VALUES (?, ?, 'test', 80, 80, 80, ?, ?, 5)",
                (uid, bid, (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), correct))
            seconds = 240 + correct * 30
        if voice:
            cursor.execute(
                "INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, logic_score, "
                "conclusion_score, fluency_score, created_at, bonus_bilig) "
                "VALUES (?, ?, 'voice', 90, 90, 90, 90, ?, ?)",
                (uid, bid, (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), voice))
        cursor.execute(
            "INSERT OR REPLACE INTO Group_Task_Members (task_id, child_id, book_id, joined_at, "
            "test_seconds) VALUES (?, ?, ?, ?, ?)", (tid, uid, bid, joined, seconds))

    _put(child_id, 112, 0, 3, 2)
    for uid, read, done, correct, voice in DEMO_TASK_RACERS:
        _put(uid, read, done, correct, voice)
    return tid


def _fill_demo_group(parent_id, child_id, child_display_name):
    """Sinfdoshlar guruhi: a'zolar, taklif kodi va bitta kutayotgan so‘rov."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("DELETE FROM Groups WHERE admin_user_id = ? AND name = ?",
                   (parent_id, DEMO_GROUP_NAME))
    cursor.execute(
        "INSERT INTO Groups (name, admin_user_id, invite_code, searchable, created_at) "
        "VALUES (?, ?, ?, 1, ?)", (DEMO_GROUP_NAME, parent_id, "BILIG-7431", now)
    )
    gid = cursor.lastrowid
    cursor.execute(
        "INSERT OR REPLACE INTO Group_Members (group_id, child_id, is_admin, joined_at) "
        "VALUES (?, ?, 1, ?)", (gid, child_id, now)
    )
    for uid, mate_name, avatar, books, week_pages, correct in DEMO_MATES:
        _demo_mate(uid, mate_name, avatar, books, week_pages, correct)
        cursor.execute(
            "INSERT OR REPLACE INTO Group_Members (group_id, child_id, is_admin, joined_at) "
            "VALUES (?, ?, 0, ?)", (gid, uid, now)
        )
    uid, mate_name, avatar, books, week_pages, correct = DEMO_MATE_REQ
    _demo_mate(uid, mate_name, avatar, books, week_pages, correct)
    cursor.execute(
        "INSERT OR REPLACE INTO Group_Requests (group_id, child_id, status, created_at) "
        "VALUES (?, ?, 'pending', ?)", (gid, uid, now)
    )
    # Namoyish bolasining o‘zi ham shu haftada ko‘rinsin: dushanbadan
    # bugungacha har kuni yozuv qo‘yiladi, aks holda u haftalik
    # reytingda umuman chiqmasdi.
    cursor.execute(
        "SELECT pb.book_id FROM Plan_Books pb JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
        "WHERE rp.child_id = ? ORDER BY pb.book_id DESC LIMIT 1", (child_id,)
    )
    r = cursor.fetchone()
    own_book = r[0] if r else None
    own_pages = [30, 24, 35, 28, 32, 26, 38]
    for i, day in enumerate(_week_days()):
        stamp = day.replace(hour=17, minute=30, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "SELECT 1 FROM Reading_Logs WHERE child_id = ? AND created_at = ?", (child_id, stamp))
        if cursor.fetchone():
            continue
        cursor.execute(
            "INSERT INTO Reading_Logs (child_id, book_id, pages_added, created_at) "
            "VALUES (?, ?, ?, ?)", (child_id, own_book, own_pages[i % len(own_pages)], stamp)
        )
    _fill_demo_task(gid, child_id, parent_id)
    # Olqishlar — namoyishda bu ekran ham bo‘sh qolmasin
    now_s = datetime.now()
    for i, (uid, phrase) in enumerate([(-9001, "Barakalla!"), (-9002, "Zo‘r o‘qiding!"),
                                       (-9003, "Davom et, oz qoldi!")]):
        cursor.execute(
            "INSERT INTO Group_Kudos (group_id, from_child, to_child, phrase, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (gid, uid, child_id, phrase,
             (now_s - timedelta(days=i + 1)).strftime("%Y-%m-%d %H:%M:%S"))
        )
    conn.commit()
    return gid


def _demo_plus(parent_id):
    """Namoyishda Bilig plus SINOV holatida turadi.

    Sabab: investorga ko‘rsatishda hech bir ekran qulflanmasin, lekin
    premium tizim borligi ham ko‘rinib tursin — bosh sahifada «sinov
    davri, N kun qoldi» yozuvi chiqadi.
    """
    now = datetime.now()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO Subscriptions (parent_id, plan, period, started_at, "
            "expires_at, trial_used, price, months_paid, provider, provider_id, updated_at) "
            "VALUES (?, 'trial', NULL, ?, ?, 1, 0, 0, NULL, NULL, ?)",
            (parent_id, (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
             (now + timedelta(days=11)).strftime("%Y-%m-%d %H:%M:%S"),
             now.strftime("%Y-%m-%d %H:%M:%S")))
    except Exception:
        pass          # jadval hali yaratilmagan bo‘lsa — e'tiborsiz


def fill_demo_child(parent_id, child_id):
    """Farzand profilini namoyish uchun to‘liq ma'lumot bilan to‘ldiradi."""
    clear_demo_child(child_id)
    _demo_plus(parent_id)
    book_ids = {}

    # 1. Marafon — bir nechta kitob, marra sovrini bilan
    cursor.execute(
        "INSERT INTO Reading_Plans (parent_id, child_id, name, prize, status, plan_type) "
        "VALUES (?, ?, ?, ?, 'active', 'marathon')",
        (parent_id, child_id, "Yozgi mutolaa marafoni", "Velosiped")
    )
    marathon_id = cursor.lastrowid
    for b in DEMO_BOOKS:
        book_ids[b[0]] = _add_book(marathon_id, b)

    # 2. Alohida tanlangan kitoblar
    for b in DEMO_SINGLE_BOOKS:
        cursor.execute(
            "INSERT INTO Reading_Plans (parent_id, child_id, name, prize, status, plan_type) "
            "VALUES (?, ?, 'Tezkor mutolaa', '', 'active', 'quick')",
            (parent_id, child_id)
        )
        book_ids[b[0]] = _add_book(cursor.lastrowid, b)

    # Namoyishda test «topshirilgan» deb turgan kitobning ORQASIDA
    # haqiqiy savollar bo‘lsin — ota-ona ularni ochib, tahrirlab
    # ko‘rsata olsin. Avval umumiy bankdan olinadi (u yerda bor).
    for _t, _bid in book_ids.items():
        cursor.execute("SELECT questions_json FROM Test_Bank WHERE title = ? LIMIT 1", (_t,))
        _r = cursor.fetchone()
        if _r and _r[0]:
            cursor.execute(
                "INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)",
                (_bid, _r[0]))

    # Bitta kitobda test bankdan qat'i nazar kafolatlangan bo‘lsin —
    # namoyish har qanday serverda bir xil ko‘rinishi kerak.
    _tid = book_ids.get(DEMO_BOOK_TEST_TITLE)
    if _tid:
        cursor.execute(
            "INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)",
            (_tid, json.dumps(DEMO_BOOK_TEST, ensure_ascii=False)))

    # 3. Mutolaa tarixi — 45 kun davomidagi kunlik yozuvlar
    schedule = [
        ("Sariq devni minib", [(44, 18), (43, 22), (41, 26), (40, 19), (38, 31),
                               (37, 24), (35, 28), (34, 21), (32, 35)]),
        ("Amir Temur haqida hikoyalar", [(30, 20), (29, 26), (27, 24), (26, 26)]),
        ("Tom Soyerning boshidan kechirganlari", [(24, 29), (23, 33), (21, 27), (20, 30),
                                                  (18, 24), (17, 34), (15, 31)]),
        ("Kapitan Grant bolalari", [(12, 22), (11, 28), (9, 19), (8, 26), (6, 23), (5, 25)]),
        ("Shum bola", [(4, 21), (3, 18), (2, 24), (1, 24)]),
    ]
    for title, entries in schedule:
        bid = book_ids.get(title)
        if not bid:
            continue
        last = ""
        for days_ago, pages in entries:
            ts = _iso(days_ago)
            if ts > last:
                last = ts
            cursor.execute(
                "INSERT INTO Reading_Logs (child_id, book_id, pages_added, created_at) "
                "VALUES (?, ?, ?, ?)",
                (child_id, bid, pages, ts)
            )
        # Kitob ro‘yxatlari «oxirgi o‘qilgani birinchi» tartibida chiqadi —
        # namoyishda ham shu tartib to‘g‘ri ko‘rinishi uchun vaqtni yozamiz.
        if last:
            cursor.execute(
                "UPDATE Plan_Books SET last_read_at = ? WHERE book_id = ?", (last, bid))

    # 4. AI Ustoz tahlillari
    for rep in DEMO_REPORTS:
        note = json.dumps({
            "summary": rep["summary"],
            "strengths": rep["strengths"],
            "weaknesses": rep["weaknesses"],
            "conversation_topic": rep["convo"],
        }, ensure_ascii=False)
        f, l, c, fl, v = rep["scores"]
        cursor.execute(
            "INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, "
            "logic_score, conclusion_score, fluency_score, vocabulary_score, "
            "parent_note, convo_topic, created_at, bonus_bilig, child_note) "
            "VALUES (?, ?, 'voice', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (child_id, book_ids.get(rep["book"]), f, l, c, fl, v,
             note, rep["convo"], _iso(rep["days_ago"], hour=20), rep["bonus"],
             rep["child"])
        )

    # 4b. Test natijalari — «Testlar» bo‘limi bo‘sh turmasin
    for b in DEMO_BOOKS + DEMO_SINGLE_BOOKS:
        title, tests = b[0], b[5]
        bid = book_ids.get(title)
        pcts = DEMO_TEST_PCT.get(title)
        if not bid or not pcts:
            continue
        last_day = min((d for t, ents in schedule if t == title for d, _ in ents),
                       default=10)
        for i, done in enumerate(tests):
            if not done or not pcts[i]:
                continue
            total = TEST_SIZES[i]
            pct = pcts[i]
            correct = int(round(total * pct / 100.0))
            cursor.execute(
                "INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, "
                "logic_score, conclusion_score, fluency_score, vocabulary_score, "
                "parent_note, convo_topic, created_at, bonus_bilig, correct_count, total_count) "
                "VALUES (?, ?, 'test', ?, ?, ?, 0, 0, '', '', ?, ?, ?, ?)",
                (child_id, bid, pct, pct, pct,
                 _iso(last_day + (2 - i) * 3, hour=17),
                 3 if pct >= 70 else 0, correct, total)
            )

    # 5. AI ustoz savoliga berilgan javoblar — kitob oynasida «bajarilgan»
    #    bo‘lib turadi va ota-ona hisobotida ko‘rinadi.
    for title, stage, days_ago, question, answer_note in DEMO_TALKS:
        bid = book_ids.get(title)
        if not bid:
            continue
        column = "talk_start_done" if stage == "start" else "talk_end_done"
        cursor.execute("UPDATE Plan_Books SET %s = 1 WHERE book_id = ?" % column, (bid,))
        note = json.dumps({"summary": answer_note, "strengths": "", "weaknesses": "",
                           "conversation_topic": question}, ensure_ascii=False)
        cursor.execute(
            "INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, "
            "logic_score, conclusion_score, fluency_score, vocabulary_score, "
            "parent_note, convo_topic, created_at, bonus_bilig, child_note) "
            "VALUES (?, ?, 'talk', 88, 90, 86, 89, 87, ?, ?, ?, 5, ?)",
            (child_id, bid, note, question, _iso(days_ago, hour=20), answer_note)
        )

    # 6. Do‘kon sovg‘alari — belgisi va narxi bilan.
    #    Nomi mos kelgani yangilanadi, boshqalari qo‘l tegizilmaydi.
    store_ids = {}
    for nm, price, emoji in DEMO_STORE:
        cursor.execute("SELECT item_id FROM Store_Items WHERE parent_id = ? AND name = ?",
                       (parent_id, nm))
        row = cursor.fetchone()
        if row:
            store_ids[nm] = row[0]
            cursor.execute("UPDATE Store_Items SET price = ?, emoji = ? WHERE item_id = ?",
                           (price, emoji, row[0]))
        else:
            cursor.execute(
                "INSERT INTO Store_Items (parent_id, name, price, emoji) VALUES (?, ?, ?, ?)",
                (parent_id, nm, price, emoji))
            store_ids[nm] = cursor.lastrowid

    # 7. Hamyon: Bilig hisob daftari. Har bir tanga qayerdan kelgani ko‘rinsin —
    #    balans shu yozuvlardan hisoblanadi, qo‘lda yozilmaydi.
    ledger = []
    for title, entries in schedule:
        for days_ago, pages in entries:
            coins = pages // 5
            if coins:
                ledger.append((coins, "pages", "O‘qilgan betlar · " + title, days_ago, 18))
    test_names = ("1-oraliq test", "2-oraliq test", "Yakuniy test")
    for b in DEMO_BOOKS + DEMO_SINGLE_BOOKS:
        title, tests = b[0], b[5]
        last_day = min((d for t, ents in schedule if t == title for d, _ in ents),
                       default=10)
        for i, done in enumerate(tests):
            if done:
                ledger.append((3, "test", test_names[i] + " · " + title,
                               last_day + (2 - i) * 3, 17))
    for rep_ in DEMO_REPORTS:
        ledger.append((rep_["bonus"], "voice", "Ovozli xulosa · " + rep_["book"],
                       rep_["days_ago"], 20))
    for title, stage, days_ago, question, _note in DEMO_TALKS:
        ledger.append((5, "talk", "AI ustoz savoli · " + title, days_ago, 20))
    ledger.append((DEMO_PARENT_BONUS, "manual", "Ota-ona qo‘shdi", 2, 21))
    # Ketma-ket o‘qish marrasi va muz — hamyon tarixida ular ham ko‘rinsin
    ledger.append((5, "streak", "Parvoz 7 kun", 5, 19))
    ledger.append((-15, "freeze", "Qanot", 8, 15))

    # 8. Xaridlar — berilgani va hali kutayotgani
    purchases = []
    for nm, days_ago, given in DEMO_PURCHASES:
        price = dict((x[0], x[1]) for x in DEMO_STORE).get(nm, 0)
        emoji = dict((x[0], x[2]) for x in DEMO_STORE).get(nm, "")
        cursor.execute(
            "INSERT INTO Purchases (child_id, parent_id, item_id, name, price, emoji, "
            "photo, status, created_at, given_at) VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, ?)",
            (child_id, parent_id, store_ids.get(nm), nm, price, emoji,
             "given" if given else "ordered", _iso(days_ago, hour=16),
             _iso(days_ago - 1, hour=19) if given else None))
        purchases.append((price, nm, days_ago, given, cursor.lastrowid))
        ledger.append((-price, "buy", nm, days_ago, 16))

    for amount, kind, note, days_ago, hour in ledger:
        cursor.execute(
            "INSERT INTO Coin_Ledger (child_id, amount, kind, note, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (child_id, amount, kind, note, _iso(days_ago, hour=hour)))

    balance = sum(x[0] for x in ledger)

    # 9. Orzu qilingan sovg‘a va Bilig kursi
    goal_id = store_ids.get(DEMO_GOAL)
    cursor.execute("UPDATE Users SET goal_item_id = ? WHERE user_id = ?", (goal_id, child_id))
    cursor.execute("UPDATE Users SET coin_rate = ?, show_som = 1 WHERE user_id = ?",
                   (DEMO_COIN_RATE, parent_id))
    # Bitta muz qo‘lida tursin — do‘konda «bor» ham, «yana olsa bo‘ladi» ham
    # ko‘rinsin.
    cursor.execute("UPDATE Users SET streak_freezes = 1 WHERE user_id = ?", (child_id,))

    # 10. Xabarnomalar — ikkala tomonda ham lenta to‘la bo‘lsin
    cursor.execute("SELECT name FROM Users WHERE user_id = ?", (child_id,))
    row = cursor.fetchone()
    name = (row[0] if row else "") or "Farzandingiz"
    pending = [p for p in purchases if not p[3]]
    pend_price, pend_name, pend_days, _g, pend_id = (
        pending[0] if pending else (0, "", 0, False, None))
    given_last = [p for p in purchases if p[3]]

    parent_feed = [
        ("gift_wait", f"«{pend_name}» sovg‘asi hali berilmadi",
         f"{name} uni {pend_price} Bilig yig‘ib qo‘lga kiritgan edi. "
         f"Va'daga vafo — eng katta saboq.", pend_id, 0, 12),
        ("badge", f"{name} «Chaqmoq kitobxon» nishonini qo‘lga kiritdi",
         "Bir o‘tirishda 30 va undan ortiq bet o‘qiganda beriladi. "
         "Bugun uni bir maqtab qo‘ying.", None, 1, 20),
        ("book_done", f"{name} «Tom Soyerning boshidan kechirganlari» kitobini tugatdi",
         "208 bet. Javonida endi 3 ta tugatilgan kitob bor.", None, 1, 21),
        ("test", f"{name} yakuniy testni topshirdi",
         "10 savoldan 9 tasi to‘g‘ri (90%). 3 Bilig oldi.", None, 2, 18),
        ("voice", f"{name} «Sariq devni minib» bo‘yicha ovozli xulosa yubordi",
         DEMO_REPORTS[0]["summary"], None, 3, 20),
        ("book_request", f"{name} «Qasoskorning oltin boshi» kitobini so‘rayapti",
         "Muallif: Xudoyberdi To‘xtaboyev. Kitobxona bo‘limidan bir bosishda "
         "rejasiga qo‘shasiz.", None, 3, 17),
        ("shield_used", f"{name} bir Qanot sarfladi",
         "O‘sha kuni o‘qimagan edi — parvozi shu bilan saqlanib qoldi.", None, 6, 20),
    ]
    for kind, title, body, ref, days_ago, hour in parent_feed:
        cursor.execute(
            "INSERT INTO Notifications (parent_id, child_id, kind, title, body, ref_id, "
            "to_user, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (parent_id, child_id, kind, title, body, ref, parent_id, _iso(days_ago, hour=hour)))

    child_feed = [
        ("shield_used", "Qanot ishlatildi",
         "O‘tgan hafta bir kun o‘qimagan eding, lekin bir Qanot sarflandi — "
         "parvozing uzilmadi.", 6, 20),
        ("gift_given", f"«{given_last[-1][1]}» sovg‘ang qo‘lingga tegdi!"
         if given_last else "Sovg‘ang qo‘lingga tegdi!",
         "Buni o‘z mehnating bilan qozonding.", 5, 19),
        ("coins", f"Ota-onang senga {DEMO_PARENT_BONUS} Bilig qo‘shdi",
         f"Hamyoningda endi {balance} Bilig bor.", 2, 21),
        ("new_book", "Senga yangi kitob: «Shum bola»",
         "Ota-onang qo‘ydi. Birinchi sahifadan boshlaymizmi?", 4, 18),
    ]
    for kind, title, body, days_ago, hour in child_feed:
        cursor.execute(
            "INSERT INTO Notifications (parent_id, child_id, kind, title, body, ref_id, "
            "to_user, created_at) VALUES (?, ?, ?, ?, ?, NULL, ?, ?)",
            (parent_id, child_id, kind, title, body, child_id, _iso(days_ago, hour=hour)))

    # «Parvozing uzilmasin» ogohlantirishi — bolaning lentasidagi ENG YANGI
    # xabar. U bosiladigan kartochka: ichidan Qanot sotib olish yoki
    # kitobga o‘tish mumkin.
    # Diqqat: haqiqiy hayotda bu xabar kechqurun soat 18 dan keyin chiqadi.
    # Namoyishda kutib o‘tirib bo‘lmaydi — vaqti HOZIR qilinadi (kechki
    # suhbat kartochkasida ham aynan shu yo‘l tutilgan).
    cursor.execute(
        "INSERT INTO Notifications (parent_id, child_id, kind, title, body, ref_id, "
        "to_user, created_at) VALUES (?, ?, 'streak_warn', ?, ?, NULL, ?, ?)",
        (parent_id, child_id, "Parvozing 12 kun — uzilib qolmasin",
         "Qanoting bor (1 ta) — parvozing uzilmaydi. Lekin eng yaxshisi "
         "bugun bir necha bet o‘qish.",
         child_id, datetime.now().isoformat(timespec="seconds")))

    # 11. Kechki suhbat — javob kutib turgan holatda (namoyishning eng
    #     ta'sirli qismlaridan biri: «Oila iftixori» nishoni shu yerdan).
    topic = DEMO_REPORTS[0]["convo"]
    cursor.execute(
        "INSERT INTO Talk_Checks (child_id, parent_id, book_id, topic, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (child_id, parent_id, book_ids.get(DEMO_REPORTS[0]["book"]), topic,
         _iso(0, hour=19)))
    check_id = cursor.lastrowid
    # Diqqat: haqiqiy hayotda bu xabar kechqurun 19:00 dan keyin chiqadi.
    # Namoyishda kutib o‘tirib bo‘lmaydi — shuning uchun vaqti HOZIR qilinadi.
    cursor.execute(
        "INSERT INTO Notifications (parent_id, child_id, kind, title, body, ref_id, "
        "to_user, created_at) VALUES (?, ?, 'talk_check', ?, ?, ?, ?, ?)",
        (parent_id, child_id, f"Bugun {name} bilan gaplashdingizmi?", topic,
         check_id, parent_id, datetime.now().isoformat(timespec="seconds")))

    # 11b. GURUH — sinfdoshlar doirasi.
    #      Sinfdoshlar haqiqiy foydalanuvchi emas: ular manfiy raqamli
    #      ichki profil (Telegramsiz farzand bilan bir xil usul). Raqamlar
    #      QAT'IY belgilangan — «To‘ldirish» qayta bosilganda takrorlanmaydi.
    _fill_demo_group(parent_id, child_id, name)

    # 12. Tanga, streak, nishonlar
    # badges_seen = 0 — nishonlar «hali ko‘rilmagan» holatda qoladi.
    # Shunda bosh sahifada tipratikanli kutib olish kartochkasi chiqadi va
    # uni bosib, to‘liq ekranli tabrikni ko‘rsatish mumkin. Namoyishning
    # eng ta'sirli qismi shu.
    cursor.execute(
        "UPDATE Users SET balance_coins = ?, streak_days = ?, total_xp = ?, "
        "badges = ?, badges_seen = 0, last_read_date = ? WHERE user_id = ?",
        (balance, 12, 758, ",".join(DEMO_BADGES),
         datetime.now().strftime("%Y-%m-%d"), child_id)
    )
    conn.commit()
    calculate_and_update_rank(child_id)
    return {"books": len(book_ids), "reports": len(DEMO_REPORTS),
            "badges": len(DEMO_BADGES), "balance": balance,
            "messages": len(parent_feed) + len(child_feed) + 2,
            "purchases": len(purchases)}
