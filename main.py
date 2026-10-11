import asyncio
import socket
import subprocess
import sys
import time
from multiprocessing import Process
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from loguru import logger
from sqlalchemy import func, select
from config import BOT_TOKEN, ADMIN_IDS, TELEGRAM_PROXY, DB_NAME, DB_HOST
from database.db import async_session
from database.init_db import init_db
from database.session import engine as db_engine
from database.models import Task
from services.task_manager import TaskManager
from handlers.start import router as start_router
from handlers.menu import router as menu_router
from handlers.tasks import router as tasks_router
from utils.commands import set_default_commands
from utils.version import get_version
from parsing.parser_avito import MIN_REQUEST_INTERVAL
from parsing.util.kill_processes import kill_chrome_processes
from utils.memory_monitor import monitor_system_memory, log_total_memory


logger.add("logs/loguru.log", rotation="50 MB", level="INFO")

DEVELOPER_ID = 1089138631  # получает стартовое уведомление помимо ADMIN_IDS


def make_bot() -> Bot:
    """Бот с прокси для Telegram API (если задан TELEGRAM_PROXY). Картинки Авито качаются мимо него."""
    session = AiohttpSession(proxy=TELEGRAM_PROXY) if TELEGRAM_PROXY else None
    return Bot(token=BOT_TOKEN, session=session)


def _chrome_version() -> str:
    try:
        out = subprocess.check_output(["google-chrome", "--version"], stderr=subprocess.DEVNULL,
                                      encoding="utf-8", timeout=10)
        return out.strip().replace("Google Chrome ", "")
    except Exception:
        return "не найден"


async def _startup_message() -> str:
    try:
        async with async_session() as session:
            active_tasks = (await session.execute(
                select(func.count()).select_from(Task).where(Task.activity.is_(True)))).scalar()
    except Exception as e:
        logger.warning(f"Не удалось посчитать активные задачи: {e}")
        active_tasks = "?"

    return (
        f"🚀 {get_version()}\n"
        f"──────────────\n"
        f"🌐 Прокси Telegram: {TELEGRAM_PROXY or '❌ нет'}\n"
        f"🗄 БД: {DB_NAME}@{DB_HOST}\n"
        f"🖥 Сервер: {socket.gethostname()}\n"
        f"🧭 Chrome: {_chrome_version()}\n"
        f"⏱ Мин. интервал запросов к Авито: {MIN_REQUEST_INTERVAL} сек\n"
        f"📋 Активных задач: {active_tasks}"
    )


async def run_bot_process():
    """Запуск бота в отдельном процессе"""
    kill_chrome_processes()

    log_total_memory("Bot")  # до запуска
    asyncio.create_task(monitor_system_memory("Bot"))  # фоновый мониторинг

    bot = make_bot()
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(tasks_router)

    await set_default_commands(bot)

    text = await _startup_message()
    for chat_id in dict.fromkeys([DEVELOPER_ID, *ADMIN_IDS]):  # без дублей, порядок сохраняем
        try:
            await bot.send_message(chat_id, text)
        except Exception as e:
            logger.error(f"Не удалось отправить стартовое сообщение {chat_id}: {e}")
    logger.info("Бот запущен.")

    await dp.start_polling(bot)


async def run_parser_process():
    """Запуск парсера в отдельном процессе"""
    kill_chrome_processes()

    bot = make_bot()
    task_manager = TaskManager(bot)
    await task_manager.start()


def _die_with_parent():
    """
    Linux: ребёнок получает SIGKILL, если умер главный процесс. Иначе после kill -9 главного
    бот и парсер остаются сиротами и работают рядом с новым запуском (двойной поллинг и двойные запросы к Авито).
    """
    if not sys.platform.startswith("linux"):
        return
    try:
        import ctypes
        import signal
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, signal.SIGKILL)  # 1 = PR_SET_PDEATHSIG
    except Exception as e:
        logger.warning(f"PR_SET_PDEATHSIG не установлен: {e}")


def run_bot():
    """Обертка для запуска бота в процессе"""
    _die_with_parent()
    asyncio.run(run_bot_process())


def run_parser():
    """Обертка для запуска парсера в процессе"""
    _die_with_parent()
    asyncio.run(run_parser_process())


if __name__ == "__main__":
    # Таблицы создаём один раз до старта процессов: параллельный create_all на пустой БД падает на дубликате типа.
    # Пул закрываем, иначе дочерние процессы унаследуют через fork соединения, привязанные к чужому event loop.
    async def _prepare_db():
        await init_db()
        await db_engine.dispose()

    asyncio.run(_prepare_db())

    # Создаем и запускаем процессы
    bot_process = Process(target=run_bot)
    parser_process = Process(target=run_parser)

    bot_process.start()
    parser_process.start()

    exit_code = 0
    try:
        # Упал любой из двух - гасим всё и выходим с ошибкой, чтобы supervisor поднял сервис заново
        while bot_process.is_alive() and parser_process.is_alive():
            time.sleep(1)
        dead = "бота" if not bot_process.is_alive() else "парсера"
        logger.error(f"Процесс {dead} завершился, останавливаем сервис для перезапуска")
        exit_code = 1
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, завершаем процессы...")

    for proc in (bot_process, parser_process):
        if proc.is_alive():
            proc.terminate()
        proc.join()
    kill_chrome_processes()
    logger.info("Процессы завершены.")
    sys.exit(exit_code)
