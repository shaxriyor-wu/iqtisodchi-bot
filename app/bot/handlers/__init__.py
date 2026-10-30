from aiogram import Router

from app.bot.handlers import chat, menu


def build_router() -> Router:
    root = Router()
    root.include_router(menu.router)
    root.include_router(chat.router)  # oxirida: boshqa handlerlar ilinmagan matnlarni oladi
    return root
