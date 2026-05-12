from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import AsyncSession

from bl.passwords import hash_password
from dal.user_repository import count_admins, fetch_by_username
from models.user import User


async def seed_admin_if_needed(session: AsyncSession) -> None:
    """See previous seed module docstring — idempotent bootstrap admin."""
    if await count_admins(session) > 0:
        return

    username = os.environ.get("GUARDIAN_ADMIN_USERNAME", "Admin").strip() or "Admin"
    password = os.environ.get("GUARDIAN_ADMIN_PASSWORD", "admin")
    full_name = os.environ.get("GUARDIAN_ADMIN_FULL_NAME", "Administrator").strip() or "Administrator"
    pwd_hash = hash_password(password)

    user = await fetch_by_username(session, username)
    if user is not None:
        user.role = "admin"
        user.password_hash = pwd_hash
        user.full_name = full_name or user.full_name
        await session.commit()
        return

    session.add(
        User(
            username=username,
            full_name=full_name,
            password_hash=pwd_hash,
            role="admin",
        )
    )
    await session.commit()
