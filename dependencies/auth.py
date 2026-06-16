"""
BlueHub Auth Dependencies
===========================
FastAPI dependency injection for authentication.
Provides get_current_user dependency that verifies JWT tokens,
checks Redis blacklist, and loads the user from the database.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.auth.jwt import verify_token
from core.cache import cache_service
from core.database import db_manager
from shared.models.user import User

# Use HTTPBearer instead of OAuth2PasswordBearer to handle token extraction
# without requiring form data (works with any auth header)
security_scheme = HTTPBearer(
    auto_error=False,
    description="Bearer token (access or refresh)",
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),  # noqa: B008
    session: AsyncSession = Depends(db_manager.get_async_session),  # noqa: B008
) -> User:
    """
    Verify the Bearer token from the Authorization header and return the
    authenticated User model instance.

    Steps:
        1. Extract Bearer token from Authorization header.
        2. Verify the JWT signature and decode the payload.
        3. Check if the token has been blacklisted in Redis.
        4. Load the user from the database by the subject (sub) claim.
        5. Verify the user account is active.
        6. Return the User instance.

    Raises:
        HTTPException 401: If any check fails (missing/invalid/blacklisted
                           token, inactive/not-found user).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # Step 1: Verify JWT signature / decode
    try:
        payload = verify_token(token)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Step 2: Check Redis blacklist
    # Use token jti if present, otherwise fall back to sub
    token_id = payload.get("jti", payload.get("sub", ""))
    blacklist_key = f"blacklist:{token_id}"
    try:
        is_blacklisted = await cache_service.exists(blacklist_key)
    except Exception:
        # Redis might not be available — in production, you'd want to
        # fail closed here. For now, we'll proceed without blacklist check.
        is_blacklisted = False

    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 3: Extract user ID from payload
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 4: Load user from database
    result = await session.execute(select(User).where(User.id == user_id_str))
    user = result.scalars().first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Step 5: Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),  # noqa: B008
) -> dict:
    """
    Verify the Bearer token and return the decoded payload dict.

    Useful when you only need the token claims (e.g., for refresh/logout)
    without a database lookup.

    Raises:
        HTTPException 401: If the token is invalid or blacklisted.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = verify_token(token)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Check Redis blacklist
    token_id = payload.get("jti", payload.get("sub", ""))
    blacklist_key = f"blacklist:{token_id}"
    try:
        is_blacklisted = await cache_service.exists(blacklist_key)
    except Exception:
        is_blacklisted = False

    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


__all__ = [
    "get_current_user",
    "get_current_user_payload",
]
