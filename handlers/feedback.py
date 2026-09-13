from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from config import OWNER_ID
from database import cursor
from keyboards import get_parent_keyboard, get_child_keyboard, get_back_reply_keyboard
from states import Feedback
from html import escape
import ai_service

router = Router()

@router.message(F.text == "📞 Qayta aloqa")
async def feedback_start(message: types.Message, state: FSMContext):
    await message.answer("✍️ <b>Qayta aloqa</b>\n\nBot haqida fikrlaringiz, takliflaringiz yoki xatoliklar bo‘lsa, shu yerda yozib qoldiring (rasm yoki video ham yuborishingiz mumkin).\n\nXabaringiz to‘g‘ridan-to‘g‘ri loyiha muallifiga yuboriladi.", parse_mode="HTML", reply_markup=get_back_reply_keyboard())
    await state.set_state(Feedback.waiting_for_message)

@router.message(Feedback.waiting_for_message)
async def feedback_receive(message: types.Message, state: FSMContext):
    if message.text == "🔙 Orqaga":
        await state.clear()
        cursor.execute("SELECT role FROM Users WHERE user_id = ?", (message.from_user.id,))
        user = cursor.fetchone()
        kb = get_parent_keyboard() if user and user[0] == 'parent' else get_child_keyboard()
        await message.answer("🚫 Bekor qilindi.", reply_markup=kb)
        return
        
    if OWNER_ID == 0:
        await message.answer("⚠️ Muallifga xabar yuborish sozlanmagan (OWNER_ID kiritilmagan).")
        await state.clear()
        return
        
    cursor.execute("SELECT role FROM Users WHERE user_id = ?", (message.from_user.id,))
    role_row = cursor.fetchone()
    role = role_row[0] if role_row else "Noma'lum"
    
    user_info = f"📩 <b>YANGI XABAR (Qayta aloqa)</b>\n\n"
    user_info += f"👤 <b>Yuboruvchi:</b> {message.from_user.full_name}\n"
    user_info += f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
    user_info += f"🎭 <b>Rol:</b> {role}\n\n"
    user_info += f"<i>Javob yozish uchun:</i>\n<code>/reply {message.from_user.id} matn</code>"
    
    try:
        await message.bot.send_message(OWNER_ID, user_info, parse_mode="HTML")
        await message.copy_to(OWNER_ID)
        
        kb = get_parent_keyboard() if role == 'parent' else get_child_keyboard()
        # Oddiy savolga AI darrov javob beradi; nozik murojaat muallifga qoladi
        # (ega qarori, 2026-09-13 — «aralash» yo‘l). Rasm/video — faqat muallifga.
        ai = None
        if message.text and ai_service.support_quota_ok(message.from_user.id):
            ai = await ai_service.answer_support(message.text, role)
        if ai and ai.get("kind") == "simple" and ai.get("answer"):
            await message.answer(
                "💬 " + escape(ai["answer"]) + "\n\n<i>Savolingiz muallifga ham yetkazildi.</i>",
                parse_mode="HTML", reply_markup=kb)
            await message.bot.send_message(
                OWNER_ID, "🤖 <b>AI javob berdi:</b>\n\n" + escape(ai["answer"]), parse_mode="HTML")
        else:
            await message.answer(
                "✅ Xabaringiz muallifga yetkazildi, tez orada javob beramiz. Fikringiz uchun tashakkur!",
                reply_markup=kb)
            if message.text:
                await message.bot.send_message(
                    OWNER_ID, "⏳ <b>Javobingizni kutyapti</b> — AI javob bermadi.", parse_mode="HTML")
    except Exception:
        await message.answer("❌ Xabar yuborishda xatolik yuz berdi.")
        
    await state.clear()
