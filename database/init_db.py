from sqlalchemy import text

from database.models import Base
from database.session import engine

# create_all создаёт только новые таблицы; новые колонки в существующих добавляем здесь.
# На сервере alembic не используется (таблицы всегда создавались через create_all).
SCHEMA_PATCHES = (
    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS profile VARCHAR",
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for sql in SCHEMA_PATCHES:
            await conn.execute(text(sql))
