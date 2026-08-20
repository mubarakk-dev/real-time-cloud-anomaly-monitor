from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func, text
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .config import get_settings


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    service: Mapped[str] = mapped_column(String(100), index=True)
    anomaly_score: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, index=True)
    inference_time_ms: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
Session = async_sessionmaker(engine, expire_on_commit=False)


async def initialise_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def database_ready() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
