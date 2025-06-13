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

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id'))
    number = Column(Integer)  # номер задачи (1, 2, 3...)
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
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="tasks")