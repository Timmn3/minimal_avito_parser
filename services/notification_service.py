from aiogram import Bot
from loguru import logger

async def notify_users_about_new_ad(bot: Bot, users, ad_data):
    """
    Отправляет новое объявление всем указанным пользователям.
    :param bot: экземпляр бота
    :param users: список пользователей (словарь с 'id' и 'username')
    :param ad_data: данные объявления {'teg', 'title', 'price', 'link'}
    """
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.id,
                text=(
                    f"📍#{ad_data['teg']}\n"
                    f"{ad_data['title']}\n"
                    f"{ad_data['price']}\n"
                    f"{ad_data['link']}"
                ),
                disable_web_page_preview=False
            )
        except Exception as e:
            logger.error(f"[User {user.id}] Не удалось отправить объявление: {e}")