"""
BlueHub API Modules Router
=========================
Admin API for module registry management.
Provides endpoints to list, inspect, and toggle service modules.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.registry import (
    ModuleRegistryResponse,
    ModuleRegistryService,
    ModuleToggleRequest,
    module_registry_service,
)
from dependencies.auth import get_current_user
from dependencies.db import get_async_session
from shared.models.user import User

router = APIRouter(prefix="/modules", tags=["Modules"])


@router.get("/")
async def list_modules(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[ModuleRegistryResponse]:
    """
    List all registered modules with their current state and flags.

    Available to all authenticated users.
    """
    modules = await module_registry_service.get_all_modules(session=session)
    return [
        ModuleRegistryService._to_response(mod) for mod in modules
    ]


@router.get("/{module_name}")
async def get_module(
    module_name: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ModuleRegistryResponse:
    """
    Get details of a specific module by its name.

    Args:
        module_name: Module identifier (e.g., 'vpn', 'vps').

    Returns:
        ModuleRegistryResponse with module details and flags.
    """
    modules = await module_registry_service.get_all_modules(session=session)
    for mod in modules:
        if mod.module_name == module_name:
            return ModuleRegistryService._to_response(mod)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Module '{module_name}' not found",
    )


@router.patch("/{module_name}/toggle")
async def toggle_module(
    module_name: str,
    request: ModuleToggleRequest,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ModuleRegistryResponse:
    """
    Toggle feature flags for a module.

    Only users with admin-level privileges can toggle modules.

    Args:
        module_name: Module identifier (e.g., 'vpn').
        request: Toggle request with fields to update (all optional).

    Returns:
        Updated ModuleRegistryResponse.
    """
    # Check admin privileges
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to toggle modules",
        )

    result = await module_registry_service.toggle_module(
        module_name=module_name,
        request=request,
        session=session,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_name}' not found",
        )
    return result


__all__ = ["router"]