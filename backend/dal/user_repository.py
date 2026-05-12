from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User


async def fetch_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def fetch_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def list_users_ordered(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).order_by(User.username.asc()))
    return list(result.scalars().all())


async def count_admins(session: AsyncSession) -> int:
    r = await session.execute(select(func.count()).select_from(User).where(User.role == "admin"))
    return int(r.scalar_one() or 0)
