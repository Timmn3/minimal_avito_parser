# bot/middlewares/logging_middleware.py
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from loguru import logger

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict,
    ):
        # Получаем текущего пользователя
        user: User = data.get("event_from_user")
        user_id = user.id if user else None

        # Логируем начало обработки события
        with logger.contextualize(user_id=user_id):
            logger.info(f"Получено событие от пользователя {user_id}")
            return await handler(event, data)