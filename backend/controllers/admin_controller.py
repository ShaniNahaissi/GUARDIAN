from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from bl import admin_user_service
from dal.database import get_session
from dependencies.security import get_admin_user
from models.user import User
from schemas.admin import AdminCreateUser, AdminUpdateUser, AdminUserOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: User = Depends(get_admin_user),
) -> list[AdminUserOut]:
    return await admin_user_service.list_users(session)


@router.post("/users", response_model=AdminUserOut)
async def create_user(
    body: AdminCreateUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: User = Depends(get_admin_user),
) -> AdminUserOut:
    return await admin_user_service.create_user(session, body)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUpdateUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    _admin: User = Depends(get_admin_user),
) -> AdminUserOut:
    return await admin_user_service.update_user(session, user_id, body)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: User = Depends(get_admin_user),
) -> dict[str, bool]:
    await admin_user_service.delete_user(session, user_id, admin.id)
    return {"ok": True}
