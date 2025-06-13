import time
from bs4 import BeautifulSoup
from loguru import logger
from util.selenium_utils import setup_driver

# === Настройки ===
seen_ads = {}  # Храним все уникальные объявления
MAX_ADS_PER_RUN = 5  # Лимит вывода новых объявлений за цикл


def parse_avito(task, config):
    base_url = task['url']
    pages = ['', '&p=2', '&p=3', '&p=4', '&p=5'][:task['count_page']]
    all_ads = task.get('all_ads', False)

    name_class = config.get("name")
    announcement_text_class = config.get("announcement_text")
    price_class = config.get("price")

    driver = setup_driver()

    try:
        while True:
            new_ads_found = False
            ads_shown = 0

            # Храним объявления, найденные в этом цикле
            seen_ads_task = set()

            for page in pages:
                url = base_url + page
                try:
                    driver.get(url)
                    time.sleep(3)
                    driver.execute_script("window.stop();")  # Остановка загрузки

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    ad = soup.find_all(class_='iva-item-root-XBsVL')

                    for item in ad:
                        try:
                            item_id = item.get('data-item-id')
                        except Exception as e:
                            logger.exception(f'нет item_id: {e}')
                            continue

                        if not item_id:
                            continue

                        try:
                            link_tag = item.find('a', {'data-marker': 'item-title'})
                            if not link_tag:
                                link = None
                            else:
                                link = link_tag.get('href')
                                if link and link.startswith('/'):
                                    link = 'https://www.avito.ru'  + link
                        except Exception as e:
                            link = None
                            logger.warning(f'Нет ссылки: {e}')

                        try:
                            name = item.find(class_=name_class).text.strip() if name_class else ''
                        except Exception:
                            name = ''

                        try:
                            price = item.find(class_=price_class).text.strip() if price_class else ''
                        except Exception:
                            price = ''

                        try:
                            announcement_tag = item.find(class_=announcement_text_class)
                            announcement_text = announcement_tag.text.strip() if announcement_tag else ''
                        except Exception:
                            announcement_text = ''

                        try:
                            text = f"{name} {announcement_text}"
                        except Exception:
                            text = ''

                        target_words = task.get("target_words", [])
                        stop_words = task.get("stop_words", [])

                        if stop_words == [""]:
                            stop_words = ["stop_words"]

                        has_target = any(word.lower() in text.lower() for word in target_words) if target_words else True
                        has_stop = any(word.lower() in text.lower() for word in stop_words) if stop_words else False

                        if has_target and not has_stop and link:
                            if item_id not in seen_ads and item_id not in seen_ads_task:
                                seen_ads[item_id] = (name, price, link)
                                seen_ads_task.add(item_id)
                                new_ads_found = True

                                if ads_shown < MAX_ADS_PER_RUN:
                                    logger.info(f"[{task['teg']}] Новое объявление: {link}")
                                    ads_shown += 1

                                    if ads_shown >= MAX_ADS_PER_RUN:
                                        logger.info(f"[{task['teg']}] Лимит ({MAX_ADS_PER_RUN}) достигнут.")
                                        break  # Выход по лимиту

                    time.sleep(task['time_repeat'])

                except Exception as e:
                    logger.error(f"Ошибка при обработке {url}: {e}")
                    time.sleep(10)

            if not new_ads_found:
                logger.info(f"[{task['teg']}] Новых объявлений нет.")

    finally:
        driver.quit()