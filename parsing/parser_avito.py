import time
from bs4 import BeautifulSoup
from loguru import logger
from parsing.util.selenium_utils import setup_driver

# === Настройки ===
seen_ads = {}  # Храним все уникальные объявления



async def parse_avito(task, config):
    base_url = task['url']
    pages = ['', '&p=2', '&p=3', '&p=4', '&p=5'][:task['count_page']]
    time_repeat = task['time_repeat']
    teg = task['teg']
    target_words = task.get("target_words", [""])
    stop_words = task.get("stop_words", [""])
    if stop_words == [""]:
        stop_words = ["stop_words"]

    max_ads_per_run = task.get("max_ads_per_run", 30)  # Лимит вывода новых объявлений (верхних на странице) за цикл

    name_class = config.get("name")
    announcement_text_class = config.get("announcement_text")
    price_class = config.get("price")
    driver = setup_driver()
    # Глобальная переменная для хранения всех найденных объявлений
    global seen_ads

    try:
        while True:
            new_ads_found = False  # Флаг для проверки наличия новых объявлений
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
                                    link = 'https://www.avito.ru'    + link
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
                            first_line = announcement_text.splitlines()[0] if announcement_text else ''
                        except Exception:
                            announcement_text = ''

                        try:
                            text = f"{name} {announcement_text}"
                        except Exception:
                            text = ''

                        has_target = any(word.lower() in text.lower() for word in target_words) if target_words else True
                        has_stop = any(word.lower() in text.lower() for word in stop_words) if stop_words else False

                        if has_target and not has_stop and link:
                            if item_id not in seen_ads:
                                logger.info(f"[{teg}] Новое объявление: {link}")
                                seen_ads[item_id] = (name, price, link)
                                current_ads.add(link)
                                new_ads_found = True
                            else:
                                # Объявление уже было
                                pass

                    time.sleep(task['time_repeat'])

                except Exception as e:
                    logger.error(f"Ошибка при обработке {url}: {e}")
                    time.sleep(10)

            if not new_ads_found:
                logger.info(f"[{teg}] Новых объявлений нет.")
    finally:
        driver.quit()