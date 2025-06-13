import os
import asyncio
from loader import load_tasks, load_page_config
from loguru import logger
from util.parser_avito import parse_avito

logger.add("logs/loguru.log", rotation="50 MB", level="INFO")


def kill_chrome_processes():
    """
    Убивает все процессы chrome и chromedriver.
    Работает под Linux/Unix системами.
    """
    try:
        # Получаем PID процессов
        chrome_pids = os.popen("pgrep -f chrome").read().splitlines()
        driver_pids = os.popen("pgrep -f chromedriver").read().splitlines()

        all_pids = set(chrome_pids + driver_pids)

        if all_pids:
            logger.info(f"Найдены зависшие процессы Chrome/Chromedriver: {all_pids}")
            for pid in all_pids:
                os.system(f"kill -9 {pid}")
            logger.info(f"Завершены {len(all_pids)} зависших процессов Chrome/Chromedriver")
        else:
            logger.info("Нет зависших процессов Chrome/Chromedriver")

    except Exception as e:
        logger.error(f"Ошибка при убивании процессов: {e}")


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