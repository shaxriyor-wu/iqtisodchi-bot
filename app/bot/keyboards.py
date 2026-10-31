from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

BUTTONS = {
    "📅 Bugungi limit": "today",
    "📈 O'rtacha kunlik": "avg",
    "🔝 Maksimum kunlik": "max",
    "💰 Oylik qolgan": "month",
    "🗂 Bo'limlar": "cats",
    "🕘 Oxirgi xarajatlar": "recent",
    "📄 CSV (10 kun)": "csv",
}


def main_menu() -> ReplyKeyboardMarkup:
    """Doimiy reply klaviatura: foydalanuvchi yopmaguncha pastda turadi."""
    kb = ReplyKeyboardBuilder()
    for text in BUTTONS:
        kb.button(text=text)
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True, is_persistent=True)


def share_phone() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
