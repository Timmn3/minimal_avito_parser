from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from config import DATABASE_URL
from database.models import Base, User, Task, SeenAd, Setting
from database.session import get_session


engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_or_create_user(session, user_data):
    result = await session.execute(select(User).where(User.id == user_data['id']))
    user = result.scalars().first()
    if not user:
        user = User(**user_data)
        session.add(user)
        await session.flush()
    return user

async def get_user_tasks(session, user_id):
    result = await session.execute(select(Task).where(Task.user_id == user_id))
    return result.scalars().all()

async def add_task(session, task_data):
    task = Task(**task_data)
    session.add(task)
    await session.flush()
    return task

async def update_task(session, task_id, update_data):
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalars().first()

    if not task:
        print(f"[DEBUG] Задача с ID {task_id} не найдена. Создаем новую...")
        user_id = update_data.get('user_id')
        if not user_id:
            return None
        task = Task(id=task_id, user_id=user_id)
        session.add(task)

    for key, value in update_data.items():
        if value is not None:
            setattr(task, key, value)

    await session.flush()
    await session.commit()
    print(f"[DEBUG] Задача {task_id} обновлена/создана: {update_data}")
    return task

async def get_users_by_task(session, teg: str):
    result = await session.execute(
        select(User).join(Task).where(Task.teg == teg)
    )
    return result.scalars().all()


async def get_all_tasks():
    async with get_session() as session:
        result = await session.execute(select(Task))
        return result.scalars().all()

async def get_users_by_task_teg(teg: str):
    async with get_session() as session:
        result = await session.execute(
            select(User).join(Task).where(Task.teg == teg)
        )
        return result.scalars().all()

async def get_setting(key: str, default: str = None):
    async with get_session() as session:
        result = await session.execute(select(Setting.value).where(Setting.key == key))
        value = result.scalar()
        return value if value is not None else default


async def set_setting(key: str, value: str):
    async with get_session() as session:
        await session.merge(Setting(key=key, value=str(value)))
        await session.commit()


async def seen_ad_exists(task_id: int, item_id: str):
    async with get_session() as session:
        result = await session.execute(
            select(SeenAd).where(SeenAd.task_id == task_id, SeenAd.item_id == item_id)
        )
        return result.scalars().first() is not None


async def add_seen_ad(task_id: int, user_id: int, item_id: str, name: str, price: str, link: str):
    async with get_session() as session:
        seen_ad = SeenAd(
            task_id=task_id,
            user_id=user_id,
            item_id=item_id,
            name=name,
            price=price,
            link=link
        )
        session.add(seen_ad)
        await session.commit()
