"""Очередь: проход research-задачи по страницам, повтор после заглушки, карточки в простое."""
import asyncio
import time

import services.task_manager as tm
from parsing.parser_avito import PAGE_BLOCKED

TASK = {"id": 7, "teg": "mbp", "profile": "macbook_pro_14", "time_repeat": 3600, "activity": True}


def make_manager(monkeypatch, pages, has=False):
    calls = []

    async def fake_step(driver, task, page, first, gate, step, state, mode, bot=None):
        calls.append((page, first))
        return pages[len(calls) - 1]

    async def fake_has(task_id):
        return has

    monkeypatch.setattr(tm, "research_step", fake_step)
    monkeypatch.setattr(tm, "has_listings", fake_has)
    m = tm.TaskManager(bot=None)
    m.driver = object()
    return m, calls


SETTINGS = {"queue_step": 15, "load_mode": "refresh", "card_interval": 240, "restart_minutes": 0}


def test_pass_goes_through_pages_then_waits_interval(monkeypatch):
    m, calls = make_manager(monkeypatch, [("ok", True), ("ok", True), ("ok", False)])
    for _ in range(3):
        asyncio.run(m._research(TASK, SETTINGS))
        if m.research_pass:
            assert m.last_check[7] == float("-inf")  # следующая страница - сразу
    assert calls == [(0, True), (1, True), (2, True)]
    assert 7 not in m.research_pass
    task, wait = tm.pick_due_task([TASK], m.last_check, time.monotonic())
    assert task is None and wait > 3000


def test_blocked_page_retried_soon_same_page(monkeypatch):
    m, calls = make_manager(monkeypatch, [("ok", True), (PAGE_BLOCKED, False), ("ok", False)], has=True)
    asyncio.run(m._research(TASK, SETTINGS))
    asyncio.run(m._research(TASK, SETTINGS))
    assert m.research_pass[7] == (1, False)
    _, wait = tm.pick_due_task([TASK], m.last_check, time.monotonic())
    assert 0 < wait <= tm.BLOCKED_RETRY
    asyncio.run(m._research(TASK, SETTINGS))
    assert calls == [(0, False), (1, False), (1, False)]


def test_card_only_when_interval_passed(monkeypatch):
    m, _ = make_manager(monkeypatch, [])
    done = []

    async def fake_next(profiles):
        assert list(profiles) == [7]
        return {"id": 1, "item_id": "42", "url": "u", "task_id": 7}

    async def fake_card(driver, listing, gate, step, state, mode, bot=None):
        done.append(listing["item_id"])
        return True

    monkeypatch.setattr(tm, "next_card", fake_next)
    monkeypatch.setattr(tm, "card_step", fake_card)
    notify_task = {"id": 8, "teg": "old", "profile": None, "time_repeat": 30, "activity": True}
    assert asyncio.run(m._maybe_card([TASK, notify_task], SETTINGS))
    assert not asyncio.run(m._maybe_card([TASK, notify_task], SETTINGS))  # рано
    assert done == ["42"]
