import json
import random
import html
from datetime import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import (
    conn, cursor, get_parent_id, update_streak,
    calculate_and_update_rank
)
from keyboards import (
    get_child_keyboard, get_bolaxona_keyboard, get_back_reply_keyboard
)
from states import ChildReading
from ai_service import verify_page_photo, evaluate_voice_summary

router = Router()

async def get_effective_child_id(event: types.Message | types.CallbackQuery, state: FSMContext) -> int:
    """Bolaxona rejimida yoki alohida bola profilida bo'lsa ham haqiqiy child_id ni aniqlash"""
    data = await state.get_data()
    active_id = data.get('active_child_id')
    if active_id:
        return active_id
    return event.from_user.id

async def get_appropriate_keyboard(child_id: int, state: FSMContext):
    data = await state.get_data()
    if data.get('active_child_id'):
        return get_bolaxona_keyboard()
    return get_child_keyboard()

# ==========================================
# BOLANING KITOB RO'YXATI
# ==========================================
async def show_child_books(message_or_callback, user_id, state: FSMContext = None):
    parent_id = get_parent_id(user_id)
    if not parent_id and state:
        data = await state.get_data()
        parent_id = data.get('bolaxona_parent_id')

    if not parent_id:
        text_no_parent = "Siz hali ota-onangizga ulanmagansiz! Iltimos, ota-onangiz bergan kod orqali ulaning."
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.answer(text_no_parent)
        else:
            await message_or_callback.message.edit_text(text_no_parent)
        return
        
    cursor.execute("SELECT COUNT(*) FROM Family_Link WHERE parent_id = ?", (parent_id,))
    total_children = cursor.fetchone()[0]

    if total_children <= 1:
        cursor.execute("SELECT plan_id, name, prize FROM Reading_Plans WHERE parent_id = ? AND (child_id = ? OR child_id IS NULL) AND status = 'active'", (parent_id, user_id))
    else:
        cursor.execute("SELECT plan_id, name, prize FROM Reading_Plans WHERE parent_id = ? AND child_id = ? AND status = 'active'", (parent_id, user_id))
        
    plans = cursor.fetchall()
    
    kb = []
    has_books = False
    text = "🦸‍♂️ <b>Qahramon! Ota-onang senga ajoyib reja tuzgan.</b>\n\n"
    
    for p in plans:
        cursor.execute("SELECT book_id, title, pages_read, is_completed FROM Plan_Books WHERE plan_id = ?", (p[0],))
        books = cursor.fetchall()
        if books:
            prize_info = f" (Sovrin: {p[2]})" if p[2] else ""
            text += f"🎯 <b>{p[1]}</b>{prize_info}\n"
            for b in books:
                if b[3] == 0: 
                    kb.append([InlineKeyboardButton(text=f"📘 {b[1]} ({b[2]} bet)", callback_data=f"cread_{b[0]}")])
                    has_books = True
            text += "\n"
            
    if not has_books:
        text = "Senda hozircha o‘qilishi kerak bo‘lgan kitoblar yo‘q. 😊"
        markup = None
    else:
        text += "👇 Qaysi kitobni o‘qishni davom ettiramiz?"
        markup = InlineKeyboardMarkup(inline_keyboard=kb)
    
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)

@router.message(F.text.in_(["📖 Kitob o‘qish", "📖 Kitob o'qish"]))
async def child_read_book_msg(message: types.Message, state: FSMContext):
    child_id = await get_effective_child_id(message, state)
    await show_child_books(message, child_id, state)

@router.callback_query(F.data == "child_books_main")
async def child_read_book_call(callback: types.CallbackQuery, state: FSMContext):
    child_id = await get_effective_child_id(callback, state)
    await show_child_books(callback, child_id, state)
    await callback.answer()

@router.callback_query(F.data.startswith("cread_"))
async def child_book_action(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT test_id FROM Book_Tests WHERE book_id = ?", (book_id,))
    has_test = cursor.fetchone()
    
    cursor.execute("SELECT mid_test_1_done, mid_test_2_done, final_test_done FROM Plan_Books WHERE book_id = ?", (book_id,))
    test_status = cursor.fetchone()
    
    test_label = "📝 Test topshirish (Bilig 🔅)"
    if not has_test:
        test_btn = InlineKeyboardButton(text="🔒 Test (Hozircha mavjud emas)", callback_data="no_test_alert")
    elif test_status and test_status[2] == 1:
        test_btn = InlineKeyboardButton(text="✅ Barcha testlar topshirilgan", callback_data="all_tests_done_alert")
    elif test_status and test_status[0] == 0:
        test_btn = InlineKeyboardButton(text="🥇 1-Oraliq testni ishlash (+5 🔅)", callback_data=f"starttest_{book_id}_mid1")
    elif test_status and test_status[1] == 0:
        test_btn = InlineKeyboardButton(text="🥈 2-Oraliq testni ishlash (+5 🔅)", callback_data=f"starttest_{book_id}_mid2")
    else:
        test_btn = InlineKeyboardButton(text="🏆 Yakuniy imtihonni topshirish (+10 🔅)", callback_data=f"starttest_{book_id}_final")
        
    kb = [
        [InlineKeyboardButton(text="📸 Sahifani rasmga olib yuborish", callback_data=f"sendpage_{book_id}")],
        [InlineKeyboardButton(text="🎤 Audio xulosa yuborish", callback_data=f"sendaudio_{book_id}")],
        [test_btn],
        [InlineKeyboardButton(text="✅ Kitobni tugatdim", callback_data=f"finishbook_{book_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="child_books_main")]
    ]
    await callback.message.edit_text("Ajoyib tanlov! O‘qishni boshla. To‘xtagan joyingda menga sahifani rasmga olib yubor.", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data == "no_test_alert")
async def no_test_alert(callback: types.CallbackQuery):
    await callback.answer("🔒 Ota-onangiz bu kitob uchun hali test tuzmagan. O‘qishda davom eting!", show_alert=True)

@router.callback_query(F.data == "all_tests_done_alert")
async def all_tests_done_alert(callback: types.CallbackQuery):
    await callback.answer("✅ Siz bu kitob bo‘yicha barcha testlarni a'lo darajada topshirib bo‘ldingiz!", show_alert=True)

# ==========================================
# SAHIFA RASMINI TEKSHIRISH (AI Vision)
# ==========================================
@router.callback_query(F.data.startswith("sendpage_"))
async def ask_page_photo(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    child_id = await get_effective_child_id(callback, state)
    await state.update_data(reading_book_id=book_id, reading_child_id=child_id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.bot.send_message(callback.from_user.id, "📸 <b>O‘qigan sahifangni rasmga olib yubor!</b>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ChildReading.waiting_for_page_photo)
    await callback.answer()

@router.message(ChildReading.waiting_for_page_photo, F.photo)
async def process_reading_photo(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>AI sahifani tekshirmoqda...</i>", parse_mode="HTML")
    try:
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)
        
        ai_result = await verify_page_photo(downloaded_file.read())
        try:
            await message.delete()
        except Exception:
            pass 
        
        data = await state.get_data()
        child_id = data.get('reading_child_id', message.from_user.id)
        appropriate_kb = await get_appropriate_keyboard(child_id, state)
        
        if not ai_result.get("is_book_page"):
            await processing_msg.delete()
            await message.answer("🚫 Bu kitob sahifasiga o‘xshamayapti. Qaytadan urinib ko‘r!", reply_markup=appropriate_kb)
            await state.clear()
            return
            
        new_page_num = int(ai_result.get("page_number", 0))
        if new_page_num == 0:
            await processing_msg.delete()
            await message.answer("⚠️ Sahifa raqami ko‘rinmadi! Raqam aniq ko‘rinsin.", reply_markup=appropriate_kb)
            await state.clear()
            return
            
        book_id = data.get('reading_book_id')
        cursor.execute("SELECT pages_read, title FROM Plan_Books WHERE book_id = ?", (book_id,))
        row = cursor.fetchone()
        old_pages, book_title = (row[0], row[1]) if row else (0, "Kitob")
        
        if new_page_num <= old_pages:
            await processing_msg.delete()
            await message.answer(f"⚠️ Sen allaqachon {old_pages}-sahifagacha o‘qigansan! Yangi sahifani yubor.", reply_markup=appropriate_kb)
            await state.clear()
            return
        
        cursor.execute("UPDATE Plan_Books SET pages_read = ? WHERE book_id = ?", (new_page_num, book_id))
        earned_bilig = (new_page_num // 5) - (old_pages // 5)
        pages_read_now = new_page_num - old_pages
        
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO Reading_Logs (child_id, book_id, pages_added, created_at) VALUES (?, ?, ?, ?)", (child_id, book_id, pages_read_now, now_ts))
        
        streak, shield_used = update_streak(child_id)
        rank, _ = calculate_and_update_rank(child_id)
        
        # 7 kunlik uzluksiz o'qish nishoni
        if streak >= 7:
            cursor.execute("SELECT badges FROM Users WHERE user_id = ?", (child_id,))
            badges = cursor.fetchone()[0]
            if "Charchamas" not in str(badges):
                new_badges = (str(badges) + " 🔥 Charchamas Kitobxon").strip()
                cursor.execute("UPDATE Users SET badges = ? WHERE user_id = ?", (new_badges, child_id))
        
        if earned_bilig > 0:
            cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (earned_bilig, child_id))
            reply_text = f"🎉 <b>Qoyilmaqom!</b> Sen {pages_read_now} bet o‘qiding va <b>{earned_bilig} 🔅 Bilig</b> ishlading!\n🔥 Streak: {streak} kun! (Darajang: <b>{rank}</b>)\n<i>(Jami: {new_page_num} bet)</i>"
        else:
            reply_text = f"👍 <b>Barakalla!</b> Sen {pages_read_now} bet o‘qiding. Yana {5 - (new_page_num % 5)} bet o‘qisang, Bilig olasan!\n🔥 Streak: {streak} kun! (Darajang: <b>{rank}</b>)"
            
        if shield_used:
            reply_text += "\n\n🛡 <b>Eslatma:</b> Kecha o‘qimagan edingiz, lekin 'Olov qalqoni' sizning streakingizni saqlab qoldi!"
            
        conn.commit()
        await processing_msg.delete()
        await message.answer(reply_text, parse_mode="HTML", reply_markup=appropriate_kb)
        await state.clear()
        
        parent_id = get_parent_id(child_id)
        if parent_id:
            await message.bot.send_message(parent_id, f"📖 Farzandingiz <b>'{book_title}'</b> kitobidan {pages_read_now} bet o‘qidi. (Jami: {new_page_num} bet).", parse_mode="HTML")
    except Exception:
        await processing_msg.delete()
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko‘r.", reply_markup=get_child_keyboard())
        await state.clear()

# ==========================================
# AUDIO XULOSA VA PEDAGOGIK DIAGNOSTIKA
# ==========================================
@router.callback_query(F.data.startswith("sendaudio_"))
async def ask_audio_summary(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    child_id = await get_effective_child_id(callback, state)
    
    cursor.execute("SELECT pages_read, audio_count FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row:
        return
        
    pages_read, audio_count = row[0], (row[1] if row[1] else 0)
    required_pages = 10 if audio_count == 0 else 10 + (audio_count * 30)
    
    if pages_read < required_pages:
        await callback.answer(f"🔒 Audio yuborish uchun kamida {required_pages}-sahifagacha o‘qishingiz kerak!\n(Hozir: {pages_read} bet)", show_alert=True)
        return
        
    await state.update_data(audio_book_id=book_id, audio_child_id=child_id, is_retry=False)
    try:
        await callback.message.delete()
    except Exception:
        pass
    
    audio_info_text = (
        "🎤 <b>Ovozli xulosa yuborish</b>\n\n"
        "Kitobda nima bo‘lganini, qaysi qahramon yoqqanini va o‘zingga qanday xulosa chiqarganingni aytib ber.\n\n"
        "💡 <i>Nutqing ravon, fikrlaring teran bo‘lsa, AI ustoz 1 dan 5 gacha Bilig beradi!</i>"
    )
    await callback.bot.send_message(callback.from_user.id, audio_info_text, parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ChildReading.waiting_for_audio)
    await callback.answer()

@router.message(ChildReading.waiting_for_audio, F.voice)
async def process_audio_summary(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>AI ustoz seni eshitmoqda va nutqingni tahlil qilmoqda...</i>", parse_mode="HTML")
    try:
        file_info = await message.bot.get_file(message.voice.file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)
        
        data = await state.get_data()
        book_id = data.get('audio_book_id')
        child_id = data.get('audio_child_id', message.from_user.id)
        is_retry = data.get('is_retry', False)
        
        cursor.execute("SELECT child_age FROM Family_Link WHERE child_id = ?", (child_id,))
        age_row = cursor.fetchone()
        age = age_row[0] if age_row else 10
        
        cursor.execute("SELECT title FROM Plan_Books WHERE book_id = ?", (book_id,))
        book_row = cursor.fetchone()
        book_title = book_row[0] if book_row else "Kitob"
        
        ai_result = await evaluate_voice_summary(downloaded_file.read(), age, book_title)
        bonus = int(ai_result.get("bonus_bilig", 1))
        give_badge = ai_result.get("give_badge", False)
        child_feedback = ai_result.get("child_feedback", "Ajoyib xulosa!")
        parent_rep = ai_result.get("parent_report", {})
        scores = ai_result.get("diagnostic_scores", {})
        
        if not is_retry:
            cursor.execute("UPDATE Plan_Books SET audio_count = audio_count + 1 WHERE book_id = ?", (book_id,))
        cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (bonus, child_id))
        update_streak(child_id)
        
        # Diagnostika jurnaliga saqlash
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Diagnostic_Logs (child_id, book_id, type, fluency_score, vocabulary_score, parent_note, convo_topic, created_at)
            VALUES (?, ?, 'audio', ?, ?, ?, ?, ?)
        """, (child_id, book_id, scores.get("fluency_score", 80), scores.get("vocabulary_score", 80), parent_rep.get("strengths", ""), parent_rep.get("conversation_topic", ""), now_ts))
        
        badge_text = ""
        if give_badge:
            cursor.execute("SELECT badges FROM Users WHERE user_id = ?", (child_id,))
            current_badges = cursor.fetchone()[0]
            if "Notiq" not in str(current_badges):
                cursor.execute("UPDATE Users SET badges = ? WHERE user_id = ?", (str(current_badges) + " 🗣 Notiq" if current_badges else "🗣 Notiq", child_id))
                badge_text = "\n\n🏅 <b>TABRIKLAYMIZ! '🗣 Notiq' nishonini olding!</b>"
                
        conn.commit()
        appropriate_kb = await get_appropriate_keyboard(child_id, state)
            
        await processing_msg.delete()
        await message.answer(f"👨‍🏫 <b>AI ustoz:</b>\n\n{child_feedback}\n\n🎁 <b>Mukofot:</b> {bonus} 🔅 Bilig!{badge_text}", parse_mode="HTML", reply_markup=appropriate_kb)
        await state.clear()
        
        # Ota-onaga tezkor kartochka va 10 daqiqalik suhbat mavzusi
        parent_id = get_parent_id(child_id)
        if parent_id:
            cursor.execute("SELECT name FROM Users WHERE user_id = ?", (child_id,))
            c_name = cursor.fetchone()[0]
            parent_text = (
                f"🎙 <b>FARZANDINGIZNING NUTQIY TAHLILI:</b>\n"
                f"👦 <b>{c_name}</b> ({age} yosh) | 📘 <b>'{book_title}'</b>\n"
                f"🎁 <b>Baholash:</b> {bonus}/5 🔅 Bilig\n\n"
                f"📝 <b>Xulosa mazmuni:</b> <i>{parent_rep.get('summary', '')}</i>\n\n"
                f"🧠 <b>AI USTOZNING PEDAGOGIK XULOSASI:</b>\n"
                f"✅ <b>Kuchli jihati:</b> {parent_rep.get('strengths', '')}\n\n"
                f"🌱 <b>Rivojlantirish nuqtasi:</b> {parent_rep.get('weaknesses', '')}\n\n"
                f"☕️ <b>BUGUNGI 10 DAQIQALIK SUHBAT UCHUN MAVZU:</b>\n"
                f"<i>{parent_rep.get('conversation_topic', 'Farzandingiz bilan asar qahramonining xatti-harakatlari haqida fikrlashing.')}</i>"
            )
            await message.bot.send_message(parent_id, parent_text, parse_mode="HTML")
    except Exception:
        await processing_msg.delete()
        await message.answer("❌ Xatolik yuz berdi.", reply_markup=get_child_keyboard())
        await state.clear()

# ==========================================
# KENGAYTIRILGAN AI TEST TOPSHIRISH (AyT)
# ==========================================
@router.callback_query(F.data.startswith("starttest_"))
async def start_extended_test(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    book_id = int(parts[1])
    test_type = parts[2] # mid1, mid2, final
    
    cursor.execute("SELECT questions_json FROM Book_Tests WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row:
        await callback.answer("🔒 Bu kitob uchun test topilmadi!", show_alert=True)
        return
        
    all_questions = json.loads(row[0])
    if len(all_questions) == 0:
        await callback.answer("🔒 Savollar mavjud emas!", show_alert=True)
        return
        
    # Savollar sonini belgilash
    q_count = 5 if test_type in ["mid1", "mid2"] else min(10, len(all_questions))
    selected_questions = random.sample(all_questions, min(q_count, len(all_questions)))
    
    child_id = await get_effective_child_id(callback, state)
    await state.update_data(
        test_book_id=book_id,
        test_type=test_type,
        test_questions=selected_questions,
        test_q_idx=0,
        test_correct_count=0,
        test_child_id=child_id
    )
    
    test_title = "🥇 1-Oraliq test" if test_type == "mid1" else ("🥈 2-Oraliq test" if test_type == "mid2" else "🏆 Yakuniy imtihon")
    await callback.message.edit_text(f"🚀 <b>{test_title} boshlanmoqda!</b>\nJami: <b>{len(selected_questions)} ta savol</b>.\nHar bir to‘g‘ri javob uchun <b>+1 🔅 Bilig</b> beriladi. Omad!", parse_mode="HTML")
    await render_active_test_question(callback, state)
    await callback.answer()

async def render_active_test_question(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    questions = data.get('test_questions', [])
    q_idx = data.get('test_q_idx', 0)
    correct_count = data.get('test_correct_count', 0)
    book_id = data.get('test_book_id')
    test_type = data.get('test_type')
    child_id = data.get('test_child_id')
    total_q = len(questions)

    # Test tugaganda
    if q_idx >= total_q:
        # Baza ustunlarini yangilash
        if test_type == "mid1":
            cursor.execute("UPDATE Plan_Books SET mid_test_1_done = 1 WHERE book_id = ?", (book_id,))
        elif test_type == "mid2":
            cursor.execute("UPDATE Plan_Books SET mid_test_2_done = 1 WHERE book_id = ?", (book_id,))
        else:
            cursor.execute("UPDATE Plan_Books SET final_test_done = 1 WHERE book_id = ?", (book_id,))

        cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (correct_count, child_id))
        
        # 100% to'g'ri topshirsa "Zukko" nishoni
        badge_reward = ""
        if correct_count == total_q and total_q >= 5:
            cursor.execute("SELECT badges FROM Users WHERE user_id = ?", (child_id,))
            b_row = cursor.fetchone()
            current_badges = b_row[0] if b_row else ""
            if "Zukko" not in str(current_badges):
                new_b = (str(current_badges) + " 🧠 Zukko").strip()
                cursor.execute("UPDATE Users SET badges = ? WHERE user_id = ?", (new_b, child_id))
                badge_reward = "\n🏅 <b>TABRIKLAYMIZ! '🧠 Zukko' nishonini qo‘lga kiritding!</b>"

        # Diagnostika jurnaliga saqlash
        pct = int((correct_count / total_q) * 100)
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO Diagnostic_Logs (child_id, book_id, type, factual_score, logic_score, conclusion_score, created_at)
            VALUES (?, ?, 'test', ?, ?, ?, ?)
        """, (child_id, book_id, pct, pct, pct, now_ts))
        conn.commit()

        finish_text = (
            f"🏁 <b>Test muvaffaqiyatli yakunlandi!</b>\n\n"
            f"✅ To‘g‘ri javoblar: <b>{correct_count} / {total_q}</b> ta ({pct}%)\n"
            f"🎁 Mukofot: <b>+{correct_count} 🔅 Bilig</b> hisobingga qo‘shildi!{badge_reward}"
        )
        finish_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Kitoblar ro‘yxatiga qaytish", callback_data="child_books_main")]
        ])
        await callback.message.edit_text(finish_text, parse_mode="HTML", reply_markup=finish_kb)

        # Ota-onaga tezkor diagnostika kartochkasi
        parent_id = get_parent_id(child_id)
        if parent_id:
            cursor.execute("SELECT name FROM Users WHERE user_id = ?", (child_id,))
            c_name = cursor.fetchone()[0]
            cursor.execute("SELECT title FROM Plan_Books WHERE book_id = ?", (book_id,))
            b_title = cursor.fetchone()[0]
            
            test_label = "1-Oraliq test" if test_type == "mid1" else ("2-Oraliq test" if test_type == "mid2" else "Yakuniy imtihon")
            parent_msg = (
                f"📊 <b>FARZANDINGIZNING TEST TAHLILI:</b>\n"
                f"👦 <b>{c_name}</b> | 📘 <b>'{b_title}'</b>\n"
                f"📝 <b>Sinov:</b> {test_label}\n"
                f"🎯 <b>Natija:</b> {correct_count} / {total_q} ta to‘g‘ri ({pct}%)\n"
                f"🎁 <b>Yutuq:</b> +{correct_count} 🔅 Bilig\n\n"
                f"🧠 <b>AI USTOZNING PEDAGOGIK XULOSASI:</b>\n"
                f"✅ <b>Kuchli jihati:</b> Asardagi asosiy voqealar va qahramonlar tafsilotini yaxshi o‘zlashtirgan.\n"
                f"🌱 <b>Rivojlantirish nuqtasi:</b> Sabab-oqibat bog‘lanishlarini chuqurroq anglashga e'tibor qaratish tavsiya etiladi.\n\n"
                f"☕️ <b>BUGUNGI 10 DAQIQALIK SUHBAT UCHUN MAVZU:</b>\n"
                f"<i>Kechki ovqat paytida farzandingizdan so‘rang: 'Asar qahramoni bu vaziyatda boshqacha yo‘l tutsa bo‘larmidi?'</i>"
            )
            await callback.bot.send_message(parent_id, parent_msg, parse_mode="HTML")
        await state.clear()
        return

    q = questions[q_idx]
    letters = ["A", "B", "C", "D", "E"]
    options = q.get('options', [])

    text = f"📝 <b>{q_idx + 1}-savol (Jami: {total_q} ta):</b>\n\n"
    text += f"❓ <b>{html.escape(q.get('question', ''))}</b>\n\n"

    buttons_row = []
    for idx, opt in enumerate(options):
        letter = letters[idx] if idx < len(letters) else str(idx+1)
        opt_clean = opt.strip()
        if opt_clean.startswith(f"{letter})") or opt_clean.startswith(f"{letter}."):
            text += f"<b>{letter})</b> {html.escape(opt_clean[2:].strip())}\n"
        else:
            text += f"<b>{letter})</b> {html.escape(opt_clean)}\n"
            
        buttons_row.append(InlineKeyboardButton(text=f"[ {letter} ]", callback_data=f"extans_{idx}"))
        
    kb = []
    if len(buttons_row) <= 4:
        kb.append(buttons_row[:2])
        if len(buttons_row) > 2:
            kb.append(buttons_row[2:])
    else:
        kb.append(buttons_row[:3])
        kb.append(buttons_row[3:])
        
    kb.append([InlineKeyboardButton(text="🔙 To‘xtatish", callback_data=f"cread_{book_id}")])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("extans_"))
async def process_extended_answer(callback: types.CallbackQuery, state: FSMContext):
    selected_idx = int(callback.data.split("_")[1])
    data = await state.get_data()
    questions = data.get('test_questions', [])
    q_idx = data.get('test_q_idx', 0)
    correct_count = data.get('test_correct_count', 0)

    if q_idx >= len(questions):
        await callback.answer()
        return

    q = questions[q_idx]
    letters = ["A", "B", "C", "D", "E"]
    options = q.get('options', [])
    
    selected_letter = letters[selected_idx] if selected_idx < len(letters) else ""
    selected_text = options[selected_idx].strip() if selected_idx < len(options) else ""
    answer = str(q.get('answer', '')).strip()

    is_correct = False
    if answer.upper() == selected_letter or answer.upper().startswith(f"{selected_letter})") or answer.upper().startswith(f"{selected_letter}."):
        is_correct = True
    elif selected_text.lower() == answer.lower():
        is_correct = True
    elif answer.lower() in selected_text.lower() and len(answer) > 1:
        is_correct = True

    new_correct = correct_count + (1 if is_correct else 0)
    await state.update_data(test_q_idx=q_idx + 1, test_correct_count=new_correct)

    if is_correct:
        await callback.answer("✅ To‘g‘ri javob!", show_alert=False)
    else:
        await callback.answer("❌ Noto‘g‘ri javob! (Xatolar ustida ishlaymiz)", show_alert=False)

    await render_active_test_question(callback, state)

# ==========================================
# KITOBNI TUGATISH
# ==========================================
@router.callback_query(F.data.startswith("finishbook_"))
async def finish_book_handler(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT final_test_done FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    
    cursor.execute("SELECT test_id FROM Book_Tests WHERE book_id = ?", (book_id,))
    has_test = cursor.fetchone()
    
    if has_test and row and row[0] == 0:
        kb = [
            [InlineKeyboardButton(text="🏆 Yakuniy imtihonni topshirish (+10 🔅)", callback_data=f"starttest_{book_id}_final")],
            [InlineKeyboardButton(text="✅ Testni o‘tkazib, kitobni yakunlash", callback_data=f"forcefinish_{book_id}")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"cread_{book_id}")]
        ]
        await callback.message.edit_text(
            "💡 <b>Kitobni tugatishdan oldin ajoyib imkoniyat!</b>\n\n"
            "Bu kitob bo‘yicha <b>Yakuniy imtihon</b> mavjud. Testni ishlab qo‘shimcha <b>10 tagacha Bilig tangalari</b> yutib olishni xohlaysanmi?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
        await callback.answer()
        return

    await complete_book_process(callback, book_id, state)

@router.callback_query(F.data.startswith("forcefinish_"))
async def force_finish_book_handler(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    await complete_book_process(callback, book_id, state)

async def complete_book_process(callback: types.CallbackQuery, book_id: int, state: FSMContext):
    child_id = await get_effective_child_id(callback, state)
    cursor.execute("UPDATE Plan_Books SET is_completed = 1 WHERE book_id = ?", (book_id,))
    cursor.execute("SELECT plan_id, title FROM Plan_Books WHERE book_id = ?", (book_id,))
    plan_data = cursor.fetchone()
    if not plan_data:
        await callback.answer("Kitob topilmadi.", show_alert=True)
        return
        
    plan_id, book_title = plan_data
    cursor.execute("SELECT COUNT(*) FROM Plan_Books WHERE plan_id = ? AND is_completed = 0", (plan_id,))
    remaining = cursor.fetchone()[0]
    parent_id = get_parent_id(child_id)
    
    if remaining == 0:
        cursor.execute("UPDATE Reading_Plans SET status = 'completed' WHERE plan_id = ?", (plan_id,))
        cursor.execute("SELECT name, prize FROM Reading_Plans WHERE plan_id = ?", (plan_id,))
        plan_name, prize = cursor.fetchone()
        
        prize_text = f"\nEndi ota-onangdan <b>'{prize}'</b> mukofotini so‘rashing mumkin!" if prize else ""
        parent_prize_text = f"\nUnga va'da qilingan <b>'{prize}'</b> mukofotini berish vaqti keldi! 🎁" if prize else ""

        await callback.message.edit_text(
            f"🎉 <b>URAA! MARAFON TUGADI!</b>\n\n"
            f"Sen '<b>{plan_name}</b>' rejasidagi barcha kitoblarni to‘liq o‘qib bo‘lding!{prize_text} Haqiqiy qahramonsan! 🦸‍♂️",
            parse_mode="HTML"
        )
        if parent_id:
            await callback.bot.send_message(
                parent_id,
                f"🎉 <b>TABRIKLAYMIZ!</b>\n\nFarzandingiz '<b>{plan_name}</b>' rejasini to‘liq yakunladi!{parent_prize_text}",
                parse_mode="HTML"
            )
    else:
        await callback.message.edit_text(
            f"✅ <b>'{book_title}'</b> kitobini tugatding! Barakalla!\nRejada yana {remaining} ta kitob qoldi. O‘qishda davom et!",
            parse_mode="HTML"
        )
        if parent_id:
            await callback.bot.send_message(
                parent_id,
                f"📚 Farzandingiz <b>'{book_title}'</b> kitobini to‘liq o‘qib tugatdi! ✅",
                parse_mode="HTML"
            )
            
    conn.commit()
    await callback.answer()

# ==========================================
# SOVRINLARIM (YUTUQLAR XAZINASI)
# ==========================================
@router.message(F.text == "🎁 Sovrinlarim")
async def show_rewards(message: types.Message, state: FSMContext):
    child_id = await get_effective_child_id(message, state)
    rank, _ = calculate_and_update_rank(child_id)
    
    cursor.execute("SELECT balance_coins, badges, streak_days, streak_freezes FROM Users WHERE user_id = ?", (child_id,))
    user = cursor.fetchone()
    balance = user[0] if user else 0
    badges_display = user[1] if (user and user[1]) else "Hali nishonlar yo‘q"
    streak = user[2] if user else 0
    freezes = user[3] if user else 0
    
    text = (
        f"🦸‍♂️ <b>Qahramon: {message.from_user.full_name}</b>\n"
        f"🎖 Darajang: <b>{rank}</b>\n\n"
        f"🔅 <b>Biliglar xazinasi:</b> {balance} ta\n"
        f"🔥 <b>Uzluksiz mutolaa (Streak):</b> {streak} kun\n"
        f"🛡 <b>Olov qalqonlari:</b> {freezes} ta\n"
        f"🏅 <b>Nishonlar:</b> {badges_display}\n\n"
        f"<i>To‘plagan Biliglaringga 🛒 Do‘kondan o‘zingga ajoyib sovg‘alar olishing mumkin!</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Do‘konga o‘tish", callback_data="child_store")]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

# ==========================================
# DO'KON (BOLA MENYUSI)
# ==========================================
async def show_child_store_view(message_or_call, user_id, state: FSMContext = None):
    parent_id = get_parent_id(user_id)
    if not parent_id and state:
        data = await state.get_data()
        parent_id = data.get('bolaxona_parent_id')

    if not parent_id:
        text = "Ota-onangiz profilingizga ulanmagan."
        if isinstance(message_or_call, types.Message):
            await message_or_call.answer(text)
        else:
            await message_or_call.message.edit_text(text)
        return
        
    cursor.execute("SELECT item_id, name, price FROM Store_Items WHERE parent_id = ?", (parent_id,))
    items = cursor.fetchall()
    
    cursor.execute("SELECT balance_coins FROM Users WHERE user_id = ?", (user_id,))
    balance_row = cursor.fetchone()
    balance = balance_row[0] if balance_row else 0
    
    if not items:
        text = (
            f"🛒 <b>Sovg‘alar do‘koni</b>\n\n"
            f"Sening hisobing: <b>{balance} 🔅 Bilig</b>\n\n"
            f"<i>Do‘konda hozircha sovg‘alar yo‘q. Ota-onang yangi sovg‘alar qo‘shishini kutib turamiz! 😊</i>"
        )
        if isinstance(message_or_call, types.Message):
            await message_or_call.answer(text, parse_mode="HTML")
        else:
            await message_or_call.message.edit_text(text, parse_mode="HTML")
        return
        
    kb = [[InlineKeyboardButton(text=f"🎁 {item[1]} — {item[2]} 🔅", callback_data=f"buyitem_{item[0]}")] for item in items]
    text = (
        f"🛒 <b>Sovg‘alar do‘koni</b>\n\n"
        f"Sening hisobing: <b>{balance} 🔅 Bilig</b>\n\n"
        f"👇 <b>Qaysi sovg‘ani xarid qilmoqchisan?</b>"
    )
    if isinstance(message_or_call, types.Message):
        await message_or_call.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await message_or_call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.message(F.text.in_(["🛒 Do‘kon", "🛒 Do'kon"]))
async def child_store_msg(message: types.Message, state: FSMContext):
    child_id = await get_effective_child_id(message, state)
    await show_child_store_view(message, child_id, state)

@router.callback_query(F.data == "child_store")
async def child_store_call(callback: types.CallbackQuery, state: FSMContext):
    child_id = await get_effective_child_id(callback, state)
    await show_child_store_view(callback, child_id, state)
    await callback.answer()

@router.callback_query(F.data.startswith("buyitem_"))
async def buy_item_handler(callback: types.CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split("_")[1])
    child_id = await get_effective_child_id(callback, state)
    
    cursor.execute("SELECT name, price, parent_id FROM Store_Items WHERE item_id = ?", (item_id,))
    item = cursor.fetchone()
    if not item:
        await callback.answer("Sovg‘a topilmadi!", show_alert=True)
        return
        
    cursor.execute("SELECT balance_coins FROM Users WHERE user_id = ?", (child_id,))
    balance = cursor.fetchone()[0]
    
    if balance < item[1]:
        await callback.answer(f"Yetarli Bilig yo‘q! Yana {item[1] - balance} 🔅 kerak.", show_alert=True)
        return
        
    cursor.execute("UPDATE Users SET balance_coins = balance_coins - ? WHERE user_id = ?", (item[1], child_id))
    conn.commit()
    
    await callback.message.edit_text(
        f"🎉 <b>Tabriklaymiz!</b>\n\nSen <b>'{item[0]}'</b> sovg‘asini sotib olding! Ota-onangga bu haqda xabar yuborildi. 🎁",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Do‘konga qaytish", callback_data="child_store")]])
    )
    await callback.bot.send_message(
        item[2],
        f"🛍 <b>DIQQAT! FARZANDINGIZ SOVG‘A SOTIB OLDI!</b>\n\nFarzandingiz do‘kondan <b>'{item[0]}'</b> ({item[1]} 🔅) sovg‘asini xarid qildi. Unga sovg‘ani topshirishni unutmang! 🎁",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(F.text == "🏆 Reyting")
async def show_leaderboard(message: types.Message):
    cursor.execute("SELECT name, balance_coins, rank_title FROM Users WHERE role = 'child' ORDER BY balance_coins DESC LIMIT 10")
    top_users = cursor.fetchall()
    if not top_users:
        await message.answer("Hali reyting shakllanmadi.")
        return
        
    text = "🏆 <b>Eng ko‘p Bilig yig‘gan kitobxonlar:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top_users):
        medal = medals[i] if i < 3 else f"{i+1}."
        rank_str = f"({u[2]})" if u[2] else ""
        text += f"{medal} <b>{u[0]}</b> {rank_str} — {u[1]} 🔅 Bilig\n"
    await message.answer(text, parse_mode="HTML")
