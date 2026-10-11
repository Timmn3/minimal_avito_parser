from database.db import get_setting, set_setting

RESTART_MINUTES = "restart_minutes"  # раз в сколько минут перезапускать браузер, 0 - не перезапускать
QUEUE_STEP = "queue_step"            # пауза между любыми двумя запросами к Авито, сек

DEFAULT_RESTART_MINUTES = 60
DEFAULT_QUEUE_STEP = 15

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
    if not validate_restart_minutes(restart):
        restart = DEFAULT_RESTART_MINUTES
    if not validate_queue_step(step):
        step = DEFAULT_QUEUE_STEP
    return {"restart_minutes": restart, "queue_step": step}


async def save_restart_minutes(value: int) -> None:
    await set_setting(RESTART_MINUTES, value)


async def save_queue_step(value: int) -> None:
    await set_setting(QUEUE_STEP, value)
