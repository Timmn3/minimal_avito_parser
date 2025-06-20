import time
from typing import Optional

from bs4 import BeautifulSoup
from loguru import logger
from parsing.util.selenium_utils import setup_driver
from services.notification_service import notify_users_about_new_ad
from database.db import seen_ad_exists, add_seen_ad
from database.db import async_session
from sqlalchemy import select
from database.models import Task
import asyncio


async def parse_avito(task, bot):
    base_url = task['url']
    pages = ['', '&p=2', '&p=3', '&p=4', '&p=5'][:task['count_page']]
    time_repeat = task['time_repeat']
    teg = task['teg']
    target_words = task.get("target_words", [""])
    stop_words = task.get("stop_words", [""])
    min_price = task.get("min_price")  # Получаем минимальную цену
    max_price = task.get("max_price")  # Получаем максимальную цену

    if stop_words == [""]:
        stop_words = ["stop_words"]

    max_ads_per_run = task.get("max_ads_per_run", 30)

    driver = setup_driver()

    try:
        while True:
            async with async_session() as session:
                result = await session.execute(select(Task.activity).where(Task.id == task['id']))
                is_active = result.scalar()
                if not is_active:
                    logger.info(f"[{teg}] Задача остановлена пользователем. Парсер завершает работу.")
                    break

            new_ads_found = False
            try:
                for page in pages:
                    url = base_url + page
                    try:
                        driver.get(url)
                        await asyncio.sleep(time_repeat)
                        driver.execute_script("window.stop();")

                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        ad = soup.find_all(class_='iva-item-root-XBsVL')

                        for item in ad[:max_ads_per_run]:
                            if not item:
                                logger.warning("Пустой элемент объявления, пропускаем.")
                                continue

                            item_id = item.get('data-item-id')
                            if not item_id:
                                logger.warning('Нет item_id у объявления.')
                                continue

                            link_tag = item.find('a', {'data-marker': 'item-title'})
                            link = link_tag.get('href') if link_tag else None
                            if link and link.startswith('/'):
                                link = 'https://www.avito.ru/' + item_id

                            name_tag = item.find('a', {'data-marker': 'item-title'})
                            name = name_tag.text.strip() if name_tag else ''

                            price_tag = item.find('meta', {'itemprop': 'price'})
                            price = price_tag.get('content') if price_tag else ''

                            # Проверяем цену на соответствие диапазону
                            try:
                                price_int = int(price) if price else 0
                                price_valid = True
                                if min_price is not None and price_int < min_price:
                                    price_valid = False
                                if max_price is not None and price_int > max_price:
                                    price_valid = False
                            except ValueError:
                                price_valid = True  # Если цена не число, пропускаем проверку

                            description_tag = item.find('meta', {'itemprop': 'description'})
                            announcement_text = description_tag.get('content') if description_tag else ''

                            date_tag = item.find('p', {'data-marker': 'item-date'})
                            date_posted = date_tag.text.strip() if date_tag else ''

                            text = f"{name} {announcement_text}"

                            description = description_tag.get('content')


                            has_target = any(
                                word.lower() in text.lower() for word in target_words) if target_words else True
                            has_stop = any(word.lower() in text.lower() for word in stop_words) if stop_words else False

                            if has_target and not has_stop and link and price_valid:
                                if not await seen_ad_exists(task['id'], item_id):
                                    logger.info(f"[{teg}] New announcement: {link}")

                                    await add_seen_ad(
                                        task_id=task['id'],
                                        user_id=task['user_id'],
                                        item_id=item_id,
                                        name=name,
                                        price=price,
                                        link=link,
                                    )

                                    from database.db import get_users_by_task_teg
                                    users = await get_users_by_task_teg(teg)

                                    # Извлечение местоположения
                                    location_tag = item.find('div', class_='geo-root-BBVai')
                                    location = location_tag.get_text(
                                        strip=True) if location_tag else "Местоположение не указано"

                                    # Извлечение изображения в лучшем качестве
                                    image_url = await extract_image_url(item)

                                    # При необходимости очищаем от параметров сжатия
                                    if image_url and '?' in image_url:
                                        image_url = image_url.split('?')[0]

                                    await notify_users_about_new_ad(bot, users, {
                                        'teg': teg,
                                        'image_url': image_url,
                                        'title': name,
                                        'price': price,
                                        'location': location,
                                        'link': link,
                                        'date': date_posted,
                                        'description': description
                                    })

                                    new_ads_found = True

                    except Exception as e:
                        if "script timeout" in str(e) or "Message: script timeout" in str(e):
                            logger.warning(f"[{teg}] Таймаут при загрузке страницы")
                        else:
                            logger.error(f"Ошибка при обработке {url}: {e}")
                        await asyncio.sleep(10)

                if not new_ads_found:
                    logger.info(f"[{teg}] There are no new announcement.")
            except asyncio.CancelledError:
                logger.info(f"[{teg}] Получен запрос на перезапуск задачи")
                raise
    finally:
        driver.quit()

from bs4 import Tag
async def extract_image_url(item: Tag) -> Optional[str]:
    """
    Извлекает URL главного изображения объявления в максимально возможном качестве.

    :param item: BeautifulSoup-элемент объявления
    :return: URL изображения или None, если не найдено
    """
    img_tag = item.find('img', class_='photo-slider-image-cD891')
    if not img_tag:
        return None

    # 1. Пробуем извлечь из srcset (если доступно)
    if img_tag.get('srcset'):
        srcset = img_tag['srcset']
        urls = [url.strip() for url in srcset.split(',') if url.strip()]
        if urls:
            # Берем последний URL (обычно самый большой размер)
            return urls[-1].split()[0]

    # 2. Модифицируем src (основной URL изображения)
    if img_tag.get('src'):
        src = img_tag['src']

        # Пробуем улучшить качество, заменяя размер
        for size in ['208w', '236w', '318w', '416w', '472w']:
            if size in src:
                return src.replace(size, '636w')

        # Возвращаем оригинальный src, если не нашли размер
        return src

    return None