import logging

from aiogram import F, Router
from aiogram.types import BufferedInputFile, Message

from app.ai.agent import Agent
from app.bot import keyboards
from app.bot.middlewares.ratelimit import SlidingWindow
from app.config import Settings
from app.rag.guard import REFUSAL, TopicGuard

log = logging.getLogger(__name__)
router = Router()


@router.message(F.text)
async def chat(
    message: Message, agent: Agent, guard: TopicGuard, ai_window: SlidingWindow, settings: Settings
):
    text = message.text.strip()
    if len(text) > settings.max_message_length:
        await message.answer(f"Xabar juda uzun (maks. {settings.max_message_length} belgi).")
        return
    if not await guard.is_on_topic(text):
        await message.answer(REFUSAL, reply_markup=keyboards.main_menu())
        return
    if not ai_window.allow(message.from_user.id):
        await message.answer(
            "Soatlik AI so'rovlar limiti tugadi. Tugmalar ishlayveradi 👇",
            reply_markup=keyboards.main_menu(),
        )
        return
    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        reply = await agent.reply(message.from_user.id, text)
    except Exception:
        log.exception("Agent xatosi")
        await message.answer("Xatolik yuz berdi, birozdan keyin qayta urinib ko'ring.")
        return
    for name, data in reply.files:
        await message.answer_document(BufferedInputFile(data, filename=name))
    await message.answer(reply.text, reply_markup=keyboards.main_menu())
