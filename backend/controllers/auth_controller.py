from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from bl import auth_service
from dal.database import get_session
from dependencies.security import get_current_user
from models.user import User
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    return await auth_service.login(session, body)


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    return await auth_service.register(session, body)


@router.get("/me", response_model=UserOut)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut.from_user(user)
