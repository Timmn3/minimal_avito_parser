from aiogram import Bot
from loguru import logger

def format_price(price_str):
    try:
        # Преобразуем строку в число и форматируем с пробелами
        price_int = int(price_str)
        return f"{price_int:,}".replace(",", " ") + " ₽"
    except:
        # Если не число — возвращаем как есть
        return price_str

async def notify_users_about_new_ad(bot: Bot, users, ad_data):
    """
    Отправляет новое объявление всем указанным пользователям.
    :param bot: экземпляр бота
    :param users: список пользователей (словарь с 'id' и 'username')
    :param ad_data: данные объявления {'teg', 'title', 'price', 'link', 'date'}
    """
    date_info = ad_data.get("date", "")
    date_text = f"🕒 Опубликовано: <i>{date_info}</i>\n\n" if date_info else ""
    formatted_price = format_price(ad_data.get("price", ""))

    for user in users:
        try:
            await bot.send_message(
                chat_id=user.id,
                text=(
                    f"📍#{ad_data['teg']}\n"
                    f"{date_text}"
                    f"{ad_data['title']}\n"
                    f"<b>{formatted_price}</b>\n\n"
                    f"{ad_data['link']}"
                ),
                disable_web_page_preview=False,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"[User {user.id}] Не удалось отправить объявление: {e}")
