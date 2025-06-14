import asyncio
from loguru import logger
from parsing.parser_avito import parse_avito
from services.task_service import load_tasks_from_db
from aiogram import Bot


class TaskManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running_tasks = {}  # task_id -> asyncio.Task
        self.lock = asyncio.Lock()

    async def start(self):
        while True:
            try:
                await self.sync_tasks()
            except Exception as e:
                logger.error(f"[TaskManager] Ошибка при синхронизации задач: {e}")
            await asyncio.sleep(10)  # Интервал проверки, можно изменить

    async def sync_tasks(self):
        tasks = await load_tasks_from_db()

        async with self.lock:
            current_ids = set(self.running_tasks.keys())
            active_tasks = [t for t in tasks if t["activity"]]
            active_ids = set(t["id"] for t in active_tasks)

            # === Запуск новых задач ===
            for task in active_tasks:
                if task["id"] not in current_ids:
                    logger.info(f"[TaskManager] Запуск новой задачи: {task['teg']} (ID {task['id']})")
                    task_future = asyncio.create_task(parse_avito(task, self.bot))
                    self.running_tasks[task["id"]] = task_future

            # === Остановка деактивированных задач ===
            for task_id in current_ids - active_ids:
                logger.info(f"[TaskManager] Остановка задачи ID {task_id}")
                task_future = self.running_tasks.pop(task_id)
                task_future.cancel()
