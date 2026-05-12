from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from models.user import User


class AdminUserOut(BaseModel):
    id: str
    username: str
    fullName: str
    role: str
    createdAt: str | None = None

    @classmethod
    def from_user(cls, u: User) -> "AdminUserOut":
        ca: datetime | None = u.created_at
        created = ca.isoformat() if ca is not None else None
        return cls(
            id=str(u.id),
            username=u.username,
            fullName=u.full_name,
            role=u.role,
            createdAt=created,
        )


class AdminCreateUser(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=128)
    full_name: str = Field(default="", max_length=256)
    role: str = Field(min_length=2, max_length=32)


class AdminUpdateUser(BaseModel):
    full_name: str | None = Field(default=None, max_length=256)
    role: str | None = Field(default=None, min_length=2, max_length=32)
    password: str | None = Field(default=None, min_length=4, max_length=128)
