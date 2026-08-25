from aiogram import Router, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import WELCOME_TEXT
from database import conn, cursor
from keyboards import get_parent_keyboard, get_child_keyboard, get_bolaxona_keyboard, get_back_reply_keyboard, get_add_book_methods_keyboard
from states import Registration, PlanCreation

router = Router()

CLOSED_BETA_TEXT = (
    "🔒 <b>Bilig AI — Yopiq test rejimi</b>\n\n"
    "Assalomu alaykum! Bilig AI platformasi hozirda muallif tomonidan <b>yopiq sinov (beta)</b> rejimida ishlamoqda.\n\n"
    "Botdan faqat <b>maxsus taklif havolasi (taklifnoma)</b> orqali foydalanish mumkin.\n\n"
    "<i>Agar sizda taklifnoma havolasi bo‘lsa, iltimos, sizga yuborilgan havola ustiga bosing.</i>"
)

# ==========================================
# AQLLI ORQAGA (CONTEXT-AWARE BACK)
# ==========================================
@router.message(F.text == "🔙 Orqaga")
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    data = await state.get_data()

    # 1. Agar kitob qo‘shish bosqichida bo‘lsa
    if current_state in [PlanCreation.waiting_for_book_text.state, PlanCreation.waiting_for_book_photo.state]:
        plan_id = data.get('current_plan_id')
        child_age = data.get('current_child_age', 10)
        mode = data.get('current_mode', 'quick')
        await state.set_state(None)
        await message.answer("📚 <b>Kitoblar qo‘shish usulini tanlang:</b>", parse_mode="HTML", reply_markup=get_add_book_methods_keyboard(child_age, plan_id, mode))
        return

    # 2. Agar Bolaxona rejimida bo‘lsa
    if data.get('active_child_id'):
        await state.clear()
        await message.answer("🧒 <b>Bolaxona menyusidasiz.</b>", reply_markup=get_bolaxona_keyboard())
        return

    # 3. Boshqa barcha holatlarda FSM tozalanadi va bosh menyuga qaytariladi
    await state.clear()
    cursor.execute("SELECT role FROM Users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()

    if user and user[0] == 'parent':
        await message.answer("🚫 Amaliyot bekor qilindi. Bosh menyudasiz.", reply_markup=get_parent_keyboard())
    elif user and user[0] == 'child':
        await message.answer("🚫 Amaliyot bekor qilindi. Bosh menyudasiz.", reply_markup=get_child_keyboard())
    else:
        await message.answer("🚫 Amaliyot bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())

@router.message(CommandStart())
async def start_handler(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    # 1. Taklif havolasi orqali kirgan bo‘lsa
    if command.args:
        code = command.args
        cursor.execute("SELECT is_used FROM Invite_Links WHERE code = ?", (code,))
        link_row = cursor.fetchone()

        if link_row:
            if link_row[0] == 0:
                cursor.execute("UPDATE Invite_Links SET is_used = 1, used_by = ? WHERE code = ?", (user_id, code))

                if code.startswith("prnt_"):
                    cursor.execute("INSERT OR REPLACE INTO Users (user_id, role, name, is_approved) VALUES (?, 'parent', ?, 1)", (user_id, message.from_user.full_name))
                    conn.commit()
                    await message.answer(
                        f"🎉 <b>Xush kelibsiz!</b>\n\nSiz <b>Ota-ona</b> sifatida muvaffaqiyatli ro‘yxatdan o‘tdingiz!\n"
                        f"Farzandingiz profilingizga ulanishi uchun oilaviy kodingiz: <b>BLG-{str(user_id)[-4:]}</b>\n\n"
                        f"Quyidagi menyu orqali farzandingiz uchun birinchi kitobni qo‘shishingiz mumkin 👇",
                        parse_mode="HTML",
                        reply_markup=get_parent_keyboard()
                    )
                    return
                elif code.startswith("chld_"):
                    cursor.execute("INSERT OR REPLACE INTO Users (user_id, role, name, is_approved) VALUES (?, 'child', ?, 1)", (user_id, message.from_user.full_name))
                    conn.commit()
                    await message.answer(
                        "🦸‍♂️ <b>Xush kelibsiz, Qahramon!</b>\n\n"
                        "Siz <b>O‘quvchi</b> sifatida ro‘yxatdan o‘tdingiz!\n"
                        "Ota-onangiz bergan kodni kiriting (masalan, <code>BLG-1234</code>):",
                        parse_mode="HTML",
                        reply_markup=get_back_reply_keyboard()
                    )
                    await state.set_state(Registration.waiting_for_parent_code)
                    return
                else:
                    cursor.execute("INSERT OR REPLACE INTO Users (user_id, name, is_approved) VALUES (?, ?, 1)", (user_id, message.from_user.full_name))
                    conn.commit()
                    kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O‘quvchiman")]]
                    await message.answer(f"✅ <b>Taklifnoma qabul qilindi!</b>\n\n{WELCOME_TEXT}", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
                    return
            else:
                await message.answer("❌ <b>Bu taklif havolasi allaqachon ishlatilgan!</b>", parse_mode="HTML")
                return

    # 2. Ro‘yxatdan o‘tgan foydalanuvchini tekshirish
    cursor.execute("SELECT role, is_approved FROM Users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if user and user[1] == 1:
        if user[0] == 'parent':
            await message.answer("<b>Asosiy menyuga xush kelibsiz!</b> 👨‍👩‍👦", parse_mode="HTML", reply_markup=get_parent_keyboard())
            return
        elif user[0] == 'child':
            await message.answer("<b>Asosiy menyuga xush kelibsiz, Qahramon!</b> 🦸‍♂️🦸‍♀️", parse_mode="HTML", reply_markup=get_child_keyboard())
            return
        else:
            kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O‘quvchiman")]]
            await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
            return

    # 3. Havolasiz kirgan begonalar uchun yopiq
    await message.answer(CLOSED_BETA_TEXT, parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())

@router.message(F.text == "👨‍👩‍👦 Men Ota-onaman")
async def parent_handler(message: types.Message):
    cursor.execute("SELECT is_approved FROM Users WHERE user_id = ?", (message.from_user.id,))
    u = cursor.fetchone()
    if not u or u[0] != 1:
        await message.answer(CLOSED_BETA_TEXT, parse_mode="HTML")
        return

    cursor.execute("UPDATE Users SET role = 'parent' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer(f"Siz Ota-ona sifatida ro‘yxatdan o‘tdingiz! ✅\nFarzandingiz ulanishi uchun kodingiz: <b>BLG-{str(message.from_user.id)[-4:]}</b>", parse_mode="HTML", reply_markup=get_parent_keyboard())

@router.message(F.text.in_(["👦👧 Men O‘quvchiman", "👦👧 Men O'quvchiman"]))
async def child_handler(message: types.Message, state: FSMContext):
    cursor.execute("SELECT is_approved FROM Users WHERE user_id = ?", (message.from_user.id,))
    u = cursor.fetchone()
    if not u or u[0] != 1:
        await message.answer(CLOSED_BETA_TEXT, parse_mode="HTML")
        return

    cursor.execute("UPDATE Users SET role = 'child' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer("Iltimos, ota-onangiz bergan kodni kiriting (masalan, BLG-1234):", reply_markup=get_back_reply_keyboard())
    await state.set_state(Registration.waiting_for_parent_code)

@router.message(Registration.waiting_for_parent_code)
async def process_parent_code(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    if not code.startswith("BLG-"):
        await message.answer("Kod xato formatda! 'BLG-1234' ko‘rinishida kiriting.")
        return
    parent_suffix = code.replace("BLG-", "")
    cursor.execute("SELECT user_id FROM Users WHERE role = 'parent' AND CAST(user_id AS TEXT) LIKE ?", ('%' + parent_suffix,))
    parent = cursor.fetchone()
    if parent:
        try:
            cursor.execute("INSERT INTO Family_Link (parent_id, child_id) VALUES (?, ?)", (parent[0], message.from_user.id))
            conn.commit()
            await message.answer("Tabriklaymiz! Ota-onangiz bilan bog‘landingiz! 🎉", reply_markup=get_child_keyboard())

            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👦👧 Farzand yoshini kiritish", callback_data=f"set_age_{message.from_user.id}")]])
            await message.bot.send_message(parent[0], f"Farzandingiz ({message.from_user.full_name}) profilingizga ulandi! ✅\n\nAI unga moslashishi uchun iltimos, farzandingizning yoshini kiriting:", reply_markup=kb)
        except Exception:
            await message.answer("Siz allaqachon bu ota-onaga ulangansiz!", reply_markup=get_child_keyboard())
        await state.clear()
    else:
        await message.answer("Bunday kodga ega ota-ona topilmadi. Qaytadan kiriting:")
