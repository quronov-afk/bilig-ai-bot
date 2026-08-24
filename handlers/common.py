from aiogram import Router, types, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import WELCOME_TEXT, ACCESS_CODE
from database import conn, cursor
from keyboards import get_parent_keyboard, get_child_keyboard, get_back_reply_keyboard
from states import Access, Registration

router = Router()

@router.message(F.text == "🔙 Orqaga")
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    cursor.execute("SELECT role FROM Users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    if user and user[0] == 'parent':
        await message.answer("🚫 Amaliyot bekor qilindi. Bosh menyudasiz.", reply_markup=get_parent_keyboard())
    elif user and user[0] == 'child':
        await message.answer("🚫 Amaliyot bekor qilindi. Bosh menyudasiz.", reply_markup=get_child_keyboard())
    else:
        kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O'quvchiman")]]
        await message.answer("🚫 Amaliyot bekor qilindi.", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@router.message(CommandStart())
async def start_handler(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
    
    # Deep-link orqali taklif tekshiruvi
    if command.args:
        code = command.args
        cursor.execute("SELECT is_used FROM Invite_Links WHERE code = ?", (code,))
        link_row = cursor.fetchone()
        if link_row:
            if link_row[0] == 0:
                cursor.execute("UPDATE Invite_Links SET is_used = 1, used_by = ? WHERE code = ?", (message.from_user.id, code))
                cursor.execute("INSERT OR IGNORE INTO Users (user_id, name, is_approved) VALUES (?, ?, 1)", (message.from_user.id, message.from_user.full_name))
                cursor.execute("UPDATE Users SET is_approved = 1 WHERE user_id = ?", (message.from_user.id,))
                conn.commit()
                
                kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O'quvchiman")]]
                await message.answer(f"✅ <b>Maxsus taklif havolasi qabul qilindi!</b>\n\n{WELCOME_TEXT}", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
                return
            else:
                await message.answer("❌ Bu taklif havolasi allaqachon ishlatilgan!")
                return

    cursor.execute("SELECT role, is_approved FROM Users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    
    if user and user[1] == 1:
        if user[0] == 'parent':
            await message.answer("<b>Asosiy menyuga xush kelibsiz!</b> 👨‍👩‍👦", parse_mode="HTML", reply_markup=get_parent_keyboard())
        elif user[0] == 'child':
            await message.answer("<b>Asosiy menyuga xush kelibsiz, Qahramon!</b> 🦸‍♂️🦸‍♀️", parse_mode="HTML", reply_markup=get_child_keyboard())
        else:
            kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O'quvchiman")]]
            await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
        return

    cursor.execute("INSERT OR IGNORE INTO Users (user_id, name, is_approved) VALUES (?, ?, 0)", (message.from_user.id, message.from_user.full_name))
    conn.commit()
    
    await message.answer(f"👋 <b>Bilig AI yopiq test rejimida ishlamoqda!</b>\n\nBotdan foydalanish uchun maxsus ruxsat kodingizni kiriting:", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Access.waiting_for_code)

@router.message(Access.waiting_for_code)
async def process_access_code(message: types.Message, state: FSMContext):
    if message.text.strip() == ACCESS_CODE:
        cursor.execute("UPDATE Users SET is_approved = 1 WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
        await state.clear()
        kb = [[KeyboardButton(text="👨‍👩‍👦 Men Ota-onaman")], [KeyboardButton(text="👦👧 Men O'quvchiman")]]
        await message.answer(WELCOME_TEXT, parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))
    else:
        await message.answer("❌ Noto'g'ri kod! Iltimos, qaytadan kiriting:")

@router.message(F.text == "👨‍👩‍👦 Men Ota-onaman")
async def parent_handler(message: types.Message):
    cursor.execute("UPDATE Users SET role = 'parent' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer(f"Siz Ota-ona sifatida ro'yxatdan o'tdingiz! ✅\nFarzandingiz ulanishi uchun kodingiz: <b>BLG-{str(message.from_user.id)[-4:]}</b>", parse_mode="HTML", reply_markup=get_parent_keyboard())

@router.message(F.text == "👦👧 Men O'quvchiman")
async def child_handler(message: types.Message, state: FSMContext):
    cursor.execute("UPDATE Users SET role = 'child' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    await message.answer("Iltimos, ota-onangiz bergan kodni kiriting (masalan, BLG-1234):", reply_markup=get_back_reply_keyboard())
    await state.set_state(Registration.waiting_for_parent_code)

@router.message(Registration.waiting_for_parent_code)
async def process_parent_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if not code.startswith("BLG-"):
        await message.answer("Kod xato formatda! 'BLG-1234' ko'rinishida kiriting.")
        return
    parent_suffix = code.replace("BLG-", "")
    cursor.execute("SELECT user_id FROM Users WHERE role = 'parent' AND CAST(user_id AS TEXT) LIKE ?", ('%' + parent_suffix,))
    parent = cursor.fetchone()
    if parent:
        try:
            cursor.execute("INSERT INTO Family_Link (parent_id, child_id) VALUES (?, ?)", (parent[0], message.from_user.id))
            conn.commit()
            await message.answer("Tabriklaymiz! Ota-onangiz bilan bog'landingiz! 🎉", reply_markup=get_child_keyboard())
            
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="👦👧 Farzand yoshini kiritish", callback_data=f"set_age_{message.from_user.id}")]])
            await message.bot.send_message(parent[0], f"Farzandingiz ({message.from_user.full_name}) profilingizga ulandi! ✅\n\nAI unga moslashishi uchun iltimos, farzandingizning yoshini kiriting:", reply_markup=kb)
        except Exception:
            await message.answer("Siz allaqachon bu ota-onaga ulangansiz!", reply_markup=get_child_keyboard())
        await state.clear()
    else:
        await message.answer("Bunday kodga ega ota-ona topilmadi. Qaytadan kiriting:")
