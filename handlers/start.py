from aiogram import Router
from aiogram.types import Message
from loguru import logger
from database.db import async_session, get_or_create_user
from config import ADMIN_IDS
from database.models import User
from keyboards.inline import get_main_menu_keyboard
from sqlalchemy import select

from keyboards.reply import get_menu_keyboard

router = Router()

@router.message(lambda msg: msg.text == "/start")
async def cmd_start(message: Message):
    user_data = {
        'id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name
    }
    async with async_session() as session:
        async with session.begin():
            result = await session.execute(select(User).where(User.id == user_data['id']))
            existing_user = result.scalars().first()
            if existing_user is None:
                # Пользователь новый — создаем его
                user = User(**user_data)
                session.add(user)
                await session.flush()
                is_new_user = True
            else:
                # Пользователь уже существует
                user = existing_user
                is_new_user = False

    # logger.info(f"[User {user.id}] Пользователь начал взаимодействие с ботом")

    await message.answer(f"👋 Привет <b>{message.from_user.username}!</b>", parse_mode="HTML",
                         reply_markup=get_menu_keyboard())

    # Отправляем уведомление только если это новый пользователь
    if is_new_user:
        from utils.notifications import notify_new_user
        await notify_new_user(message.bot, user, ADMIN_IDS)