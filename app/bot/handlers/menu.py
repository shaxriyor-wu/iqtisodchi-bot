import contextlib

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, CallbackQuery, Message, ReplyKeyboardRemove
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
    "Statistikani tugmalardan ko'ring 👇"
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
    # ReplyKeyboardRemove faqat xabar bilan birga ishlaydi: qisqa xabar yuborib, darhol o'chiramiz
    note = await message.answer("✅ Raqam saqlandi.", reply_markup=ReplyKeyboardRemove())
    await panel.delete(message.bot, message.chat.id, note.message_id)
    await _show_menu(message, panel)


@router.callback_query(F.data.startswith("stat:"))
async def stat(call: CallbackQuery, sessions: async_sessionmaker, settings: Settings):
    action = call.data.split(":", 1)[1]
    if action == "csv":
        async with sessions() as s:
            rows = await ledger.history(s, call.from_user.id, 10)
        if not rows:
            await call.answer("Oxirgi 10 kunda xarajat yo'q.", show_alert=True)
            return
        await call.message.answer_document(
            BufferedInputFile(build_csv(rows, settings.tz), filename="xarajatlar_10_kun.csv")
        )
        await call.answer()
        return
    if action == "menu":
        text, markup = WELCOME, keyboards.main_menu()
    else:
        async with sessions() as s:
            if action == "recent":
                text = views.recent(await ledger.recent_expenses(s, call.from_user.id))
            else:
                ov = await ledger.get_overview(s, call.from_user.id)
                render = {
                    "today": views.today,
                    "avg": views.average,
                    "max": views.max_daily,
                    "month": views.month,
                    "cats": views.categories,
                }.get(action)
                if render is None:
                    await call.answer()
                    return
                text = render(ov)
        markup = keyboards.back_menu()
    try:
        await call.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        pass  # matn o'zgarmagan
    await call.answer()
