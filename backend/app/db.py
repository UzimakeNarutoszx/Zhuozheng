from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Integer, String, Text, UniqueConstraint, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

engine = create_engine(settings.database_url, connect_args={'check_same_thread': False, 'timeout': 30} if settings.database_url.startswith('sqlite:') else {}, pool_pre_ping=True)
if settings.database_url.startswith('sqlite:'):
    @event.listens_for(engine, 'connect')
    def configure_sqlite(connection, _):
        connection.execute('PRAGMA journal_mode=WAL')
        connection.execute('PRAGMA foreign_keys=ON')
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(11), unique=True)
    nickname: Mapped[str] = mapped_column(String(40))
    password_hash: Mapped[str] = mapped_column(String(255))
    token_version: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SmsCode(Base):
    __tablename__ = 'sms_codes'
    phone: Mapped[str] = mapped_column(String(11), primary_key=True)
    scene: Mapped[str] = mapped_column(String(32))
    issued_at: Mapped[int] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(default=0)


class Work(Base):
    __tablename__ = 'works'
    __table_args__ = (UniqueConstraint('user_id', 'work_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    work_id: Mapped[str] = mapped_column(String(100))
    payload: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Usage(Base):
    __tablename__ = 'ai_daily_usage'
    __table_args__ = (UniqueConstraint('user_id', 'day'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    day: Mapped[str] = mapped_column(String(10))
    used: Mapped[int] = mapped_column(default=0)


class AiRecord(Base):
    __tablename__ = 'ai_records'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='complete')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Post(Base):
    # Public community state for one private work; the work payload stays the editable source.
    __tablename__ = 'community_posts'
    __table_args__ = (UniqueConstraint('user_id', 'work_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True)
    user_id: Mapped[int] = mapped_column(index=True)
    work_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(16), default='pending', index=True)  # private|pending|approved|rejected
    reject_reason: Mapped[str] = mapped_column(String(200), default='')
    title: Mapped[str] = mapped_column(String(120), default='')
    method_id: Mapped[str] = mapped_column(String(16), default='frame', index=True)
    frame_id: Mapped[str] = mapped_column(String(16), default='round')
    note: Mapped[str] = mapped_column(Text, default='')
    media_key: Mapped[str] = mapped_column(String(32), default='')
    like_count: Mapped[int] = mapped_column(default=0)
    comment_count: Mapped[int] = mapped_column(default=0)
    published_ts: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Like(Base):
    __tablename__ = 'community_likes'
    __table_args__ = (UniqueConstraint('post_id', 'user_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(index=True)


class Favorite(Base):
    __tablename__ = 'community_favorites'
    __table_args__ = (UniqueConstraint('post_id', 'user_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(index=True)


class Comment(Base):
    __tablename__ = 'community_comments'
    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default='visible', index=True)  # visible|pending|hidden
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Report(Base):
    __tablename__ = 'community_reports'
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(index=True)
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default='open', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def get_db():
    with SessionLocal() as session:
        yield session

