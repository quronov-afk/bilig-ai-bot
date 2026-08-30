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
    ):
        try:
            cursor.execute(sql, (child_id,))
        except Exception:
            pass          # jadval hali yaratilmagan bo‘lsa — e'tiborsiz
    cursor.execute(
        "UPDATE Users SET balance_coins = 0, streak_days = 0, total_xp = 0, badges = '', "
        "badges_seen = 0, goal_item_id = NULL, streak_freezes = 0 WHERE user_id = ?",
        (child_id,)
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
