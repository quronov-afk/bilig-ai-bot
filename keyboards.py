from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_parent_keyboard():
    kb = [
        [KeyboardButton(text="📝 Mutolaa rejasini tuzish"), KeyboardButton(text="📚 Faol rejalarim")],
        [KeyboardButton(text="📊 Farzandim natijalari"), KeyboardButton(text="🛒 Do‘kon")],
        [KeyboardButton(text="📞 Qayta aloqa")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_child_keyboard():
    kb = [
        [KeyboardButton(text="📖 Kitob o'qish")],
        [KeyboardButton(text="🎁 Sovrinlarim"), KeyboardButton(text="🛒 Do‘kon")],
        [KeyboardButton(text="🏆 Reyting")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_back_reply_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Orqaga")]], resize_keyboard=True)

def get_add_book_keyboard():
    kb = [
        [InlineKeyboardButton(text="👶 Yosh bo'yicha tavsiyalar", callback_data="add_book_age")],
        [InlineKeyboardButton(text="✍️ Matn orqali qo'shish", callback_data="add_book_text")],
        [InlineKeyboardButton(text="📸 Rasm orqali (AI Vision)", callback_data="add_book_photo")],
        [InlineKeyboardButton(text="✅ Rejani yakunlash", callback_data="finish_plan")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_rewards_main_keyboard():
    kb = [
        [InlineKeyboardButton(text="🔅 Bilig kursini belgilash", callback_data="rewards_bilig_rate")],
        [InlineKeyboardButton(text="🛍 Sovg'alar do'konini tahrirlash", callback_data="rewards_store_edit")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_bilig_rate_inline_keyboard():
    kb = [
        [InlineKeyboardButton(text="🔅 500 so'm", callback_data="rate_500"),
         InlineKeyboardButton(text="🔅 1,000 so'm", callback_data="rate_1000")],
        [InlineKeyboardButton(text="🔅 5,000 so'm", callback_data="rate_5000"),
         InlineKeyboardButton(text="🔅 10,000 so'm", callback_data="rate_10000")],
        [InlineKeyboardButton(text="✍️ Boshqa summa kiritish", callback_data="rate_custom")],
        [InlineKeyboardButton(text="🚫 Pul bilan rag'batlantirmaslik", callback_data="rate_0")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="rewards_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
