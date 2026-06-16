"""
BlueHub RBAC Unit Tests
========================
Tests for role-based access control: role hierarchy, permission checking,
role assignment logic, decorators, and API schemas.
Uses pytest-asyncio for async database operations.

Run: pytest tests/unit/test_rbac.py -v --asyncio-mode=auto
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status

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
from shared.models.enums import UserRole
from shared.models.user import User

# ──────────────────────────────────────────────
# Utility Function Tests
# ──────────────────────────────────────────────


class TestRoleLevel:
    """Tests for get_role_level utility function."""

    def test_get_role_level_superadmin(self):
        assert get_role_level(UserRole.SUPERADMIN) == 100
        assert get_role_level("superadmin") == 100

    def test_get_role_level_admin(self):
        assert get_role_level(UserRole.ADMIN) == 80
        assert get_role_level("admin") == 80

    def test_get_role_level_reseller(self):
        assert get_role_level(UserRole.RESELLER) == 50
        assert get_role_level("reseller") == 50

    def test_get_role_level_user(self):
        assert get_role_level(UserRole.USER) == 10
        assert get_role_level("user") == 10

    def test_get_role_level_unknown(self):
        assert get_role_level("unknown_role") == 0
        assert get_role_level("") == 0


class TestIsAdminRole:
    """Tests for is_admin_role utility function."""

    def test_superadmin_is_admin(self):
        assert is_admin_role(UserRole.SUPERADMIN) is True
        assert is_admin_role("superadmin") is True

    def test_admin_is_admin(self):
        assert is_admin_role(UserRole.ADMIN) is True
        assert is_admin_role("admin") is True

    def test_reseller_is_not_admin(self):
        assert is_admin_role(UserRole.RESELLER) is False
        assert is_admin_role("reseller") is False

    def test_user_is_not_admin(self):
        assert is_admin_role(UserRole.USER) is False
        assert is_admin_role("user") is False

    def test_unknown_role_is_not_admin(self):
        assert is_admin_role("unknown") is False


class TestIsSuperadminRole:
    """Tests for is_superadmin_role utility function."""

    def test_superadmin_is_superadmin(self):
        assert is_superadmin_role(UserRole.SUPERADMIN) is True
        assert is_superadmin_role("superadmin") is True

    def test_admin_is_not_superadmin(self):
        assert is_superadmin_role(UserRole.ADMIN) is False
        assert is_superadmin_role("admin") is False

    def test_unknown_role_is_not_superadmin(self):
        assert is_superadmin_role("unknown") is False


class TestGetAssignableRoles:
    """Tests for get_assignable_roles utility function."""

    def test_superadmin_can_assign_all(self):
        roles = get_assignable_roles(UserRole.SUPERADMIN)
        assert roles == {"superadmin", "admin", "reseller", "user"}

    def test_admin_can_assign_reseller_user(self):
        roles = get_assignable_roles(UserRole.ADMIN)
        assert roles == {"reseller", "user"}

    def test_reseller_can_assign_user(self):
        roles = get_assignable_roles(UserRole.RESELLER)
        assert roles == {"user"}

    def test_user_cannot_assign_any(self):
        roles = get_assignable_roles(UserRole.USER)
        assert roles == set()

    def test_unknown_role_cannot_assign_any(self):
        roles = get_assignable_roles("unknown")
        assert roles == set()

    def test_string_input(self):
        roles = get_assignable_roles("admin")
        assert roles == {"reseller", "user"}


class TestCanAssignRole:
    """Tests for can_assign_role utility function."""

    def test_superadmin_can_assign_superadmin(self):
        assert can_assign_role(UserRole.SUPERADMIN, UserRole.SUPERADMIN) is True

    def test_superadmin_can_assign_admin(self):
        assert can_assign_role(UserRole.SUPERADMIN, UserRole.ADMIN) is True

    def test_superadmin_can_assign_reseller(self):
        assert can_assign_role(UserRole.SUPERADMIN, UserRole.RESELLER) is True

    def test_superadmin_can_assign_user(self):
        assert can_assign_role(UserRole.SUPERADMIN, UserRole.USER) is True

    def test_admin_can_assign_reseller(self):
        assert can_assign_role(UserRole.ADMIN, UserRole.RESELLER) is True

    def test_admin_can_assign_user(self):
        assert can_assign_role(UserRole.ADMIN, UserRole.USER) is True

    def test_admin_cannot_assign_admin(self):
        assert can_assign_role(UserRole.ADMIN, UserRole.ADMIN) is False

    def test_admin_cannot_assign_superadmin(self):
        assert can_assign_role(UserRole.ADMIN, UserRole.SUPERADMIN) is False

    def test_reseller_can_assign_user(self):
        assert can_assign_role(UserRole.RESELLER, UserRole.USER) is True

    def test_reseller_cannot_assign_reseller(self):
        assert can_assign_role(UserRole.RESELLER, UserRole.RESELLER) is False

    def test_reseller_cannot_assign_admin(self):
        assert can_assign_role(UserRole.RESELLER, UserRole.ADMIN) is False

    def test_user_cannot_assign_any(self):
        assert can_assign_role(UserRole.USER, UserRole.USER) is False
        assert can_assign_role(UserRole.USER, UserRole.ADMIN) is False

    def test_string_inputs(self):
        assert can_assign_role("admin", "reseller") is True
        assert can_assign_role("reseller", "admin") is False

    def test_unknown_actor_role(self):
        assert can_assign_role("unknown", "user") is False

    def test_unknown_target_role(self):
        assert can_assign_role("admin", "unknown") is False


class TestCheckPermission:
    """Tests for check_permission utility function."""

    def test_exact_role_match(self):
        assert check_permission("admin", ["admin", "superadmin"]) is True

    def test_hierarchy_grant(self):
        # admin (level 80) should pass check for reseller (level 50)
        assert check_permission("admin", ["reseller"]) is True
        # superadmin (level 100) should pass check for admin (level 80)
        assert check_permission("superadmin", ["admin"]) is True

    def test_no_match(self):
        assert check_permission("user", ["admin", "superadmin"]) is False

    def test_hierarchy_deny(self):
        # user (level 10) should not pass check for reseller (level 50)
        assert check_permission("user", ["reseller"]) is False
        # reseller (level 50) should not pass check for admin (level 80)
        assert check_permission("reseller", ["admin"]) is False

    def test_allow_self_true(self):
        assert (
            check_permission(
                "user",
                ["admin"],
                user_id="user-1",
                resource_owner_id="user-1",
                allow_self=True,
            )
            is True
        )

    def test_allow_self_different_owner(self):
        assert (
            check_permission(
                "user",
                ["admin"],
                user_id="user-1",
                resource_owner_id="user-2",
                allow_self=True,
            )
            is False
        )

    def test_allow_self_false(self):
        assert (
            check_permission(
                "user",
                ["admin"],
                user_id="user-1",
                resource_owner_id="user-1",
                allow_self=False,
            )
            is False
        )

    def test_user_role_enum_input(self):
        assert check_permission(UserRole.ADMIN, ["admin"]) is True
        assert check_permission(UserRole.USER, ["admin"]) is False


# ──────────────────────────────────────────────
# RBACService Tests
# ──────────────────────────────────────────────


class TestRBACService:
    """Tests for RBACService class methods."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        """Create an RBACService instance with a mock session."""
        return RBACService(session=mock_session)

    @pytest.fixture
    def sample_user(self):
        """Create a sample User instance for testing."""
        user = MagicMock(spec=User)
        user.id = "123e4567-e89b-12d3-a456-426614174000"
        user.role = UserRole.USER
        user.is_superadmin = False
        user.is_admin = False
        user.is_reseller = False
        return user

    @pytest.mark.asyncio
    async def test_get_user_role_success(self, service, mock_session):
        """Test get_user_role returns the role string."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = UserRole.ADMIN
        mock_session.execute = AsyncMock(return_value=mock_result)

        role = await service.get_user_role("test-user-id")
        assert role == "admin"

    @pytest.mark.asyncio
    async def test_get_user_role_not_found(self, service, mock_session):
        """Test get_user_role raises UserNotFoundError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(UserNotFoundError) as exc_info:
            await service.get_user_role("nonexistent-id")
        assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_check_user_permission_granted(self, service, mock_session):
        """Test check_user_permission returns True when allowed."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = UserRole.ADMIN
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.check_user_permission(
            "test-user-id", required_roles=["admin", "superadmin"]
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_check_user_permission_denied(self, service, mock_session):
        """Test check_user_permission returns False when denied."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = UserRole.USER
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.check_user_permission(
            "test-user-id", required_roles=["admin", "superadmin"]
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_check_user_permission_not_found(self, service, mock_session):
        """Test check_user_permission returns False for unknown user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.check_user_permission(
            "nonexistent-id", required_roles=["admin"]
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_assign_role_success(self, service, mock_session, sample_user):
        """Test assign_role successfully updates user role."""
        # Mock session.execute to return the sample_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute = AsyncMock(return_value=mock_user_result)

        with patch(
            "core.rbac.service.can_assign_role", return_value=True
        ):
            user = await service.assign_role(
                user_id=sample_user.id,
                new_role="admin",
                actor_role="superadmin",
            )
            assert user.role == UserRole.ADMIN
            mock_session.commit.assert_awaited_once()
            mock_session.refresh.assert_awaited_once_with(sample_user)

    @pytest.mark.asyncio
    async def test_assign_role_invalid_role(self, service, mock_session):
        """Test assign_role raises InvalidRoleAssignmentError for invalid role."""
        with pytest.raises(InvalidRoleAssignmentError) as exc_info:
            await service.assign_role(
                user_id="some-id",
                new_role="invalid_role",
                actor_role="superadmin",
            )
        assert "Invalid role" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_assign_role_insufficient_privileges(
        self, service, mock_session
    ):
        """Test assign_role raises error when actor lacks permission."""
        with patch("core.rbac.service.can_assign_role", return_value=False):
            with pytest.raises(InvalidRoleAssignmentError) as exc_info:
                await service.assign_role(
                    user_id="some-id",
                    new_role="admin",
                    actor_role="user",
                )
            assert "Cannot assign" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_assign_role_user_not_found(self, service, mock_session):
        """Test assign_role raises UserNotFoundError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("core.rbac.service.can_assign_role", return_value=True):
            with pytest.raises(UserNotFoundError) as exc_info:
                await service.assign_role(
                    user_id="nonexistent-id",
                    new_role="user",
                    actor_role="admin",
                )
            assert "not found" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_require_role_granted(self, service, mock_session):
        """Test require_role does not raise for authorized user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = UserRole.ADMIN
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise
        await service.require_role(
            "test-user-id", required_roles=["admin", "superadmin"]
        )

    @pytest.mark.asyncio
    async def test_require_role_denied(self, service, mock_session):
        """Test require_role raises HTTPException 403 for unauthorized user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = UserRole.USER
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await service.require_role(
                "test-user-id", required_roles=["admin", "superadmin"]
            )
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_require_role_not_found(self, service, mock_session):
        """Test require_role raises HTTPException 404 for unknown user."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await service.require_role(
                "nonexistent-id", required_roles=["admin"]
            )
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_users_by_role(self, service, mock_session):
        """Test get_users_by_role returns users and total count."""
        mock_users = [MagicMock(spec=User) for _ in range(3)]
        for i, u in enumerate(mock_users):
            u.id = f"user-{i}"
            u.role = UserRole.ADMIN

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_session.execute = AsyncMock(return_value=mock_result)

        users, total = await service.get_users_by_role(
            UserRole.ADMIN, page=1, page_size=20
        )
        assert len(users) == 3
        assert total == 3

    @pytest.mark.asyncio
    async def test_get_users_by_role_invalid_role(self, service, mock_session):
        """Test get_users_by_role returns empty for invalid role."""
        users, total = await service.get_users_by_role(
            "invalid_role", page=1, page_size=20
        )
        assert users == []
        assert total == 0


# ──────────────────────────────────────────────
# Decorator / Dependency Tests
# ──────────────────────────────────────────────


class TestRequireRoleDecorator:
    """Tests for the @require_role() decorator."""

    @pytest.mark.asyncio
    async def test_require_role_allowed(self):
        """Test decorator passes for allowed role."""
        mock_user = MagicMock(spec=User)
        mock_user.role = UserRole.ADMIN

        @require_role("admin", "superadmin")
        async def test_endpoint(current_user: User = None):
            return {"success": True}

        result = await test_endpoint(current_user=mock_user)
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_require_role_denied(self):
        """Test decorator raises 403 for disallowed role."""
        mock_user = MagicMock(spec=User)
        mock_user.role = UserRole.USER

        @require_role("admin", "superadmin")
        async def test_endpoint(current_user: User = None):
            return {"success": True}

        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint(current_user=mock_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Insufficient permissions" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_role_no_user(self):
        """Test decorator raises 401 when no user is provided."""

        @require_role("admin")
        async def test_endpoint(current_user: User = None):
            return {"success": True}

        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint(current_user=None)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_require_role_with_user_role_enum(self):
        """Test decorator works with UserRole enum values."""
        mock_user = MagicMock(spec=User)
        mock_user.role = UserRole.ADMIN

        @require_role(UserRole.ADMIN, UserRole.SUPERADMIN)
        async def test_endpoint(current_user: User = None):
            return {"success": True}

        result = await test_endpoint(current_user=mock_user)
        assert result == {"success": True}


class TestRequirePermissionDecorator:
    """Tests for the @require_permission() decorator (alias for require_role)."""

    @pytest.mark.asyncio
    async def test_require_permission_allowed(self):
        """Test decorator passes for allowed role."""
        mock_user = MagicMock(spec=User)
        mock_user.role = UserRole.ADMIN

        @require_permission("admin", "superadmin")
        async def test_endpoint(current_user: User = None):
            return {"success": True}

        result = await test_endpoint(current_user=mock_user)
        assert result == {"success": True}

    @pytest.mark.asyncio
    async def test_require_permission_denied(self):
        """Test decorator raises 403 for disallowed role."""
        mock_user = MagicMock(spec=User)
        mock_user.role = UserRole.USER

        @require_permission("admin")
        async def test_endpoint(current_user: User = None):
            return {"success": True}

        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint(current_user=mock_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestHasRoleDependency:
    """Tests for the has_role FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_has_role_true(self):
        """Test has_role returns True when user has required role."""
        mock_user = MagicMock(spec=User)
        mock_user.role = UserRole.ADMIN

        result = await has_role(
            required_roles=["admin", "superadmin"], current_user=mock_user
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_has_role_false(self):
        """Test has_role returns False when user lacks required role."""
        mock_user = MagicMock(spec=User)
        mock_user.role = UserRole.USER

        result = await has_role(
            required_roles=["admin", "superadmin"], current_user=mock_user
        )
        assert result is False


class TestRequireAdminDependency:
    """Tests for the require_admin FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_require_admin_allowed(self):
        """Test require_admin returns the user for admin roles."""
        mock_user = MagicMock(spec=User)
        mock_user.is_admin = True

        result = await require_admin(current_user=mock_user)
        assert result is mock_user

    @pytest.mark.asyncio
    async def test_require_admin_denied(self):
        """Test require_admin raises 403 for non-admin."""
        mock_user = MagicMock(spec=User)
        mock_user.is_admin = False

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(current_user=mock_user)
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Admin privileges required" in exc_info.value.detail


# ──────────────────────────────────────────────
# Schema Tests
# ──────────────────────────────────────────────


class TestRBACSchemas:
    """Tests for RBAC Pydantic schemas."""

    def test_role_assignment_valid(self):
        """Test RoleAssignment schema with valid data."""
        ra = RoleAssignment(user_id="user-1", role="admin")
        assert ra.user_id == "user-1"
        assert ra.role == "admin"

    def test_role_assignment_invalid_role(self):
        """Test RoleAssignment schema rejects invalid role."""
        with pytest.raises(Exception):
            RoleAssignment(user_id="user-1", role="invalid_role")

    def test_role_assignment_case_insensitive(self):
        """Test RoleAssignment normalises role to lowercase."""
        ra = RoleAssignment(user_id="user-1", role="ADMIN")
        assert ra.role == "admin"

    def test_permission_check_valid(self):
        """Test PermissionCheck schema with valid data."""
        pc = PermissionCheck(
            user_id="user-1",
            required_roles=["admin", "superadmin"],
        )
        assert pc.user_id == "user-1"
        assert pc.required_roles == ["admin", "superadmin"]
        assert pc.allow_self is False
        assert pc.resource_owner_id is None

    def test_permission_check_with_self_access(self):
        """Test PermissionCheck with self-access enabled."""
        pc = PermissionCheck(
            user_id="user-1",
            required_roles=["admin"],
            allow_self=True,
            resource_owner_id="user-1",
        )
        assert pc.allow_self is True
        assert pc.resource_owner_id == "user-1"

    def test_permission_check_response(self):
        """Test PermissionCheckResponse schema."""
        pcr = PermissionCheckResponse(
            granted=True,
            user_id="user-1",
            user_role="admin",
            required_roles=["admin", "superadmin"],
        )
        assert pcr.granted is True
        assert pcr.user_role == "admin"

    def test_role_hierarchy(self):
        """Test RoleHierarchy schema."""
        rh = RoleHierarchy(role="admin", level=80)
        assert rh.role == "admin"
        assert rh.level == 80
        assert rh.inherits_from == []

    def test_bulk_role_assignment(self):
        """Test BulkRoleAssignment schema."""
        assignments = [
            RoleAssignment(user_id="user-1", role="admin"),
            RoleAssignment(user_id="user-2", role="reseller"),
        ]
        bra = BulkRoleAssignment(assignments=assignments)
        assert len(bra.assignments) == 2

    def test_role_update_response(self):
        """Test RoleUpdateResponse schema."""
        now = datetime.now(timezone.utc)
        rur = RoleUpdateResponse(
            user_id="user-1",
            old_role="user",
            new_role="admin",
            updated_at=now,
        )
        assert rur.old_role == "user"
        assert rur.new_role == "admin"
        assert rur.updated_at == now


# ──────────────────────────────────────────────
# RBAC Exception Tests
# ──────────────────────────────────────────────


class TestRBACExceptions:
    """Tests for RBAC custom exceptions."""

    def test_rbac_error(self):
        exc = RBACError("Something went wrong")
        assert exc.message == "Something went wrong"
        assert exc.status_code == status.HTTP_400_BAD_REQUEST

    def test_user_not_found_error(self):
        exc = UserNotFoundError("user-123")
        assert "not found" in exc.message.lower()
        assert exc.status_code == status.HTTP_404_NOT_FOUND

    def test_invalid_role_assignment_error(self):
        exc = InvalidRoleAssignmentError("Cannot assign this role")
        assert exc.message == "Cannot assign this role"
        assert exc.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_insufficient_privileges_error(self):
        exc = InsufficientPrivilegesError(["admin", "superadmin"])
        assert "admin" in exc.message
        assert "superadmin" in exc.message
        assert exc.status_code == status.HTTP_403_FORBIDDEN