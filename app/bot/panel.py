"""Chatni toza saqlash: har chatda faqat oxirgi bot paneli qoladi."""

import contextlib

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message


class Panel:
    def __init__(self, delete_user_messages: bool = True):
        self._delete_user_messages = delete_user_messages
        self._last: dict[int, int] = {}  # chat_id -> oxirgi panel xabari

    def remember(self, chat_id: int, message_id: int) -> None:
        self._last[chat_id] = message_id

    def forget(self, chat_id: int) -> None:
        self._last.pop(chat_id, None)

    async def delete(self, bot: Bot, chat_id: int, message_id: int) -> None:
        # 48 soatdan eski yoki allaqachon o'chirilgan xabarlar xato beradi: e'tibor bermaymiz
        with contextlib.suppress(TelegramBadRequest, TelegramForbiddenError):
            await bot.delete_message(chat_id, message_id)

    async def drop_previous(self, bot: Bot, chat_id: int) -> None:
        if (prev := self._last.pop(chat_id, None)) is not None:
            await self.delete(bot, chat_id, prev)

    async def discard_user_message(self, message: Message) -> None:
        if self._delete_user_messages:
            await self.delete(message.bot, message.chat.id, message.message_id)
