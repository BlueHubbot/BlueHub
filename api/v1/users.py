"""
BlueHub Users API Endpoints
============================
FastAPI router for user management: CRUD, listing, profile update,
password change, and admin user management.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import db_manager
from core.users import (
    DuplicateEmailError,
    InvalidPasswordError,
    UpdatePasswordRequest,
    UserCreate,
    UserListResponse,
    UserNotFoundError,
    UserResponse,
    UserService,
    UserUpdate,
)
from dependencies.auth import get_current_user, get_current_user_payload
from shared.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────


def _build_user_response(user: User) -> UserResponse:
    """Build a UserResponse from a User model instance."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        is_active=user.is_active,
        language_code=user.language_code,
        two_fa_enabled=user.two_fa_enabled,
        wallet_balance=float(user.wallet_balance or 0.0),
        telegram_user_id=user.telegram_user_id,
        tenant_id=str(user.tenant_id) if user.tenant_id else None,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _require_admin(token_payload: dict) -> None:
    """Check if the authenticated user has admin privileges."""
    role = token_payload.get("role", "user")
    if role not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


# ──────────────────────────────────────────────
# Admin Endpoints
# ──────────────────────────────────────────────


@router.get("/", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    role: str | None = Query(None, description="Filter by role"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    search: str | None = Query(None, description="Search by email or name"),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    List users with pagination and filters.

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = UserService(session)
    users, total = await service.list_users(
        page=page,
        page_size=page_size,
        role=role,
        is_active=is_active,
        search=search,
    )

    total_pages = max(1, (total + page_size - 1) // page_size)
    items = [_build_user_response(u) for u in users]

    return UserListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Create a new user (admin only).

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = UserService(session)
    try:
        user = await service.create_user(request)
    except DuplicateEmailError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return _build_user_response(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Get a user by ID.

    Requires admin or superadmin role, or the user accessing their own profile.
    """
    role = token_payload.get("role", "user")
    token_user_id = str(token_payload.get("sub", ""))

    # Allow users to access their own profile
    if role not in ("admin", "superadmin") and token_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this user",
        )

    service = UserService(session)
    user = await service.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found",
        )

    return _build_user_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Update a user's profile.

    Requires admin or superadmin role, or the user updating their own profile.
    Non-admin users can only update limited fields.
    """
    role = token_payload.get("role", "user")
    token_user_id = str(token_payload.get("sub", ""))

    is_own_profile = token_user_id == user_id
    is_admin = role in ("admin", "superadmin")

    if not is_admin and not is_own_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )

    # Non-admin users cannot change role or is_active
    if not is_admin and (request.role is not None or request.is_active is not None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change role or active status",
        )

    service = UserService(session)
    try:
        user = await service.update_user(user_id, request)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return _build_user_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> None:
    """
    Soft-delete a user (set inactive).

    Requires admin or superadmin role.
    """
    _require_admin(token_payload)

    service = UserService(session)
    try:
        await service.delete_user(user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ──────────────────────────────────────────────
# Authenticated User Endpoints
# ──────────────────────────────────────────────


@router.post("/me/password", status_code=status.HTTP_200_OK)
async def update_my_password(
    request: UpdatePasswordRequest,
    current_user: User = Depends(get_current_user),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Update the authenticated user's password.

    Requires current password verification.
    """
    user_id = str(token_payload.get("sub", ""))
    service = UserService(session)

    try:
        await service.update_password(
            user_id=user_id,
            current_password=request.current_password,
            new_password=request.new_password,
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidPasswordError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {"message": "Password updated successfully"}


@router.patch("/me/preferences", response_model=UserResponse)
async def update_my_preferences(
    language_code: str = Query(..., min_length=2, max_length=10),
    current_user: User = Depends(get_current_user),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Update the authenticated user's preferences (language, etc.).
    """
    user_id = str(token_payload.get("sub", ""))
    service = UserService(session)

    try:
        user = await service.update_preferences(
            user_id=user_id,
            language_code=language_code,
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return _build_user_response(user)


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get the authenticated user's full profile.
    """
    return _build_user_response(current_user)


__all__ = ["router"]
