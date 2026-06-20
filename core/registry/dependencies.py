"""
BlueHub Module Registry Dependencies
=====================================
FastAPI dependency injection for module feature flag checks.
Provides ``require_module`` dependency to guard route handlers.

Usage:

    @router.get("/vpn/servers")
    async def list_vpn_servers(
        _: None = Depends(require_module("vpn")),
        session: AsyncSession = Depends(get_async_session),
    ):
        ...
"""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.registry.service import module_registry_service
from dependencies.db import get_async_session

F = TypeVar("F", bound=Callable[..., Any])


def require_module(module_name: str) -> Callable[[F], F]:
    """
    Decorator that checks whether the specified module is enabled.

    Must be used on route handlers that depend on a module being active.
    If the module is disabled, the handler returns HTTP 503 Service Unavailable.

    Args:
        module_name: The module identifier (e.g., 'vpn', 'vps').

    Returns:
        A decorator that wraps the route handler with the enabled check.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract session from kwargs (injected by FastAPI Depends)
            session: AsyncSession | None = kwargs.get("session")
            if session is None:
                # Fall back: create a new session if not provided
                async with get_async_session() as sess:
                    enabled = await module_registry_service.is_module_enabled(
                        module_name, session=sess
                    )
                    if not enabled:
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Module '{module_name}' is currently disabled",
                        )
                    return await func(*args, **kwargs)

            enabled = await module_registry_service.is_module_enabled(
                module_name, session=session
            )
            if not enabled:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Module '{module_name}' is currently disabled",
                )
            return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


async def require_module_dep(
    module_name: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
) -> None:
    """
    FastAPI dependency that checks if a module is enabled.

    Can be used with ``Depends()`` for inline module checks without a decorator.

    Args:
        module_name: The module identifier to check.
        session: Injected database session.

    Raises:
        HTTPException 503: If the module is disabled.
    """
    enabled = await module_registry_service.is_module_enabled(
        module_name, session=session
    )
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Module '{module_name}' is currently disabled",
        )


__all__ = [
    "require_module",
    "require_module_dep",
]
