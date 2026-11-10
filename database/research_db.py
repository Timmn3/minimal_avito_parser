"""Хранилище research-задач: объявления, история цен, очередь карточек."""
from datetime import datetime
from types import ModuleType
from typing import Optional

from sqlalchemy import select, update

from database.models import Listing, PriceHistory
from database.session import get_session

MAX_CARD_ATTEMPTS = 3  # после стольких неудачных заходов карточка уходит в failed
CARD_QUEUE_SCAN = 300  # сколько pending-кандидатов смотрим при выборе следующей карточки


async def upsert_page(task_id: int, items: list[dict], profile: Optional[ModuleType]) -> tuple[int, int]:
    """
    Пишет объявления страницы ленты. Новые кандидаты профиля встают в очередь карточек.
    Возвращает (новых, с изменившейся ценой).
    """
    if not items:
        return 0, 0
    now = datetime.utcnow()
    new = changed = 0
    async with get_session() as session:
        ids = [i['item_id'] for i in items]
        existing = {l.item_id: l for l in (await session.execute(
            select(Listing).where(Listing.task_id == task_id, Listing.item_id.in_(ids)))).scalars()}
        for it in items:
            row = existing.get(it['item_id'])
            if row is None:
                candidate = profile is not None and profile.prefilter(it['title'], it['price'])
                row = Listing(task_id=task_id, item_id=it['item_id'], title=it['title'], price=it['price'],
                              url=it['url'], location=it['location'], first_seen=now, last_seen=now,
                              detail_status='pending' if candidate else None, detail_attempts=0)
                session.add(row)
                await session.flush()
                if it['price']:
                    session.add(PriceHistory(listing_id=row.id, price=it['price'], seen_at=now))
                new += 1
                continue
            row.last_seen = now
            row.title = it['title'] or row.title
            if it['price'] and it['price'] != row.price:
                session.add(PriceHistory(listing_id=row.id, price=it['price'], seen_at=now))
                row.price = it['price']
                row.price_changed_at = now
                changed += 1
        await session.commit()
    return new, changed


async def has_listings(task_id: int) -> bool:
    async with get_session() as session:
        return (await session.execute(
            select(Listing.id).where(Listing.task_id == task_id).limit(1))).first() is not None


async def next_card(task_profiles: dict[int, ModuleType]) -> Optional[dict]:
    """
    Следующая карточка для захода среди активных research-задач: приоритет профиля
    (вероятные цели первыми), внутри - самые свежие.
    """
    if not task_profiles:
        return None
    async with get_session() as session:
        rows = (await session.execute(
            select(Listing).where(Listing.task_id.in_(task_profiles.keys()), Listing.detail_status == 'pending')
            .order_by(Listing.first_seen.desc()).limit(CARD_QUEUE_SCAN))).scalars().all()
    if not rows:
        return None

    def rank(row: Listing):
        profile = task_profiles[row.task_id]
        return profile.priority(profile.extract(row.title or "")), -row.first_seen.timestamp()

    best = min(rows, key=rank)
    return {'id': best.id, 'item_id': best.item_id, 'url': best.url, 'task_id': best.task_id}


async def save_card(listing_id: int, card: dict) -> None:
    now = datetime.utcnow()
    async with get_session() as session:
        row = await session.get(Listing, listing_id)
        if row is None:
            return
        row.detail_status = 'gone' if card.get('closed') else 'ok'
        row.detail_fetched_at = now
        row.params = card['params']
        row.description = card['description']
        row.seller = card['seller']
        row.posted = card['posted']
        row.views = card['views']
        if card['title']:
            row.title = card['title']
        if card['price'] and card['price'] != row.price:
            session.add(PriceHistory(listing_id=row.id, price=card['price'], seen_at=now))
            row.price = card['price']
            row.price_changed_at = now
        await session.commit()


async def mark_card_failed(listing_id: int) -> None:
    async with get_session() as session:
        await session.execute(
            update(Listing).where(Listing.id == listing_id)
            .values(detail_attempts=Listing.detail_attempts + 1))
        await session.execute(
            update(Listing).where(Listing.id == listing_id, Listing.detail_attempts >= MAX_CARD_ATTEMPTS)
            .values(detail_status='failed'))
        await session.commit()
