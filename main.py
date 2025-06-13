import asyncio
from aiogram import Bot, Dispatcher
from loguru import logger

# === Импорты из проекта ===
from parsing.util.kill_processes import kill_chrome_processes
from parsing.parser_avito import parse_avito

from handlers.start import router as start_router
from handlers.menu import router as menu_router
from handlers.tasks import router as tasks_router
from utils.commands import set_default_commands

from services.task_service import load_tasks_from_db

from config import BOT_TOKEN, ADMIN_IDS
from database.init_db import init_db


# === Настройка логгирования ===
logger.add("logs/loguru.log", rotation="50 MB", level="INFO")


# === Функция запуска парсера ===
async def run_parser(bot: Bot):
    await init_db()
    tasks = await load_tasks_from_db()

    if not tasks:
        logger.warning("Нет активных задач для запуска")
        return

    logger.info(f"Запускается {len(tasks)} активных задач парсинга")

    parsers = [parse_avito(task, {}, bot) for task in tasks if task['activity']]
    await asyncio.gather(*parsers)


# === Функция запуска бота ===
async def run_bot():
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем все роутеры
    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(tasks_router)

    await set_default_commands(bot)

    # Уведомление админов
    try:
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, "🤖 Бот успешно запущен")
        logger.info("Бот запущен. Администраторы уведомлены.")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение админам: {e}")

    # Старт polling
    await dp.start_polling(bot)


# === Точка входа ===
if __name__ == "__main__":
    kill_chrome_processes()  # Очищаем старые процессы Chrome/Chromedriver

    # Создаем бота до запуска задач
    bot = Bot(token=BOT_TOKEN)

    async def run_all():
        parser_task = asyncio.create_task(run_parser(bot))
        bot_task = asyncio.create_task(run_bot())
        await asyncio.gather(parser_task, bot_task)

    asyncio.run(run_all())