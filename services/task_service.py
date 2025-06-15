from database.db import get_all_tasks
from database.models import Task


def serialize_task(task: Task) -> dict:
    return {
        "id": task.id,
        "user_id": task.user_id,
        "number": task.number,
        "teg": task.teg,
        "url": task.url,
        "time_repeat": task.time_repeat,
        "count_page": task.count_page,
        "target_words": task.target_words or [],
        "stop_words": task.stop_words or [],
        "max_ads_per_run": task.max_ads_per_run,
        "activity": task.activity,
        "price_change": task.price_change,
        "all_ads": task.all_ads,
        "min_price": task.min_price,
        "max_price": task.max_price,
    }


async def load_tasks_from_db() -> list[dict]:
    tasks = await get_all_tasks()
    return [serialize_task(task) for task in tasks]
