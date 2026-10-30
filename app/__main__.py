import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.ai.agent import Agent
from app.bot.handlers import build_router
from app.bot.middlewares.access import AccessMiddleware
from app.bot.middlewares.ratelimit import RateLimitMiddleware, SlidingWindow
from app.bot.middlewares.registration import RegistrationMiddleware
from app.config import get_settings
from app.db.base import SessionFactory, engine
from app.rag.embeddings import make_embedder
from app.rag.guard import TopicGuard


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    embedder = make_embedder(settings)
    guard = TopicGuard(settings, SessionFactory, embedder)
    await guard.index()

    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    # tartib muhim: ruxsat -> rate limit (DB'ga yetmasdan) -> ro'yxatdan o'tish tekshiruvi
    for observer in (dp.message, dp.callback_query):
        observer.middleware(AccessMiddleware(settings.allowed_usernames, settings.allowed_user_ids))
        observer.middleware(RateLimitMiddleware(settings.rate_limit_per_second))
        observer.middleware(RegistrationMiddleware(SessionFactory))
    dp.include_router(build_router())

    try:
        await dp.start_polling(
            bot,
            sessions=SessionFactory,
            settings=settings,
            guard=guard,
            agent=Agent(settings, SessionFactory),
            ai_window=SlidingWindow(settings.rate_limit_ai_per_hour, 3600),
        )
    finally:
        if embedder:
            await embedder.close()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
