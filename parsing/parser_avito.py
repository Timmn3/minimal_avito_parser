import time
from typing import Optional

from bs4 import BeautifulSoup
from loguru import logger
from services.notification_service import notify_users_about_new_ad
from database.db import seen_ad_exists, add_seen_ad
import asyncio

BLOCK_MARKER = "доступ ограничен:"  # «Доступ ограничен: проблема с IP» / «...: проверка безопасности»
MAX_BLOCK_REFRESHES = 6
MIN_REQUEST_INTERVAL = 60  # сек. Авито банит по IP за частые запросы - одну задачу чаще раза в минуту не проверяем
PAGE_LOAD_WAIT = 10        # сек. на отрисовку страницы после загрузки/обновления
SOFT_BLOCK_PAUSE = 60      # сек. пауза всей очереди, если заглушка висит поверх нормальной выдачи
BLOCK_COOLDOWN = 180       # сек. пауза всей очереди, если заглушку не удалось снять
DEAD_SESSION_MARKERS = ("invalid session id", "no such window", "disconnected", "chrome not reachable",
                        "target window already closed", "session deleted", "tab crashed")

PAGE_OK = "ok"
PAGE_SOFT_BLOCK = "soft_block"  # заглушка есть, но объявления в разметке тоже есть
PAGE_BLOCKED = "blocked"        # одна заглушка, парсить нечего


def _is_dead_session(exc: Exception) -> bool:
    """Браузер закрыт пользователем или упал - драйвер надо пересоздавать."""
    return any(marker in str(exc).lower() for marker in DEAD_SESSION_MARKERS)


class RequestGate:
    """
    Общая очередь запросов к Авито на весь процесс: между любыми двумя запросами (в том числе обновлениями
    при заглушке) проходит не меньше step сек. Блокировки добавляют паузу сверху через cooldown().
    """

    def __init__(self):
        self.last_request = float("-inf")
        self.not_before = float("-inf")

    async def wait(self, step: float) -> None:
        wait = max(self.last_request + step, self.not_before) - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        self.last_request = time.monotonic()

    def cooldown(self, seconds: float) -> None:
        self.not_before = max(self.not_before, time.monotonic() + seconds)


def classify_page(title: str, source: str, items: int) -> str:
    """
    Тип страницы. Заголовок ловит отдельную страницу блокировки, фраза в исходнике - ещё и заглушку поверх выдачи
    (на чистой выдаче фразы нет совсем, проверено на сервере).
    """
    if BLOCK_MARKER.rstrip(":") in title.lower():
        return PAGE_BLOCKED
    if BLOCK_MARKER in source.lower():
        return PAGE_SOFT_BLOCK if items else PAGE_BLOCKED
    return PAGE_OK


def _read_page(driver) -> tuple[str, str, int]:
    driver.execute_script("window.stop();")
    source = driver.page_source
    items = source.count('data-marker="item"')  # хэш-классы Авито меняются, data-marker стабилен
    return classify_page(driver.title or "", source, items), source, items


async def load_page(driver, url: str, teg: str, gate: RequestGate, step: float,
                    state: dict) -> tuple[str, Optional[BeautifulSoup]]:
    """
    Загружает страницу в той же вкладке: тот же URL - refresh(), другой - get(). Заглушку «Доступ ограничен»
    снимаем обновлением (до MAX_BLOCK_REFRESHES раз), каждое обновление тоже идёт через общую очередь.
    Возвращает (статус, soup); soup только если страницу можно парсить.
    """
    await gate.wait(step)
    if state.get('url') == url:
        driver.refresh()
    else:
        driver.get(url)
        state['url'] = url
    await asyncio.sleep(PAGE_LOAD_WAIT)

    status, source, items = _read_page(driver)
    for attempt in range(1, MAX_BLOCK_REFRESHES + 1):
        if status != PAGE_BLOCKED:
            break
        logger.warning(f"[{teg}] Страница блокировки Авито, обновляем (попытка {attempt}/{MAX_BLOCK_REFRESHES})")
        await gate.wait(step)
        driver.refresh()
        await asyncio.sleep(PAGE_LOAD_WAIT)
        status, source, items = _read_page(driver)

    if status == PAGE_BLOCKED:
        logger.warning(f"[{teg}] Блокировка не снялась после {MAX_BLOCK_REFRESHES} обновлений")
        return status, None
    if status == PAGE_SOFT_BLOCK:
        logger.warning(f"[{teg}] Заглушка поверх выдачи ({items} объявл. в разметке), парсим и притормаживаем очередь")
    return status, BeautifulSoup(source, "html.parser")


async def process_items(soup: BeautifulSoup, task: dict, bot) -> bool:
    """Разбор одной страницы выдачи для задачи. True, если нашли и отправили новые объявления."""
    teg = task['teg']
    target_words = task.get("target_words", [""])
    stop_words = task.get("stop_words", [""])
    min_price = task.get("min_price")  # Получаем минимальную цену
    max_price = task.get("max_price")  # Получаем максимальную цену

    if stop_words == [""]:
        stop_words = ["stop_words"]

    max_ads_per_run = task.get("max_ads_per_run", 30)
    new_ads_found = False

    ad = soup.find_all(attrs={'data-marker': 'item'})  # хэш-классы Авито меняются, data-marker стабилен

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
            link = 'https://www.avito.ru' + link.split('?')[0]  # без трекингового context=

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
        if not announcement_text:
            # в новой выдаче описания нет - берём характеристики («127 см³ / 14 л.с., ...»)
            params_tag = item.find(attrs={'data-marker': 'item-specific-params'})
            announcement_text = params_tag.get_text(' ', strip=True) if params_tag else ''

        date_tag = item.find('p', {'data-marker': 'item-date'})
        date_posted = date_tag.text.strip() if date_tag else ''

        text = f"{name} {announcement_text}"

        description = announcement_text

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
                location_tag = item.find(attrs={'data-marker': 'item-location'})
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

    return new_ads_found


async def check_task_page(driver, task: dict, page_index: int, bot, gate: RequestGate, step: float,
                          state: dict) -> str:
    """
    Один шаг очереди: загрузить страницу page_index задачи и разобрать её.
    Возвращает статус страницы; BLOCKED = цикл неудачный, парсинг не выполнялся.
    """
    teg = task['teg']
    pages = ['', '&p=2', '&p=3', '&p=4', '&p=5'][:task['count_page']] or ['']
    url = task['url'] + pages[page_index % len(pages)]

    status, soup = await load_page(driver, url, teg, gate, step, state)
    if status == PAGE_BLOCKED:
        logger.warning(f"[{teg}] Цикл неудачный: блокировка не снялась, страницу не парсим")
        gate.cooldown(BLOCK_COOLDOWN)
        return status

    if not await process_items(soup, task, bot):
        logger.info(f"[{teg}] There are no new announcement.")
    if status == PAGE_SOFT_BLOCK:
        gate.cooldown(SOFT_BLOCK_PAUSE)
    return status


from bs4 import Tag
async def extract_image_url(item: Tag) -> Optional[str]:
    """
    Извлекает URL главного изображения объявления в максимально возможном качестве.

    :param item: BeautifulSoup-элемент объявления
    :return: URL изображения или None, если не найдено
    """
    img_tag = item.find('img', attrs={'itemprop': 'image'})
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
