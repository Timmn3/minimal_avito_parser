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
    date_info = "только что" if ad_data.get("date") == "1 час назад" else ad_data.get("date", "")

    date_text = f"🕒 Опубликовано: <i>{date_info}</i>\n\n" if date_info else ""
    formatted_price = format_price(ad_data.get("price", ""))
    description = ad_data.get("description", "")
    location = ad_data.get("location", "")
    image_url = ad_data.get("image_url", "")
    message_text = (
        f"📍#{ad_data['teg']}\n"
        f"{date_text}"
        f"<b>{ad_data['title']}</b>\n"
        f"💵 <b>{formatted_price}</b>\n"
        f"🌍 <i>{location}</i>\n"
        f"{ad_data['link']}\n\n"
        f"{description}"
    )
    for user in users:
        try:
            # Если есть URL изображения - отправляем фото с подписью
            if image_url:
                await bot.send_photo(
                    chat_id=user.id,
                    photo=image_url,
                    caption=message_text,
                    parse_mode="HTML"
                )
            # Если изображения нет - отправляем текстовое сообщение
            else:
                await bot.send_message(
                    chat_id=user.id,
                    text=message_text,
                    parse_mode="HTML",
                    disable_web_page_preview=False
                )
        except Exception as e:
            logger.error(f"[User {user.id}] Не удалось отправить объявление: {e}")
