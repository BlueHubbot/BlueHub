"""
BlueHub Audit Logging Unit Tests
==================================
Tests for the audit logging system: AuditService, AuditLogger, log_audit
decorator, and Pydantic schemas. Uses pytest-asyncio for async tests
and mocks for database session isolation.

Run: python -m pytest tests/unit/test_audit.py -v --asyncio-mode=auto
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit.logger import AuditLogger, log_audit
from core.audit.schemas import (
    AuditLogListResponse,
    AuditLogQueryParams,
    AuditLogResponse,
    AuditLogStatsResponse,
)
from core.audit.service import AuditLogNotFoundError, AuditService
from shared.models.audit_log import AuditLog
from shared.models.enums import AuditAction

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture()
def mock_session():
    """Create a mock async session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture()
def service(mock_session):
    """Create an AuditService instance with a mock session."""
    return AuditService(session=mock_session)


@pytest.fixture()
def logger(mock_session):
    """Create an AuditLogger instance with a mock session."""
    return AuditLogger(session=mock_session)


@pytest.fixture()
def sample_audit_log():
    """Create a sample AuditLog instance for testing."""
    log = MagicMock(spec=AuditLog)
    log.id = "123e4567-e89b-12d3-a456-426614174000"
    log.action = AuditAction.CREATE
    log.resource_type = "user"
    log.resource_id = "user-abc-123"
    log.tenant_id = "tenant-xyz-789"
    log.user_id = "actor-def-456"
    log.details = {"key": "value", "email": "test@example.com"}
    log.ip_address = "192.168.1.100"
    log.user_agent = "Mozilla/5.0 Test Agent"
    log.timestamp = datetime.now(UTC)
    log.created_at = datetime.now(UTC)
    return log


# ──────────────────────────────────────────────
# AuditService Tests
# ──────────────────────────────────────────────


class TestAuditService:
    """Tests for AuditService class methods."""

    # ── log_event ──────────────────────────────

    @pytest.mark.asyncio()
    async def test_log_event_creates_entry(self, service, mock_session):
        """Test log_event creates an AuditLog entry and returns it."""
        # Configure mock to simulate refresh setting an ID
        def refresh_side_effect(entry):
            entry.id = "new-log-id-123"

        mock_session.refresh = AsyncMock(side_effect=refresh_side_effect)

        result = await service.log_event(
            action=AuditAction.CREATE,
            resource_type="user",
            resource_id="user-123",
            tenant_id="tenant-1",
            user_id="actor-1",
            details={"email": "test@example.com"},
            ip_address="10.0.0.1",
            user_agent="TestAgent/1.0",
        )

        # Verify the entry was added to session and committed
        assert mock_session.add.called
        assert mock_session.commit.awaited_once
        assert mock_session.refresh.awaited_once

        # Verify the returned entry has the expected attributes
        assert isinstance(result, AuditLog)
        assert result.id == "new-log-id-123"
        assert result.action == AuditAction.CREATE
        assert result.resource_type == "user"
        assert result.resource_id == "user-123"
        assert result.tenant_id == "tenant-1"
        assert result.user_id == "actor-1"
        assert result.details == {"email": "test@example.com"}
        assert result.ip_address == "10.0.0.1"
        assert result.user_agent == "TestAgent/1.0"

    @pytest.mark.asyncio()
    async def test_log_event_with_string_action(self, service, mock_session):
        """Test log_event accepts string action values."""
        mock_session.refresh = AsyncMock()

        result = await service.log_event(
            action="create",
            resource_type="user",
        )

        assert result.action == AuditAction.CREATE

    @pytest.mark.asyncio()
    async def test_log_event_with_unknown_string_action(self, service, mock_session):
        """Test log_event passes through unknown string actions."""
        mock_session.refresh = AsyncMock()

        result = await service.log_event(
            action="custom_action",
            resource_type="custom",
        )

        assert result.action == "custom_action"

    @pytest.mark.asyncio()
    async def test_log_event_minimal_params(self, service, mock_session):
        """Test log_event works with only required parameters."""
        mock_session.refresh = AsyncMock()

        result = await service.log_event(
            action=AuditAction.LOGIN,
            resource_type="auth",
        )

        assert result.details == {}
        assert result.resource_id is None
        assert result.tenant_id is None
        assert result.user_id is None
        assert result.ip_address is None
        assert result.user_agent is None

    # ── get_log ───────────────────────────────

    @pytest.mark.asyncio()
    async def test_get_log_found(self, service, mock_session, sample_audit_log):
        """Test get_log returns the log entry when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_audit_log
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await service.get_log(sample_audit_log.id)

        assert result is sample_audit_log
        assert result.id == sample_audit_log.id
        assert result.action == AuditAction.CREATE

    @pytest.mark.asyncio()
    async def test_get_log_not_found(self, service, mock_session):
        """Test get_log raises AuditLogNotFoundError when not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(AuditLogNotFoundError) as exc_info:
            await service.get_log("nonexistent-id")
        assert "not found" in str(exc_info.value).lower()
        assert "nonexistent-id" in str(exc_info.value)

    # ── query_logs ────────────────────────────

    @pytest.mark.asyncio()
    async def test_query_logs_no_filters(self, service, mock_session, sample_audit_log):
        """Test query_logs returns all entries without filters."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [
            sample_audit_log,
            sample_audit_log,
            sample_audit_log,
        ]

        # Return count first, then data
        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        entries, total = await service.query_logs()

        assert total == 3
        assert len(entries) == 3
        assert entries[0] is sample_audit_log

    @pytest.mark.asyncio()
    async def test_query_logs_with_action_filter(self, service, mock_session, sample_audit_log):
        """Test query_logs filters by action type."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_audit_log]

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        entries, total = await service.query_logs(action=AuditAction.CREATE)

        assert total == 1
        assert len(entries) == 1

    @pytest.mark.asyncio()
    async def test_query_logs_with_resource_filter(self, service, mock_session, sample_audit_log):
        """Test query_logs filters by resource type."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_audit_log]

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        entries, total = await service.query_logs(resource_type="user")

        assert total == 1

    @pytest.mark.asyncio()
    async def test_query_logs_with_user_filter(self, service, mock_session, sample_audit_log):
        """Test query_logs filters by user ID."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_audit_log]

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        entries, total = await service.query_logs(user_id="actor-def-456")

        assert total == 1

    @pytest.mark.asyncio()
    async def test_query_logs_with_date_filters(self, service, mock_session, sample_audit_log):
        """Test query_logs filters by date range."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_audit_log]

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        entries, total = await service.query_logs(
            start_date="2026-01-01T00:00:00Z",
            end_date="2026-12-31T23:59:59Z",
        )

        assert total == 1

    @pytest.mark.asyncio()
    async def test_query_logs_pagination(self, service, mock_session, sample_audit_log):
        """Test query_logs supports pagination."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 50

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_audit_log] * 10

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        entries, total = await service.query_logs(page=2, page_size=10)

        assert total == 50
        assert len(entries) == 10

    # ── get_logs_by_user ──────────────────────

    @pytest.mark.asyncio()
    async def test_get_logs_by_user(self, service, mock_session, sample_audit_log):
        """Test get_logs_by_user delegates to query_logs with user_id."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [
            sample_audit_log,
            sample_audit_log,
        ]

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        entries, total = await service.get_logs_by_user(
            user_id="actor-def-456",
            page=1,
            page_size=20,
        )

        assert total == 2
        assert len(entries) == 2

    # ── get_logs_by_resource ──────────────────

    @pytest.mark.asyncio()
    async def test_get_logs_by_resource(self, service, mock_session, sample_audit_log):
        """Test get_logs_by_resource delegates to query_logs."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_audit_log]

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        entries, total = await service.get_logs_by_resource(
            resource_type="user",
            resource_id="user-abc-123",
        )

        assert total == 1
        assert len(entries) == 1

    # ── get_logs_by_tenant ────────────────────

    @pytest.mark.asyncio()
    async def test_get_logs_by_tenant(self, service, mock_session, sample_audit_log):
        """Test get_logs_by_tenant delegates to query_logs."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_audit_log]

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        entries, total = await service.get_logs_by_tenant(
            tenant_id="tenant-xyz-789",
        )

        assert total == 1
        assert len(entries) == 1

    # ── cleanup_old_logs ──────────────────────

    @pytest.mark.asyncio()
    async def test_cleanup_old_logs(self, service, mock_session):
        """Test cleanup_old_logs deletes old entries and returns count."""
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        count = await service.cleanup_old_logs(retention_days=30)

        assert count == 5
        assert mock_session.execute.awaited_once
        assert mock_session.commit.awaited_once

    @pytest.mark.asyncio()
    async def test_cleanup_old_logs_default_retention(self, service, mock_session):
        """Test cleanup_old_logs uses 365-day default retention."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await service.cleanup_old_logs()

        assert count == 0

    @pytest.mark.asyncio()
    async def test_cleanup_old_logs_no_old_logs(self, service, mock_session):
        """Test cleanup_old_logs returns 0 when no logs to delete."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await service.cleanup_old_logs(retention_days=365)

        assert count == 0

    # ── get_stats ─────────────────────────────

    @pytest.mark.asyncio()
    async def test_get_stats(self, service, mock_session):
        """Test get_stats returns aggregated statistics."""
        # First mock: total count
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 10

        # Second mock: action counts
        mock_action_row_1 = MagicMock()
        mock_action_row_1.action = AuditAction.CREATE
        mock_action_row_1.count = 5
        mock_action_row_2 = MagicMock()
        mock_action_row_2.action = AuditAction.LOGIN
        mock_action_row_2.count = 3

        mock_action_result = MagicMock()
        mock_action_result.__iter__.return_value = iter([mock_action_row_1, mock_action_row_2])

        # Third mock: resource counts
        mock_resource_row_1 = MagicMock()
        mock_resource_row_1.resource_type = "user"
        mock_resource_row_1.count = 7
        mock_resource_row_2 = MagicMock()
        mock_resource_row_2.resource_type = "auth"
        mock_resource_row_2.count = 3

        mock_resource_result = MagicMock()
        mock_resource_result.__iter__.return_value = iter([mock_resource_row_1, mock_resource_row_2])

        mock_session.execute = AsyncMock(
            side_effect=[mock_total_result, mock_action_result, mock_resource_result]
        )

        stats = await service.get_stats()

        assert stats["total_logs"] == 10
        assert stats["actions_by_type"]["create"] == 5
        assert stats["actions_by_type"]["login"] == 3
        assert stats["resources"]["user"] == 7
        assert stats["resources"]["auth"] == 3

    @pytest.mark.asyncio()
    async def test_get_stats_with_filters(self, service, mock_session):
        """Test get_stats applies tenant and date filters."""
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 3

        mock_action_result = MagicMock()
        mock_action_result.__iter__.return_value = iter([])

        mock_resource_result = MagicMock()
        mock_resource_result.__iter__.return_value = iter([])

        mock_session.execute = AsyncMock(
            side_effect=[mock_total_result, mock_action_result, mock_resource_result]
        )

        stats = await service.get_stats(
            tenant_id="tenant-1",
            start_date="2026-01-01T00:00:00Z",
            end_date="2026-12-31T23:59:59Z",
        )

        assert stats["total_logs"] == 3


# ──────────────────────────────────────────────
# AuditLogger Tests
# ──────────────────────────────────────────────


class TestAuditLogger:
    """Tests for AuditLogger convenience methods."""

    @pytest.mark.asyncio()
    async def test_log_create(self, logger, mock_session):
        """Test log_create convenience method."""
        mock_session.refresh = AsyncMock()

        result = await logger.log_create(
            resource_type="user",
            resource_id="user-123",
            tenant_id="tenant-1",
            user_id="actor-1",
            details={"name": "Test User"},
        )

        assert result.action == AuditAction.CREATE
        assert result.resource_type == "user"

    @pytest.mark.asyncio()
    async def test_log_read(self, logger, mock_session):
        """Test log_read convenience method."""
        mock_session.refresh = AsyncMock()

        result = await logger.log_read(
            resource_type="document",
            resource_id="doc-456",
            user_id="actor-1",
        )

        assert result.action == AuditAction.READ

    @pytest.mark.asyncio()
    async def test_log_update(self, logger, mock_session):
        """Test log_update convenience method."""
        mock_session.refresh = AsyncMock()

        result = await logger.log_update(
            resource_type="service",
            resource_id="svc-789",
            user_id="actor-1",
            details={"changed_fields": ["name", "price"]},
        )

        assert result.action == AuditAction.UPDATE

    @pytest.mark.asyncio()
    async def test_log_delete(self, logger, mock_session):
        """Test log_delete convenience method."""
        mock_session.refresh = AsyncMock()

        result = await logger.log_delete(
            resource_type="user",
            resource_id="user-to-delete",
            user_id="actor-1",
        )

        assert result.action == AuditAction.DELETE

    @pytest.mark.asyncio()
    async def test_log_login(self, logger, mock_session):
        """Test log_login convenience method."""
        mock_session.refresh = AsyncMock()

        result = await logger.log_login(
            user_id="user-1",
            ip_address="192.168.1.1",
        )

        assert result.action == AuditAction.LOGIN
        assert result.resource_type == "auth"

    @pytest.mark.asyncio()
    async def test_log_logout(self, logger, mock_session):
        """Test log_logout convenience method."""
        mock_session.refresh = AsyncMock()

        result = await logger.log_logout(
            user_id="user-1",
        )

        assert result.action == AuditAction.LOGOUT
        assert result.resource_type == "auth"

    @pytest.mark.asyncio()
    async def test_log_payment(self, logger, mock_session):
        """Test log_payment convenience method."""
        mock_session.refresh = AsyncMock()

        result = await logger.log_payment(
            resource_id="invoice-123",
            user_id="user-1",
            details={"amount": 99.99, "currency": "USD"},
        )

        assert result.action == AuditAction.PAYMENT
        assert result.resource_type == "payment"


# ──────────────────────────────────────────────
# log_audit Decorator Tests
# ──────────────────────────────────────────────


class TestLogAuditDecorator:
    """Tests for the @log_audit decorator."""

    @pytest.mark.asyncio()
    async def test_log_audit_decorator_logs_after_execution(self, mock_session):
        """Test decorator logs audit event after function execution."""
        mock_session.refresh = AsyncMock()
        mock_session.add = MagicMock()

        @log_audit(
            AuditAction.CREATE,
            "user",
            get_resource_id=lambda *a, **kw: kw.get("user_id"),
            get_user_id=lambda *a, **kw: kw.get("actor_id"),
        )
        async def create_user(session: AsyncSession, user_id: str, actor_id: str):
            return {"id": user_id, "name": "Test"}

        result = await create_user(session=mock_session, user_id="user-1", actor_id="actor-1")

        # The original function result should be returned
        assert result == {"id": "user-1", "name": "Test"}

        # Audit log should have been created
        assert mock_session.add.called

        # Verify the entry added has correct attributes
        added_entry = mock_session.add.call_args[0][0]
        assert added_entry.action == AuditAction.CREATE
        assert added_entry.resource_type == "user"
        assert added_entry.resource_id == "user-1"
        assert added_entry.user_id == "actor-1"

    @pytest.mark.asyncio()
    async def test_log_audit_decorator_no_session(self):
        """Test decorator handles missing session gracefully."""
        @log_audit(
            AuditAction.READ,
            "document",
        )
        async def read_document(doc_id: str):
            return {"id": doc_id, "content": "test"}

        result = await read_document(doc_id="doc-1")

        # Should still return result even without session
        assert result == {"id": "doc-1", "content": "test"}

    @pytest.mark.asyncio()
    async def test_log_audit_decorator_does_not_break_on_error(self, mock_session):
        """Test decorator does not break original function if audit logging fails."""
        mock_session.add = MagicMock(side_effect=Exception("DB error"))

        @log_audit(
            AuditAction.UPDATE,
            "service",
            get_resource_id=lambda *a, **kw: kw.get("service_id"),
        )
        async def update_service(session: AsyncSession, service_id: str, name: str):
            return {"id": service_id, "name": name}

        result = await update_service(session=mock_session, service_id="svc-1", name="NewName")

        # Original function result should still be returned even if audit logging fails
        assert result == {"id": "svc-1", "name": "NewName"}

    @pytest.mark.asyncio()
    async def test_log_audit_decorator_with_all_extractors(self, mock_session):
        """Test decorator works with all extractor callables."""
        mock_session.refresh = AsyncMock()
        mock_session.add = MagicMock()

        @log_audit(
            AuditAction.CREATE,
            "tenant",
            get_resource_id=lambda *a, **kw: kw.get("tenant_id"),
            get_tenant_id=lambda *a, **kw: kw.get("tenant_id"),
            get_user_id=lambda *a, **kw: kw.get("created_by"),
            get_details=lambda *a, **kw: {"name": kw.get("name")},
            get_ip_address=lambda *a, **kw: kw.get("ip"),
            get_user_agent=lambda *a, **kw: kw.get("ua"),
        )
        async def create_tenant(
            session: AsyncSession,
            tenant_id: str,
            name: str,
            created_by: str,
            ip: str,
            ua: str,
        ):
            return {"id": tenant_id, "name": name}

        result = await create_tenant(
            session=mock_session,
            tenant_id="tenant-1",
            name="Acme Corp",
            created_by="admin-1",
            ip="10.0.0.1",
            ua="Chrome/120",
        )

        assert result == {"id": "tenant-1", "name": "Acme Corp"}

        added_entry = mock_session.add.call_args[0][0]
        assert added_entry.action == AuditAction.CREATE
        assert added_entry.resource_type == "tenant"
        assert added_entry.resource_id == "tenant-1"
        assert added_entry.tenant_id == "tenant-1"
        assert added_entry.user_id == "admin-1"
        assert added_entry.details == {"name": "Acme Corp"}
        assert added_entry.ip_address == "10.0.0.1"
        assert added_entry.user_agent == "Chrome/120"


# ──────────────────────────────────────────────
# AuditLogNotFoundError Tests
# ──────────────────────────────────────────────


class TestAuditExceptions:
    """Tests for audit custom exceptions."""

    def test_audit_log_not_found_error(self):
        """Test AuditLogNotFoundError formatting."""
        exc = AuditLogNotFoundError("log-id-123")
        assert "log-id-123" in str(exc)
        assert "not found" in str(exc).lower()

    def test_audit_log_not_found_error_empty_id(self):
        """Test AuditLogNotFoundError with empty ID."""
        exc = AuditLogNotFoundError("")
        assert "not found" in str(exc).lower()


# ──────────────────────────────────────────────
# Schema Tests
# ──────────────────────────────────────────────


class TestAuditSchemas:
    """Tests for audit Pydantic schemas."""

    def test_audit_log_response(self):
        """Test AuditLogResponse schema with valid data."""
        now = datetime.now(UTC)
        response = AuditLogResponse(
            id="log-1",
            action="create",
            resource_type="user",
            resource_id="user-123",
            tenant_id="tenant-1",
            user_id="actor-1",
            details={"key": "value"},
            ip_address="10.0.0.1",
            user_agent="TestAgent/1.0",
            timestamp=now,
            created_at=now,
        )
        assert response.id == "log-1"
        assert response.action == "create"
        assert response.resource_type == "user"
        assert response.resource_id == "user-123"
        assert response.tenant_id == "tenant-1"
        assert response.user_id == "actor-1"
        assert response.details == {"key": "value"}
        assert response.ip_address == "10.0.0.1"
        assert response.user_agent == "TestAgent/1.0"
        assert response.timestamp == now
        assert response.created_at == now

    def test_audit_log_response_minimal(self):
        """Test AuditLogResponse with only required fields."""
        now = datetime.now(UTC)
        response = AuditLogResponse(
            id="log-1",
            action="read",
            resource_type="document",
            timestamp=now,
            created_at=now,
        )
        assert response.resource_id is None
        assert response.tenant_id is None
        assert response.user_id is None
        assert response.details is None
        assert response.ip_address is None
        assert response.user_agent is None

    def test_audit_log_list_response(self):
        """Test AuditLogListResponse schema."""
        now = datetime.now(UTC)
        items = [
            AuditLogResponse(
                id="log-1",
                action="create",
                resource_type="user",
                timestamp=now,
                created_at=now,
            ),
            AuditLogResponse(
                id="log-2",
                action="delete",
                resource_type="user",
                timestamp=now,
                created_at=now,
            ),
        ]
        response = AuditLogListResponse(
            items=items,
            total=2,
            page=1,
            page_size=10,
            total_pages=1,
        )
        assert len(response.items) == 2
        assert response.total == 2
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 1

    def test_audit_log_list_response_multiple_pages(self):
        """Test AuditLogListResponse with multiple pages."""
        now = datetime.now(UTC)
        items = [AuditLogResponse(
            id=f"log-{i}",
            action="read",
            resource_type="document",
            timestamp=now,
            created_at=now,
        ) for i in range(5)]
        response = AuditLogListResponse(
            items=items,
            total=25,
            page=2,
            page_size=5,
            total_pages=5,
        )
        assert response.total == 25
        assert response.page == 2
        assert response.page_size == 5
        assert response.total_pages == 5

    def test_audit_log_query_params(self):
        """Test AuditLogQueryParams schema."""
        params = AuditLogQueryParams(
            action="create",
            resource_type="user",
            resource_id="user-123",
            tenant_id="tenant-1",
            user_id="actor-1",
            start_date="2026-01-01T00:00:00Z",
            end_date="2026-12-31T23:59:59Z",
            page=1,
            page_size=50,
        )
        assert params.action == "create"
        assert params.resource_type == "user"
        assert params.resource_id == "user-123"
        assert params.tenant_id == "tenant-1"
        assert params.user_id == "actor-1"
        assert params.start_date == "2026-01-01T00:00:00Z"
        assert params.end_date == "2026-12-31T23:59:59Z"
        assert params.page == 1
        assert params.page_size == 50

    def test_audit_log_query_params_defaults(self):
        """Test AuditLogQueryParams default values."""
        params = AuditLogQueryParams()
        assert params.action is None
        assert params.resource_type is None
        assert params.page == 1
        assert params.page_size == 50

    def test_audit_log_stats_response(self):
        """Test AuditLogStatsResponse schema."""
        response = AuditLogStatsResponse(
            total_logs=100,
            actions_by_type={"create": 40, "delete": 30, "login": 30},
            resources={"user": 50, "auth": 30, "service": 20},
        )
        assert response.total_logs == 100
        assert response.actions_by_type["create"] == 40
        assert response.resources["user"] == 50

    def test_audit_log_stats_response_empty(self):
        """Test AuditLogStatsResponse with no data."""
        response = AuditLogStatsResponse(
            total_logs=0,
            actions_by_type={},
            resources={},
        )
        assert response.total_logs == 0
        assert response.actions_by_type == {}
        assert response.resources == {}


# ──────────────────────────────────────────────
# Integration-style Service Tests
# ──────────────────────────────────────────────


class TestAuditServiceIntegration:
    """Integration-style tests for AuditService with real db-like mocks."""

    @pytest.mark.asyncio()
    async def test_log_and_retrieve_flow(self, service, mock_session, sample_audit_log):
        """Test a complete log then retrieve flow."""
        # Step 1: Create log entry
        def refresh_side_effect(entry):
            entry.id = sample_audit_log.id
            entry.timestamp = sample_audit_log.timestamp

        mock_session.refresh = AsyncMock(side_effect=refresh_side_effect)

        created = await service.log_event(
            action=AuditAction.CREATE,
            resource_type="user",
            resource_id="user-789",
            user_id="actor-1",
        )

        # Step 2: Retrieve the entry
        # Reconfigure mock for get_log
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = sample_audit_log
        mock_session.execute = AsyncMock(return_value=mock_get_result)

        retrieved = await service.get_log(sample_audit_log.id)

        assert retrieved is sample_audit_log
        assert retrieved.resource_type == "user"

    @pytest.mark.asyncio()
    async def test_cleanup_does_not_affect_recent_logs(self, service, mock_session):
        """Test cleanup only removes old logs, not recent ones."""
        # First call: cleanup returns count of deleted old logs
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 2
        mock_session.execute = AsyncMock(return_value=mock_delete_result)

        deleted_count = await service.cleanup_old_logs(retention_days=30)

        assert deleted_count == 2
        assert mock_session.commit.awaited_once

    @pytest.mark.asyncio()
    async def test_get_stats_empty(self, service, mock_session):
        """Test get_stats returns zeroed data when no logs exist."""
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 0

        mock_action_result = MagicMock()
        mock_action_result.__iter__.return_value = iter([])

        mock_resource_result = MagicMock()
        mock_resource_result.__iter__.return_value = iter([])

        mock_session.execute = AsyncMock(
            side_effect=[mock_total_result, mock_action_result, mock_resource_result]
        )

        stats = await service.get_stats()

        assert stats["total_logs"] == 0
        assert stats["actions_by_type"] == {}
        assert stats["resources"] == {}
