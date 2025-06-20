import asyncio
from multiprocessing import Process
from aiogram import Bot, Dispatcher
from loguru import logger
from config import BOT_TOKEN, ADMIN_IDS
from database.init_db import init_db
from services.task_manager import TaskManager
from handlers.start import router as start_router
from handlers.menu import router as menu_router
from handlers.tasks import router as tasks_router
from utils.commands import set_default_commands
from parsing.util.kill_processes import kill_chrome_processes
from utils.memory_monitor import monitor_system_memory, log_total_memory


logger.add("logs/loguru.log", rotation="50 MB", level="INFO")


async def run_bot_process():
    """Запуск бота в отдельном процессе"""
    await init_db()
    kill_chrome_processes()

    log_total_memory("Bot")  # до запуска
    asyncio.create_task(monitor_system_memory("Bot"))  # фоновый мониторинг

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(tasks_router)

    await set_default_commands(bot)

    try:
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, "🤖 Бот успешно запущен ")
        logger.info("Бот запущен. Администраторы уведомлены.")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение админам: {e}")

    await dp.start_polling(bot)


async def run_parser_process():
    """Запуск парсера в отдельном процессе"""
    await init_db()
    kill_chrome_processes()

    bot = Bot(token=BOT_TOKEN)
    task_manager = TaskManager(bot)
    await task_manager.start()


def run_bot():
    """Обертка для запуска бота в процессе"""
    asyncio.run(run_bot_process())


def run_parser():
    """Обертка для запуска парсера в процессе"""
    asyncio.run(run_parser_process())


if __name__ == "__main__":
    # Создаем и запускаем процессы
    bot_process = Process(target=run_bot)
    parser_process = Process(target=run_parser)

    bot_process.start()
    parser_process.start()

    try:
        # Ожидаем завершения процессов (обычно бесконечно)
        bot_process.join()
        parser_process.join()
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, завершаем процессы...")
        bot_process.terminate()
        parser_process.terminate()
        bot_process.join()
        parser_process.join()
        logger.info("Процессы завершены.")