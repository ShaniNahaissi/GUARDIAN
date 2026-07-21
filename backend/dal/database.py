from __future__ import annotations

import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.environ.get(
    "GUARDIAN_DATABASE_URL",
    "postgresql+asyncpg://guardian:guardian@localhost:5432/guardian",
)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, echo=os.environ.get("GUARDIAN_SQL_ECHO", "").strip() == "1")
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    from models.user import User  # noqa: F401 — register ORM metadata
    from models.metrics import FrameMetric, SequenceMetric  # noqa: F401 — register ORM metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
