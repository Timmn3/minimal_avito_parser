from database.db import get_all_tasks

async def load_tasks_from_db():
    tasks = await get_all_tasks()
    return [task.__dict__ for task in tasks]