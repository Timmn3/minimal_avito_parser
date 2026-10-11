from database.db import get_setting, set_setting

RESTART_MINUTES = "restart_minutes"  # раз в сколько минут перезапускать браузер, 0 - не перезапускать
QUEUE_STEP = "queue_step"            # пауза между любыми двумя запросами к Авито, сек
LOAD_MODE = "load_mode"              # как открывать страницу на каждом шаге очереди

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


def validate_restart_minutes(value: int) -> bool:
    return value == 0 or MIN_RESTART_MINUTES <= value <= MAX_RESTART_MINUTES


def validate_queue_step(value: int) -> bool:
    return MIN_QUEUE_STEP <= value <= MAX_QUEUE_STEP


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
    return {"restart_minutes": restart, "queue_step": step, "load_mode": mode}


async def save_restart_minutes(value: int) -> None:
    await set_setting(RESTART_MINUTES, value)


async def save_queue_step(value: int) -> None:
    await set_setting(QUEUE_STEP, value)


async def cycle_load_mode() -> str:
    """Переключает режим загрузки на следующий по кругу и возвращает новый."""
    current = (await get_queue_settings())["load_mode"]
    new = LOAD_MODES[(LOAD_MODES.index(current) + 1) % len(LOAD_MODES)]
    await set_setting(LOAD_MODE, new)
    return new
