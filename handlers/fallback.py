from aiogram import Router, types, F
from aiogram.filters import StateFilter

from handlers.common import send_open_app

# Eng oxirgi router: boshqa hech bir handler ushlamagan oddiy xabarga
# ilovani ochish tugmasi bilan javob beradi (ega qarori, 2026-09-14 —
# bot menyusi olib tashlandi). Kutilayotgan holatlarga (qayta aloqa,
# kod kiritish) tegmaydi.
router = Router()


@router.message(StateFilter(None), F.text, ~F.text.startswith("/"))
async def open_app_hint(message: types.Message):
    # send_open_app eski pastki tugmalarni ham tozalaydi (masalan, bola
    # hali ham eski "📚 Faol rejalar" tugmasini bossa — shu yerga tushadi).
    await send_open_app(message)
