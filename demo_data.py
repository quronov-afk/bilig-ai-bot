"""Namoyish (demo) ma'lumoti.

Loyihani investorlarga to‘liq ko‘rsatish uchun bitta farzand profilini
haqiqiyga o‘xshash natijalar bilan to‘ldiradi: o‘qilgan kitoblar, mutolaa
tarixi, testlar, AI Ustozning ovozli tahlillari va nishonlar.

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
        "bonus": 5,
        "scores": (92, 88, 90, 86, 84),
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
        "bonus": 4,
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
        "bonus": 5,
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

# Do‘kon mahsulotlari — ota-ona farzandiga qo‘yadigan sovg‘alar
DEMO_STORE = [
    ("Muzqaymoq", 10),
    ("Hot-dog", 15),
    ("Gamburger", 25),
    ("Pizza", 60),
    ("Kinoga borish", 120),
    ("Yangi kitob", 150),
    ("Smart soat", 400),
]

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
    cursor.execute(
        "UPDATE Users SET balance_coins = 0, streak_days = 0, total_xp = 0, badges = '', "
        "badges_seen = 0 WHERE user_id = ?", (child_id,)
    )
    conn.commit()


def fill_demo_child(parent_id, child_id):
    """Farzand profilini namoyish uchun to‘liq ma'lumot bilan to‘ldiradi."""
    clear_demo_child(child_id)
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
        for days_ago, pages in entries:
            cursor.execute(
                "INSERT INTO Reading_Logs (child_id, book_id, pages_added, created_at) "
                "VALUES (?, ?, ?, ?)",
                (child_id, bid, pages, _iso(days_ago))
            )

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

    # 5. Do‘kon mahsulotlari — namoyishda do‘kon bo‘sh turmasin
    cursor.execute("SELECT COUNT(*) FROM Store_Items WHERE parent_id = ?", (parent_id,))
    if not cursor.fetchone()[0]:
        for nm, price in DEMO_STORE:
            cursor.execute(
                "INSERT INTO Store_Items (parent_id, name, price) VALUES (?, ?, ?)",
                (parent_id, nm, price)
            )

    # 6. Tanga, streak, nishonlar
    # badges_seen = 0 — nishonlar «hali ko‘rilmagan» holatda qoladi.
    # Shunda bosh sahifada tipratikanli kutib olish kartochkasi chiqadi va
    # uni bosib, to‘liq ekranli tabrikni ko‘rsatish mumkin. Namoyishning
    # eng ta'sirli qismi shu.
    cursor.execute(
        "UPDATE Users SET balance_coins = ?, streak_days = ?, total_xp = ?, "
        "badges = ?, badges_seen = 0, last_read_date = ? WHERE user_id = ?",
        (214, 12, 758, ",".join(DEMO_BADGES),
         datetime.now().strftime("%Y-%m-%d"), child_id)
    )
    conn.commit()
    calculate_and_update_rank(child_id)
    return {"books": len(book_ids), "reports": len(DEMO_REPORTS), "badges": len(DEMO_BADGES)}
