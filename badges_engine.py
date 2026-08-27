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


def _num(sql, params=()):
    """Bitta sonli natija qaytaradi (bo‘sh bo‘lsa 0)."""
    try:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except Exception:
        return 0


def check_badges(child_id, ctx=None):
    """Bolaning hamma nishon shartlarini tekshiradi.

    ctx — shu daqiqada sodir bo‘lgan, bazada saqlanmaydigan holatlar:
        shield_used — «Olov qalqoni» ishlatildi (Qalqon nishoni uchun)
        ezgulik     — AI ustoz «qahramon fazilatlari» xulosasini a'lo dedi

    Qaytaradi: YANGI berilgan nishonlar ro‘yxati (bo‘lmasa — bo‘sh ro‘yxat).
    """
    ctx = ctx or {}
    new = []

    def give(name):
        try:
            if award_badge(child_id, name):
                new.append(name)
        except Exception:
            pass

    # ---------- I. Mutolaa hajmi (sahifalar) ----------
    pages = get_child_total_pages(child_id)
    for need, name in ((5, "Birinchi qadam"), (100, "Kitobxon sayyoh"),
                       (500, "Kitoblar sultoni"), (1000, "Ming betlik dovon"),
                       (5000, "Kitoblar ummoni")):
        if pages >= need:
            give(name)

    # ---------- II. Uzluksizlik (streak) ----------
    streak = _num("SELECT streak_days FROM Users WHERE user_id = ?", (child_id,))
    for need, name in ((3, "Olovli qanot"), (7, "Yengilmas qahramon"),
                       (30, "Mutolaa afsonasi"), (100, "Olmos iroda"),
                       (365, "Yil qahramoni")):
        if streak >= need:
            give(name)
    if ctx.get("shield_used"):
        give("Qalqon")

    # ---------- III. Tugatilgan kitoblar ----------
    done = _num(
        "SELECT COUNT(*) FROM Plan_Books pb "
        "JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id "
        "WHERE rp.child_id = ? AND pb.is_completed = 1", (child_id,))
    for need, name in ((1, "Marra g‘olibi"), (10, "Kichik kutubxonachi"),
                       (25, "Mutolaa akademigi")):
        if done >= need:
            give(name)

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
        give("Tezkor mutolaa")

    # ---------- IV. Notiqlik va tafakkur (ovozli xulosa) ----------
    if _num("SELECT COUNT(*) FROM Diagnostic_Logs WHERE child_id = ? "
            "AND type = 'voice' AND bonus_bilig >= 5", (child_id,)):
        give("Bilim notig‘i")
    if _num("SELECT COUNT(*) FROM Diagnostic_Logs WHERE child_id = ? "
            "AND type = 'voice' AND conclusion_score >= 90", (child_id,)):
        give("Tafakkur")
    if _num("SELECT COUNT(*) FROM Diagnostic_Logs WHERE child_id = ? "
            "AND type = 'voice' AND vocabulary_score >= 90", (child_id,)):
        give("Oltin qalam")
    if _num(
        "SELECT COUNT(*) FROM ("
        " SELECT book_id FROM Diagnostic_Logs WHERE child_id = ? AND type = 'voice' "
        " AND (factual_score + logic_score + conclusion_score + fluency_score "
        "      + vocabulary_score) / 5.0 >= 85 GROUP BY book_id)",
            (child_id,)) >= 10:
        give("Buyuk suxandon")
    if ctx.get("ezgulik"):
        give("Ezgulik elchisi")

    # ---------- V. Zukkolik (testlar) ----------
    if _num("SELECT COUNT(*) FROM Diagnostic_Logs WHERE child_id = ? AND type = 'test' "
            "AND total_count > 0 AND correct_count = total_count", (child_id,)):
        give("Zukko kitobxon")
    if _num("SELECT SUM(correct_count) FROM Diagnostic_Logs "
            "WHERE child_id = ? AND type = 'test'", (child_id,)) >= 50:
        give("Mantiq ustasi")
    try:
        cursor.execute(
            "SELECT correct_count, total_count FROM Diagnostic_Logs "
            "WHERE child_id = ? AND type = 'test' AND total_count > 0 "
            "ORDER BY diag_id DESC LIMIT 10", (child_id,))
        last10 = cursor.fetchall()
        if len(last10) == 10 and all(r[0] == r[1] for r in last10):
            give("Bilim akademiyasi")
    except Exception:
        pass

    # ---------- VI. Odat va intizom ----------
    if _num("SELECT COUNT(*) FROM Reading_Logs WHERE child_id = ? "
            "AND CAST(strftime('%H', created_at) AS INTEGER) BETWEEN 6 AND 8", (child_id,)):
        give("Tonggi qaldirg‘och")
    if _num("SELECT COUNT(*) FROM Reading_Logs WHERE child_id = ? "
            "AND CAST(strftime('%H', created_at) AS INTEGER) BETWEEN 21 AND 23", (child_id,)):
        give("Qutb yulduzi")
    if _num("SELECT COUNT(*) FROM Reading_Logs WHERE child_id = ? "
            "AND strftime('%w', created_at) IN ('0', '6')", (child_id,)):
        give("Maroqli")
    if _num("SELECT COUNT(*) FROM Reading_Logs WHERE child_id = ? "
            "AND pages_added >= 30", (child_id,)):
        give("Chaqmoq kitobxon")
    if _num("SELECT balance_coins FROM Users WHERE user_id = ?", (child_id,)) >= 2000:
        give("Xazinabon")

    return new
