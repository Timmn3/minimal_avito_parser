from sqlalchemy import (Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, BigInteger, Text,
                        UniqueConstraint)
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="owner")
    seen_ads = relationship("SeenAd", back_populates="user")  # Новое отношение



class SeenAd(Base):
    __tablename__ = 'seen_ads'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)  # Новое поле связи
    item_id = Column(String, nullable=False, index=True)
    name = Column(String)
    price = Column(String)
    link = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="seen_ads")
    user = relationship("User", back_populates="seen_ads")  # Новое отношение

class Setting(Base):
    """Общие настройки бота (key-value). Лежат в БД, потому что бот и парсер - разные процессы."""
    __tablename__ = 'settings'

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id'))
    number = Column(Integer)
    teg = Column(String)
    url = Column(String)
    time_repeat = Column(Integer)
    count_page = Column(Integer)
    target_words = Column(JSON)
    stop_words = Column(JSON)
    max_ads_per_run = Column(Integer)
    activity = Column(Boolean)
    price_change = Column(Boolean)
    all_ads = Column(Boolean)
    min_price = Column(Integer, nullable=True)
    max_price = Column(Integer, nullable=True)
    # профиль товара (profiles/*.py): задан - задача research (собирает рынок), пусто - обычная «новые объявления»
    profile = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="tasks")
    seen_ads = relationship("SeenAd", order_by=SeenAd.timestamp.desc(), back_populates="task")


class Listing(Base):
    """Объявление, собранное research-задачей: данные из ленты + (для кандидатов) из карточки."""
    __tablename__ = 'listings'
    __table_args__ = (UniqueConstraint('task_id', 'item_id'),)

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False, index=True)
    item_id = Column(String, nullable=False, index=True)
    title = Column(String)
    price = Column(Integer)
    url = Column(String)
    location = Column(String)
    # заголовок и цена из ленты на момент появления: по ним ищем клоны-дубли (title/price потом уточняет карточка)
    feed_title = Column(String)
    feed_price = Column(Integer)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    price_changed_at = Column(DateTime)
    # карточка: None - не кандидат, pending - ждёт захода, ok - разобрана, failed - не удалось (после N попыток),
    # gone - снято, dup - клон уже разобранного объявления (тот же заголовок, цена и место)
    detail_status = Column(String, index=True)
    detail_attempts = Column(Integer, default=0)
    detail_fetched_at = Column(DateTime)
    params = Column(JSON)        # «Состояние», «Циклов перезарядки»... как на Авито
    description = Column(Text)
    seller = Column(JSON)        # имя, тип, рейтинг, отзывы, год на Авито, отметки
    posted = Column(String)      # дата публикации как на Авито («5 ноября в 14:54»)
    views = Column(Integer)
    notified_at = Column(DateTime)  # когда последний раз писали о нём в Telegram


class PriceHistory(Base):
    __tablename__ = 'price_history'

    id = Column(Integer, primary_key=True)
    listing_id = Column(Integer, ForeignKey('listings.id'), nullable=False, index=True)
    price = Column(Integer, nullable=False)
    seen_at = Column(DateTime, default=datetime.utcnow)

