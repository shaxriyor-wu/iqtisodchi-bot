import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class SlidingWindow:
    """Foydalanuvchi bo'yicha: `window` soniyada ko'pi bilan `limit` ta hodisa."""

    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self._hits: dict[int, deque[float]] = defaultdict(deque)

    def allow(self, key: int, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self._hits[key]
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


class RateLimitMiddleware(BaseMiddleware):
    """Soniyasiga `per_second` tadan ortiq so'rovni jim tashlaydi."""

    def __init__(self, per_second: int):
        self._window = SlidingWindow(per_second, 1.0)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: dict[str, Any],
    ) -> Any:
        user = event.from_user
        if user is None or not self._window.allow(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer()  # tugma "aylanib" qolmasligi uchun
            return None
        return await handler(event, data)
