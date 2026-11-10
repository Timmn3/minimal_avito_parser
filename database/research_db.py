"""Хранилище research-задач: объявления, история цен, очередь карточек."""
from datetime import datetime
from types import ModuleType
from typing import Optional

from sqlalchemy import select, update

from database.models import Listing, PriceHistory
from database.session import get_session

MAX_CARD_ATTEMPTS = 3  # после стольких неудачных заходов карточка уходит в failed
CARD_QUEUE_SCAN = 3000  # сколько pending-кандидатов смотрим при выборе следующей карточки (ранжируем все)


async def upsert_page(task_id: int, items: list[dict], profile: Optional[ModuleType]) -> tuple[int, list]:
    """
    Пишет объявления страницы ленты. Новые кандидаты профиля встают в очередь карточек.
    Возвращает (число новых, [(listing_id, старая цена, новая цена)] для изменившихся цен).
    """
    if not items:
        return 0, []
    now = datetime.utcnow()
    new, changed = 0, []
    async with get_session() as session:
        ids = [i['item_id'] for i in items]
        existing = {l.item_id: l for l in (await session.execute(
            select(Listing).where(Listing.task_id == task_id, Listing.item_id.in_(ids)))).scalars()}
        done_keys = set((await session.execute(
            select(Listing.feed_title, Listing.feed_price, Listing.location)
            .where(Listing.task_id == task_id, Listing.detail_status.in_(('ok', 'gone'))))).all())
        for it in items:
            row = existing.get(it['item_id'])
            if row is None:
                candidate = profile is not None and profile.prefilter(it['title'], it['price'])
                status = None
                if candidate:
                    # продавцы клонируют объявления: тот же заголовок, цена и место, что у уже разобранного - дубль
                    status = 'dup' if (it['title'], it['price'], it['location']) in done_keys else 'pending'
                row = Listing(task_id=task_id, item_id=it['item_id'], title=it['title'], price=it['price'],
                              url=it['url'], location=it['location'], first_seen=now, last_seen=now,
                              feed_title=it['title'], feed_price=it['price'],
                              detail_status=status, detail_attempts=0)
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
                changed.append((row.id, row.price, it['price']))
                row.price = it['price']
                row.price_changed_at = now
        await session.commit()
    return new, changed


async def has_listings(task_id: int) -> bool:
    async with get_session() as session:
        return (await session.execute(
            select(Listing.id).where(Listing.task_id == task_id).limit(1))).first() is not None


async def next_card(task_profiles: dict[int, ModuleType]) -> Optional[dict]:
    """
    Следующая карточка для захода среди активных research-задач: приоритет профиля
    (вероятные цели первыми), внутри - самые свежие. Кандидатов B, чья цена по ленте выше порога
    уведомления относительно медианы группы, пропускаем: в Telegram они всё равно не уйдут,
    а запросы к карточкам дорогие (Авито банит по IP).
    """
    if not task_profiles:
        return None
    from services.research_scoring import B_NOTIFY_RATIO, MIN_GROUP, medians  # поздний импорт: без цикла

    async with get_session() as session:
        rows = (await session.execute(
            select(Listing).where(Listing.task_id.in_(task_profiles.keys()), Listing.detail_status == 'pending')
            .order_by(Listing.first_seen.desc()).limit(CARD_QUEUE_SCAN))).scalars().all()
    if not rows:
        return None
    group_medians = {tid: await medians(tid, prof) for tid, prof in task_profiles.items()}
    async with get_session() as session:
        handled = set((await session.execute(
            select(Listing.task_id, Listing.feed_title, Listing.feed_price)
            .where(Listing.task_id.in_(task_profiles.keys()),
                   Listing.detail_status.in_(('ok', 'gone', 'dup'))))).all())

    def rank(row: Listing):
        profile = task_profiles[row.task_id]
        specs = profile.extract(row.title or "")
        tier = profile.tier(specs)
        if tier == "B":
            median, n = group_medians[row.task_id].get(profile.group_key(specs), (None, 0))
            if median and n >= MIN_GROUP and row.price and row.price > median * B_NOTIFY_RATIO:
                return None
        # клон уже разобранного объявления (тот же заголовок и цена, чаще всего тот же магазин в другом городе)
        # идёт после всех уникальных; продавца узнаем из карточки, там он и станет dup
        clone = 10 if (row.task_id, row.feed_title, row.feed_price) in handled else 0
        return {"A": 0, "?": 1, "B": 2}.get(tier, 3) + clone, -row.first_seen.timestamp()

    ranked = [(r, rank(r)) for r in rows]
    ranked = [(r, k) for r, k in ranked if k is not None]
    if not ranked:
        return None
    best = min(ranked, key=lambda x: x[1])[0]
    return {'id': best.id, 'item_id': best.item_id, 'url': best.url, 'task_id': best.task_id}


async def save_card(listing_id: int, card: dict) -> None:
    now = datetime.utcnow()
    async with get_session() as session:
        row = await session.get(Listing, listing_id)
        if row is None:
            return
        await session.execute(
            update(Listing).where(
                Listing.task_id == row.task_id, Listing.id != row.id, Listing.detail_status == 'pending',
                Listing.feed_title == row.feed_title, Listing.feed_price == row.feed_price,
                Listing.location == row.location).values(detail_status='dup'))
        row.detail_status = 'gone' if card.get('closed') else 'ok'
        row.detail_fetched_at = now
        row.params = card['params']
        row.description = card['description']
        row.seller = card['seller']
        if row.detail_status == 'ok' and await _has_seller_twin(session, row):
            row.detail_status = 'dup'
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


def _seller_id(seller: Optional[dict]) -> Optional[tuple]:
    if not seller:
        return None
    return tuple(seller.get(k) for k in ('name', 'rating', 'reviews', 'since', 'ads'))


async def _has_seller_twin(session, row: Listing) -> bool:
    """Уже разобрано объявление с тем же заголовком и ценой от того же продавца (клон по другим городам)."""
    if not row.feed_title or not row.feed_price:
        return False
    twins = (await session.execute(
        select(Listing).where(Listing.task_id == row.task_id, Listing.id != row.id,
                              Listing.feed_title == row.feed_title, Listing.feed_price == row.feed_price,
                              Listing.detail_status == 'ok'))).scalars().all()
    mine = _seller_id(row.seller)
    return mine is not None and any(_seller_id(t.seller) == mine for t in twins)
