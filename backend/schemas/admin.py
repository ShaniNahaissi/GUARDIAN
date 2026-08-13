from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from models.user import User


class AdminUserOut(BaseModel):
    id: str
    username: str
    fullName: str
    role: str
    primaryPhone: str = ""
    additionalPhone: str = ""
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
            primaryPhone=getattr(u, "primary_phone", "") or "",
            additionalPhone=getattr(u, "additional_phone", "") or "",
            createdAt=created,
        )


class AdminCreateUser(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=128)
    full_name: str = Field(default="", max_length=256)
    role: str = Field(min_length=2, max_length=32)
    primary_phone: str = Field(default="", max_length=32)
    additional_phone: str = Field(default="", max_length=256)
    primaryPhone: str | None = None
    additionalPhone: str | None = None


class AdminUpdateUser(BaseModel):
    full_name: str | None = Field(default=None, max_length=256)
    role: str | None = Field(default=None, min_length=2, max_length=32)
    password: str | None = Field(default=None, min_length=4, max_length=128)
    primary_phone: str | None = Field(default=None, max_length=32)
    additional_phone: str | None = Field(default=None, max_length=256)
    primaryPhone: str | None = Field(default=None, max_length=32)
    additionalPhone: str | None = Field(default=None, max_length=256)
