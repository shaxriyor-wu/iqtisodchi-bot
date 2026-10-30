from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

BUTTONS = [
    ("📅 Bugungi limit", "stat:today"),
    ("📈 O'rtacha kunlik", "stat:avg"),
    ("🔝 Maksimum kunlik", "stat:max"),
    ("💰 Oylik qolgan", "stat:month"),
    ("🗂 Bo'limlar", "stat:cats"),
    ("🕘 Oxirgi xarajatlar", "stat:recent"),
    ("📄 CSV (10 kun)", "stat:csv"),
]


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for text, data in BUTTONS:
        kb.button(text=text, callback_data=data)
    kb.adjust(2)
    return kb.as_markup()


def back_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Menyu", callback_data="stat:menu")
    return kb.as_markup()


def share_phone() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
