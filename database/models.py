from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, BigInteger
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
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="tasks")
    seen_ads = relationship("SeenAd", order_by=SeenAd.timestamp.desc(), back_populates="task")

