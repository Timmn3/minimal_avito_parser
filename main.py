import asyncio
from multiprocessing import Process
from aiogram import Bot, Dispatcher
from loguru import logger

from parsing.util.kill_processes import kill_chrome_processes
from handlers.start import router as start_router
from handlers.menu import router as menu_router
from handlers.tasks import router as tasks_router
from utils.commands import set_default_commands

from config import BOT_TOKEN, ADMIN_IDS
from database.init_db import init_db


logger.add("logs/loguru.log", rotation="50 MB", level="INFO")


# === Функция запуска парсера ===
def run_parser():
    import asyncio
    from services.task_service import load_tasks_from_db
    from parsing.parser_avito import parse_avito
    from database.init_db import init_db as parser_init_db
    from aiogram import Bot as ParserBot
    from config import BOT_TOKEN

    async def parser_main():
        await parser_init_db()
        tasks = await load_tasks_from_db()
        if not tasks:
            logger.warning("Нет активных задач для запуска")
            return

        logger.info(f"Запускается {len(tasks)} активных задач парсинга")

        bot = ParserBot(token=BOT_TOKEN)
        parsers = [parse_avito(task, bot) for task in tasks if task['activity']]
        await asyncio.gather(*parsers)

    asyncio.run(parser_main())


# === Функция запуска бота ===
async def run_bot():
    await init_db()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(tasks_router)

    await set_default_commands(bot)

    try:
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, "🤖 Бот успешно запущен")
        logger.info("Бот запущен. Администраторы уведомлены.")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение админам: {e}")

    await dp.start_polling(bot)


# === Точка входа ===
if __name__ == "__main__":
    kill_chrome_processes()

    parser_process = Process(target=run_parser)
    parser_process.start()

    asyncio.run(run_bot())
