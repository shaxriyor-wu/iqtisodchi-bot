import contextlib
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, Message

from app.ai.agent import Agent
from app.bot import keyboards
from app.bot.middlewares.ratelimit import SlidingWindow
from app.bot.panel import Panel
from app.config import Settings
from app.rag.guard import REFUSAL, TopicGuard

log = logging.getLogger(__name__)
router = Router()

MAX_TEXT = 4000  # Telegram limiti 4096


@router.message(F.text)
async def chat(
    message: Message,
    agent: Agent,
    guard: TopicGuard,
    ai_window: SlidingWindow,
    settings: Settings,
    panel: Panel,
):
    bot, chat_id, text = message.bot, message.chat.id, message.text.strip()
    await panel.drop_previous(bot, chat_id)
    pending = await message.answer("⏳ Ishlayapman…")  # keyin shu xabar tahrirlanadi
    panel.remember(chat_id, pending.message_id)

    files: list[tuple[str, bytes]] = []
    if len(text) > settings.max_message_length:
        answer = f"Xabar juda uzun (maks. {settings.max_message_length} belgi)."
    elif not await guard.is_on_topic(text):
        answer = REFUSAL
    elif not ai_window.allow(message.from_user.id):
        answer = "Soatlik AI so'rovlar limiti tugadi. Tugmalar ishlayveradi 👇"
    else:
        await bot.send_chat_action(chat_id, "typing")
        try:
            reply = await agent.reply(message.from_user.id, text)
            answer, files = reply.text, reply.files
        except Exception:
            log.exception("Agent xatosi")
            answer = "Xatolik yuz berdi, birozdan keyin qayta urinib ko'ring."

    answer = answer[:MAX_TEXT]
    if files:
        # fayllar panel tepasida, javob matni ularning ostida bo'lsin
        await panel.drop_previous(bot, chat_id)
        for name, data in files:
            await message.answer_document(BufferedInputFile(data, filename=name))
        sent = await message.answer(answer, reply_markup=keyboards.main_menu())
        panel.remember(chat_id, sent.message_id)
    else:
        try:
            await pending.edit_text(answer, reply_markup=keyboards.main_menu())
        except TelegramBadRequest:
            sent = await message.answer(answer, reply_markup=keyboards.main_menu())
            panel.remember(chat_id, sent.message_id)
    with contextlib.suppress(Exception):
        await panel.discard_user_message(message)
