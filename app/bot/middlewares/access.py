import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

log = logging.getLogger(__name__)


class AccessMiddleware(BaseMiddleware):
    """Faqat ruxsat berilgan username/ID dagilar o'tadi, qolganlari jim tashlanadi."""

    def __init__(self, usernames: list[str], user_ids: list[int]):
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
            if user is not None and user.id not in self._denied:
                self._denied.add(user.id)
                log.info("Ruxsatsiz urinish: id=%s username=%s", user.id, user.username)
            return None
        return await handler(event, data)
