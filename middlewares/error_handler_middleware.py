from aiogram.exceptions import AiogramError, TelegramNetworkError, ClientDecodeError
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from loguru import logger
from utils.notifications import notify_admins_about_error


class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        try:
            return await handler(event, data)
        except AiogramError as e:
            logger.error(f"[Telegram] Ошибка при обработке события: {type(e).__name__}: {e}")
            user_id = data.get("event_from_user", None)
            if user_id:
                user_id = user_id.id
            await notify_admins_about_error(data["bot"], e, user_id)

            # Обработка специфичных ошибок
            if isinstance(e, TelegramNetworkError):
                logger.warning("Ошибка сети с Telegram API")
                if "Conflict" in str(e) or "409" in str(e):
                    logger.critical("Конфликт: бот уже запущен где-то ещё")

            elif isinstance(e, ClientDecodeError):
                logger.warning("Ошибка декодирования ответа от Telegram")

            # Попытка ответить пользователю, если это возможно
            if hasattr(event, "answer"):
                try:
                    await event.answer("⚠️ Произошла внутренняя ошибка. Администратор уже уведомлен.")
                except AiogramError:
                    logger.warning("Не удалось отправить сообщение пользователю")
        except Exception as e:
            logger.exception(f"[Unknown] Непредвиденная ошибка: {e}")
            user_id = data.get("event_from_user", None)
            if user_id:
                user_id = user_id.id
            await notify_admins_about_error(data["bot"], e, user_id)