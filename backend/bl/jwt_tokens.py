from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

JWT_SECRET = os.environ.get("GUARDIAN_JWT_SECRET", "dev-only-change-me")
JWT_ALG = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("GUARDIAN_JWT_EXPIRE_MINUTES", "10080"))


def create_access_token(*, subject: str, username: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": subject,
        "username": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])


def safe_decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return decode_access_token(token)
    except JWTError:
        return None
