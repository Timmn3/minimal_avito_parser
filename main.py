import asyncio
from aiogram import Bot, Dispatcher
from loguru import logger
from config import BOT_TOKEN, ADMIN_IDS
from database.init_db import init_db
from services.task_manager import TaskManager  # Новый импорт
from handlers.start import router as start_router
from handlers.menu import router as menu_router
from handlers.tasks import router as tasks_router
from utils.commands import set_default_commands
from parsing.util.kill_processes import kill_chrome_processes


logger.add("logs/loguru.log", rotation="50 MB", level="INFO")


async def run_bot():
    await init_db()
    kill_chrome_processes()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(tasks_router)

    await set_default_commands(bot)

    # === Запуск менеджера задач ===
    task_manager = TaskManager(bot)
    asyncio.create_task(task_manager.start())  # фоновый запуск

    try:
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, "🤖 Бот успешно запущен")
        logger.info("Бот запущен. Администраторы уведомлены.")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение админам: {e}")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(run_bot())
