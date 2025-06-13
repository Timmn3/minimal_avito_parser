# bot/handlers/start.py
from aiogram import Router, F
from aiogram.types import Message
from loguru import logger
from utils.notifications import notify_new_user
from database.db import async_session, get_or_create_user
from config import ADMIN_IDS

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    user_data = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name
    }

    async with async_session() as session:
        async with session.begin():
            user = await get_or_create_user(session, user_data)

    logger.info(f"[User {user.id}] Пользователь начал взаимодействие с ботом")

    if user.is_admin:
        await message.answer("Привет, администратор! Это главное меню.")
    else:
        await message.answer("Привет! Это Telegram-бот для управления парсером Avito.")

    # Уведомляем админов о новом пользователе
    if user.created_at:  # только что созданный пользователь
        await notify_new_user(message.bot, user, ADMIN_IDS)