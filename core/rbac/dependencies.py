"""
BlueHub RBAC Dependencies
==========================
Decorator-based permission checks and FastAPI dependency injection for RBAC.

Provides:
- ``require_role()`` decorator for route handlers
- ``require_permission()`` async dependency for FastAPI routes
- ``has_role()`` sync dependency check
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from fastapi import Depends, HTTPException, status

from dependencies.auth import get_current_user
from shared.models.enums import UserRole
from shared.models.user import User

F = TypeVar("F", bound=Callable[..., Any])


def require_role(*allowed_roles: str | UserRole) -> Callable[[F], F]:
    """
    Decorator for FastAPI route handlers that checks the current user's role.

    Must be used in conjunction with a ``current_user`` parameter of type ``User``
    injected via FastAPI's ``Depends(get_current_user)``.

    Args:
        *allowed_roles: One or more role names (strings or ``UserRole`` enums)
                        that are permitted to access the endpoint.

    Returns:
        A decorator that wraps the route handler with permission checking.

    Raises:
        HTTPException 403: If the current user's role is not in ``allowed_roles``.

    Example::

        @router.get("/admin-only")
        @require_role("admin", "superadmin")
        async def admin_endpoint(current_user: User = Depends(get_current_user)):
            return {"message": f"Welcome {current_user.full_name}"}

        @router.get("/reseller-or-admin")
        @require_role(UserRole.RESELLER, UserRole.ADMIN, UserRole.SUPERADMIN)
        async def mixed_endpoint(current_user: User = Depends(get_current_user)):
            return {"message": "Access granted"}
    """
    # Normalise allowed roles to a set of strings for fast lookup
    allowed_set: set[str] = set()
    for r in allowed_roles:
        if isinstance(r, UserRole):
            allowed_set.add(r.value)
        else:
            allowed_set.add(r.lower())

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract current_user from kwargs (injected by FastAPI Depends)
            current_user: User | None = kwargs.get("current_user")
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user_role_str: str = (
                current_user.role.value
                if isinstance(current_user.role, UserRole)
                else str(current_user.role)
            )

            if user_role_str not in allowed_set:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Insufficient permissions. "
                        f"Required one of: {', '.join(sorted(allowed_set))}. "
                        f"Your role: {user_role_str}"
                    ),
                )

            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def require_permission(*allowed_roles: str | UserRole) -> Callable[[F], F]:
    """
    Alias for ``require_role()``.

    Provides a more semantic name for endpoints that check resource-level
    permissions (e.g., "can delete", "can edit") rather than just role names.
    Behaviour is identical to ``require_role()``.

    Args:
        *allowed_roles: One or more role names (strings or ``UserRole`` enums).

    Returns:
        The same decorator as ``require_role()``.
    """
    return require_role(*allowed_roles)


async def has_role(
    required_roles: list[str],
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> bool:
    """
    FastAPI dependency that returns ``True`` if the current user has at least
    one of the required roles.

    Useful for conditional logic inside route handlers.

    Args:
        required_roles: List of role names that grant access.
        current_user: Injected authenticated user.

    Returns:
        ``True`` if the user's role is in ``required_roles``.
    """
    user_role_str: str = (
        current_user.role.value
        if isinstance(current_user.role, UserRole)
        else str(current_user.role)
    )
    return user_role_str in required_roles


async def require_admin(
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> User:
    """
    FastAPI dependency that requires the current user to have an admin-level
    role (superadmin or admin).

    Args:
        current_user: Injected authenticated user.

    Returns:
        The authenticated ``User`` instance if they are an admin.

    Raises:
        HTTPException 403: If the user is not an admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


__all__ = [
    "has_role",
    "require_admin",
    "require_permission",
    "require_role",
]
