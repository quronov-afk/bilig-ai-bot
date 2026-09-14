from aiogram import Router, types, F
from aiogram.filters import StateFilter

from keyboards import OPEN_APP_TEXT, get_open_app_keyboard

# Eng oxirgi router: boshqa hech bir handler ushlamagan oddiy xabarga
# ilovani ochish tugmasi bilan javob beradi (ega qarori, 2026-09-14 —
# bot menyusi olib tashlandi). Kutilayotgan holatlarga (qayta aloqa,
# kod kiritish) tegmaydi.
router = Router()


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def open_app_hint(message: types.Message):
    await message.answer(OPEN_APP_TEXT, parse_mode="HTML", reply_markup=get_open_app_keyboard())
