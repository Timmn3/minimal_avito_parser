"""
Research-задачи: сбор рынка по профилю товара.

Лента: все объявления страницы пишутся в listings (цена, история цены), кандидаты по профилю
ставятся в очередь карточек. Карточка: параметры, описание, продавец - для оценки.
"""
import re
from typing import Optional

from bs4 import BeautifulSoup, Tag
from loguru import logger

from database.research_db import save_card, mark_card_failed, upsert_page
from parsing.parser_avito import PAGE_BLOCKED, RequestGate, load_page, BLOCK_COOLDOWN, SOFT_BLOCK_PAUSE
from profiles import get_profile
from services.research_notify import after_card, after_price_changes

FIRST_PASS_PAGES = 25  # первый проход набирает весь рынок для медиан (MacBook 14" 120-180 тыс. - 1 250 объявлений)
MAX_PASS_PAGES = 5     # обычный проход: листаем, пока есть невиденные, но не дальше
PAGE_STEP = 30         # сек. минимум между страницами research, даже если шаг очереди меньше


def _digits(text: str) -> Optional[int]:
    d = re.sub(r"\D", "", text or "")
    return int(d) if d else None


def parse_list_item(item: Tag) -> Optional[dict]:
    """Одно объявление из ленты; None, если нет id или ссылки."""
    item_id = item.get('data-item-id')
    link_tag = item.find('a', {'data-marker': 'item-title'})
    if not item_id or not link_tag or not link_tag.get('href'):
        return None
    href = link_tag['href'].split('?')[0]
    url = 'https://www.avito.ru' + href if href.startswith('/') else href
    price_tag = item.find('meta', {'itemprop': 'price'})
    location_tag = item.find(attrs={'data-marker': 'item-location'})
    return {
        'item_id': item_id,
        'title': link_tag.get_text(strip=True),
        'price': _digits(price_tag.get('content')) if price_tag else None,
        'url': url,
        'location': location_tag.get_text(' ', strip=True) if location_tag else None,
    }


def parse_list_page(soup: BeautifulSoup) -> list[dict]:
    items = [parse_list_item(el) for el in soup.find_all(attrs={'data-marker': 'item'})]
    return [i for i in items if i]


def _marker_text(soup: BeautifulSoup, marker: str, sep: str = " ") -> str:
    tag = soup.find(attrs={'data-marker': marker})
    return tag.get_text(sep, strip=True) if tag else ""


def parse_seller(soup: BeautifulSoup) -> dict:
    box = soup.find(attrs={'data-marker': 'item-view/seller-info'})
    text = box.get_text(" ", strip=True) if box else ""
    rating = re.search(r"\b([1-5],\d)\b", text)
    # «4,9 1054 отзыва»: число не должно цеплять хвост рейтинга; «1 054» с разделителем тысяч тоже бывает
    num = r"\b(\d{1,3}(?:[  ]\d{3})+|\d+)\s+"
    reviews = re.search(num + "отзыв", text)
    since = re.search(r"На Авито [cс] (\d{4})", text)
    ads = re.search(num + "объявлен", text)
    return {
        'name': _marker_text(soup, 'seller-info/name') or None,
        'label': _marker_text(soup, 'seller-info/label') or None,  # «Частное лицо», «Компания»
        'rating': float(rating.group(1).replace(",", ".")) if rating else None,
        'reviews': _digits(reviews.group(1)) if reviews else 0,
        'since': int(since.group(1)) if since else None,
        'ads': _digits(ads.group(1)) if ads else None,
        'reliable': "Надёжный продавец" in text,
        'verified': "Данные подтверждены" in text,
    }


def parse_card(soup: BeautifulSoup) -> Optional[dict]:
    """Карточка объявления; None, если на странице нет ни цены, ни заголовка (заглушка без данных)."""
    title = _marker_text(soup, 'item-view/title-info')
    price = _digits(_marker_text(soup, 'item-view/item-price'))
    if not title and not price:
        return None
    params = {}
    box = soup.find(attrs={'data-marker': 'item-view/item-params'})
    if box:
        for li in box.find_all('li'):
            key, sep, value = li.get_text(" ", strip=True).partition(":")
            if sep:
                params[key.strip()] = value.strip()
    desc_tag = soup.find(attrs={'data-marker': 'item-view/item-description'})
    return {
        'title': title,
        'price': price,
        'params': params,
        'description': desc_tag.get_text("\n", strip=True) if desc_tag else "",
        'seller': parse_seller(soup),
        'posted': _marker_text(soup, 'item-view/item-date').lstrip("· ").strip() or None,
        'views': _digits(_marker_text(soup, 'item-view/total-views')),
        # точный маркер снятого объявления не проверен, ловим по тексту страницы
        'closed': bool(re.search(r"снято с публикации|объявление (?:закрыто|удалено)", soup.get_text(" ")[:20000], re.I)),
    }


async def research_step(driver, task: dict, page_index: int, first_pass: bool, gate: RequestGate,
                        step: float, state: dict, mode: str, bot=None) -> tuple[str, bool]:
    """
    Одна страница прохода research-задачи. Возвращает (статус страницы, листать ли дальше).
    Дальше листаем, пока на странице есть невиденные объявления и не упёрлись в потолок страниц.
    """
    teg = task['teg']
    profile = get_profile(task['profile'])
    url = task['url'] + (f"&p={page_index + 1}" if page_index else "")
    status, soup = await load_page(driver, url, teg, gate, max(step, PAGE_STEP), state, mode)
    if status == PAGE_BLOCKED:
        gate.cooldown(BLOCK_COOLDOWN)
        return status, False
    if status != "ok":
        gate.cooldown(SOFT_BLOCK_PAUSE)

    items = parse_list_page(soup)
    new, changes = await upsert_page(task['id'], items, profile)
    await after_price_changes(bot, task, changes)
    limit = FIRST_PASS_PAGES if first_pass else MAX_PASS_PAGES
    more = bool(items) and new > 0 and page_index + 1 < limit
    logger.info(f"[{teg}] research стр. {page_index + 1}: объявлений {len(items)}, новых {new}, "
                f"цена изменилась {len(changes)}" + (", листаем дальше" if more else ""))
    if new and page_index + 1 >= limit and new == len(items):
        logger.warning(f"[{teg}] Упёрлись в потолок {limit} стр., а невиденные ещё идут: "
                       f"интервал великоват или поиск слишком широкий")
    return status, more


async def card_step(driver, listing: dict, gate: RequestGate, step: float, state: dict, mode: str,
                    bot=None) -> bool:
    """Заход в карточку кандидата. True - разобрана и сохранена."""
    teg = f"card {listing['item_id']}"
    status, soup = await load_page(driver, listing['url'], teg, gate, step, state, mode)
    card = parse_card(soup) if soup is not None else None
    if status == PAGE_BLOCKED:
        gate.cooldown(BLOCK_COOLDOWN)
    elif status != "ok":
        gate.cooldown(SOFT_BLOCK_PAUSE)
    if card is None:
        if status != PAGE_BLOCKED:  # бан по IP - не вина карточки, попытку не списываем
            await mark_card_failed(listing['id'])
        logger.warning(f"[{teg}] карточка не разобрана ({status})")
        return False
    await save_card(listing['id'], card)
    logger.info(f"[{teg}] карточка: {card['title'][:60]} | {card['price']} | параметров {len(card['params'])}")
    await after_card(bot, listing['id'])
    return True
