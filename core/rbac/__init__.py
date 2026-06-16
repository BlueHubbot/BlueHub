"""
BlueHub RBAC Module
====================
Role-Based Access Control with 4 roles: superadmin, admin, reseller, user.
Provides role hierarchy, permission checking, role assignment services,
and decorator-based permission checks.
"""

from __future__ import annotations

from core.rbac.dependencies import (
    has_role,
    require_admin,
    require_permission,
    require_role,
)
from core.rbac.schemas import (
    BulkRoleAssignment,
    PermissionCheck,
    PermissionCheckResponse,
    RoleAssignment,
    RoleHierarchy,
    RoleUpdateResponse,
)
from core.rbac.service import (
    InsufficientPrivilegesError,
    InvalidRoleAssignmentError,
    RBACError,
    RBACService,
    UserNotFoundError,
    can_assign_role,
    check_permission,
    get_assignable_roles,
    get_role_level,
    is_admin_role,
    is_superadmin_role,
)

__all__: list[str] = [
    "BulkRoleAssignment",
    # Dependencies
    "has_role",
    "InsufficientPrivilegesError",
    "InvalidRoleAssignmentError",
    "PermissionCheck",
    "PermissionCheckResponse",
    "RBACError",
    # Service
    "RBACService",
    "require_admin",
    "require_permission",
    "require_role",
    # Schemas
    "RoleAssignment",
    "RoleHierarchy",
    "RoleUpdateResponse",
    "UserNotFoundError",
    "can_assign_role",
    "check_permission",
    "get_assignable_roles",
    # Utility functions
    "get_role_level",
    "is_admin_role",
    "is_superadmin_role",
]