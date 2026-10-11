import os
from dotenv import load_dotenv
from pathlib import Path

# Загрузка .env файла
load_dotenv()

# Путь к проекту
BASE_DIR = Path(__file__).resolve().parent.parent

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверяем, что токен задан
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env файле")

# Прокси для Telegram API (на серверах без прямого доступа к Telegram), например socks5://127.0.0.1:1080.
# Авито через него НЕ ходит - Chrome подключается напрямую.
TELEGRAM_PROXY = os.getenv("TELEGRAM_PROXY") or None

# Список админов
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []

# Настройки логгирования
LOGS_PATH = BASE_DIR / os.getenv("LOGS_PATH", "logs/bot.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

