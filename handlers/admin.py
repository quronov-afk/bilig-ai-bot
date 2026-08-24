import uuid
from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID
from database import conn, cursor, generate_admin_stats_text

router = Router()

@router.message(Command("stats"))
@router.message(Command("admin"))
async def admin_stats_handler(message: types.Message):
    user_id = message.from_user.id
    if OWNER_ID != 0 and user_id != OWNER_ID:
        return  

    stats_text = generate_admin_stats_text()
    if OWNER_ID == 0:
        stats_text += f"\n\n⚙️ <i>Eslatma: Xavfsizlik uchun Render.com'da Environment Variables qismiga <b>OWNER_ID={user_id}</b> o'zgaruvchisini qo'shing.</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh_stats")]
    ])
    await message.answer(stats_text, parse_mode="HTML", reply_markup=kb)

@router.callback_query(F.data == "admin_refresh_stats")
async def refresh_admin_stats(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if OWNER_ID != 0 and user_id != OWNER_ID:
        await callback.answer("Ruxsat berilmagan!", show_alert=True)
        return
        
    stats_text = generate_admin_stats_text()
    if OWNER_ID == 0:
        stats_text += f"\n\n⚙️ <i>Eslatma: Xavfsizlik uchun Render.com'da Environment Variables qismiga <b>OWNER_ID={user_id}</b> o'zgaruvchisini qo'shing.</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh_stats")]
    ])
    
    try:
        await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer("Statistika yangilandi!")

@router.message(Command("invite"))
async def generate_invite_link(message: types.Message):
    if OWNER_ID != 0 and message.from_user.id != OWNER_ID:
        return
        
    code = str(uuid.uuid4())[:8]
    cursor.execute("INSERT INTO Invite_Links (code) VALUES (?)", (code,))
    conn.commit()
    
    bot_info = await message.bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"
    
    await message.answer(f"🔗 <b>Bir martalik taklif havolasi yaratildi:</b>\n\n<code>{link}</code>\n\n<i>Ushbu havola orqali faqat 1 kishi ro'yxatdan o'ta oladi.</i>", parse_mode="HTML")

@router.message(Command("reply"))
async def admin_reply_handler(message: types.Message, command: CommandObject):
    if OWNER_ID != 0 and message.from_user.id != OWNER_ID:
        return
        
    if not command.args:
        await message.answer("⚠️ <b>Foydalanish:</b> /reply <foydalanuvchi_id> <matn>", parse_mode="HTML")
        return
        
    parts = command.args.split(" ", 1)
    if len(parts) < 2:
        await message.answer("⚠️ <b>Foydalanish:</b> /reply <foydalanuvchi_id> <matn>", parse_mode="HTML")
        return
        
    user_id, text = parts[0], parts[1]
    
    try:
        await message.bot.send_message(int(user_id), f"👨‍💻 <b>Admindan javob:</b>\n\n{text}", parse_mode="HTML")
        await message.answer("✅ Javob muvaffaqiyatli yuborildi!")
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}")
