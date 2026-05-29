"""Database models and connection for Signal Feed."""

from datetime import datetime, timezone

from sqlalchemy import String, Float, DateTime, Integer, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker


class Base(DeclarativeBase):
    pass


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("idx_source_created", "source", "created_at"),
        Index("idx_category_signal_score", "category", "signal_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # reddit, news, onchain
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # crypto, stocks, forex, general
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    signal_score: Mapped[float] = mapped_column(Float, default=0.0)  # -1.0 to 1.0
    sentiment_label: Mapped[str] = mapped_column(String(10), default="neutral")  # bullish, bearish, neutral
    raw_score: Mapped[float] = mapped_column(Float, default=0.0)  # original score before normalization
    metadata_json: Mapped[str] = mapped_column(Text, nullable=True)  # JSON blob for extra data
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="free")  # free, pro, enterprise
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    requests_total: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[int] = mapped_column(Integer, default=1)  # 0 or 1
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def get_engine(database_url: str):
    return create_async_engine(database_url, echo=False)


def get_session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
