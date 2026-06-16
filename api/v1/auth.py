"""
BlueHub Auth API Endpoints
===========================
FastAPI router for authentication: register, login, refresh, logout, me.
All endpoints use async/await with SQLAlchemy async sessions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.jwt import (
    generate_access_token,
    generate_refresh_token,
)
from core.auth.password import hash_password, verify_password
from core.cache import cache_service
from core.database import db_manager
from dependencies.auth import get_current_user, get_current_user_payload
from shared.models.enums import UserRole
from shared.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ──────────────────────────────────────────────
# Pydantic Schemas
# ──────────────────────────────────────────────


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public user info returned in auth responses."""

    id: str
    email: str
    full_name: str | None = None
    role: str
    created_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    """Response schema for successful login/register."""

    access_token: str
    refresh_token: str
    user: UserResponse


class RefreshResponse(BaseModel):
    """Response schema for token refresh."""

    access_token: str


class LogoutResponse(BaseModel):
    """Response schema for logout."""

    message: str


class MeResponse(BaseModel):
    """Response schema for /auth/me."""

    id: str
    email: str
    full_name: str | None = None
    role: str
    created_at: str | None = None


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────


def _build_user_response(user: User) -> UserResponse:
    """Build a UserResponse from a User model instance."""
    return UserResponse(
        id=str(user.id),
        email=str(user.email or ""),
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


def _build_me_response(user: User) -> MeResponse:
    """Build a MeResponse from a User model instance."""
    return MeResponse(
        id=str(user.id),
        email=str(user.email or ""),
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(db_manager.get_async_session),  # noqa: B008
) -> Any:
    """
    Register a new user.

    Validates email uniqueness, hashes password, creates user record,
    and returns JWT access + refresh tokens.
    """
    # Check if email already exists
    result = await session.execute(select(User).where(User.email == request.email))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    new_user = User(
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role=UserRole.USER,
        is_active=True,
    )
    session.add(new_user)
    await session.flush()
    await session.refresh(new_user)

    # Generate tokens
    user_id_str = str(new_user.id)
    role_str = new_user.role.value if hasattr(new_user.role, "value") else str(new_user.role)
    access_token = generate_access_token(user_id=user_id_str, role=role_str)
    refresh_token = generate_refresh_token(user_id=user_id_str)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_response(new_user),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(db_manager.get_async_session),  # noqa: B008
) -> Any:
    """
    Authenticate a user by email and password.

    Returns JWT access + refresh tokens on success.
    Raises 401 on invalid credentials or inactive account.
    """
    # Find user by email
    result = await session.execute(select(User).where(User.email == request.email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not user.password_hash or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    user_id_str = str(user.id)
    role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
    access_token = generate_access_token(user_id=user_id_str, role=role_str)
    refresh_token = generate_refresh_token(user_id=user_id_str)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_response(user),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    token_payload: dict = Depends(get_current_user_payload),  # noqa: B008
) -> Any:
    """
    Refresh an access token using a valid refresh token.

    Expects Authorization: Bearer <refresh_token> header.
    Returns a new access token.
    """
    user_id = str(token_payload.get("sub", ""))
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    new_access = generate_access_token(
        user_id=user_id,
        role=str(token_payload.get("role", "user")),
    )
    return RefreshResponse(access_token=new_access)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: User = Depends(get_current_user),  # noqa: ARG001
    token_payload: dict = Depends(get_current_user_payload),  # noqa: B008
) -> Any:
    """
    Logout the current user by blacklisting their access token in Redis.

    Expects Authorization: Bearer <access_token> header.
    The blacklist TTL equals the remaining token expiry.
    """
    # Extract jti from token payload if present, otherwise use a hash of the sub+exp
    jti = token_payload.get("jti", token_payload.get("sub", ""))
    exp_timestamp = token_payload.get("exp", 0)
    now_timestamp = datetime.now(timezone.utc).timestamp()
    remaining_ttl = max(int(exp_timestamp - now_timestamp), 0)

    if remaining_ttl > 0:
        blacklist_key = f"blacklist:{jti}"
        await cache_service.set(blacklist_key, "true", ttl=remaining_ttl)

    return LogoutResponse(message="logged out")


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> Any:
    """
    Get the current authenticated user's profile.

    Expects Authorization: Bearer <access_token> header.
    """
    return _build_me_response(current_user)
