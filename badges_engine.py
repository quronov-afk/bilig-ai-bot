# -*- coding: utf-8 -*-
# ==========================================================
# badges_engine.py — NISHONLARNI AVTOMATIK BERISH
# ------------------------------------------------------------
# Ilgari 29 ta nishondan faqat 3 tasi berilardi, qolganlari abadiy
# xira turardi. Endi bolaning har bir harakatidan keyin (sahifa
# qo‘shildi, test topshirildi, ovozli xulosa yuborildi) shu fayldagi
# check_badges() chaqiriladi va SHARTI BAJARILGAN hamma nishon
# birdaniga beriladi.
#
# Nishon nomlari webapp/badges/index.json dagi nomlar bilan AYNAN
# bir xil bo‘lishi shart — chizma shu nom orqali topiladi.
#
# Hozircha avtomatlashtirilmagan yagona nishon: «Oila iftixori»
# (ota-ona kechki suhbatni baholaydigan alohida oqim hali yo‘q).
# ==========================================================

from database import conn, cursor, award_badge, get_child_total_pages


# ==========================================================
# NISHON QAYSI HARAKATGA TEGISHLI
# ----------------------------------------------------------
# Ilgari har bir harakatdan keyin BARCHA nishon shartlari tekshirilib,
# sharti bajarilgan hammasi darrov ko‘rsatilardi. Natijada bola ovozli
# xulosa yuborganda «Tonggi qaldirg‘och» nishoni chiqib, u ovoz uchun
# berilgandek tuyulardi — bog‘liqlik uzilib qolardi.
#
# Endi har bir nishon o‘z «oilasi»ga tegishli. Bola qanday harakat
# qilgan bo‘lsa, FAQAT o‘sha oiladagi nishon darrov tabriklanadi.
# Qolganlari yo‘qolmaydi — ular ham beriladi, lekin bosh sahifadagi
# tipratikanli kutib olish kartochkasi orqali keyinroq yetkaziladi.
# ==========================================================
FAMILY_PAGES = "pages"      # sahifa o‘qish
FAMILY_STREAK = "streak"    # kunlar ketma-ketligi
FAMILY_BOOKS = "books"      # kitobni tugatish
FAMILY_VOICE = "voice"      # ovozli xulosa
FAMILY_TEST = "test"        # test topshirish
FAMILY_COINS = "coins"      # to‘plangan Bilig

# Qaysi harakatdan keyin qaysi oilalar DARROV ko‘rsatiladi.
# Bilig hamma harakatdan yig‘iladi, shuning uchun u hamma joyda bor.
# Kitob tugatilishi yakuniy test bilan bo‘ladi — shuning uchun «books»
# oilasi test harakatiga qo‘shilgan.
ACTION_FAMILIES = {
    "page":  (FAMILY_PAGES, FAMILY_STREAK, FAMILY_COINS),
    "voice": (FAMILY_VOICE, FAMILY_COINS),
    "test":  (FAMILY_TEST, FAMILY_BOOKS, FAMILY_COINS),
}


def _num(sql, params=()):
    """Bitta sonli natija qaytaradi (bo‘sh bo‘lsa 0)."""
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except Exception:
        return 0


def check_badges(child_id, ctx=None, action=None):
    """Bolaning hamma nishon shartlarini tekshiradi.

    ctx — shu daqiqada sodir bo‘lgan, bazada saqlanmaydigan holatlar:
        shield_used — «Olov qalqoni» ishlatildi (Qalqon nishoni uchun)
        ezgulik     — AI ustoz «qahramon fazilatlari» xulosasini a'lo dedi

    action — bola nima qildi: "page" | "voice" | "test".
        Shu harakatga tegishli nishonlar DARROV tabriklanadi.
        Qolganlari ham beriladi, lekin keyinroq — kutib olish kartochkasi
        orqali. Berilmasa (None) — hammasi darrov qaytariladi (eski xatti-harakat).

    Qaytaradi: (darrov_ko‘rsatiladiganlar, keyinroq_yetkaziladiganlar)
    """
    ctx = ctx or {}
    candidates = []          # [(oila, nom), ...] — hali berilmagan

    def give(name, family):
        candidates.append((family, name))

    # ---------- I. Mutolaa hajmi (sahifalar) ----------
    pages = get_child_total_pages(child_id)
    for need, name in ((5, "Birinchi qadam"), (100, "Kitobxon sayyoh"),
                       (500, "Kitoblar sultoni"), (1000, "Ming bir sahifa"),
                       (5000, "Kitob ummoni")):
        if pages >= need:
            give(name, FAMILY_PAGES)

    # ---------- II. Uzluksizlik (streak) ----------
    streak = _num("SELECT streak_days FROM Users WHERE user_id = ?", (child_id,))
    for need, name in ((3, "Olovli qanot"), (7, "Tengsiz qahramon"),
                       (30, "Mutolaa afsonasi"), (100, "Olmos iroda"),
                       (365, "Yil qahramoni")):
        if streak >= need:
            give(name, FAMILY_STREAK)
    if ctx.get("shield_used"):
        give("Qalqon", FAMILY_STREAK)

    # ---------- III. Tugatilgan kitoblar ----------
    done = _num(
        "SELECT COUNT(*) FROM Plan_Books pb "
        "JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
        "WHERE rp.child_id = ? AND pb.is_completed = 1", (child_id,))
    for need, name in ((1, "Marra g‘olibi"), (10, "Yosh kutubxonachi"),
                       (25, "Mutolaa akademigi")):
        if done >= need:
            give(name, FAMILY_BOOKS)

    # «Tezkor mutolaa» — tugatilgan kitobning birinchi va oxirgi yozuvi
    # orasi 3 kundan oshmagan bo‘lsa.
    if _num(
        "SELECT COUNT(*) FROM ("
        " SELECT rl.book_id FROM Reading_Logs rl "
        " JOIN Plan_Books pb ON pb.book_id = rl.book_id "
        " WHERE rl.child_id = ? AND pb.is_completed = 1 "
        " GROUP BY rl.book_id "
        " HAVING julianday(MAX(rl.created_at)) - julianday(MIN(rl.created_at)) <= 3)",
            (child_id,)):
        give("Tezkor mutolaa", FAMILY_BOOKS)

    # ---------- IV. Notiqlik va tafakkur (ovozli xulosa) ----------
    # «talk» — AI ustoz savoliga ovozli javob. U ham nutq mashqi, shuning
    # uchun shu oiladagi nishonlarga erkin xulosa bilan teng hisoblanadi.
    if _num("SELECT COUNT(*) FROM Diagnostic_Logs WHERE child_id = ? "
            "AND type IN ('voice', 'talk') "
            "AND (factual_score + logic_score + conclusion_score + fluency_score "
            "     + vocabulary_score) / 5.0 >= 90", (child_id,)):
        give("Ilm notig‘i", FAMILY_VOICE)
    if _num("SELECT COUNT(*) FROM Diagnostic_Logs WHERE child_id = ? "
            "AND type IN ('voice', 'talk') AND conclusion_score >= 90", (child_id,)):
        give("Tafakkur", FAMILY_VOICE)
    if _num("SELECT COUNT(*) FROM Diagnostic_Logs WHERE child_id = ? "
            "AND type IN ('voice', 'talk') AND vocabulary_score >= 90", (child_id,)):
        give("Oltin qalam", FAMILY_VOICE)
    if _num(
        "SELECT COUNT(*) FROM ("
        " SELECT book_id FROM Diagnostic_Logs WHERE child_id = ? "
        " AND type IN ('voice', 'talk') "
        " AND (factual_score + logic_score + conclusion_score + fluency_score "
        "      + vocabulary_score) / 5.0 >= 85 GROUP BY book_id)",
            (child_id,)) >= 10:
        give("Buyuk suxandon", FAMILY_VOICE)
    if ctx.get("ezgulik"):
        give("Ezgulik elchisi", FAMILY_VOICE)

    # ---------- V. Zukkolik (testlar) ----------
    if _num("SELECT COUNT(*) FROM Diagnostic_Logs WHERE child_id = ? AND type = 'test' "
            "AND total_count > 0 AND correct_count = total_count", (child_id,)):
        give("Zukko kitobxon", FAMILY_TEST)
    if _num("SELECT SUM(correct_count) FROM Diagnostic_Logs "
            "WHERE child_id = ? AND type = 'test'", (child_id,)) >= 50:
        give("Mantiq ustasi", FAMILY_TEST)
    try:
        cursor.execute(
            "SELECT correct_count, total_count FROM Diagnostic_Logs "
            "WHERE child_id = ? AND type = 'test' AND total_count > 0 "
            "ORDER BY diag_id DESC LIMIT 10", (child_id,))
        last10 = cursor.fetchall()
        if len(last10) == 10 and all(r[0] == r[1] for r in last10):
            give("Bilimdon", FAMILY_TEST)
    except Exception:
        pass

    # ---------- VI. Odat va intizom ----------
    if _num("SELECT COUNT(*) FROM Reading_Logs WHERE child_id = ? "
            "AND CAST(strftime('%H', created_at) AS INTEGER) BETWEEN 6 AND 8", (child_id,)):
        give("Tonggi qaldirg‘och", FAMILY_PAGES)
    if _num("SELECT COUNT(*) FROM Reading_Logs WHERE child_id = ? "
            "AND CAST(strftime('%H', created_at) AS INTEGER) BETWEEN 21 AND 23", (child_id,)):
        give("Qutb yulduzi", FAMILY_PAGES)
    if _num("SELECT COUNT(*) FROM Reading_Logs WHERE child_id = ? "
            "AND strftime('%w', created_at) IN ('0', '6')", (child_id,)):
        give("Maroqli", FAMILY_PAGES)
    if _num("SELECT COUNT(*) FROM Reading_Logs WHERE child_id = ? "
            "AND pages_added >= 30", (child_id,)):
        give("Chaqmoq kitobxon", FAMILY_PAGES)
    if _num("SELECT balance_coins FROM Users WHERE user_id = ?", (child_id,)) >= 2000:
        give("Xazinabon", FAMILY_COINS)

    # ---------- Nishonlarni tartib bilan berish ----------
    # AVVAL shu harakatga tegishlilari beriladi — shunda ular ro‘yxatning
    # oxirida ketma-ket turadi va «ko‘rilgan» deb belgilash oson bo‘ladi.
    # Keyin qolganlari beriladi: ular «ko‘rilmagan» bo‘lib qoladi va
    # bosh sahifadagi kutib olish kartochkasi orqali yetkaziladi.
    allowed = ACTION_FAMILIES.get(action) if action else None
    related = [n for f, n in candidates if allowed is None or f in allowed]
    other = [n for f, n in candidates if allowed is not None and f not in allowed]

    shown, later = [], []
    for name in related:
        try:
            if award_badge(child_id, name):
                shown.append(name)
        except Exception:
            pass
    for name in other:
        try:
            if award_badge(child_id, name):
                later.append(name)
        except Exception:
            pass
    return shown, later
