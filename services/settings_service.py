from database.db import get_setting, set_setting

RESTART_MINUTES = "restart_minutes"  # раз в сколько минут перезапускать браузер, 0 - не перезапускать
QUEUE_STEP = "queue_step"            # пауза между любыми двумя запросами к Авито, сек
LOAD_MODE = "load_mode"              # как открывать страницу на каждом шаге очереди
CARD_INTERVAL = "card_interval"      # research: не чаще раза в столько сек заходим в карточку объявления
RESEARCH_NOTIFY = "research_notify"  # research: слать ли находки в Telegram ("1"/"0"), по умолчанию выключено

MODE_REFRESH = "refresh"      # тот же URL - refresh(), другой - get()
MODE_GET = "get"              # всегда get(): заход заново, без перезагрузки текущей страницы
MODE_GET_CLEAN = "get_clean"  # get() + чистка cookies и кэша: Авито видит нового посетителя
LOAD_MODES = (MODE_REFRESH, MODE_GET, MODE_GET_CLEAN)
LOAD_MODE_TITLES = {
    MODE_REFRESH: "refresh (обновление страницы)",
    MODE_GET: "get (заход заново)",
    MODE_GET_CLEAN: "get + чистка cookies и кэша",
}

DEFAULT_RESTART_MINUTES = 60
DEFAULT_QUEUE_STEP = 15
DEFAULT_LOAD_MODE = MODE_REFRESH  # прежнее поведение; на сервере режим переключается настройкой

MIN_RESTART_MINUTES = 5
MAX_RESTART_MINUTES = 1440
MIN_QUEUE_STEP = 10
MAX_QUEUE_STEP = 600

# карточки Авито бережёт сильнее ленты: проба 10.11.2026 с паузой 25 сек поймала 5 заглушек из 6
DEFAULT_CARD_INTERVAL = 240
MIN_CARD_INTERVAL = 60
MAX_CARD_INTERVAL = 3600


def validate_restart_minutes(value: int) -> bool:
    return value == 0 or MIN_RESTART_MINUTES <= value <= MAX_RESTART_MINUTES


def validate_queue_step(value: int) -> bool:
    return MIN_QUEUE_STEP <= value <= MAX_QUEUE_STEP


def validate_card_interval(value: int) -> bool:
    return MIN_CARD_INTERVAL <= value <= MAX_CARD_INTERVAL


async def _get_int(key: str, default: int) -> int:
    raw = await get_setting(key)
    try:
        return int(raw) if raw is not None else default
    except ValueError:
        return default  # битое значение в БД не должно ронять парсер


async def get_queue_settings() -> dict:
    """Текущие настройки очереди; парсер читает их перед каждым шагом, поэтому правки действуют сразу."""
    restart = await _get_int(RESTART_MINUTES, DEFAULT_RESTART_MINUTES)
    step = await _get_int(QUEUE_STEP, DEFAULT_QUEUE_STEP)
    mode = await get_setting(LOAD_MODE, DEFAULT_LOAD_MODE)
    if not validate_restart_minutes(restart):
        restart = DEFAULT_RESTART_MINUTES
    if not validate_queue_step(step):
        step = DEFAULT_QUEUE_STEP
    if mode not in LOAD_MODES:
        mode = DEFAULT_LOAD_MODE
    card = await _get_int(CARD_INTERVAL, DEFAULT_CARD_INTERVAL)
    if not validate_card_interval(card):
        card = DEFAULT_CARD_INTERVAL
    return {"restart_minutes": restart, "queue_step": step, "load_mode": mode, "card_interval": card}


async def save_restart_minutes(value: int) -> None:
    await set_setting(RESTART_MINUTES, value)


async def save_queue_step(value: int) -> None:
    await set_setting(QUEUE_STEP, value)


async def save_card_interval(value: int) -> None:
    await set_setting(CARD_INTERVAL, value)


async def cycle_load_mode() -> str:
    """Переключает режим загрузки на следующий по кругу и возвращает новый."""
    current = (await get_queue_settings())["load_mode"]
    new = LOAD_MODES[(LOAD_MODES.index(current) + 1) % len(LOAD_MODES)]
    await set_setting(LOAD_MODE, new)
    return new


async def get_research_notify() -> bool:
    return (await get_setting(RESEARCH_NOTIFY, "0")) == "1"


async def save_research_notify(on: bool) -> None:
    await set_setting(RESEARCH_NOTIFY, "1" if on else "0")
