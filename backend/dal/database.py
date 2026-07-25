from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

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


def _drop_tables_with_schema_mismatch(sync_conn: Any, tables: tuple[Any, ...]) -> None:
    """Metrics tables are pure logging/analytics data -- safe to lose on a schema change,
    unlike users/cameras. create_all only creates *missing* tables, so a column added to
    FrameMetric/SequenceMetric would otherwise silently never appear in an already-existing
    database. This drops just those tables when their live columns don't match the current
    model, so the create_all right after recreates them with the correct schema."""
    from sqlalchemy import inspect

    inspector = inspect(sync_conn)
    existing_table_names = set(inspector.get_table_names())
    for table in tables:
        if table.name not in existing_table_names:
            continue
        existing_columns = {col["name"] for col in inspector.get_columns(table.name)}
        expected_columns = {col.name for col in table.columns}
        if existing_columns != expected_columns:
            table.drop(sync_conn)


async def init_db() -> None:
    from models.user import User  # noqa: F401 — register ORM metadata
    from models.metrics import FrameMetric, SequenceMetric  # noqa: F401 — register ORM metadata
    from models.camera import Camera  # noqa: F401 — register ORM metadata

    async with engine.begin() as conn:
        await conn.run_sync(_drop_tables_with_schema_mismatch, (FrameMetric.__table__, SequenceMetric.__table__))
        await conn.run_sync(Base.metadata.create_all)
