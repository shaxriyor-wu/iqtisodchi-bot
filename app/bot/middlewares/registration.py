from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bot import keyboards
from app.services import ledger

ASK_PHONE = (
    "Botdan foydalanish uchun avval telefon raqamingizni ulashing.\n"
    "Pastdagi «📱 Raqamni ulashish» tugmasini bosing."
)


class RegistrationMiddleware(BaseMiddleware):
    """Telefon raqam ulashmagan foydalanuvchini faqat o'z kontaktini yuborishga ruxsat beradi."""

    def __init__(self, sessions: async_sessionmaker):
        self._sessions = sessions

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        user = event.from_user
        if user is None:
            return None
        async with self._sessions() as s:
            registered = await ledger.is_registered(s, user.id)
        if registered or (isinstance(event, Message) and event.contact):
            return await handler(event, data)
        if isinstance(event, CallbackQuery):
            await event.answer("Avval telefon raqamingizni ulashing.", show_alert=True)
        else:
            await event.answer(ASK_PHONE, reply_markup=keyboards.share_phone())
        return None
