import uuid
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID
from database import conn, cursor, generate_admin_stats_text
from keyboards import get_parent_keyboard, get_child_keyboard

router = Router()

@router.message(Command("stats"))
@router.message(Command("admin"))
async def admin_stats_handler(message: types.Message):
    user_id = message.from_user.id
    if OWNER_ID != 0 and user_id != OWNER_ID:
        return  

    stats_text = generate_admin_stats_text()
    if OWNER_ID == 0:
        stats_text += f"\n\n⚙️ <i>Eslatma: Xavfsizlik uchun Render.com'da Environment Variables qismiga <b>OWNER_ID={user_id}</b> o‘zgaruvchisini qo‘shing.</i>"

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
        stats_text += f"\n\n⚙️ <i>Eslatma: Xavfsizlik uchun Render.com'da Environment Variables qismiga <b>OWNER_ID={user_id}</b> o‘zgaruvchisini qo‘shing.</i>"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh_stats")]
    ])
    
    try:
        await callback.message.edit_text(stats_text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass
    await callback.answer("Statistika yangilandi!")

@router.message(Command("invite"))
async def generate_invite_package(message: types.Message):
    if OWNER_ID != 0 and message.from_user.id != OWNER_ID:
        return
        
    parent_token = f"prnt_{uuid.uuid4().hex[:8]}"
    child_token = f"chld_{uuid.uuid4().hex[:8]}"
    
    cursor.execute("INSERT INTO Invite_Links (code) VALUES (?)", (parent_token,))
    cursor.execute("INSERT INTO Invite_Links (code) VALUES (?)", (child_token,))
    conn.commit()
    
    bot_info = await message.bot.get_me()
    parent_link = f"https://t.me/{bot_info.username}?start={parent_token}"
    child_link = f"https://t.me/{bot_info.username}?start={child_token}"
    
    invitation_text = (
        f"🌟 <b>BILIG AI — Kitobxonlik sari intellektual sayohat!</b>\n\n"
        f"Assalomu alaykum! Siz bolalarda kitob mutolaasiga mehr uyg‘otuvchi <b>Bilig AI</b> platformasining yopiq sinov dasturiga taklif qilindingiz.\n\n"
        f"🤖 <b>Bilig AI nima bera oladi?</b>\n"
        f"• 📚 O‘qilgan sahifani <b>AI Vision</b> orqali tekshirish va rag‘batlantirish;\n"
        f"• 🎙 Bolaning ovozli fikrini <b>AI ustoz</b> sifatida tahlil qilish;\n"
        f"• 🧠 Mutolaa qilingan kitoblar bo‘yicha qiziqarli <b>AI testlar</b> tuzish;\n"
        f"• 🟡 Har bir sahifa uchun <b>Bilig tangalari</b>, streak va rag‘batlantiruvchi sovg‘alar.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>TIZIMGA KIRISH YO‘RIQNOMASI:</b>\n\n"
        f"1️⃣ <b>OTA-ONA UCHUN:</b>\n"
        f"Avval ota-ona quyidagi havola orqali botga kiradi va mutolaa rejasini tuzadi:\n"
        f"👉 <code>{parent_link}</code>\n\n"
        f"2️⃣ <b>FARZAND UCHUN:</b>\n"
        f"So‘ngra farzand o‘z telefonida ushbu havola orqali botga ulanadi:\n"
        f"👉 <code>{child_link}</code>\n\n"
        f"<i>⚠️ Eslatma: Har bir havola bir martalik bo‘lib, faqat bitta hisob (account) uchun mo‘ljallangan.</i>"
    )
    
    await message.answer(invitation_text, parse_mode="HTML")

# ==========================================
# OMMAVIY XABAR YUBORISH VA MENYULARNI YANGILASH
# ==========================================
@router.message(Command("send"))
@router.message(Command("broadcast"))
async def broadcast_message_handler(message: types.Message, command: CommandObject):
    if OWNER_ID != 0 and message.from_user.id != OWNER_ID:
        return
        
    if not command.args:
        await message.answer(
            "⚠️ <b>Foydalanish:</b>\n<code>/send Sizning xabaringiz...</code>\n\n"
            "<i>Ushbu buyruq barcha foydalanuvchilarga xabarni yuboradi va ularning menyularini yangilaydi.</i>",
            parse_mode="HTML"
        )
        return
        
    broadcast_text = command.args
    status_msg = await message.answer("⏳ <i>Barcha foydalanuvchilarga xabar yetkazilmoqda...</i>", parse_mode="HTML")
    
    cursor.execute("SELECT user_id, role FROM Users WHERE is_approved = 1")
    users = cursor.fetchall()
    
    success_count = 0
    fail_count = 0
    
    for u in users:
        u_id, u_role = u[0], u[1]
        try:
            if u_role == 'parent':
                markup = get_parent_keyboard()
            elif u_role == 'child':
                markup = get_child_keyboard()
            else:
                markup = None
                
            await message.bot.send_message(
                u_id,
                f"📢 <b>BILIG AI BILDIRISHNOMASI:</b>\n\n{broadcast_text}",
                parse_mode="HTML",
                reply_markup=markup
            )
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail_count += 1

    await status_msg.edit_text(
        f"✅ <b>Ommaviy xabar yuborildi!</b>\n\n"
        f"📨 Yetkazildi: <b>{success_count} ta</b> foydalanuvchiga\n"
        f"⚠️ Yetib bormadi (botni bloklaganlar): <b>{fail_count} ta</b>\n\n"
        f"<i>Barcha faol foydalanuvchilarning bosh menyusi eng so‘nggi holatga yangilandi! 🚀</i>",
        parse_mode="HTML"
    )

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
