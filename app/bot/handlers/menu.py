import contextlib

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bot import keyboards, views
from app.bot.panel import Panel
from app.config import Settings
from app.services import ledger
from app.services.export import build_csv

router = Router()

WELCOME = (
    "Salom! Men shaxsiy iqtisodchingizman.\n\n"
    "Oddiy matn yozing:\n"
    "• «oyiga 2 mln so'm sarflay olaman»\n"
    "• «taksiga 15 ming berdim»\n"
    "• «transportga oyiga 300 ming limit qo'y»\n\n"
    "Statistikani pastdagi tugmalardan ko'ring 👇"
)


@router.message(Command("start", "menu"))
async def start(message: Message, sessions: async_sessionmaker, panel: Panel):
    async with sessions() as s:
        await ledger.ensure_user(s, message.from_user.id)
    await _show_menu(message, panel)


@router.message(Command("clear"))
async def clear(message: Message, panel: Panel):
    """Oxirgi ~1000 ta xabarni o'chirishga urinadi (Telegram faqat 48 soatdan yangilarini ruxsat beradi)."""
    chat_id, top = message.chat.id, message.message_id
    for hi in range(top, max(top - 1000, 0), -100):
        ids = list(range(hi, max(hi - 100, 0), -1))
        with contextlib.suppress(TelegramBadRequest):
            await message.bot.delete_messages(chat_id, ids)
    panel.forget(chat_id)
    sent = await message.bot.send_message(chat_id, WELCOME, reply_markup=keyboards.main_menu())
    panel.remember(chat_id, sent.message_id)


async def _show_menu(message: Message, panel: Panel) -> None:
    await panel.drop_previous(message.bot, message.chat.id)
    sent = await message.answer(WELCOME, reply_markup=keyboards.main_menu())
    panel.remember(message.chat.id, sent.message_id)
    await panel.discard_user_message(message)


@router.message(F.contact)
async def contact(message: Message, sessions: async_sessionmaker, panel: Panel):
    c = message.contact
    # faqat o'z raqami: boshqa odamning kontaktini yuborib aldab bo'lmaydi
    if c.user_id != message.from_user.id:
        await message.answer(
            "Iltimos, o'zingizning raqamingizni tugma orqali ulashing.",
            reply_markup=keyboards.share_phone(),
        )
        return
    async with sessions() as s:
        try:
            await ledger.register_phone(s, message.from_user.id, c.phone_number)
        except ledger.LedgerError as e:
            await message.answer(str(e))
            return
    # share_phone klaviaturasi _show_menu'dagi doimiy menyu bilan almashadi
    await _show_menu(message, panel)


@router.message(F.text.in_(keyboards.BUTTONS))
async def stat(
    message: Message,
    sessions: async_sessionmaker,
    settings: Settings,
    panel: Panel,
):
    action = keyboards.BUTTONS[message.text]
    bot, chat_id, user_id = message.bot, message.chat.id, message.from_user.id
    await panel.drop_previous(bot, chat_id)
    if action == "csv":
        async with sessions() as s:
            rows = await ledger.history(s, user_id, 10)
        if rows:
            await message.answer_document(
                BufferedInputFile(build_csv(rows, settings.tz), filename="xarajatlar_10_kun.csv")
            )
            await panel.discard_user_message(message)
            return
        text = "Oxirgi 10 kunda xarajat yo'q."
    else:
        async with sessions() as s:
            if action == "recent":
                text = views.recent(await ledger.recent_expenses(s, user_id))
            else:
                ov = await ledger.get_overview(s, user_id)
                text = {
                    "today": views.today,
                    "avg": views.average,
                    "max": views.max_daily,
                    "month": views.month,
                    "cats": views.categories,
                }[action](ov)
    sent = await message.answer(text, reply_markup=keyboards.main_menu())
    panel.remember(chat_id, sent.message_id)
    await panel.discard_user_message(message)
