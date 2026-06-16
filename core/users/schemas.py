"""
BlueHub User Schemas
=====================
Pydantic schemas for user management requests/responses.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=255)
    language_code: str = Field("en", max_length=10)
    telegram_user_id: int | None = Field(None)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            msg = "Invalid email format"
            raise ValueError(msg)
        return v.lower().strip()


class UserUpdate(BaseModel):
    """Schema for updating an existing user."""

    full_name: str | None = Field(None, max_length=255)
    language_code: str | None = Field(None, max_length=10)
    is_active: bool | None = Field(None)
    role: str | None = Field(None, max_length=20)


class UserResponse(BaseModel):
    """Schema for user response (safe, no password)."""

    id: str
    email: str | None = None
    full_name: str | None = None
    role: str
    is_active: bool
    language_code: str
    two_fa_enabled: bool
    wallet_balance: float
    telegram_user_id: int | None = None
    tenant_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Schema for paginated user list."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UpdatePasswordRequest(BaseModel):
    """Schema for password update."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class UserPreferences(BaseModel):
    """Schema for user preferences."""

    language_code: str = Field("en", max_length=10)
    notifications_enabled: bool = True
    theme: str = Field("light", max_length=20)


__all__ = [
    "UpdatePasswordRequest",
    "UserCreate",
    "UserListResponse",
    "UserPreferences",
    "UserResponse",
    "UserUpdate",
]
