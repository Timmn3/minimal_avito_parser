"""
Отчёт по research-задаче из БД (к Авито не ходит).

    cd /srv/avito_parser && sudo -u avito .venv/bin/python -m tools.report <task_id> [--tiers A,B] [--limit 40]
        [--desc]   - печатать описания (для разбора топа)
        [--ids 123,456] - только эти объявления
"""
import argparse
import asyncio
from collections import Counter

from sqlalchemy import select

from database.models import Listing, Task
from database.session import get_session
from profiles import get_profile
from services.research_scoring import evaluate, medians, worth_notifying


async def run(task_id: int, tiers: set, limit: int, desc: bool, ids: set) -> None:
    async with get_session() as session:
        task = await session.get(Task, task_id)
        rows = (await session.execute(select(Listing).where(Listing.task_id == task_id))).scalars().all()
    profile = get_profile(task.profile)
    group_medians = await medians(task_id, profile)
    status = Counter(r.detail_status or "не кандидат" for r in rows)
    print(f"# {task.teg}: объявлений {len(rows)}, карточки: {dict(status)}")

    print("\n## Медианы (группа: медиана, объявлений)")
    for key, (med, n) in sorted(group_medians.items(), key=lambda x: -x[1][1]):
        if n >= 3:
            print(f"  {key:<22} {med:>8,} ₽  n={n}".replace(",", " "))

    evaluated = []
    for r in rows:
        if ids and r.item_id not in ids:
            continue
        ev = evaluate(r, profile, group_medians)
        if ids or (ev["tier"] in tiers and r.detail_status in ("ok", "pending")):
            evaluated.append((r, ev))
    order = {"A": 0, "B": 1, "?": 2, "X": 3}
    evaluated.sort(key=lambda x: (x[0].detail_status != "ok", bool(x[1]["flags"]), order[x[1]["tier"]],
                                  x[1]["ratio"] or 9, x[0].price or 0))
    print(f"\n## Кандидаты ({len(evaluated)}, показаны первые {limit}); ✉ - прошёл бы фильтр уведомлений")
    for r, ev in evaluated[:limit]:
        ratio = f"{ev['ratio']:.0%}" if ev["ratio"] is not None else "  - "
        mark = "✉" if worth_notifying(r, ev) else " "
        card = "" if r.detail_status == "ok" else f" [{r.detail_status}]"
        print(f"{mark} {ev['tier']} {r.price:>7,} {ratio:>5} {str(ev['group']):<20} {r.title[:55]}{card}".replace(",", " "))
        print(f"      {r.location or ''} | {r.url}")
        if ev["flags"]:
            print("      🚩 " + "; ".join(ev["flags"]))
        if ev["pluses"]:
            print("      ➕ " + ", ".join(ev["pluses"]))
        for note in ev["notes"]:
            print("      " + note)
        if desc and r.description:
            print("      " + r.description.replace("\n", " ")[:700])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("task_id", type=int)
    ap.add_argument("--tiers", default="A,B,?")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--desc", action="store_true")
    ap.add_argument("--ids", default="")
    a = ap.parse_args()
    asyncio.run(run(a.task_id, set(a.tiers.split(",")), a.limit, a.desc, set(filter(None, a.ids.split(",")))))


if __name__ == "__main__":
    main()
