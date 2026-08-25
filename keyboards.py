from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_parent_keyboard():
    kb = [
        [KeyboardButton(text="➕ Kitob qo‘shish"), KeyboardButton(text="📚 Faol rejalar")],
        [KeyboardButton(text="📊 Farzandim natijalari"), KeyboardButton(text="🛒 Do‘kon")],
        [KeyboardButton(text="🧒 Bolaxona"), KeyboardButton(text="📞 Qayta aloqa")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_child_keyboard():
    kb = [
        [KeyboardButton(text="📖 Kitob o‘qish")],
        [KeyboardButton(text="🎁 Sovrinlarim"), KeyboardButton(text="🛒 Do‘kon")],
        [KeyboardButton(text="🏆 Reyting")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_bolaxona_keyboard():
    kb = [
        [KeyboardButton(text="📖 Kitob o‘qish")],
        [KeyboardButton(text="🎁 Sovrinlarim"), KeyboardButton(text="🛒 Do‘kon")],
        [KeyboardButton(text="🏆 Reyting")],
        [KeyboardButton(text="👨‍👩‍👦 Ota-ona kabinetiga qaytish")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_back_reply_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔙 Orqaga")]], resize_keyboard=True)

def get_skip_prize_keyboard():
    kb = [
        [KeyboardButton(text="⏭ O‘tkazib yuborish")],
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_plan_mode_keyboard(child_id: int):
    kb = [
        [InlineKeyboardButton(text="⚡️ Tezkor mutolaa (Bitta kitob)", callback_data=f"mode_quick_{child_id}")],
        [InlineKeyboardButton(text="🎯 Mutolaa marafoni (Katta reja)", callback_data=f"mode_marathon_{child_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="addbook_select_child")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_add_book_methods_keyboard(child_age: int, plan_id: int, mode: str = "quick"):
    kb = [
        [InlineKeyboardButton(text=f"👶 Tavsiya etilgan kitoblar ({child_age} yosh)", callback_data=f"addmethod_rec_{plan_id}_{mode}")],
        [InlineKeyboardButton(text="✍️ Kitob nomini yozish", callback_data=f"addmethod_text_{plan_id}_{mode}")],
        [InlineKeyboardButton(text="📸 Muqovani rasmga olish (AI Vision)", callback_data=f"addmethod_photo_{plan_id}_{mode}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"addmethod_back_{plan_id}_{mode}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_marathon_manage_keyboard(plan_id: int):
    kb = [
        [InlineKeyboardButton(text="➕ Yana kitob qo‘shish", callback_data=f"addmore_marathon_{plan_id}")],
        [InlineKeyboardButton(text="✅ Marafonni yakunlash", callback_data="finish_marathon")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_rewards_main_keyboard():
    kb = [
        [InlineKeyboardButton(text="🔅 Bilig kursini belgilash", callback_data="rewards_bilig_rate")],
        [InlineKeyboardButton(text="🛍 Sovg‘alar do‘konini tahrirlash", callback_data="rewards_store_edit")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_bilig_rate_inline_keyboard():
    kb = [
        [InlineKeyboardButton(text="🔅 500 so‘m", callback_data="rate_500"),
         InlineKeyboardButton(text="🔅 1 000 so‘m", callback_data="rate_1000")],
        [InlineKeyboardButton(text="🔅 5 000 so‘m", callback_data="rate_5000"),
         InlineKeyboardButton(text="🔅 10 000 so‘m", callback_data="rate_10000")],
        [InlineKeyboardButton(text="✍️ Boshqa summa kiritish", callback_data="rate_custom")],
        [InlineKeyboardButton(text="🚫 Pul bilan rag‘batlantirmaslik", callback_data="rate_0")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="rewards_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_plan_edit_keyboard(plan_id: int):
    kb = [
        [InlineKeyboardButton(text="📝 Nomini o‘zgartirish", callback_data=f"editplanname_{plan_id}")],
        [InlineKeyboardButton(text="🎁 Marra sovrinini o‘zgartirish", callback_data=f"editplanprize_{plan_id}")],
        [InlineKeyboardButton(text="👦 Farzandni o‘zgartirish", callback_data=f"editplanchild_{plan_id}")],
        [InlineKeyboardButton(text="🔙 Rejaga qaytish", callback_data=f"showplan_{plan_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
