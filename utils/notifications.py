from aiogram import Bot
from loguru import logger


async def notify_new_user(bot: Bot, user, admin_ids):
    message = (
        f"🆕 Новый пользователь зарегистрирован:\n"
        f"ID: {user.id}\n"
        f"Имя: {user.first_name} {user.last_name or ''}\n"
        f"Username: @{user.username or 'нет'}\n"
        f"Дата регистрации: {user.created_at}"
    )
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, message)
        except Exception as e:
            logger.warning(f"Не удалось уведомить админа {admin_id}: {e}")

async def notify_admins_about_error(bot: Bot, error: Exception, user_id: int = None):
    """
    Отправляет сообщение всем админам о возникшей ошибке.
    :param bot: экземпляр бота
    :param error: объект исключения
    :param user_id: ID пользователя, если есть
    """
    from config import ADMIN_IDS

    message = (
        "⚠️ <b>Произошла критическая ошибка</b>\n"
        f"Ошибка: <code>{type(error).__name__}: {str(error)}</code>\n"
        f"Пользователь: {'Неизвестен' if user_id is None else f'{user_id}'}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, message, parse_mode="HTML")
        except Exception as e:
            logger.error(f"[Admin {admin_id}] Не удалось отправить сообщение об ошибке: {e}")