import asyncio
from loguru import logger
from parsing.parser_avito import parse_avito
from services.task_service import load_tasks_from_db
from aiogram import Bot
from datetime import datetime, timedelta


class TaskManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.running_tasks = {}  # task_id -> asyncio.Task
        self.lock = asyncio.Lock()
        self.last_restart = datetime.now()

    async def start(self):
        while True:
            try:
                # Проверяем, нужно ли выполнить принудительный перезапуск
                if datetime.now() - self.last_restart > timedelta(minutes=10):
                    logger.info("[TaskManager] Выполняю принудительный перезапуск всех задач")
                    await self.restart_all_tasks()
                    self.last_restart = datetime.now()

                await self.sync_tasks()
            except Exception as e:
                logger.error(f"[TaskManager] Ошибка при синхронизации задач: {e}")
            await asyncio.sleep(10)  # Интервал проверки

    async def restart_all_tasks(self):
        """Принудительно перезапускает все активные задачи"""
        async with self.lock:
            # Сначала останавливаем все текущие задачи
            for task_id, task_future in list(self.running_tasks.items()):
                task_future.cancel()
                try:
                    await task_future
                except asyncio.CancelledError:
                    pass
                self.running_tasks.pop(task_id)

            # Затем загружаем и запускаем активные задачи снова
            tasks = await load_tasks_from_db()
            active_tasks = [t for t in tasks if t["activity"]]

            for task in active_tasks:
                logger.info(f"[TaskManager] Перезапуск задачи: {task['teg']} (ID {task['id']})")
                task_future = asyncio.create_task(run_with_restart(task, self.bot))
                self.running_tasks[task["id"]] = task_future

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
                    task_future = asyncio.create_task(run_with_restart(task, self.bot))
                    self.running_tasks[task["id"]] = task_future

            # === Остановка деактивированных задач ===
            for task_id in current_ids - active_ids:
                logger.info(f"[TaskManager] Остановка задачи ID {task_id}")
                task_future = self.running_tasks.pop(task_id)
                task_future.cancel()


async def run_with_restart(task_data, bot):
    teg = task_data["teg"]
    attempt = 1
    while True:
        try:
            logger.info(f"[{teg}] Запуск задачи (попытка #{attempt})")
            await parse_avito(task_data, bot)
            logger.info(f"[{teg}] Задача завершена нормально.")
            break
        except Exception as e:
            logger.exception(f"[{teg}] Ошибка: {e}. Перезапуск через 5 сек.")
            attempt += 1
            await asyncio.sleep(5)




