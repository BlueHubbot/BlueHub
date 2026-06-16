"""
BlueHub RBAC Schemas
=====================
Pydantic schemas for role-based access control:
role validation, permission checks, and user role management.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from shared.models.enums import UserRole


class RoleAssignment(BaseModel):
    """Schema for assigning a role to a user."""

    user_id: str = Field(..., description="UUID of the user")
    role: str = Field(..., min_length=1, max_length=20, description="Role to assign")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        valid_roles = {e.value for e in UserRole}
        if v.lower() not in valid_roles:
            msg = f"Invalid role '{v}'. Must be one of: {', '.join(sorted(valid_roles))}"
            raise ValueError(
                msg
            )
        return v.lower()


class PermissionCheck(BaseModel):
    """Schema for checking a user's permission."""

    user_id: str = Field(..., description="UUID of the user")
    required_roles: list[str] = Field(
        ..., min_length=1, description="List of roles that grant access"
    )
    allow_self: bool = Field(
        False,
        description="Whether the resource owner (matched by user_id) is allowed",
    )
    resource_owner_id: str | None = Field(
        None, description="UUID of the resource owner for self-access check"
    )


class PermissionCheckResponse(BaseModel):
    """Schema for permission check result."""

    granted: bool = Field(..., description="Whether access is granted")
    user_id: str = Field(..., description="UUID of the user checked")
    user_role: str = Field(..., description="Current role of the user")
    required_roles: list[str] = Field(
        ..., description="Roles that would grant access"
    )


class RoleHierarchy(BaseModel):
    """Schema representing the RBAC role hierarchy."""

    role: str = Field(..., description="Role name")
    level: int = Field(..., description="Hierarchy level (higher = more privileges)")
    inherits_from: list[str] = Field(
        default_factory=list,
        description="Roles this role inherits permissions from",
    )


class BulkRoleAssignment(BaseModel):
    """Schema for assigning roles to multiple users."""

    assignments: list[RoleAssignment] = Field(
        ..., min_length=1, max_length=100, description="List of role assignments"
    )


class RoleUpdateResponse(BaseModel):
    """Schema for role update response."""

    user_id: str
    old_role: str
    new_role: str
    updated_at: datetime


__all__ = [
    "BulkRoleAssignment",
    "PermissionCheck",
    "PermissionCheckResponse",
    "RoleAssignment",
    "RoleHierarchy",
    "RoleUpdateResponse",
]
