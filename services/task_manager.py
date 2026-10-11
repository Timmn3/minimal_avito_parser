import asyncio
import time
from typing import Optional

from aiogram import Bot
from loguru import logger

from parsing.parser_avito import (MIN_REQUEST_INTERVAL, PAGE_BLOCKED, RequestGate, check_task_page,
                                  _is_dead_session)
from parsing.util.selenium_utils import setup_driver
from services.settings_service import get_queue_settings
from services.task_service import load_tasks_from_db

IDLE_POLL = 5  # сек. максимум между опросами БД, пока нет задач, готовых к проверке


def task_interval(task: dict) -> float:
    """Не чаще раза в MIN_REQUEST_INTERVAL (или time_repeat задачи, если он больше)."""
    return max(MIN_REQUEST_INTERVAL, task.get("time_repeat") or 0)


def pick_due_task(tasks: list, last_check: dict, now: float) -> tuple[Optional[dict], float]:
    """
    Выбор следующей задачи очереди среди активных: готова та, что не проверялась дольше своего интервала;
    из готовых берём ждущую дольше всех (ни разу не проверенные - первыми, по id).
    Возвращает (задача или None, через сколько сек освободится ближайшая).
    """
    due, soonest = [], float("inf")
    for task in tasks:
        last = last_check.get(task["id"], float("-inf"))
        ready_in = last + task_interval(task) - now
        if ready_in <= 0:
            due.append((last, task["id"], task))
        else:
            soonest = min(soonest, ready_in)
    if due:
        return min(due, key=lambda x: (x[0], x[1]))[2], 0.0
    return None, soonest


class TaskManager:
    """
    Один браузер и одна вкладка на все задачи. Задачи идут по очереди, между любыми двумя запросами к Авито -
    шаг очереди из настроек. Активные задачи и настройки читаются из БД перед каждым шагом, поэтому
    включение/выключение задач и правки в /settings подхватываются без перезапуска.
    """

    def __init__(self, bot: Bot):
        self.bot = bot
        self.gate = RequestGate()
        self.last_check: dict = {}   # task_id -> time.monotonic() последнего запроса
        self.next_page: dict = {}    # task_id -> индекс следующей страницы выдачи (count_page > 1)
        self.driver = None
        self.driver_started = 0.0
        self.page_state: dict = {'url': None}

    def _close_driver(self) -> None:
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
        self.driver = None
        self.page_state['url'] = None

    def _open_driver(self) -> None:
        self.driver = setup_driver()
        self.driver_started = time.monotonic()
        self.page_state['url'] = None
        logger.info("Браузер запущен")

    async def start(self):
        try:
            while True:
                try:
                    await self._tick()
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Ошибка очереди: {e}")
                    await asyncio.sleep(IDLE_POLL)
        finally:
            self._close_driver()

    async def _tick(self) -> None:
        settings = await get_queue_settings()
        tasks = [t for t in await load_tasks_from_db() if t["activity"]]

        if not tasks:
            if self.driver is not None:
                logger.info("Нет активных задач, закрываем браузер")
                self._close_driver()
            await asyncio.sleep(IDLE_POLL)
            return

        restart_minutes = settings["restart_minutes"]
        if self.driver is not None and restart_minutes and \
                time.monotonic() - self.driver_started >= restart_minutes * 60:
            logger.info(f"Плановый перезапуск браузера (каждые {restart_minutes} мин)")
            self._close_driver()

        task, wait_for = pick_due_task(tasks, self.last_check, time.monotonic())
        if task is None:
            await asyncio.sleep(min(max(wait_for, 1), IDLE_POLL))
            return

        if self.driver is None:
            self._open_driver()

        teg = task["teg"]
        page = self.next_page.get(task["id"], 0)
        try:
            status = await check_task_page(self.driver, task, page, self.bot, self.gate,
                                           settings["queue_step"], self.page_state)
            if status != PAGE_BLOCKED:
                self.next_page[task["id"]] = page + 1  # неудачную страницу повторим, а не пропустим
        except asyncio.CancelledError:
            raise
        except Exception as e:
            if "script timeout" in str(e):
                logger.warning(f"[{teg}] Таймаут при загрузке страницы")
            elif _is_dead_session(e):
                logger.warning(f"[{teg}] Браузер закрыт/упал, запускаем заново ({str(e).splitlines()[0]})")
                self._close_driver()
            else:
                logger.error(f"[{teg}] Ошибка при обработке: {e}")
        finally:
            # отсчёт интервала задачи - от последнего реального запроса, даже если шаг закончился ошибкой
            last_request = self.gate.last_request
            self.last_check[task["id"]] = last_request if last_request != float("-inf") else time.monotonic()
