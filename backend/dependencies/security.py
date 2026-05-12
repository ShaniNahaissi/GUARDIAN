from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from bl.jwt_tokens import safe_decode_access_token
from bl.rbac import role_has
from dal.database import get_session
from dal.user_repository import fetch_by_id
from models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = safe_decode_access_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        uid = uuid.UUID(str(sub))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    user = await fetch_by_id(session, uid)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_permission(permission: str):
    async def _dep(user: User = Depends(get_current_user)) -> User:
        if not role_has(user.role, permission):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _dep


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user
