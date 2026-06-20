"""
BlueHub RBAC Service
======================
Role-Based Access Control service for permission checking,
role assignment, and role hierarchy management.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.enums import UserRole
from shared.models.user import User


class RBACError(Exception):
    """Base exception for RBAC operations."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class UserNotFoundError(RBACError):
    """Raised when a user is not found."""

    def __init__(self, user_id: str) -> None:
        super().__init__(
            message=f"User with id '{user_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidRoleAssignmentError(RBACError):
    """Raised when a role assignment is invalid (e.g., cannot change superadmin)."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class InsufficientPrivilegesError(RBACError):
    """Raised when a user lacks required privileges for an action."""

    def __init__(self, required_roles: list[str]) -> None:
        super().__init__(
            message=f"Requires one of these roles: {', '.join(required_roles)}",
            status_code=status.HTTP_403_FORBIDDEN,
        )


# ──────────────────────────────────────────────
# Role Hierarchy Configuration
# ──────────────────────────────────────────────

_ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.SUPERADMIN: 100,
    UserRole.ADMIN: 80,
    UserRole.RESELLER: 50,
    UserRole.USER: 10,
}

# Define which roles can assign which other roles
_ROLE_ASSIGNMENT_RULES: dict[UserRole, set[UserRole]] = {
    UserRole.SUPERADMIN: {
        UserRole.SUPERADMIN,
        UserRole.ADMIN,
        UserRole.RESELLER,
        UserRole.USER,
    },
    UserRole.ADMIN: {
        UserRole.RESELLER,
        UserRole.USER,
    },
    UserRole.RESELLER: {
        UserRole.USER,
    },
    UserRole.USER: set(),
}

# Define which roles can perform admin-level operations
_ADMIN_ROLES: frozenset[UserRole] = frozenset(
    {UserRole.SUPERADMIN, UserRole.ADMIN}
)

# Default role for new users
_DEFAULT_ROLE: UserRole = UserRole.USER


def get_role_level(role: str | UserRole) -> int:
    """
    Get the hierarchy level for a role.

    Args:
        role: Role name (string or UserRole enum).

    Returns:
        Integer representing the role's privilege level.
        Returns 0 for unknown roles.
    """
    if isinstance(role, str):
        try:
            role_enum = UserRole(role.lower())
        except ValueError:
            return 0
    else:
        role_enum = role
    return _ROLE_HIERARCHY.get(role_enum, 0)


def is_admin_role(role: str | UserRole) -> bool:
    """
    Check if a role has admin-level privileges.

    Args:
        role: Role name (string or UserRole enum).

    Returns:
        True if the role is superadmin or admin.
    """
    if isinstance(role, str):
        try:
            role_enum = UserRole(role.lower())
        except ValueError:
            return False
    else:
        role_enum = role
    return role_enum in _ADMIN_ROLES


def is_superadmin_role(role: str | UserRole) -> bool:
    """
    Check if a role is superadmin.

    Args:
        role: Role name (string or UserRole enum).

    Returns:
        True if the role is superadmin.
    """
    if isinstance(role, str):
        return role.lower() == UserRole.SUPERADMIN.value
    return role == UserRole.SUPERADMIN


def get_assignable_roles(actor_role: str | UserRole) -> set[str]:
    """
    Get the set of roles that an actor can assign to others.

    Args:
        actor_role: The role of the user performing the assignment.

    Returns:
        Set of role strings that can be assigned.
    """
    if isinstance(actor_role, str):
        try:
            role_enum = UserRole(actor_role.lower())
        except ValueError:
            return set()
    else:
        role_enum = actor_role

    return {r.value for r in _ROLE_ASSIGNMENT_RULES.get(role_enum, set())}


def can_assign_role(
    actor_role: str | UserRole, target_role: str | UserRole
) -> bool:
    """
    Check if an actor can assign a specific target role.

    Args:
        actor_role: The role of the user performing the assignment.
        target_role: The role being assigned.

    Returns:
        True if the assignment is allowed.
    """
    if isinstance(actor_role, str):
        try:
            actor_enum = UserRole(actor_role.lower())
        except ValueError:
            return False
    else:
        actor_enum = actor_role

    if isinstance(target_role, str):
        try:
            target_enum = UserRole(target_role.lower())
        except ValueError:
            return False
    else:
        target_enum = target_role

    return target_enum in _ROLE_ASSIGNMENT_RULES.get(actor_enum, set())


def check_permission(
    user_role: str | UserRole,
    required_roles: list[str],
    *,
    user_id: str | None = None,
    resource_owner_id: str | None = None,
    allow_self: bool = False,
) -> bool:
    """
    Check if a user with a given role has permission.

    Args:
        user_role: The user's current role.
        required_roles: List of roles that grant access.
        user_id: The user's ID (for self-access check).
        resource_owner_id: The resource owner's ID.
        allow_self: Whether to allow access if user is the resource owner.

    Returns:
        True if the user has permission.
    """
    # Check self-access first
    if (
        allow_self
        and user_id is not None
        and resource_owner_id is not None
        and user_id == resource_owner_id
    ):
        return True

    # Convert user_role to string for comparison
    user_role_str = user_role.value if isinstance(user_role, UserRole) else user_role.lower()

    # Check if user's role is in required roles
    if user_role_str in required_roles:
        return True

    # Check hierarchy: if user's role level >= any required role level, grant access
    user_level = get_role_level(user_role_str)
    for req_role in required_roles:
        req_level = get_role_level(req_role)
        if user_level >= req_level:
            return True

    return False


class RBACService:
    """
    Service for RBAC operations on user roles.

    Provides methods for assigning roles, checking permissions,
    and managing role-based access controls.

    Usage:
        service = RBACService(session)
        result = await service.check_user_permission("user-id", ["admin", "superadmin"])
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the RBAC service.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self.session = session

    async def get_user_role(self, user_id: str) -> str:
        """
        Get the current role of a user.

        Args:
            user_id: UUID of the user.

        Returns:
            The user's role as a string.

        Raises:
            UserNotFoundError: If the user is not found.
        """
        result = await self.session.execute(
            select(User.role).where(User.id == user_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise UserNotFoundError(user_id)
        if isinstance(row, UserRole):
            return row.value
        return str(row)

    async def assign_role(
        self,
        user_id: str,
        new_role: str,
        actor_role: str,
    ) -> User:
        """
        Assign a new role to a user.

        Args:
            user_id: UUID of the target user.
            new_role: The new role to assign.
            actor_role: The role of the user performing the assignment.

        Returns:
            The updated User object.

        Raises:
            UserNotFoundError: If the target user is not found.
            InvalidRoleAssignmentError: If the actor cannot assign the target role.
            RBACError: If the actor tries to change a superadmin's role.
        """
        # Validate the new role
        try:
            new_role_enum = UserRole(new_role.lower())
        except ValueError:
            msg = (
                f"Invalid role '{new_role}'. Must be one of: "
                f"{', '.join(r.value for r in UserRole)}"
            )
            raise InvalidRoleAssignmentError(
                msg
            )

        # Check if actor can assign this role
        if not can_assign_role(actor_role, new_role_enum):
            msg = f"Cannot assign role '{new_role}' with your current role"
            raise InvalidRoleAssignmentError(
                msg
            )

        # Fetch the user
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundError(user_id)

        # Prevent changing superadmin roles from non-superadmin actors
        if user.is_superadmin and not is_superadmin_role(actor_role):
            msg = "Cannot modify a superadmin user's role"
            raise InvalidRoleAssignmentError(
                msg
            )

        # Update the role
        user.role = new_role_enum
        await self.session.commit()
        await self.session.refresh(user)

        return user

    async def check_user_permission(
        self,
        user_id: str,
        required_roles: list[str],
        *,
        resource_owner_id: str | None = None,
        allow_self: bool = False,
    ) -> bool:
        """
        Check if a user has one of the required roles.

        Args:
            user_id: UUID of the user to check.
            required_roles: List of role strings that grant access.
            resource_owner_id: UUID of the resource owner (for self-access).
            allow_self: Whether to allow self-access.

        Returns:
            True if the user has permission.
        """
        try:
            user_role = await self.get_user_role(user_id)
        except UserNotFoundError:
            return False

        return check_permission(
            user_role,
            required_roles,
            user_id=user_id,
            resource_owner_id=resource_owner_id,
            allow_self=allow_self,
        )

    async def require_role(
        self,
        user_id: str,
        required_roles: list[str],
        *,
        resource_owner_id: str | None = None,
        allow_self: bool = False,
    ) -> None:
        """
        Require a user to have one of the specified roles.
        Raises HTTPException if not granted.

        Args:
            user_id: UUID of the user to check.
            required_roles: List of role strings that grant access.
            resource_owner_id: UUID of the resource owner (for self-access).
            allow_self: Whether to allow self-access.

        Raises:
            HTTPException 403: If the user lacks required permissions.
            HTTPException 404: If the user is not found.
        """
        try:
            user_role_str = await self.get_user_role(user_id)
        except UserNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{user_id}' not found",
            )

        granted = check_permission(
            user_role_str,
            required_roles,
            user_id=user_id,
            resource_owner_id=resource_owner_id,
            allow_self=allow_self,
        )

        if not granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Requires one of these roles: {', '.join(required_roles)}"
                ),
            )

    async def bulk_assign_roles(
        self,
        assignments: list[tuple[str, str]],
        actor_role: str,
    ) -> list[User]:
        """
        Assign roles to multiple users in a single transaction.

        Args:
            assignments: List of (user_id, new_role) tuples.
            actor_role: The role of the user performing the assignments.

        Returns:
            List of updated User objects.

        Raises:
            InvalidRoleAssignmentError: If any assignment is invalid.
        """
        updated_users: list[User] = []

        try:
            for user_id, new_role in assignments:
                user = await self.assign_role(
                    user_id=user_id,
                    new_role=new_role,
                    actor_role=actor_role,
                )
                updated_users.append(user)
        except RBACError:
            await self.session.rollback()
            raise

        return updated_users

    async def get_users_by_role(
        self,
        role: str | UserRole,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        """
        Get all users with a specific role, with pagination.

        Args:
            role: The role to filter by.
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Tuple of (list of Users, total count).
        """
        if isinstance(role, str):
            try:
                role_enum = UserRole(role.lower())
            except ValueError:
                return [], 0
        else:
            role_enum = role

        # Count total
        count_query = (
            select(User)
            .where(User.role == role_enum)
        )
        total_result = await self.session.execute(count_query)
        total = len(total_result.scalars().all())

        # Fetch paginated
        offset = (page - 1) * page_size
        query = (
            select(User)
            .where(User.role == role_enum)
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        users = list(result.scalars().all())

        return users, total


__all__ = [
    "_ADMIN_ROLES",
    "_DEFAULT_ROLE",
    "_ROLE_HIERARCHY",
    "InsufficientPrivilegesError",
    "InvalidRoleAssignmentError",
    "RBACError",
    "RBACService",
    "UserNotFoundError",
    "can_assign_role",
    "check_permission",
    "get_assignable_roles",
    "get_role_level",
    "is_admin_role",
    "is_superadmin_role",
]
