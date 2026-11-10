"""
Управление research-задачами из консоли сервера (в меню бота профиль пока не выбрать).

    cd /srv/avito_parser && sudo -u avito .venv/bin/python -m tools.research_task list
    ... add <user_id> <teg> <profile> "<url>" [--interval 3600]
    ... on|off <task_id>
"""
import argparse
import asyncio

from sqlalchemy import func, select

from database.init_db import init_db
from database.models import Listing, Task, User
from database.session import get_session
from profiles import PROFILES


async def cmd_list() -> None:
    async with get_session() as session:
        tasks = (await session.execute(select(Task).order_by(Task.id))).scalars().all()
        counts = dict((await session.execute(
            select(Listing.task_id, func.count()).group_by(Listing.task_id))).all())
    for t in tasks:
        kind = f"research:{t.profile}" if t.profile else "notify"
        print(f"#{t.id} user={t.user_id} [{'ON ' if t.activity else 'off'}] {t.teg!r} {kind} "
              f"каждые {t.time_repeat} с, объявлений {counts.get(t.id, 0)}\n    {t.url}")


async def cmd_add(user_id: int, teg: str, profile: str, url: str, interval: int) -> None:
    if profile not in PROFILES:
        raise SystemExit(f"Нет профиля {profile!r}, есть: {', '.join(PROFILES)}")
    async with get_session() as session:
        if await session.get(User, user_id) is None:
            raise SystemExit(f"Пользователя {user_id} нет в БД (он должен хотя бы раз нажать /start)")
        number = (await session.execute(
            select(func.coalesce(func.max(Task.number), 0)).where(Task.user_id == user_id))).scalar() + 1
        task = Task(user_id=user_id, number=number, teg=teg, url=url, time_repeat=interval, count_page=1,
                    target_words=[], stop_words=[], max_ads_per_run=50, activity=True, price_change=False,
                    all_ads=False, profile=profile)
        session.add(task)
        await session.commit()
        print(f"Создана research-задача #{task.id} ({teg}), профиль {profile}, интервал {interval} с")


async def cmd_toggle(task_id: int, on: bool) -> None:
    async with get_session() as session:
        task = await session.get(Task, task_id)
        if task is None:
            raise SystemExit(f"Задачи #{task_id} нет")
        task.activity = on
        await session.commit()
        print(f"#{task_id} {task.teg!r}: {'включена' if on else 'выключена'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    a = sub.add_parser("add")
    a.add_argument("user_id", type=int)
    a.add_argument("teg")
    a.add_argument("profile")
    a.add_argument("url")
    a.add_argument("--interval", type=int, default=3600)
    for name in ("on", "off"):
        sub.add_parser(name).add_argument("task_id", type=int)
    args = ap.parse_args()

    async def run():
        await init_db()  # на случай, если утилиту запустили раньше обновлённого сервиса
        if args.cmd == "list":
            await cmd_list()
        elif args.cmd == "add":
            await cmd_add(args.user_id, args.teg, args.profile, args.url, args.interval)
        else:
            await cmd_toggle(args.task_id, args.cmd == "on")

    asyncio.run(run())


if __name__ == "__main__":
    main()
