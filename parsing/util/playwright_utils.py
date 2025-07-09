import random
from pathlib import Path
from loguru import logger
from playwright.async_api import async_playwright

# Исправленный путь к файлу с User-Agent
USER_AGENT_FILE = Path(__file__).resolve().parent.parent / 'data' / 'user-agent-database.txt'


async def setup_browser():
    # Чтение User-Agent из файла
    try:
        if USER_AGENT_FILE.exists():
            user_agents = USER_AGENT_FILE.read_text(encoding='utf-8').splitlines()
            user_agents = [ua.strip() for ua in user_agents if ua.strip()]
            user_agent = random.choice(user_agents) if user_agents else None
            logger.info(f"Выбран User-Agent: {user_agent[:60]}...")
        else:
            logger.warning(f"Файл User-Agent не найден: {USER_AGENT_FILE}")
            user_agent = None
    except Exception as e:
        logger.error(f"Ошибка чтения User-Agent файла: {e}")
        user_agent = None

    playwright = await async_playwright().start()

    # Если не удалось прочитать User-Agent, используем дефолтный
    if not user_agent:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        logger.info("Используется стандартный User-Agent")

    # Дополнительные опции запуска
    launch_options = {
        "headless": True,
        "args": [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--memory-pressure-off',
            '--disable-software-rasterizer',
            '--no-zygote',
            '--js-flags="--max-old-space-size=64"',
            '--window-size=1200,800'
        ]
    }

    browser = await playwright.chromium.launch(**launch_options)

    context_options = {
        "user_agent": user_agent,
        "viewport": {'width': 1200, 'height': 800},
        "ignore_https_errors": True,
        "java_script_enabled": True,
        "bypass_csp": True,
        "color_scheme": 'light',
        "locale": 'ru-RU',
        "timezone_id": 'Europe/Moscow'
    }

    context = await browser.new_context(**context_options)

    # Добавляем скрипт для маскировки под обычный браузер
    await context.add_init_script("""
        delete navigator.__proto__.webdriver;
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3],
            configurable: true
        });
        Object.defineProperty(navigator, 'languages', {
            get: () => ['ru-RU', 'ru'],
            configurable: true
        });
        window.chrome = {
            app: {
                isInstalled: false,
                InstallState: {},
                RunningState: {}
            },
            runtime: {
                OnInstalledReason: {},
                OnRestartRequiredReason: {},
                PlatformArch: {},
                PlatformNaclArch: {},
                PlatformOs: {},
                RequestUpdateCheckStatus: {}
            }
        };
    """)

    return context, browser, playwright