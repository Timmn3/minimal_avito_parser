import asyncio
from loguru import logger
from parsing.parser_avito import parse_avito
from services.task_service import load_tasks_from_db
from aiogram import Bot
from datetime import datetime, timedelta


class TaskManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running_tasks = {}
        self.lock = asyncio.Lock()
        self.last_restart = datetime.now()

    async def start(self):
        while True:
            try:
                if datetime.now() - self.last_restart > timedelta(minutes=10):
                    logger.info("Принудительный перезапуск задач")
                    await self.restart_all_tasks()
                    self.last_restart = datetime.now()
                await self.sync_tasks()
            except Exception as e:
                logger.error(f"Ошибка синхронизации: {e}")
            await asyncio.sleep(10)

    async def restart_all_tasks(self):
        async with self.lock:
            for task_id, task in list(self.running_tasks.items()):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                self.running_tasks.pop(task_id)

            tasks = await load_tasks_from_db()
            active_tasks = [t for t in tasks if t["activity"]]

            for task in active_tasks:
                logger.info(f"Перезапуск задачи: {task['teg']}")
                task_future = asyncio.create_task(run_with_restart(task, self.bot))
                self.running_tasks[task["id"]] = task_future

    async def sync_tasks(self):
        tasks = await load_tasks_from_db()
        async with self.lock:
            current_ids = set(self.running_tasks.keys())
            active_ids = set(t["id"] for t in tasks if t["activity"])

            # Запуск новых задач
            for task in tasks:
                if task["activity"] and task["id"] not in current_ids:
                    logger.info(f"Запуск новой задачи: {task['teg']}")
                    task_future = asyncio.create_task(run_with_restart(task, self.bot))
                    self.running_tasks[task["id"]] = task_future

            # Остановка деактивированных
            for task_id in current_ids - active_ids:
                logger.info(f"Остановка задачи ID {task_id}")
                task_future = self.running_tasks.pop(task_id)
                task_future.cancel()


async def run_with_restart(task_data, bot):
    teg = task_data["teg"]
    attempt = 1
    while True:
        try:
            logger.info(f"[{teg}] Запуск (попытка #{attempt})")
            await parse_avito(task_data, bot)
        except Exception as e:
            logger.error(f"[{teg}] Ошибка: {e}")
            attempt += 1
            await asyncio.sleep(5)