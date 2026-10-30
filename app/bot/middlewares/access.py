import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

log = logging.getLogger(__name__)


class AccessMiddleware(BaseMiddleware):
    """Faqat ruxsat berilgan username/ID dagilar o'tadi, qolganlari jim tashlanadi."""

    REPLY_COOLDOWN = 60.0  # bir odamga ko'pi bilan daqiqada bir marta javob (spamga qarshi)

    def __init__(self, usernames: list[str], user_ids: list[int], contact: str = ""):
        self._contact = contact.lstrip("@")
        self._last_reply: dict[int, float] = {}
        self._usernames = {u.lower() for u in usernames}
        self._ids = set(user_ids)
        self._denied: set[int] = set()  # logni to'ldirib yubormaslik uchun
        if not (self._usernames or self._ids):
            log.warning(
                "ALLOWED_USERNAMES va ALLOWED_USER_IDS bo'sh: bot hech kimga javob bermaydi"
            )

    def _allowed(self, user) -> bool:
        return user.id in self._ids or (
            user.username is not None and user.username.lower() in self._usernames
        )

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        user = event.from_user
        if user is None or not self._allowed(user):
            if user is not None:
                if user.id not in self._denied:
                    self._denied.add(user.id)
                    log.info("Ruxsatsiz urinish: id=%s username=%s", user.id, user.username)
                await self._notify(event, user)
            return None
        return await handler(event, data)

    async def _notify(self, event: Message | CallbackQuery, user) -> None:
        now = time.monotonic()
        if now - self._last_reply.get(user.id, -self.REPLY_COOLDOWN) < self.REPLY_COOLDOWN:
            return
        self._last_reply[user.id] = now
        text = "Bu botdan foydalanish uchun ruxsat kerak."
        if self._contact:
            text += f"\nRuxsat olish uchun @{self._contact} ga bog'laning."
        text += f"\n\nSizning ID: {user.id}"
        if isinstance(event, CallbackQuery):
            await event.answer(text, show_alert=True)
        else:
            await event.answer(text)
