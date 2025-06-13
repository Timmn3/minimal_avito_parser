import asyncio
from loader import load_tasks, load_page_config
from loguru import logger

from parsing.util.kill_processes import kill_chrome_processes
from parsing.parser_avito import parse_avito

logger.add("logs/loguru.log", rotation="50 MB", level="INFO")


async def main():
    tasks = load_tasks()
    page_config = load_page_config()

    # Создаем список задач
    parsers = [parse_avito(task, page_config) for task in tasks if task['activity']]

    logger.info(f"Запускается {len(parsers)} активных задач")

    # Параллельный запуск
    await asyncio.gather(*parsers)


if __name__ == "__main__":
    kill_chrome_processes()  # Убиваем старые процессы перед стартом
    asyncio.run(main())