from unittest.mock import AsyncMock, MagicMock

from aiogram.exceptions import TelegramBadRequest

from app.bot.panel import Panel


async def test_drop_previous_deletes_only_once():
    bot = AsyncMock()
    p = Panel()
    p.remember(1, 10)
    await p.drop_previous(bot, 1)
    await p.drop_previous(bot, 1)
    bot.delete_message.assert_awaited_once_with(1, 10)


async def test_delete_errors_are_ignored():
    bot = AsyncMock()
    bot.delete_message.side_effect = TelegramBadRequest(MagicMock(), "message can't be deleted")
    await Panel().delete(bot, 1, 5)  # xato ko'tarilmasligi kerak


async def test_user_message_deletion_can_be_disabled():
    msg = MagicMock(bot=AsyncMock(), chat=MagicMock(id=1), message_id=7)
    await Panel(delete_user_messages=False).discard_user_message(msg)
    msg.bot.delete_message.assert_not_awaited()
    await Panel(delete_user_messages=True).discard_user_message(msg)
    msg.bot.delete_message.assert_awaited_once_with(1, 7)
