from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from bl.passwords import hash_password
from bl.rbac import VALID_ROLES
from dal.user_repository import count_admins, fetch_by_id, fetch_by_username, list_users_ordered
from models.user import User
from schemas.admin import AdminCreateUser, AdminUpdateUser, AdminUserOut


def _validate_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role}")


async def list_users(session: AsyncSession) -> list[AdminUserOut]:
    rows = await list_users_ordered(session)
    return [AdminUserOut.from_user(u) for u in rows]


async def create_user(session: AsyncSession, body: AdminCreateUser) -> AdminUserOut:
    _validate_role(body.role)
    uname = body.username.strip()
    if not uname:
        raise HTTPException(status_code=400, detail="Username required")
    if await fetch_by_username(session, uname) is not None:
        raise HTTPException(status_code=409, detail="Username already taken")
    user = User(
        username=uname,
        full_name=(body.full_name or uname).strip(),
        password_hash=hash_password(body.password),
        role=body.role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return AdminUserOut.from_user(user)


async def update_user(session: AsyncSession, user_id: uuid.UUID, body: AdminUpdateUser) -> AdminUserOut:
    target = await fetch_by_id(session, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    if body.role is not None:
        _validate_role(body.role)
        if target.role == "admin" and body.role != "admin":
            if await count_admins(session) <= 1:
                raise HTTPException(status_code=400, detail="Cannot demote the last administrator")
        target.role = body.role

    if body.full_name is not None:
        target.full_name = body.full_name.strip() or target.username

    if body.password is not None:
        target.password_hash = hash_password(body.password)

    await session.commit()
    await session.refresh(target)
    return AdminUserOut.from_user(target)


async def delete_user(session: AsyncSession, user_id: uuid.UUID, acting_admin_id: uuid.UUID) -> None:
    if user_id == acting_admin_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    target = await fetch_by_id(session, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    if target.role == "admin" and await count_admins(session) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last administrator")

    session.delete(target)
    await session.commit()
