"""
BlueHub User Management Module
===============================
User CRUD, profile management, and user preferences.
"""

from __future__ import annotations

from core.users.schemas import (
    UpdatePasswordRequest,
    UserCreate,
    UserListResponse,
    UserPreferences,
    UserResponse,
    UserUpdate,
)
from core.users.service import (
    DuplicateEmailError,
    InvalidPasswordError,
    UserNotFoundError,
    UserService,
)

__all__: list[str] = [
    "DuplicateEmailError",
    "InvalidPasswordError",
    "UpdatePasswordRequest",
    "UserCreate",
    "UserListResponse",
    "UserNotFoundError",
    "UserPreferences",
    "UserResponse",
    "UserService",
    "UserUpdate",
]
