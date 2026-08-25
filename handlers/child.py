import json
import html
from datetime import datetime
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import conn, cursor, get_parent_id, update_streak
from keyboards import get_child_keyboard, get_back_reply_keyboard
from states import ChildReading
from ai_service import verify_page_photo, evaluate_voice_summary

router = Router()

# ==========================================
# BOLANING KITOB RO'YXATI (Faqat o'ziniki)
# ==========================================
async def show_child_books(message_or_callback, user_id):
    cursor.execute("SELECT parent_id FROM Family_Link WHERE child_id = ?", (user_id,))
    link = cursor.fetchone()
    if not link:
        text_no_parent = "Siz hali ota-onangizga ulanmagansiz! Iltimos, ota-onangiz bergan kod orqali ulaning."
        if isinstance(message_or_callback, types.Message): await message_or_callback.answer(text_no_parent)
        else: await message_or_callback.message.edit_text(text_no_parent)
        return
        
    parent_id = link[0]
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
async def child_read_book_msg(message: types.Message):
    await show_child_books(message, message.from_user.id)

@router.callback_query(F.data == "child_books_main")
async def child_read_book_call(callback: types.CallbackQuery):
    await show_child_books(callback, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data.startswith("cread_"))
async def child_book_action(callback: types.CallbackQuery):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT test_id FROM Book_Tests WHERE book_id = ?", (book_id,))
    has_test = cursor.fetchone()
    
    test_btn = InlineKeyboardButton(text="📝 Testni ishlash (Bilig 🔅)", callback_data=f"taketest_{book_id}_0_0") if has_test else InlineKeyboardButton(text="🔒 Test (Hozircha mavjud emas)", callback_data="no_test_alert")
        
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

# ==========================================
# KITOBNI TUGATISH VA TEST TEKSHIRUVI
# ==========================================
@router.callback_query(F.data.startswith("finishbook_"))
async def finish_book_check_test(callback: types.CallbackQuery):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT test_id FROM Book_Tests WHERE book_id = ?", (book_id,))
    has_test = cursor.fetchone()
    
    if has_test:
        kb = [
            [InlineKeyboardButton(text="📝 Ha, testni ishlayman (+Bilig 🔅)", callback_data=f"taketest_{book_id}_0_0")],
            [InlineKeyboardButton(text="✅ Testni o‘tkazib, kitobni yakunlash", callback_data=f"forcefinish_{book_id}")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"cread_{book_id}")]
        ]
        await callback.message.edit_text(
            "💡 <b>Kitobni tugatishdan oldin ajoyib imkoniyat!</b>\n\n"
            "Bu kitob bo‘yicha AI testi mavjud. Testni ishlab qo‘shimcha <b>Bilig tangalari</b> yutib olishni xohlaysanmi?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
        )
        await callback.answer()
        return

    await complete_book_process(callback, book_id)

@router.callback_query(F.data.startswith("forcefinish_"))
async def force_finish_book_handler(callback: types.CallbackQuery):
    book_id = int(callback.data.split("_")[1])
    await complete_book_process(callback, book_id)

async def complete_book_process(callback: types.CallbackQuery, book_id: int):
    cursor.execute("UPDATE Plan_Books SET is_completed = 1 WHERE book_id = ?", (book_id,))
    cursor.execute("SELECT plan_id, title FROM Plan_Books WHERE book_id = ?", (book_id,))
    plan_data = cursor.fetchone()
    if not plan_data:
        await callback.answer("Kitob topilmadi.", show_alert=True)
        return
        
    plan_id, book_title = plan_data
    cursor.execute("SELECT COUNT(*) FROM Plan_Books WHERE plan_id = ? AND is_completed = 0", (plan_id,))
    remaining = cursor.fetchone()[0]
    parent_id = get_parent_id(callback.from_user.id)
    
    if remaining == 0:
        cursor.execute("UPDATE Reading_Plans SET status = 'completed' WHERE plan_id = ?", (plan_id,))
        cursor.execute("SELECT name, prize FROM Reading_Plans WHERE plan_id = ?", (plan_id,))
        plan_name, prize = cursor.fetchone()
        
        prize_text = f"\nEndi ota-onangdan <b>'{prize}'</b> mukofotini so‘rashing mumkin!" if prize else ""
        parent_prize_text = f"\nUnga va'da qilingan <b>'{prize}'</b> mukofotini berish vaqti keldi! 🎁" if prize else ""

        await callback.message.edit_text(
            f"🎉 <b>URAA! MARAFON TUGADI!</b>\n\n"
            f"Sen '<b>{plan_name}</b>' rejasidagi barcha kitoblarni o‘qib bo‘lding!{prize_text} Qahramon! 🦸‍♂️",
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
# SAHIFA RASMINI TEKSHIRISH (AI VISION)
# ==========================================
@router.callback_query(F.data.startswith("sendpage_"))
async def ask_page_photo(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    await state.update_data(reading_book_id=book_id)
    try: await callback.message.delete()
    except Exception: pass
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
        try: await message.delete()
        except Exception: pass 
        
        if not ai_result.get("is_book_page"):
            await processing_msg.delete()
            await message.answer("🚫 Bu kitob sahifasiga o‘xshamayapti. Qaytadan urinib ko‘r!", reply_markup=get_child_keyboard())
            await state.clear()
            return
            
        new_page_num = int(ai_result.get("page_number", 0))
        if new_page_num == 0:
            await processing_msg.delete()
            await message.answer("⚠️ Sahifa raqami ko‘rinmadi! Raqam aniq ko‘rinsin.", reply_markup=get_child_keyboard())
            await state.clear()
            return
            
        data = await state.get_data()
        book_id = data.get('reading_book_id')
        child_id = message.from_user.id
        
        cursor.execute("SELECT pages_read, title FROM Plan_Books WHERE book_id = ?", (book_id,))
        row = cursor.fetchone()
        old_pages, book_title = (row[0], row[1]) if row else (0, "Kitob")
        
        if new_page_num <= old_pages:
            await processing_msg.delete()
            await message.answer(f"⚠️ Sen allaqachon {old_pages}-sahifagacha o‘qigansan! Yangi sahifani yubor.", reply_markup=get_child_keyboard())
            await state.clear()
            return
        
        cursor.execute("UPDATE Plan_Books SET pages_read = ? WHERE book_id = ?", (new_page_num, book_id))
        earned_bilig = (new_page_num // 5) - (old_pages // 5)
        pages_read_now = new_page_num - old_pages
        
        now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO Reading_Logs (child_id, book_id, pages_added, created_at) VALUES (?, ?, ?, ?)", (child_id, book_id, pages_read_now, now_ts))
        streak = update_streak(child_id) 
        
        if earned_bilig > 0:
            cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (earned_bilig, child_id))
            reply_text = f"🎉 <b>Qoyilmaqom!</b> Sen {pages_read_now} bet o‘qiding va <b>{earned_bilig} 🔅 Bilig</b> ishlading!\n🔥 Streak: {streak} kun!\n<i>(Jami: {new_page_num} bet)</i>"
        else:
            reply_text = f"👍 <b>Barakalla!</b> Sen {pages_read_now} bet o‘qiding. Yana {5 - (new_page_num % 5)} bet o‘qisang, Bilig olasan!\n🔥 Streak: {streak} kun!"
            
        conn.commit()
        await processing_msg.delete()
        await message.answer(reply_text, parse_mode="HTML", reply_markup=get_child_keyboard())
        await state.clear()
        
        parent_id = get_parent_id(child_id)
        if parent_id:
            await message.bot.send_message(parent_id, f"📖 Farzandingiz <b>'{book_title}'</b> kitobidan {pages_read_now} bet o‘qidi. (Jami: {new_page_num} bet).", parse_mode="HTML")
    except Exception:
        await processing_msg.delete()
        await message.answer("❌ Xatolik yuz berdi. Qaytadan urinib ko‘r.", reply_markup=get_child_keyboard())
        await state.clear()

# ==========================================
# AUDIO XULOSA VA AI USTOZ BAHOSI
# ==========================================
@router.callback_query(F.data.startswith("sendaudio_"))
async def ask_audio_summary(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT pages_read, audio_count FROM Plan_Books WHERE book_id = ?", (book_id,))
    row = cursor.fetchone()
    if not row: return
        
    pages_read, audio_count = row[0], (row[1] if row[1] else 0)
    required_pages = 10 if audio_count == 0 else 10 + (audio_count * 30)
    
    if pages_read < required_pages:
        await callback.answer(f"🔒 Audio yuborish uchun kamida {required_pages}-sahifagacha o‘qishingiz kerak!\n(Hozir: {pages_read} bet)", show_alert=True)
        return
        
    await state.update_data(audio_book_id=book_id, is_retry=False)
    try: await callback.message.delete()
    except Exception: pass
    
    audio_info_text = (
        "🎤 <b>Ovozli xulosa yuborish</b>\n\n"
        "Kitobda nima bo‘lganini, qaysi qahramon yoqqanini va o‘zingga qanday xulosa chiqarganingni aytib ber.\n\n"
        "💡 <i>Agar nutqing ravon, fikrlaring teran bo‘lsa, AI ustoz 1 dan 5 gacha Bilig beradi!</i>"
    )
    await callback.bot.send_message(callback.from_user.id, audio_info_text, parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ChildReading.waiting_for_audio)
    await callback.answer()

@router.callback_query(F.data.startswith("retryaudio_"))
async def retry_audio_summary(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    await state.update_data(audio_book_id=book_id, is_retry=True)
    try: await callback.message.delete()
    except Exception: pass
    await callback.bot.send_message(callback.from_user.id, "🎤 <b>Qayta ovozli xabar yubor!</b>\nBatafsilroq va ravonroq gapirishga harakat qil!", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ChildReading.waiting_for_audio)
    await callback.answer()

@router.message(ChildReading.waiting_for_audio, F.voice)
async def process_audio_summary(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>AI ustoz seni eshitmoqda...</i>", parse_mode="HTML")
    try:
        file_info = await message.bot.get_file(message.voice.file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)
        
        data = await state.get_data()
        book_id, is_retry = data.get('audio_book_id'), data.get('is_retry', False)
        
        cursor.execute("SELECT child_age FROM Family_Link WHERE child_id = ?", (message.from_user.id,))
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
        
        if not is_retry: cursor.execute("UPDATE Plan_Books SET audio_count = audio_count + 1 WHERE book_id = ?", (book_id,))
        cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (bonus, message.from_user.id))
        update_streak(message.from_user.id)
        
        badge_text = ""
        if give_badge:
            cursor.execute("SELECT badges FROM Users WHERE user_id = ?", (message.from_user.id,))
            current_badges = cursor.fetchone()[0]
            if "Notiq" not in str(current_badges):
                cursor.execute("UPDATE Users SET badges = ? WHERE user_id = ?", (str(current_badges) + " 🗣 Notiq" if current_badges else "🗣 Notiq", message.from_user.id))
                badge_text = "\n\n🏅 <b>TABRIKLAYMIZ! 'Notiq' nishonini olding!</b>"
                
        conn.commit()
        kb_child = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🎤 Qayta aytib berish (+{5 - bonus} 🔅)", callback_data=f"retryaudio_{book_id}")]]) if bonus < 5 else None
            
        await processing_msg.delete()
        await message.answer(f"👨‍🏫 <b>AI ustoz:</b>\n\n{child_feedback}\n\n🎁 <b>Mukofot:</b> {bonus} 🔅 Bilig!{badge_text}", parse_mode="HTML", reply_markup=kb_child if kb_child else get_child_keyboard())
        await state.clear()
        
        parent_id = get_parent_id(message.from_user.id)
        if parent_id:
            cursor.execute("SELECT name FROM Users WHERE user_id = ?", (message.from_user.id,))
            c_name = cursor.fetchone()[0]
            parent_text = (
                f"📊 <b>FARZANDINGIZNING AUDIO TAHLILI</b>\n\n"
                f"👦 <b>Farzand:</b> {c_name}\n📘 <b>Kitob:</b> {book_title}\n🎁 <b>Bilig:</b> {bonus}/5 🔅\n\n"
                f"📝 <b>Mazmuni:</b> <i>{parent_rep.get('summary')}</i>\n\n"
                f"✅ <b>Yutuqlari:</b> {parent_rep.get('strengths')}\n\n"
                f"⚠️ <b>Kamchiliklar:</b> {parent_rep.get('weaknesses')}"
            )
            await message.bot.send_message(parent_id, parent_text, parse_mode="HTML")
    except Exception:
        await processing_msg.delete()
        await message.answer("❌ Xatolik yuz berdi.", reply_markup=get_child_keyboard())
        await state.clear()

# ==========================================
# TEST TOPSHIRISH
# ==========================================
async def render_test_question(message_or_callback, book_id: int, q_idx: int, correct_count: int):
    cursor.execute("SELECT questions_json FROM Book_Tests WHERE book_id = ?", (book_id,))
    test_row = cursor.fetchone()
    if not test_row:
        if isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.answer("🔒 Test topilmadi!", show_alert=True)
        return
        
    questions = json.loads(test_row[0])
    total_q = len(questions)
    user_id = message_or_callback.from_user.id
    
    if q_idx >= total_q:
        cursor.execute("UPDATE Users SET balance_coins = balance_coins + ? WHERE user_id = ?", (correct_count, user_id))
        cursor.execute("DELETE FROM Book_Tests WHERE book_id = ?", (book_id,))
        conn.commit()
        
        finish_text = (
            f"🏁 <b>Test yakunlandi!</b>\n\n"
            f"✅ To‘g‘ri javoblar: <b>{correct_count} / {total_q}</b> ta\n"
            f"🎁 Mukofot: <b>+{correct_count} 🔅 Bilig</b> tangasi hisobingga qo‘shildi! 🧠"
        )
        finish_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Kitobni yakunlash", callback_data=f"finishbook_{book_id}")],
            [InlineKeyboardButton(text="📚 Kitoblar ro‘yxatiga qaytish", callback_data="child_books_main")]
        ])
        
        if isinstance(message_or_callback, types.CallbackQuery):
            await message_or_callback.message.edit_text(finish_text, parse_mode="HTML", reply_markup=finish_kb)
        else:
            await message_or_callback.answer(finish_text, parse_mode="HTML", reply_markup=finish_kb)
            
        parent_id = get_parent_id(user_id)
        if parent_id:
            cursor.execute("SELECT name FROM Users WHERE user_id = ?", (user_id,))
            c_name = cursor.fetchone()[0]
            cursor.execute("SELECT title FROM Plan_Books WHERE book_id = ?", (book_id,))
            b_title = cursor.fetchone()[0]
            pct = int((correct_count / total_q) * 100)
            await message_or_callback.bot.send_message(
                parent_id,
                f"📝 <b>TEST NATIJASI</b>\n\n👦 <b>{c_name}</b> | 📘 {b_title}\n🎯 Natija: {correct_count}/{total_q} ({pct}%)\n🎁 +{correct_count} 🔅 Bilig berildi!",
                parse_mode="HTML"
            )
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
            
        buttons_row.append(InlineKeyboardButton(text=f"[ {letter} ]", callback_data=f"tans_{book_id}_{q_idx}_{idx}_{correct_count}"))
        
    kb = []
    if len(buttons_row) <= 4:
        kb.append(buttons_row[:2])
        if len(buttons_row) > 2:
            kb.append(buttons_row[2:])
    else:
        kb.append(buttons_row[:3])
        kb.append(buttons_row[3:])
        
    kb.append([InlineKeyboardButton(text="🔙 To‘xtatish", callback_data=f"cread_{book_id}")])
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.callback_query(F.data.startswith("taketest_"))
async def execute_test(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    book_id, q_idx, correct_count = int(parts[1]), int(parts[2]), int(parts[3])
    await render_test_question(callback, book_id, q_idx, correct_count)
    await callback.answer()

@router.callback_query(F.data.startswith("tans_"))
async def process_test_answer(callback: types.CallbackQuery):
    try:
        parts = callback.data.split("_")
        book_id, q_idx, selected_opt_idx, correct_count = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
        
        cursor.execute("SELECT questions_json FROM Book_Tests WHERE book_id = ?", (book_id,))
        test_row = cursor.fetchone()
        if not test_row:
            await callback.answer("🔒 Test topilmadi!", show_alert=True)
            return
            
        questions = json.loads(test_row[0])
        q = questions[q_idx]
        letters = ["A", "B", "C", "D", "E"]
        
        options = q.get('options', [])
        selected_letter = letters[selected_opt_idx] if selected_opt_idx < len(letters) else ""
        selected_text = options[selected_opt_idx].strip() if selected_opt_idx < len(options) else ""
        answer = str(q.get('answer', '')).strip()
        
        is_correct = False
        if answer.upper() == selected_letter or answer.upper().startswith(f"{selected_letter})") or answer.upper().startswith(f"{selected_letter}."):
            is_correct = True
        elif selected_text.lower() == answer.lower():
            is_correct = True
        elif answer.lower() in selected_text.lower() and len(answer) > 1:
            is_correct = True
            
        new_correct_count = correct_count + (1 if is_correct else 0)
        
        if is_correct:
            await callback.answer("✅ To‘g‘ri javob!", show_alert=False)
        else:
            await callback.answer("❌ Noto‘g‘ri javob!", show_alert=False)
            
        await render_test_question(callback, book_id, q_idx + 1, new_correct_count)
    except Exception:
        await callback.answer("⚠️ Xatolik yuz berdi. Qaytadan urinib ko‘ring.", show_alert=True)

# ==========================================
# SOVRINLARIM (YUTUQLAR XAZINASI)
# ==========================================
@router.message(F.text == "🎁 Sovrinlarim")
async def show_rewards(message: types.Message):
    cursor.execute("SELECT balance_coins, badges, streak_days FROM Users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    balance = user[0] if user else 0
    badges_display = user[1] if (user and user[1]) else "Hali nishonlar yo‘q"
    streak = user[2] if user else 0
    
    text = (
        f"🦸‍♂️ <b>Qahramon: {message.from_user.full_name}</b>\n\n"
        f"🔅 <b>Biliglar xazinasi:</b> {balance} ta\n"
        f"🔥 <b>Uzluksiz mutolaa (Streak):</b> {streak} kun\n"
        f"🏅 <b>Nishonlar:</b> {badges_display}\n\n"
        f"<i>To‘plagan Biliglaringga 🛒 Do‘kondan o‘zingga ajoyib sovg‘alar olishing mumkin!</i>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Do‘konga o‘tish", callback_data="child_store")]])
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

# ==========================================
# DO'KON (BOLA MENYUSI)
# ==========================================
async def show_child_store_view(message_or_call, user_id):
    parent_id = get_parent_id(user_id)
    if not parent_id:
        text = "Ota-onangiz profilingizga ulanmagan."
        if isinstance(message_or_call, types.Message): await message_or_call.answer(text)
        else: await message_or_call.message.edit_text(text)
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
        if isinstance(message_or_call, types.Message): await message_or_call.answer(text, parse_mode="HTML")
        else: await message_or_call.message.edit_text(text, parse_mode="HTML")
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
async def child_store_msg(message: types.Message):
    await show_child_store_view(message, message.from_user.id)

@router.callback_query(F.data == "child_store")
async def child_store_call(callback: types.CallbackQuery):
    await show_child_store_view(callback, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data.startswith("buyitem_"))
async def buy_item_handler(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT name, price, parent_id FROM Store_Items WHERE item_id = ?", (item_id,))
    item = cursor.fetchone()
    if not item:
        await callback.answer("Sovg‘a topilmadi!", show_alert=True)
        return
        
    cursor.execute("SELECT balance_coins FROM Users WHERE user_id = ?", (callback.from_user.id,))
    balance = cursor.fetchone()[0]
    
    if balance < item[1]:
        await callback.answer(f"Yetarli Bilig yo‘q! Yana {item[1] - balance} 🔅 kerak.", show_alert=True)
        return
        
    cursor.execute("UPDATE Users SET balance_coins = balance_coins - ? WHERE user_id = ?", (item[1], callback.from_user.id))
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
    cursor.execute("SELECT name, balance_coins FROM Users WHERE role = 'child' ORDER BY balance_coins DESC LIMIT 10")
    top_users = cursor.fetchall()
    if not top_users:
        await message.answer("Hali reyting shakllanmadi.")
        return
        
    text = "🏆 <b>Eng ko‘p Bilig yig‘gan kitobxonlar:</b>\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top_users):
        medal = medals[i] if i < 3 else f"{i+1}."
        text += f"{medal} <b>{u[0]}</b> — {u[1]} 🔅 Bilig\n"
    await message.answer(text, parse_mode="HTML")
