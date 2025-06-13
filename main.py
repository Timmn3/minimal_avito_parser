# main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from loader import load_tasks, load_page_config
from loguru import logger
from parsing.util.kill_processes import kill_chrome_processes
from parsing.parser_avito import parse_avito
from handlers.start import router as start_router
from config import BOT_TOKEN, ADMIN_IDS
from aiogram import Dispatcher
from middlewares.error_handler_middleware import ErrorHandlerMiddleware


# Настройка логгирования
logger.add("logs/loguru.log", rotation="50 MB", level="INFO")

dp = Dispatcher()
dp.update.middleware(ErrorHandlerMiddleware())

# === Парсер ===
async def run_parser(bot=None):
    tasks = load_tasks()
    page_config = load_page_config()

    parsers = [parse_avito(task, page_config, bot) for task in tasks if task['activity']]
    logger.info(f"Запускается {len(parsers)} активных задач парсинга")

    await asyncio.gather(*parsers)


# === Бот ===
async def run_bot():
    # Инициализируем бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Подключаем роутеры
    dp.include_router(start_router)

    # Уведомляем админа о запуске
    try:
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, "🤖 Бот успешно запущен")
        logger.info("Бот запущен. Администраторы уведомлены.")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение админам: {e}")

    # Запуск бота
    await dp.start_polling(bot)


# === Точка входа ===
if __name__ == "__main__":
    kill_chrome_processes()  # Убиваем старые процессы перед стартом

    # === Выбор режима запуска ===
    mode = input("Выберите режим запуска:\n1 - Только парсер\n2 - Только бот\n3 - Парсер + бот (параллельно)\n> ")

    if mode == '1':
        asyncio.run(run_parser())
    elif mode == '2':
        asyncio.run(run_bot())
    elif mode == '3':
        async def run_all():
            parser_task = asyncio.create_task(run_parser())
            bot_task = asyncio.create_task(run_bot())
            await asyncio.gather(parser_task, bot_task)

        asyncio.run(run_all())
    else:
        print("Неверный выбор режима.")