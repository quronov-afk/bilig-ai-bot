from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import RECOMMENDED_BOOKS, MUTOLAA_NOTE
from database import conn, cursor
from keyboards import (
    get_parent_keyboard, get_back_reply_keyboard, 
    get_add_book_keyboard, get_rewards_main_keyboard, 
    get_bilig_rate_inline_keyboard
)
from states import ParentSettings, PlanCreation, AITestCreation, StoreSettings
from ai_service import analyze_book_cover, generate_test_from_photos

router = Router()

# ==========================================
# FARZAND YOSHINI SOZLASH
# ==========================================
@router.callback_query(F.data.startswith("set_age_"))
async def ask_child_age(callback: types.CallbackQuery, state: FSMContext):
    child_id = int(callback.data.split("_")[2])
    await state.update_data(target_child_id=child_id)
    try: await callback.message.delete()
    except Exception: pass
    await callback.bot.send_message(callback.from_user.id, "✍️ <b>Farzandingiz yoshini raqamda kiriting (masalan: 10):</b>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ParentSettings.waiting_for_child_age)
    await callback.answer()

@router.message(ParentSettings.waiting_for_child_age)
async def save_child_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return
    age = int(message.text)
    data = await state.get_data()
    child_id = data.get('target_child_id')
    
    cursor.execute("UPDATE Family_Link SET child_age = ? WHERE child_id = ? AND parent_id = ?", (age, child_id, message.from_user.id))
    conn.commit()
    
    await message.answer(f"✅ <b>Farzandingiz yoshi ({age} yosh) saqlandi!</b>\nEndi AI ustoz uning yoshiga moslashib baholaydi.", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await state.clear()

# ==========================================
# DO'KON VA MOTIVATSIYA SOZLAMALARI
# ==========================================
def get_rewards_text():
    return (
        "🛒 <b>Do‘kon va Rag‘bat tizimi</b>\n\n"
        "Tizimda 2 xil rag‘batlantirish falsafasi mavjud:\n"
        "1️⃣ <b>Yo‘l-yo‘lakay quvvat (Biliglar):</b> Har 5 bet mutolaa uchun beriladi — har kungi odat va kichik quvonchlar uchun.\n"
        "2️⃣ <b>Marra sovrini (Katta mukofot):</b> Butun rejadagi kitoblar to‘liq o‘qib bo‘linganda beriladi — katta maqsad sari yetaklaydi.\n\n"
        "<i>👇 Kerakli bo‘limni tanlang:</i>"
    )

@router.message(F.text.in_(["🛒 Do‘kon", "🛒 Do'kon", "🎁 Mukofotlar"]))
async def mukofotlar_handler(message: types.Message):
    await message.answer(get_rewards_text(), parse_mode="HTML", reply_markup=get_rewards_main_keyboard())

@router.callback_query(F.data == "rewards_main")
async def rewards_main_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(get_rewards_text(), parse_mode="HTML", reply_markup=get_rewards_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "rewards_bilig_rate")
async def rewards_bilig_rate_callback(callback: types.CallbackQuery):
    text = (
        "🔅 <b>Bilig kursini belgilash</b>\n\n"
        "📖 <b>Asosiy qoida:</b> Har 5 sahifa mutolaa = <b>1 ta Bilig (🔅)</b>.\n\n"
        "💡 <i>Byudjet misoli: Farzandingiz 50 bet kitob o‘qisa, 10 ta Bilig to‘playdi. Kursni 1 000 so‘m qilib belgilasangiz, bu 10 000 so‘m rag‘bat bo‘ladi.</i>\n\n"
        "👇 <b>1 ta Bilig (🔅) qiymatini tanlang:</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_bilig_rate_inline_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("rate_"))
async def process_rate_callback(callback: types.CallbackQuery, state: FSMContext):
    rate_val = callback.data.split("_")[1]
    if rate_val == "custom":
        try: await callback.message.delete()
        except Exception: pass
        await callback.bot.send_message(callback.from_user.id, "✍️ <b>Iltimos, 1 ta Bilig (🔅) uchun summani kiriting:</b>\n<i>(Masalan: 1000, 5000)</i>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
        await state.set_state(ParentSettings.waiting_for_custom_rate)
        return
    rate = int(rate_val)
    cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, callback.from_user.id))
    conn.commit()
    
    if rate == 0:
        await callback.message.edit_text("✅ <b>Siz pul bilan rag‘batlantirmaslik rejimini tanladingiz!</b>\n\nEndi farzandingiz faqat nishonlar, reyting va bilim uchun o‘qiydi. Bu ajoyib tanlov! 🧠", parse_mode="HTML", reply_markup=get_rewards_main_keyboard())
    else:
        await callback.message.edit_text(f"✅ <b>Bilig kursi o‘rnatildi!</b>\n1 🔅 = {rate:,} so‘m.", parse_mode="HTML", reply_markup=get_rewards_main_keyboard())
    await callback.answer()

@router.message(ParentSettings.waiting_for_custom_rate)
async def process_custom_rate(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return
    rate = int(message.text)
    cursor.execute("UPDATE Users SET coin_rate = ? WHERE user_id = ?", (rate, message.from_user.id))
    conn.commit()
    await message.answer(f"✅ <b>Bilig kursi o‘rnatildi!</b>\n1 🔅 = {rate:,} so‘m.", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await state.clear()

@router.callback_query(F.data == "rewards_store_edit")
async def store_edit_callback(callback: types.CallbackQuery):
    cursor.execute("SELECT item_id, name, price FROM Store_Items WHERE parent_id = ?", (callback.from_user.id,))
    items = cursor.fetchall()
    
    kb = []
    for item in items:
        kb.append([InlineKeyboardButton(text=f"🗑 {item[1]} — {item[2]} 🔅", callback_data=f"delitem_{item[0]}")])
        
    kb.append([InlineKeyboardButton(text="➕ Yangi sovg‘a qo‘shish", callback_data="add_store_item")])
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="rewards_main")])
    
    text = (
        "🛍 <b>Sovg‘alar do‘koni</b>\n\n"
        "Bu yerdagi sovg‘alarni farzandingiz o‘z Biliglariga sotib olishi mumkin.\n"
        "<i>(O‘chirmoqchi bo‘lgan sovg‘angiz ustiga bosing)</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("delitem_"))
async def delete_store_item(callback: types.CallbackQuery):
    item_id = int(callback.data.split("_")[1])
    cursor.execute("DELETE FROM Store_Items WHERE item_id = ? AND parent_id = ?", (item_id, callback.from_user.id))
    conn.commit()
    await store_edit_callback(callback)

@router.callback_query(F.data == "add_store_item")
async def add_store_item_start(callback: types.CallbackQuery, state: FSMContext):
    try: await callback.message.delete()
    except Exception: pass
    await callback.bot.send_message(
        callback.from_user.id,
        "✍️ <b>Sovg‘a nomini kiriting:</b>\n"
        "<i>(Emojilar bilan ham yozishingiz mumkin! Masalan: 🍦 Muzqaymoq, 🎡 Parkka borish, 🎮 O‘yin)</i>",
        parse_mode="HTML",
        reply_markup=get_back_reply_keyboard()
    )
    await state.set_state(StoreSettings.waiting_for_item_name)
    await callback.answer()

@router.message(StoreSettings.waiting_for_item_name)
async def store_item_name(message: types.Message, state: FSMContext):
    await state.update_data(item_name=message.text)
    await message.answer("💰 <b>Bu sovg‘a necha Bilig (🔅) turadi?</b>\nFaqat raqam kiriting:\n<i>(Masalan: 10, 50, 100)</i>", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(StoreSettings.waiting_for_item_price)

@router.message(StoreSettings.waiting_for_item_price)
async def store_item_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return
    data = await state.get_data()
    cursor.execute("INSERT INTO Store_Items (parent_id, name, price) VALUES (?, ?, ?)", (message.from_user.id, data['item_name'], int(message.text)))
    conn.commit()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yana sovg‘a qo‘shish", callback_data="add_store_item")],
        [InlineKeyboardButton(text="🔙 Do‘konga qaytish", callback_data="rewards_store_edit")]
    ])
    await message.answer(f"✅ <b>{data['item_name']}</b> do‘konga qo‘shildi!\n\nYana sovg‘a qo‘shasizmi?", parse_mode="HTML", reply_markup=kb)
    await state.clear()

# ==========================================
# MUTOLAA REJASINI TUZISH
# ==========================================
@router.message(F.text == "📝 Mutolaa rejasini tuzish")
async def create_plan_start(message: types.Message, state: FSMContext):
    cursor.execute("SELECT child_id FROM Family_Link WHERE parent_id = ?", (message.from_user.id,))
    children = cursor.fetchall()
    
    if not children:
        parent_code = f"BLG-{str(message.from_user.id)[-4:]}"
        await message.answer(
            f"⚠️ <b>Sizga hali hech qaysi farzand ulanmagan!</b>\n\n"
            f"Farzandingiz o‘z telefonida botga kirsin va kodingizni kiritsin:\n🔑 Kodingiz: <b>{parent_code}</b>",
            parse_mode="HTML"
        )
        return
        
    if len(children) == 1:
        child_id = children[0][0]
        await state.update_data(plan_child_id=child_id)
        cursor.execute("SELECT name FROM Users WHERE user_id = ?", (child_id,))
        c_name = cursor.fetchone()[0]
        text = f"📝 <b>Mutolaa rejasi tuzish</b> (Farzand: <b>{c_name}</b>)\n\n👇 <b>1-qadam:</b> Rejaga qanday nom berasiz?\n<i>(Masalan: 'Yozgi ta'til mutolaasi', 'Sarguzashtlar olami')</i>"
        await message.answer(text, parse_mode="HTML", reply_markup=get_back_reply_keyboard())
        await state.set_state(PlanCreation.waiting_for_name)
    else:
        kb = []
        for c in children:
            cursor.execute("SELECT name FROM Users WHERE user_id = ?", (c[0],))
            c_name_row = cursor.fetchone()
            if c_name_row:
                kb.append([InlineKeyboardButton(text=f"👦👧 {c_name_row[0]}", callback_data=f"planfor_{c[0]}")])
        
        await message.answer("📝 <b>Mutolaa rejasi tuzish</b>\n\nUshbu rejani qaysi farzandingiz uchun tuzmoqchisiz?", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
        await state.set_state(PlanCreation.waiting_for_child)

@router.callback_query(PlanCreation.waiting_for_child, F.data.startswith("planfor_"))
async def plan_child_selected(callback: types.CallbackQuery, state: FSMContext):
    child_id = int(callback.data.split("_")[1])
    await state.update_data(plan_child_id=child_id)
    try: await callback.message.delete()
    except Exception: pass
    
    cursor.execute("SELECT name FROM Users WHERE user_id = ?", (child_id,))
    c_name = cursor.fetchone()[0]
    text = f"📝 <b>Mutolaa rejasi tuzish</b> (Farzand: <b>{c_name}</b>)\n\n👇 <b>1-qadam:</b> Rejaga qanday nom berasiz?\n<i>(Masalan: 'Yozgi ta'til mutolaasi', 'Sarguzashtlar olami')</i>"
    await callback.bot.send_message(callback.from_user.id, text, parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(PlanCreation.waiting_for_name)
    await callback.answer()

@router.message(PlanCreation.waiting_for_name)
async def plan_name_received(message: types.Message, state: FSMContext):
    await state.update_data(plan_name=message.text)
    await message.answer(
        "🎁 <b>2-qadam: Marra sovrini (Katta mukofot)!</b>\n\n"
        "Farzandingiz butun rejadagi kitoblarni to‘liq o‘qib tugatganda qanday katta sovrin oladi?\n"
        "<i>(Masalan: 'Velosiped', 'Akva-parkka sayohat', '100 ta Bilig')</i>",
        parse_mode="HTML",
        reply_markup=get_back_reply_keyboard()
    )
    await state.set_state(PlanCreation.waiting_for_prize)

@router.message(PlanCreation.waiting_for_prize)
async def plan_prize_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    child_id = data.get('plan_child_id')
    plan_name = data.get('plan_name')
    plan_prize = message.text
    
    cursor.execute(
        "INSERT INTO Reading_Plans (parent_id, child_id, name, prize, deadline) VALUES (?, ?, ?, ?, '')",
        (message.from_user.id, child_id, plan_name, plan_prize)
    )
    plan_id = cursor.lastrowid
    conn.commit()
    
    await state.update_data(current_plan_id=plan_id)
    await message.answer("✅ <b>Reja yaratildi!</b>", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await message.answer("📚 <b>Endi bu rejaga kitoblar qo‘shamiz!</b>\n👇 <i>Qaysi usuldan foydalanasiz?</i>", parse_mode="HTML", reply_markup=get_add_book_keyboard())

@router.callback_query(F.data == "finish_plan")
async def finish_plan_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("✅ <b>Mutolaa rejasi muvaffaqiyatli saqlandi!</b>\nFarzandingiz o‘z telefonida ushbu kitoblarni o‘qishni boshlashi mumkin. 🚀", parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "add_book_text")
async def add_book_text_handler(callback: types.CallbackQuery, state: FSMContext):
    try: await callback.message.delete()
    except Exception: pass
    await callback.bot.send_message(
        callback.from_user.id,
        "✍️ <b>Matn orqali qo‘shish</b>\n\n"
        "Kitob nomi va muallifini nuqta bilan ajratib yozing:\n"
        "<i>(Masalan: Sariq devni minib. Xudoyberdi To‘xtaboyev)</i>",
        parse_mode="HTML",
        reply_markup=get_back_reply_keyboard()
    )
    await state.set_state(PlanCreation.waiting_for_book_text)
    await callback.answer()

@router.message(PlanCreation.waiting_for_book_text)
async def process_book_text(message: types.Message, state: FSMContext):
    if "." not in message.text:
        await message.answer("⚠️ Iltimos, kitob nomi va muallifini nuqta (.) bilan ajrating.\n<i>Masalan: Shum bola. G‘afur G‘ulom</i>")
        return
    title, author = message.text.split(".", 1)
    data = await state.get_data()
    cursor.execute("INSERT INTO Plan_Books (plan_id, title, author) VALUES (?, ?, ?)", (data.get('current_plan_id'), title.strip(), author.strip()))
    conn.commit()
    await message.answer(f"📚 <b>'{title.strip()}'</b> kitobi rejangizga qo‘shildi!", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await message.answer("Yana kitob qo‘shasizmi yoki rejani yakunlaysizmi?", reply_markup=get_add_book_keyboard())

@router.callback_query(F.data == "add_book_photo")
async def add_book_photo_handler(callback: types.CallbackQuery, state: FSMContext):
    try: await callback.message.delete()
    except Exception: pass
    await callback.bot.send_message(callback.from_user.id, "📸 <b>Rasm orqali qo‘shish</b>\n\nKitobning muqovasini rasmga olib yuboring.", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(PlanCreation.waiting_for_book_photo)
    await callback.answer()

@router.message(PlanCreation.waiting_for_book_photo, F.photo)
async def process_book_photo(message: types.Message, state: FSMContext):
    processing_msg = await message.answer("⏳ <i>Gemini AI muqovani tahlil qilmoqda...</i>", parse_mode="HTML")
    try:
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)
        
        title, author = await analyze_book_cover(downloaded_file.read())
        
        data = await state.get_data()
        cursor.execute("INSERT INTO Plan_Books (plan_id, title, author) VALUES (?, ?, ?)", (data.get('current_plan_id'), title, author))
        conn.commit()
        
        await processing_msg.delete()
        await message.answer(f"✅ <b>AI aniqladi!</b>\n📚 <b>'{title}'</b> ({author})\nKitob qo‘shildi!", parse_mode="HTML", reply_markup=get_parent_keyboard())
        await message.answer("Yana kitob qo‘shasizmi yoki rejani yakunlaysizmi?", reply_markup=get_add_book_keyboard())
    except Exception:
        await processing_msg.delete()
        await message.answer("❌ Muqovani aniqlab bo‘lmadi. Iltimos, kitobni matn orqali qo‘shing.", parse_mode="HTML", reply_markup=get_parent_keyboard())

# YOSH BO'YICHA TAVSIYALAR
@router.callback_query(F.data == "add_book_age")
async def show_age_recommendation_menu(callback: types.CallbackQuery):
    kb = [
        [InlineKeyboardButton(text="👶 3+ yosh", callback_data="rec_age_3"), InlineKeyboardButton(text="👦 6+ yosh", callback_data="rec_age_6")],
        [InlineKeyboardButton(text="🧒 8+ yosh", callback_data="rec_age_8"), InlineKeyboardButton(text="🧑 12+ yosh", callback_data="rec_age_12")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_add_books")]
    ]
    await callback.message.edit_text("👶 <b>Farzandingiz yosh toifasini tanlang:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data == "back_to_add_books")
async def back_to_add_books_callback(callback: types.CallbackQuery):
    await callback.message.edit_text("📚 <b>Kitoblar qo‘shish usulini tanlang:</b>", reply_markup=get_add_book_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("rec_age_"))
async def show_recommended_books_list(callback: types.CallbackQuery):
    age_group = callback.data.split("_")[2]
    books_list = RECOMMENDED_BOOKS.get(age_group, [])
    
    text = (
        f"📚 <b>{age_group}+ yoshli bolalar uchun tavsiya etilgan asarlar:</b>\n\n"
        f"<i>(Istalgan kitob ustiga bir marta bosing — avtomatik nusxalanadi!)</i>\n\n"
    )
    for idx, b_name in enumerate(books_list, 1):
        text += f"{idx}. <code>{b_name}</code>\n"
        
    text += f"\n{MUTOLAA_NOTE}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Yosh toifalariga qaytish", callback_data="add_book_age")],
        [InlineKeyboardButton(text="📚 Kitob qo‘shishga qaytish", callback_data="back_to_add_books")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

# ==========================================
# FAOL REJALAR VA AI TEST TUZISH
# ==========================================
async def show_parent_plans(message_or_callback, user_id):
    cursor.execute("""
        SELECT rp.plan_id, rp.name, rp.prize, u.name 
        FROM Reading_Plans rp 
        LEFT JOIN Users u ON rp.child_id = u.user_id 
        WHERE rp.parent_id = ? AND rp.status = 'active'
    """, (user_id,))
    plans = cursor.fetchall()
    
    if not plans:
        text = "Sizda hozircha faol rejalar yo‘q."
        if isinstance(message_or_callback, types.Message): await message_or_callback.answer(text, reply_markup=get_parent_keyboard())
        else: await message_or_callback.message.edit_text(text)
        return
        
    kb = []
    for p in plans:
        cursor.execute("SELECT COUNT(*) FROM Plan_Books WHERE plan_id = ?", (p[0],))
        book_count = cursor.fetchone()[0]
        child_label = f" (👦 {p[3]})" if p[3] else ""
        kb.append([InlineKeyboardButton(text=f"🎯 {p[1]}{child_label} ({book_count} ta kitob)", callback_data=f"showplan_{p[0]}")])
        
    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    if isinstance(message_or_callback, types.Message): await message_or_callback.answer("📚 <b>Sizning faol rejalaringiz:</b>", parse_mode="HTML", reply_markup=markup)
    else: await message_or_callback.message.edit_text("📚 <b>Sizning faol rejalaringiz:</b>", parse_mode="HTML", reply_markup=markup)

@router.message(F.text == "📚 Faol rejalarim")
async def parent_active_plans_msg(message: types.Message):
    await show_parent_plans(message, message.from_user.id)

@router.callback_query(F.data == "parent_plans_main")
async def parent_active_plans_call(callback: types.CallbackQuery):
    await show_parent_plans(callback, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data.startswith("showplan_"))
async def show_plan_details(callback: types.CallbackQuery):
    plan_id = int(callback.data.split("_")[1])
    cursor.execute("""
        SELECT rp.name, rp.prize, u.name 
        FROM Reading_Plans rp 
        LEFT JOIN Users u ON rp.child_id = u.user_id 
        WHERE rp.plan_id = ?
    """, (plan_id,))
    plan = cursor.fetchone()
    
    cursor.execute("SELECT book_id, title, is_completed FROM Plan_Books WHERE plan_id = ?", (plan_id,))
    books = cursor.fetchall()
    
    kb = []
    for b in books:
        status_icon = "✅" if b[2] == 1 else "📘"
        kb.append([InlineKeyboardButton(text=f"{status_icon} {b[1]}", callback_data=f"showbook_{b[0]}")])
        
    kb.append([InlineKeyboardButton(text="🗑 Rejani o‘chirish", callback_data=f"delplan_{plan_id}")])
    kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="parent_plans_main")])
    
    child_info = f"\n👦 Farzand: <b>{plan[2]}</b>" if plan[2] else ""
    prize_text = f"\n🎁 Marra sovrini: <b>{plan[1]}</b>" if plan[1] else ""
    text = f"🎯 <b>{plan[0]}</b>{child_info}{prize_text}\n\n📚 <b>Kitoblar ro‘yxati:</b>"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("delplan_"))
async def delete_plan_handler(callback: types.CallbackQuery):
    plan_id = int(callback.data.split("_")[1])
    cursor.execute("DELETE FROM Book_Tests WHERE book_id IN (SELECT book_id FROM Plan_Books WHERE plan_id = ?)", (plan_id,))
    cursor.execute("DELETE FROM Plan_Books WHERE plan_id = ?", (plan_id,))
    cursor.execute("DELETE FROM Reading_Plans WHERE plan_id = ?", (plan_id,))
    conn.commit()
    
    await callback.answer("✅ Reja va uning kitoblari to‘liq o‘chirildi!", show_alert=True)
    await show_parent_plans(callback, callback.from_user.id)

@router.callback_query(F.data.startswith("showbook_"))
async def show_book_details(callback: types.CallbackQuery):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT plan_id, title, author, pages_read, is_completed FROM Plan_Books WHERE book_id = ?", (book_id,))
    book = cursor.fetchone()
    if not book:
        await callback.answer("Kitob topilmadi!", show_alert=True)
        return
        
    cursor.execute("SELECT test_id FROM Book_Tests WHERE book_id = ?", (book_id,))
    has_test = cursor.fetchone()
    test_btn_text = "🔄 Testni qayta tuzish (AI)" if has_test else "📝 AI Test tuzish (Rasm orqali)"
    
    kb = [
        [InlineKeyboardButton(text=test_btn_text, callback_data=f"aitest_{book_id}")],
        [InlineKeyboardButton(text="🗑 Kitobni o‘chirish", callback_data=f"delbook_{book_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"showplan_{book[0]}")]
    ]
    status_text = "Tugatilgan ✅" if book[4] == 1 else "O‘qilmoqda ⏳"
    test_status = "Mavjud ✅" if has_test else "Hali tuzilmagan ❌"
    text = f"📘 <b>{book[1]}</b>\n✍️ Muallif: {book[2]}\n📖 O‘qildi: {book[3]} bet\n📊 Holati: {status_text}\n🧠 AI Test: {test_status}"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await callback.answer()

@router.callback_query(F.data.startswith("delbook_"))
async def delete_book_handler(callback: types.CallbackQuery):
    book_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT plan_id, title FROM Plan_Books WHERE book_id = ?", (book_id,))
    book = cursor.fetchone()
    
    if book:
        plan_id = book[0]
        cursor.execute("DELETE FROM Book_Tests WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM Plan_Books WHERE book_id = ?", (book_id,))
        conn.commit()
        await callback.answer("✅ Kitob o‘chirildi!", show_alert=True)
        
        cursor.execute("""
            SELECT rp.name, rp.prize, u.name 
            FROM Reading_Plans rp 
            LEFT JOIN Users u ON rp.child_id = u.user_id 
            WHERE rp.plan_id = ?
        """, (plan_id,))
        plan = cursor.fetchone()
        cursor.execute("SELECT book_id, title, is_completed FROM Plan_Books WHERE plan_id = ?", (plan_id,))
        books = cursor.fetchall()
        
        kb = []
        for b in books:
            status_icon = "✅" if b[2] == 1 else "📘"
            kb.append([InlineKeyboardButton(text=f"{status_icon} {b[1]}", callback_data=f"showbook_{b[0]}")])
            
        kb.append([InlineKeyboardButton(text="🗑 Rejani o‘chirish", callback_data=f"delplan_{plan_id}")])
        kb.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="parent_plans_main")])
        
        child_info = f"\n👦 Farzand: <b>{plan[2]}</b>" if plan[2] else ""
        prize_text = f"\n🎁 Marra sovrini: <b>{plan[1]}</b>" if plan[1] else ""
        text = f"🎯 <b>{plan[0]}</b>{child_info}{prize_text}\n\n📚 <b>Kitoblar ro‘yxati:</b>"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else:
        await callback.answer("Kitob topilmadi!", show_alert=True)

@router.callback_query(F.data.startswith("aitest_"))
async def ask_for_test_photo(callback: types.CallbackQuery, state: FSMContext):
    book_id = int(callback.data.split("_")[1])
    await state.update_data(test_book_id=book_id, photos=[])
    try: await callback.message.delete()
    except Exception: pass
    
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Testni tuzish")], [KeyboardButton(text="🔙 Orqaga")]], resize_keyboard=True)
    await callback.bot.send_message(
        callback.from_user.id,
        "📸 <b>AI Test tuzish uchun sahifalar rasmini yuboring!</b>\n\n"
        "Sahifalarni ketma-ket rasmga olib yuboring.\n\n"
        "Barcha rasmlarni yuborgach, pastdagi <b>'✅ Testni tuzish'</b> tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=kb
    )
    await state.set_state(AITestCreation.waiting_for_page_photo)
    await callback.answer()

@router.message(AITestCreation.waiting_for_page_photo, F.photo)
async def collect_test_photo(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)
    downloaded_file = await message.bot.download_file(file_info.file_path)
    
    data = await state.get_data()
    photos = data.get('photos', [])
    photos.append(downloaded_file.read())
    await state.update_data(photos=photos)
    
    photo_count = len(photos)
    await message.answer(f"📸 <b>{photo_count}-sahifa rasmi qabul qilindi!</b>\n\nYetarli rasmlar yig‘ilgach, testni tuzish uchun pastdagi <b>'✅ Testni tuzish'</b> tugmasini bosing.")

@router.message(AITestCreation.waiting_for_page_photo, F.text == "✅ Testni tuzish")
async def generate_ai_test_multi(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get('photos', [])
    book_id = data.get('test_book_id')
    
    if len(photos) < 1:
        await message.answer("⚠️ Iltimos, kamida 1 ta sahifa rasmini yuboring!")
        return
        
    processing_msg = await message.answer(f"⏳ <i>Gemini AI {len(photos)} ta sahifani tahlil qilib, 5 ta mantiqiy test savoli tuzmoqda... Iltimos kuting.</i>", parse_mode="HTML")
    
    try:
        questions, raw_json = await generate_test_from_photos(photos)
        cursor.execute("INSERT OR REPLACE INTO Book_Tests (book_id, questions_json) VALUES (?, ?)", (book_id, raw_json))
        conn.commit()
        
        test_text = f"✅ <b>AI Test {len(photos)} ta sahifa asosida muvaffaqiyatli tuzildi!</b>\n\n<i>Quyidagi 5 ta savol bazaga saqlandi:</i>\n\n"
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
# FARZAND NATIJALARI VA BILIG BOSHQARUVI (+ / -)
# ==========================================
async def show_single_child_result(message_or_call, child_id, parent_id):
    cursor.execute("SELECT child_age FROM Family_Link WHERE child_id = ? AND parent_id = ?", (child_id, parent_id))
    row = cursor.fetchone()
    child_age = row[0] if (row and row[0]) else "Kiritilmagan"
    
    cursor.execute("SELECT name, balance_coins, badges, streak_days FROM Users WHERE user_id = ?", (child_id,))
    child = cursor.fetchone()
    if not child: return
    child_name, balance, badges, streak = child
    badges_text = badges if badges else "Hali nishonlar yo‘q"
    
    cursor.execute("""
        SELECT pb.title, pb.pages_read, pb.is_completed 
        FROM Plan_Books pb 
        JOIN Reading_Plans rp ON pb.plan_id = rp.plan_id 
        WHERE rp.parent_id = ? AND rp.child_id = ?
    """, (parent_id, child_id))
    books = cursor.fetchall()
    total_pages = sum([b[1] for b in books]) if books else 0
    
    text = (
        f"📊 <b>{child_name}ning natijalari:</b>\n\n"
        f"👦 Yoshi: <b>{child_age} yosh</b>\n"
        f"🔅 Yig‘ilgan Biliglar: <b>{balance} ta</b>\n"
        f"🔥 Uzluksiz o‘qish: <b>{streak} kun</b>\n"
        f"🏅 Nishonlar: {badges_text}\n\n"
        f"📖 <b>Jami o‘qilgan: {total_pages} bet</b>\n"
    )
    if books:
        text += "\n📚 <b>Kitoblar bo‘yicha:</b>\n"
        for b in books:
            status = "✅" if b[2] else "⏳"
            text += f" ➖ <i>{b[0]}</i>: {b[1]} bet {status}\n"
    else:
        text += "\n<i>Bu farzandingiz uchun hali kitoblar qo‘shilmagan.</i>\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Haftalik hisobot va AI Tahlil", callback_data=f"weeklyrep_{child_id}")],
        [InlineKeyboardButton(text="🔅 Biliglarni boshqarish (+ / -)", callback_data=f"manage_coins_{child_id}")],
        [InlineKeyboardButton(text="✍️ Farzand yoshini o‘zgartirish", callback_data=f"set_age_{child_id}")],
        [InlineKeyboardButton(text="➕ Boshqa farzand qo‘shish", callback_data="add_child_info")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="parent_results_main")]
    ])
    
    if isinstance(message_or_call, types.Message):
        await message_or_call.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message_or_call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data.startswith("manage_coins_"))
async def manage_coins_menu(callback: types.CallbackQuery):
    child_id = int(callback.data.split("_")[2])
    cursor.execute("SELECT name, balance_coins FROM Users WHERE user_id = ?", (child_id,))
    child = cursor.fetchone()
    if not child: return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Bilig sovg‘a qilish (+ 🔅)", callback_data=f"addcoins_{child_id}")],
        [InlineKeyboardButton(text="➖ Bilig ayirish (- 🔅)", callback_data=f"dedcustom_{child_id}")],
        [InlineKeyboardButton(text="🔄 Hisobni 0 ga tushirish", callback_data=f"dedzero_{child_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"childres_{child_id}")]
    ])
    text = (
        f"🔅 <b>{child[0]}ning Biliglarini boshqarish</b>\n\n"
        f"Hozirgi hisobi: <b>{child[1]} 🔅 Bilig</b>\n\n"
        f"<i>Quyidagi amallardan birini tanlang:</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

# ➕ BILIG QO'SHISH
@router.callback_query(F.data.startswith("addcoins_"))
async def add_coins_start(callback: types.CallbackQuery, state: FSMContext):
    child_id = int(callback.data.split("_")[1])
    await state.update_data(target_add_child_id=child_id)
    try: await callback.message.delete()
    except Exception: pass
    await callback.bot.send_message(
        callback.from_user.id,
        "🎁 <b>Farzandingizga necha Bilig (🔅) sovg‘a qilmoqchisiz?</b>\n\n<i>(Masalan: 10, 20, 50)</i>",
        parse_mode="HTML",
        reply_markup=get_back_reply_keyboard()
    )
    await state.set_state(ParentSettings.waiting_for_coin_addition)
    await callback.answer()

@router.message(ParentSettings.waiting_for_coin_addition)
async def process_coin_addition(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return
    amount = int(message.text)
    data = await state.get_data()
    child_id = data.get('target_add_child_id')
    
    cursor.execute("SELECT name, balance_coins FROM Users WHERE user_id = ?", (child_id,))
    child = cursor.fetchone()
    if not child: return
    new_balance = child[1] + amount
    cursor.execute("UPDATE Users SET balance_coins = ? WHERE user_id = ?", (new_balance, child_id))
    conn.commit()
    
    await message.answer(f"🎉 <b>{child[0]}ga +{amount} 🔅 Bilig sovg‘a qilindi!</b>\nYangi balans: <b>{new_balance} 🔅</b>", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await state.clear()
    
    try:
        await message.bot.send_message(
            child_id,
            f"🎉 <b>TABRIKLAYMIZ, QAHRAMON!</b>\n\n"
            f"Ota-onangiz sizga ajoyib mehnatingiz uchun <b>+{amount} 🔅 Bilig</b> sovg‘a qildi! 🎁\n\n"
            f"Hozirgi balansingiz: <b>{new_balance} 🔅 Bilig</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass

# ➖ BILIG AYIRISH
@router.callback_query(F.data.startswith("dedcustom_"))
async def deduct_custom_start(callback: types.CallbackQuery, state: FSMContext):
    child_id = int(callback.data.split("_")[1])
    await state.update_data(target_deduct_child_id=child_id)
    try: await callback.message.delete()
    except Exception: pass
    await callback.bot.send_message(callback.from_user.id, "✍️ <b>Hisobdan necha Bilig (🔅) ayirmoqchisiz?</b> (Masalan: 10):", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(ParentSettings.waiting_for_coin_deduction)
    await callback.answer()

@router.message(ParentSettings.waiting_for_coin_deduction)
async def process_coin_deduction(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting!")
        return
    amount = int(message.text)
    data = await state.get_data()
    child_id = data.get('target_deduct_child_id')
    
    cursor.execute("SELECT name, balance_coins FROM Users WHERE user_id = ?", (child_id,))
    child = cursor.fetchone()
    if not child: return
    new_balance = max(0, child[1] - amount)
    cursor.execute("UPDATE Users SET balance_coins = ? WHERE user_id = ?", (new_balance, child_id))
    conn.commit()
    
    await message.answer(f"✅ <b>{child[0]}ning hisobidan {amount} 🔅 ayirildi!</b>\nYangi balans: <b>{new_balance} 🔅</b>", parse_mode="HTML", reply_markup=get_parent_keyboard())
    await state.clear()
    try: await message.bot.send_message(child_id, f"ℹ️ <b>Ota-onangiz hisobingizdan {amount} 🔅 ayirdi.</b>\nHozirgi balansingiz: <b>{new_balance} 🔅</b>", parse_mode="HTML")
    except Exception: pass

@router.callback_query(F.data.startswith("dedzero_"))
async def deduct_zero_handler(callback: types.CallbackQuery):
    child_id = int(callback.data.split("_")[1])
    cursor.execute("SELECT name, balance_coins FROM Users WHERE user_id = ?", (child_id,))
    child = cursor.fetchone()
    cursor.execute("UPDATE Users SET balance_coins = 0 WHERE user_id = ?", (child_id,))
    conn.commit()
    
    await callback.answer(f"{child[0]}ning balansi 0 ga tushirildi!", show_alert=True)
    await show_single_child_result(callback, child_id, callback.from_user.id)
    try: await callback.bot.send_message(child_id, "ℹ️ <b>Ota-onangiz hisobingizdagi Biliglarni nolga tushirdi.</b>\nHozirgi balansingiz: <b>0 🔅</b>", parse_mode="HTML")
    except Exception: pass

@router.callback_query(F.data.startswith("weeklyrep_"))
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
    pct_text = "Yangi ko‘rsatkich 🚀" if last_week == 0 else (f"+{int((diff/last_week)*100)}% ga oshgan 🚀" if diff > 0 else (f"-{int((abs(diff)/last_week)*100)}% ga pasaygan 📉" if diff < 0 else "Bir xil barqaror ⏸"))
    dynamic_icon = "📈" if diff >= 0 else "📉"

    if diff >= 0:
        advice_text = "Farzandingiz shu haftada juda faol bo‘ldi! Uni doimiy ravishda rag‘batlantirib turing."
    else:
        advice_text = "Farzandingiz bu hafta biroz kamroq o‘qidi. Birgalikda kitob mutolaa qilish foydali bo‘ladi."

    report_text = (
        f"📈 <b>{c_name}ning HAFTALIK MUTOLAA HISOBOTI</b>\n\n"
        f"🗓 <b>Shu hafta o‘qildi:</b> {this_week} bet\n"
        f"🗓 <b>O‘tgan hafta o‘qilgan edi:</b> {last_week} bet\n"
        f"{dynamic_icon} <b>Dinamika:</b> {pct_text}\n\n"
        f"🧠 <b>AI Pedagogik Tavsiyasi:</b>\n"
        f"<i>{advice_text}</i>"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Farzand natijalariga qaytish", callback_data=f"childres_{child_id}")]])
    await callback.message.edit_text(report_text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()

async def show_parent_results_menu(message_or_call, parent_id):
    cursor.execute("SELECT child_id FROM Family_Link WHERE parent_id = ?", (parent_id,))
    links = cursor.fetchall()
    
    if not links:
        parent_code = f"BLG-{str(parent_id)[-4:]}"
        text = f"Sizga hali hech qaysi farzand ulanmagan.\n\nFarzandingiz botga kirib <b>'👦👧 Men O‘quvchiman'</b> bo‘limini tanlasin va kodingizni kiritsin:\n\n🔑 Kodingiz: <b>{parent_code}</b>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Farzand qo‘shish yo‘riqnomasi", callback_data="add_child_info")]])
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
            
    kb.append([InlineKeyboardButton(text="➕ Boshqa farzand qo‘shish", callback_data="add_child_info")])
    text = "📊 <b>Qaysi farzandingizning natijasini ko‘rmoqchisiz?</b>"
    
    if isinstance(message_or_call, types.Message): await message_or_call.answer(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    else: await message_or_call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@router.message(F.text == "📊 Farzandim natijalari")
async def parent_results_handler(message: types.Message):
    await show_parent_results_menu(message, message.from_user.id)

@router.callback_query(F.data == "parent_results_main")
async def parent_results_main_callback(callback: types.CallbackQuery):
    await show_parent_results_menu(callback, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data.startswith("childres_"))
async def childres_callback(callback: types.CallbackQuery):
    child_id = int(callback.data.split("_")[1])
    await show_single_child_result(callback, child_id, callback.from_user.id)
    await callback.answer()

@router.callback_query(F.data == "add_child_info")
async def add_child_info_handler(callback: types.CallbackQuery):
    parent_code = f"BLG-{str(callback.from_user.id)[-4:]}"
    text = (
        f"➕ <b>Yangi farzand qo‘shish yo‘riqnomasi:</b>\n\n"
        f"1. Farzandingiz telefonida botni oching va <b>'👦👧 Men O‘quvchiman'</b>ni bosing.\n"
        f"2. Quyidagi kodingizni kiritsin:\n\n🔑 <b>{parent_code}</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="parent_results_main")]])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()
