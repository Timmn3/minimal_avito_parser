import time
from bs4 import BeautifulSoup
from loguru import logger

from parsing.util.selenium_utils import setup_driver
from services.notification_service import notify_users_about_new_ad

# === Настройки ===
seen_ads = {}  # Храним все уникальные объявления

async def parse_avito(task, config, bot):
    base_url = task['url']
    pages = ['', '&p=2', '&p=3', '&p=4', '&p=5'][:task['count_page']]
    time_repeat = task['time_repeat']
    teg = task['teg']
    target_words = task.get("target_words", [""])
    stop_words = task.get("stop_words", [""])
    if stop_words == [""]:
        stop_words = ["stop_words"]

    max_ads_per_run = task.get("max_ads_per_run", 30)  # Лимит вывода новых объявлений (верхних на странице) за цикл

    driver = setup_driver()
    global seen_ads

    try:
        while True:
            new_ads_found = False
            current_ads = set()

            for page in pages:
                url = base_url + page
                try:
                    driver.get(url)
                    time.sleep(time_repeat)
                    driver.execute_script("window.stop();")  # Остановка загрузки страницы

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    ad = soup.find_all(class_='iva-item-root-XBsVL')

                    for item in ad[:max_ads_per_run]:
                        if not item:
                            logger.warning("Пустой элемент объявления, пропускаем.")
                            continue

                        try:
                            item_id = item.get('data-item-id')
                        except Exception as e:
                            logger.exception(f'нет item_id: {e}')
                            continue

                        try:
                            link_tag = item.find('a', {'data-marker': 'item-title'})
                            if not link_tag:
                                link = None
                            else:
                                link = link_tag.get('href')
                                if link and link.startswith('/'):
                                    link = 'https://www.avito.ru' + link
                        except Exception as e:
                            link = None
                            logger.warning(f'Нет ссылки: {e}')

                        try:
                            name_tag = item.find('a', {'data-marker': 'item-title'})
                            name = name_tag.text.strip() if name_tag else ''
                        except Exception as e:
                            name = ''
                            logger.exception(f'Ошибка при извлечении названия: {e}')

                        try:
                            price_tag = item.find('meta', {'itemprop': 'price'})
                            price = price_tag.get('content') if price_tag else ''
                        except Exception as e:
                            price = ''
                            logger.exception(f'Ошибка при извлечении цены: {e}')

                        try:
                            description_tag = item.find('meta', {'itemprop': 'description'})
                            announcement_text = description_tag.get('content') if description_tag else ''
                        except Exception as e:
                            announcement_text = ''
                            logger.exception(f'Ошибка при извлечении описания: {e}')

                        try:
                            text = f"{name} {announcement_text}"
                        except Exception:
                            text = ''

                        has_target = any(
                            word.lower() in text.lower() for word in target_words) if target_words else True
                        has_stop = any(word.lower() in text.lower() for word in stop_words) if stop_words else False

                        if has_target and not has_stop and link:
                            if item_id not in seen_ads:
                                # logger.info(f"[{teg}] Новое объявление: {link}")
                                seen_ads[item_id] = (name, price, link)

                                from database.db import get_users_by_task_teg
                                users = await get_users_by_task_teg(teg)
                                await notify_users_about_new_ad(bot, users, {
                                    'teg': teg,
                                    'title': name,
                                    'price': price,
                                    'link': link
                                })

                                new_ads_found = True

                except Exception as e:
                    logger.error(f"Ошибка при обработке {url}: {e}")
                    time.sleep(10)

            if not new_ads_found:
                pass
                # logger.debug(f"[{teg}] Новых объявлений нет.")

    finally:
        driver.quit()