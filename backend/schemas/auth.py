from __future__ import annotations

from pydantic import BaseModel, Field

from models.user import User


class UserOut(BaseModel):
    id: str
    username: str
    fullName: str
    role: str

    @staticmethod
    def from_user(u: User) -> "UserOut":
        return UserOut(id=str(u.id), username=u.username, fullName=u.full_name, role=u.role)


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=4, max_length=128)
    full_name: str = Field(default="", max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
