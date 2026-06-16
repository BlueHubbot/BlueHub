"""
BlueHub RBAC API Endpoints
============================
FastAPI router for role-based access control management:
role assignment, permission checking, and user role queries.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import db_manager
from core.rbac import (
    BulkRoleAssignment,
    InvalidRoleAssignmentError,
    PermissionCheckResponse,
    RBACService,
    RoleAssignment,
    RoleUpdateResponse,
    UserNotFoundError,
    get_assignable_roles,
    is_admin_role,
)
from dependencies.auth import get_current_user_payload

router = APIRouter(prefix="/rbac", tags=["RBAC"])


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────


def _require_admin(token_payload: dict) -> None:
    """Check if the authenticated user has admin privileges."""
    role = token_payload.get("role", "user")
    if not is_admin_role(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


def _get_actor_role(token_payload: dict) -> str:
    """Extract and validate the actor's role from token payload."""
    return token_payload.get("role", "user")


def _get_actor_id(token_payload: dict) -> str:
    """Extract the actor's user ID from token payload."""
    return str(token_payload.get("sub", ""))


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────


@router.get("/roles", response_model=dict[str, Any])
async def list_roles(
    token_payload: dict = Depends(get_current_user_payload),
) -> Any:
    """
    List all available roles with their hierarchy levels.

    Returns the role hierarchy configuration.
    Requires authentication.
    """
    from core.rbac.service import _ADMIN_ROLES, _DEFAULT_ROLE, _ROLE_HIERARCHY

    roles_data = []
    for role_enum, level in _ROLE_HIERARCHY.items():
        roles_data.append({
            "role": role_enum.value,
            "level": level,
            "is_admin": role_enum in _ADMIN_ROLES,
            "is_default": role_enum == _DEFAULT_ROLE,
        })

    return {
        "roles": sorted(roles_data, key=lambda r: r["level"], reverse=True),
        "total": len(roles_data),
    }


@router.get("/assignable-roles", response_model=dict[str, Any])
async def list_assignable_roles(
    token_payload: dict = Depends(get_current_user_payload),
) -> Any:
    """
    List roles that the current user can assign to others.

    Returns the set of roles the authenticated user is allowed to assign.
    """
    actor_role = _get_actor_role(token_payload)
    assignable = get_assignable_roles(actor_role)

    return {
        "actor_role": actor_role,
        "assignable_roles": sorted(assignable),
        "total": len(assignable),
    }


@router.post("/assign", response_model=RoleUpdateResponse)
async def assign_role(
    request: RoleAssignment,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Assign a role to a user.

    Requires admin privileges. Only superadmin can assign superadmin role.
    """
    _require_admin(token_payload)

    actor_role = _get_actor_role(token_payload)
    service = RBACService(session)

    try:
        user = await service.assign_role(
            user_id=request.user_id,
            new_role=request.role,
            actor_role=actor_role,
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except InvalidRoleAssignmentError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Get the old role from the token context (we don't persist old role in this call)
    old_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)

    return RoleUpdateResponse(
        user_id=str(user.id),
        old_role=old_role_str,
        new_role=request.role,
        updated_at=user.updated_at,
    )


@router.post("/bulk-assign", response_model=list[RoleUpdateResponse])
async def bulk_assign_roles(
    request: BulkRoleAssignment,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Assign roles to multiple users in a single request.

    Requires admin privileges. All assignments must be valid.
    """
    _require_admin(token_payload)

    actor_role = _get_actor_role(token_payload)
    service = RBACService(session)

    assignments = [
        (assignment.user_id, assignment.role)
        for assignment in request.assignments
    ]

    try:
        updated_users = await service.bulk_assign_roles(
            assignments=assignments,
            actor_role=actor_role,
        )
    except (UserNotFoundError, InvalidRoleAssignmentError) as e:
        raise HTTPException(
            status_code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            detail=str(e),
        )

    results = []
    for user in updated_users:
        results.append(
            RoleUpdateResponse(
                user_id=str(user.id),
                old_role=user.role.value if hasattr(user.role, "value") else str(user.role),
                new_role=user.role.value if hasattr(user.role, "value") else str(user.role),
                updated_at=user.updated_at,
            )
        )

    return results


@router.get("/check", response_model=PermissionCheckResponse)
async def check_permission(
    user_id: str = Query(..., description="UUID of the user to check"),
    required_role: str = Query(
        ..., description="Comma-separated list of roles that grant access"
    ),
    resource_owner_id: str = Query(
        None, description="UUID of the resource owner for self-access check"
    ),
    allow_self: bool = Query(
        False, description="Whether to allow self-access"
    ),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Check if a user has a specific role permission.

    Requires admin privileges.
    """
    _require_admin(token_payload)

    service = RBACService(session)
    required_roles = [r.strip() for r in required_role.split(",")]

    try:
        user_role = await service.get_user_role(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found",
        )

    from core.rbac.service import check_permission as _check_permission
    granted = _check_permission(
        user_role,
        required_roles,
        user_id=user_id,
        resource_owner_id=resource_owner_id,
        allow_self=allow_self,
    )

    return PermissionCheckResponse(
        granted=granted,
        user_id=user_id,
        user_role=user_role,
        required_roles=required_roles,
    )


@router.get("/users/{role}", response_model=dict[str, Any])
async def get_users_by_role(
    role: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Get all users with a specific role.

    Requires admin privileges.
    """
    _require_admin(token_payload)

    service = RBACService(session)
    users, total = await service.get_users_by_role(
        role=role,
        page=page,
        page_size=page_size,
    )

    items = []
    for user in users:
        items.append({
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "is_active": user.is_active,
        })

    total_pages = max(1, (total + page_size - 1) // page_size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/hierarchy", response_model=dict[str, Any])
async def get_role_hierarchy(
    token_payload: dict = Depends(get_current_user_payload),
) -> Any:
    """
    Get the complete role hierarchy configuration.

    Returns all roles with their levels, assignment rules, and admin status.
    Requires authentication.
    """
    from core.rbac.service import (
        _ADMIN_ROLES,
        _DEFAULT_ROLE,
        _ROLE_ASSIGNMENT_RULES,
        _ROLE_HIERARCHY,
    )

    hierarchy = []
    for role_enum, level in sorted(
        _ROLE_HIERARCHY.items(), key=lambda x: x[1], reverse=True
    ):
        assignable = {
            r.value for r in _ROLE_ASSIGNMENT_RULES.get(role_enum, set())
        }
        hierarchy.append({
            "role": role_enum.value,
            "level": level,
            "is_admin": role_enum in _ADMIN_ROLES,
            "is_default": role_enum == _DEFAULT_ROLE,
            "can_assign": sorted(assignable),
        })

    return {
        "hierarchy": hierarchy,
        "total_levels": len(hierarchy),
    }


__all__ = ["router"]
