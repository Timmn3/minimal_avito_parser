"""Telegram-уведомления research-задач: интересная находка после разбора карточки и снижение цены."""
from datetime import datetime

from loguru import logger

from database.models import Listing, Task
from database.session import get_session
from profiles import get_profile
from services.research_scoring import PRICE_DROP_NOTIFY, evaluate, format_message, medians, worth_notifying
from services.settings_service import get_research_notify


async def _send(bot, chat_id: int, text: str) -> bool:
    try:
        await bot.send_message(chat_id, text, parse_mode="HTML")
        return True
    except Exception as e:  # Telegram недоступен - не роняем парсер, находка останется в отчёте
        logger.error(f"Не удалось отправить находку в {chat_id}: {e}")
        return False


async def after_card(bot, listing_id: int) -> None:
    """После разбора карточки: если объявление стоит внимания и о нём ещё не писали - пишем владельцу задачи."""
    if bot is None or not await get_research_notify():
        return
    async with get_session() as session:
        row = await session.get(Listing, listing_id)
        task = await session.get(Task, row.task_id) if row else None
    profile = get_profile(task.profile) if task else None
    if not profile or row.notified_at:
        return
    ev = evaluate(row, profile, await medians(task.id, profile))
    if not worth_notifying(row, ev):
        return
    if await _send(bot, task.user_id, format_message(row, ev, task.teg)):
        await _mark_notified(listing_id)
        logger.info(f"[{task.teg}] находка отправлена: {row.item_id} {row.price} ({ev['tier']})")


async def after_price_changes(bot, task: dict, changes: list) -> None:
    """Снижение цены от PRICE_DROP_NOTIFY у объявлений, о которых уже писали (и без новых флагов)."""
    drops = [(lid, old, new) for lid, old, new in changes if old and new and new <= old * (1 - PRICE_DROP_NOTIFY)]
    if bot is None or not drops or not await get_research_notify():
        return
    profile = get_profile(task["profile"])
    group_medians = await medians(task["id"], profile)
    for lid, old, new in drops:
        async with get_session() as session:
            row = await session.get(Listing, lid)
        if row is None or not row.notified_at:
            continue
        ev = evaluate(row, profile, group_medians)
        if ev["flags"] or ev["tier"] not in ("A", "B"):
            continue
        if await _send(bot, task["user_id"], format_message(row, ev, task["teg"], old_price=old)):
            await _mark_notified(lid)


async def _mark_notified(listing_id: int) -> None:
    async with get_session() as session:
        row = await session.get(Listing, listing_id)
        row.notified_at = datetime.utcnow()
        await session.commit()
