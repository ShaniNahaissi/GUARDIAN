from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from bl.jwt_tokens import create_access_token
from bl.passwords import hash_password, verify_password
from dal.user_repository import fetch_by_username
from models.user import User
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut


async def login(session: AsyncSession, body: LoginRequest) -> TokenResponse:
    uname = body.username.strip()
    user = await fetch_by_username(session, uname)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(subject=str(user.id), username=user.username, role=user.role)
    return TokenResponse(access_token=token, user=UserOut.from_user(user))


async def register(session: AsyncSession, body: RegisterRequest) -> TokenResponse:
    uname = body.username.strip()
    if not uname:
        raise HTTPException(status_code=400, detail="Username required")
    existing = await fetch_by_username(session, uname)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Username already taken")
    user = User(
        username=uname,
        full_name=(body.full_name or uname).strip(),
        password_hash=hash_password(body.password),
        role="viewer",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    token = create_access_token(subject=str(user.id), username=user.username, role=user.role)
    return TokenResponse(access_token=token, user=UserOut.from_user(user))
