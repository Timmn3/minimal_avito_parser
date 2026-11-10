from sqlalchemy import text

from database.models import Base
from database.session import engine

# create_all создаёт только новые таблицы; новые колонки в существующих добавляем здесь.
# На сервере alembic не используется (таблицы всегда создавались через create_all).
SCHEMA_PATCHES = (
    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS profile VARCHAR",
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS feed_title VARCHAR",
    "ALTER TABLE listings ADD COLUMN IF NOT EXISTS feed_price INTEGER",
    # листинги, созданные до появления колонок: лента на момент появления ~ title/price (у разобранных title
    # взят из карточки, он обычно совпадает с заголовком ленты)
    "UPDATE listings SET feed_title = title, feed_price = price WHERE feed_title IS NULL",
    # идемпотентная уборка: ждущие клоны уже разобранных объявлений (тот же заголовок, цена и место) - dup
    "UPDATE listings l SET detail_status = 'dup' WHERE l.detail_status = 'pending' AND EXISTS ("
    "SELECT 1 FROM listings o WHERE o.task_id = l.task_id AND o.id <> l.id AND o.detail_status IN ('ok', 'gone') "
    "AND o.feed_title = l.feed_title AND o.feed_price = l.feed_price AND o.location IS NOT DISTINCT FROM l.location)",
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for sql in SCHEMA_PATCHES:
            await conn.execute(text(sql))
