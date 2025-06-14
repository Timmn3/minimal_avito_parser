import time
from bs4 import BeautifulSoup
from loguru import logger

from parsing.util.selenium_utils import setup_driver
from services.notification_service import notify_users_about_new_ad

from database.db import seen_ad_exists, add_seen_ad


async def parse_avito(task, config, bot):
    base_url = task['url']
    pages = ['', '&p=2', '&p=3', '&p=4', '&p=5'][:task['count_page']]
    time_repeat = task['time_repeat']
    teg = task['teg']
    target_words = task.get("target_words", [""])
    stop_words = task.get("stop_words", [""])
    if stop_words == [""]:
        stop_words = ["stop_words"]

    max_ads_per_run = task.get("max_ads_per_run", 30)

    driver = setup_driver()

    try:
        while True:
            new_ads_found = False

            for page in pages:
                url = base_url + page
                try:
                    driver.get(url)
                    time.sleep(time_repeat)
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
                            link = 'https://www.avito.ru' + link

                        name_tag = item.find('a', {'data-marker': 'item-title'})
                        name = name_tag.text.strip() if name_tag else ''

                        price_tag = item.find('meta', {'itemprop': 'price'})
                        price = price_tag.get('content') if price_tag else ''

                        description_tag = item.find('meta', {'itemprop': 'description'})
                        announcement_text = description_tag.get('content') if description_tag else ''

                        text = f"{name} {announcement_text}"

                        has_target = any(
                            word.lower() in text.lower() for word in target_words) if target_words else True
                        has_stop = any(word.lower() in text.lower() for word in stop_words) if stop_words else False

                        if has_target and not has_stop and link:
                            if not await seen_ad_exists(task['id'], item_id):
                                logger.info(f"[{teg}] New announcement: {link}")

                                await add_seen_ad(
                                    task_id=task['id'],
                                    user_id=task['user_id'],
                                    item_id=item_id,
                                    name=name,
                                    price=price,
                                    link=link
                                )

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
                # logger.debug(f"[{teg}] There are no new announcement.")

    finally:
        driver.quit()
