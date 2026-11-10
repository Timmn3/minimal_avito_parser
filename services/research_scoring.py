"""
Оценка объявлений research-задачи: медиана цены по группе конфигурации, плюсы, красные флаги, решение «слать ли».

Красные флаги - отдельно от плюсов: объявление с флагом не уходит в Telegram, сколько бы плюсов ни было.
"""
import html
import re
import statistics
from datetime import datetime, timedelta
from types import ModuleType
from typing import Optional

from sqlalchemy import select

from database.models import Listing
from database.session import get_session
from profiles.base import is_obfuscated, normalize

MEDIAN_WINDOW_DAYS = 14   # медиана по объявлениям, виденным за столько дней
MIN_GROUP = 5             # меньше объявлений в группе - медиане не доверяем
CHEAP_SUSPICIOUS = 0.75   # дешевле 75% медианы - похоже на развод
B_NOTIFY_RATIO = 0.90     # B шлём, только если цена не выше 90% медианы
PRICE_DROP_NOTIFY = 0.03  # снижение цены от 3% у объявления, о котором уже писали

GOOD_REGIONS = ("москв", "московск", "новороссийск")
_SCAM = re.compile(r"предоплат|только доставк|только почт|пишите в (?:тг|телеграм|whatsapp|ватсап)|"
                   r"\b(?:тг|telegram|whatsapp|ватсап)\b.{0,15}@", re.I)


def specs_of(row: Listing, profile: ModuleType) -> dict:
    return profile.extract(row.title or "", row.description or "", row.params or None)


async def medians(task_id: int, profile: ModuleType) -> dict[str, tuple[int, int]]:
    """Группа конфигурации -> (медиана цены, число объявлений) по свежим объявлениям задачи."""
    since = datetime.utcnow() - timedelta(days=MEDIAN_WINDOW_DAYS)
    async with get_session() as session:
        rows = (await session.execute(
            select(Listing).where(Listing.task_id == task_id, Listing.last_seen >= since,
                                  Listing.price.is_not(None)))).scalars().all()
    groups: dict[str, list[int]] = {}
    for row in rows:
        if row.detail_status == 'gone':
            continue
        key = profile.group_key(specs_of(row, profile))
        if key:
            groups.setdefault(key, []).append(row.price)
    return {k: (int(statistics.median(v)), len(v)) for k, v in groups.items()}


def evaluate(row: Listing, profile: ModuleType, group_medians: dict) -> dict:
    """Оценка одного объявления. Флаги считаются только по данным карточки (если она разобрана)."""
    specs = specs_of(row, profile)
    tier = profile.tier(specs)
    key = profile.group_key(specs)
    median, n = group_medians.get(key, (None, 0))
    ratio = row.price / median if (median and n >= MIN_GROUP and row.price) else None

    flags, pluses = [], []
    if ratio is not None and ratio < CHEAP_SUSPICIOUS:
        flags.append(f"цена {ratio:.0%} от медианы")
    if row.detail_status == 'ok':
        desc = row.description or ""
        seller = row.seller or {}
        if _SCAM.search(normalize(desc)):
            flags.append("предоплата/уход в мессенджер")
        if specs.get("defects"):
            flags.append("дефекты: " + "; ".join(specs["defects"]))
        cond = (specs.get("condition") or "").lower()
        if cond and cond not in ("новое", "отличное", "хорошее"):
            flags.append(f"состояние: {specs['condition']}")
        if not seller.get("reviews"):
            flags.append("продавец без отзывов")
        if is_obfuscated(desc):
            pluses.append("⚠️ текст замаскирован латиницей")  # не флаг: часто у честных, но стоит знать
        if specs.get("cyrillic"):
            pluses.append("кириллица")
        elif specs.get("cyrillic") is False:
            pluses.append("⚠️ без кириллицы")
        if "коробк" in (specs.get("kit") or "").lower():
            pluses.append("коробка")
        if specs.get("cycles") is not None:
            pluses.append(f"{specs['cycles']} циклов")
        if (seller.get("rating") or 0) >= 4.8 and (seller.get("reviews") or 0) >= 10:
            pluses.append(f"продавец {seller['rating']} ({seller['reviews']} отз.)")
        if seller.get("reliable"):
            pluses.append("надёжный продавец")
    if any(r in (row.location or "").lower() for r in GOOD_REGIONS):
        pluses.append(row.location.split(",")[0])

    return {"specs": specs, "tier": tier, "group": key, "median": median, "group_n": n, "ratio": ratio,
            "flags": flags, "pluses": pluses}


def worth_notifying(row: Listing, ev: dict) -> bool:
    """«Хлам не слать»: только разобранная карточка, без флагов, A не дороже медианы, B заметно дешевле."""
    if row.detail_status != 'ok' or ev["flags"]:
        return False
    if ev["tier"] == "A":
        return ev["ratio"] is None or ev["ratio"] <= 1.0
    if ev["tier"] == "B":
        return ev["ratio"] is not None and ev["ratio"] <= B_NOTIFY_RATIO
    return False


def format_message(row: Listing, ev: dict, title: str, old_price: Optional[int] = None) -> str:
    s = ev["specs"]
    spec = " / ".join(x for x in (s.get("chip"), f"{s['ram']} ГБ" if s.get("ram") else None,
                                   f"{s['ssd'] // 1024} ТБ" if (s.get("ssd") or 0) >= 1024
                                   else (f"{s['ssd']} ГБ" if s.get("ssd") else None)) if x)
    price = f"{row.price:,}".replace(",", " ")
    head = (f"📉 Цена снижена: {old_price:,} → {price} ₽".replace(",", " ") if old_price
            else f"{'🟢' if ev['tier'] == 'A' else '🟡'} {html.escape(title)}: {ev['tier']}")
    median = (f"медиана {ev['median']:,} ₽ по {ev['group_n']} объявл. ({ev['ratio']:.0%})".replace(",", " ")
              if ev["ratio"] is not None else "медианы по группе пока нет")
    lines = [head, f"<b>{html.escape(row.title or '')}</b>", f"💰 {price} ₽ - {median}", f"⚙️ {spec}"]
    if ev["pluses"]:
        lines.append("➕ " + html.escape(", ".join(ev["pluses"])))
    lines.append(row.url)
    return "\n".join(lines)
