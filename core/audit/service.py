"""
BlueHub Audit Service
======================
Service layer for audit log operations: creating, querying,
and managing the immutable audit trail.
"""

from __future__ import annotations

from datetime import timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.audit_log import AuditLog
from shared.models.enums import AuditAction


class AuditLogNotFoundError(Exception):
    """Raised when an audit log entry is not found."""

    def __init__(self, log_id: str) -> None:
        self.message = f"Audit log with id '{log_id}' not found"
        super().__init__(self.message)


class AuditService:
    """
    Service for managing audit log entries.

    Provides methods for creating, querying, and cleaning up
    audit logs. Audit logs are immutable - they cannot be updated
    or deleted individually (only bulk cleanup by retention).
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the audit service.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self.session = session

    async def log_event(
        self,
        action: AuditAction | str,
        resource_type: str,
        *,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """
        Create a new audit log entry.

        Args:
            action: Type of action performed (from AuditAction enum or string).
            resource_type: Type of resource affected.
            resource_id: Identifier of the affected resource.
            tenant_id: Tenant UUID associated with the action.
            user_id: User UUID who performed the action.
            details: Arbitrary metadata/context about the action.
            ip_address: Client IP address.
            user_agent: User-Agent string from the request.

        Returns:
            The created AuditLog entry.
        """
        # Convert string action to enum if needed
        if isinstance(action, str):
            try:
                action_enum = AuditAction(action.lower())
            except ValueError:
                action_enum = action  # type: ignore[assignment]
        else:
            action_enum = action

        entry = AuditLog(
            action=action_enum,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            user_id=user_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)

        return entry

    async def get_log(self, log_id: str) -> AuditLog:
        """
        Get a single audit log entry by ID.

        Args:
            log_id: UUID of the audit log entry.

        Returns:
            The AuditLog entry.

        Raises:
            AuditLogNotFoundError: If the log entry is not found.
        """
        result = await self.session.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            raise AuditLogNotFoundError(log_id)
        return entry

    async def query_logs(
        self,
        *,
        action: AuditAction | str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """
        Query audit logs with optional filters and pagination.

        Args:
            action: Filter by action type.
            resource_type: Filter by resource type.
            resource_id: Filter by resource ID.
            tenant_id: Filter by tenant UUID.
            user_id: Filter by user UUID.
            start_date: Filter logs after this date (ISO format string).
            end_date: Filter logs before this date (ISO format string).
            page: Page number (1-indexed).
            page_size: Items per page (max 100).

        Returns:
            Tuple of (list of AuditLog entries, total count).
        """
        # Build base query
        query = select(AuditLog)
        count_query = select(func.count(AuditLog.id))

        # Apply filters
        conditions = []
        if action is not None:
            if isinstance(action, str):
                try:
                    action_enum = AuditAction(action.lower())
                except ValueError:
                    action_enum = action  # type: ignore[assignment]
            else:
                action_enum = action
            conditions.append(AuditLog.action == action_enum)

        if resource_type is not None:
            conditions.append(AuditLog.resource_type == resource_type)
        if resource_id is not None:
            conditions.append(AuditLog.resource_id == resource_id)
        if tenant_id is not None:
            conditions.append(AuditLog.tenant_id == tenant_id)
        if user_id is not None:
            conditions.append(AuditLog.user_id == user_id)
        if start_date is not None:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date is not None:
            conditions.append(AuditLog.created_at <= end_date)

        # Apply conditions to both queries
        for cond in conditions:
            query = query.where(cond)
            count_query = count_query.where(cond)

        # Order by most recent first
        query = query.order_by(AuditLog.created_at.desc())

        # Count total
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute
        result = await self.session.execute(query)
        entries = list(result.scalars().all())

        return entries, int(total)

    async def get_logs_by_user(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """
        Get all audit logs for a specific user.

        Args:
            user_id: UUID of the user.
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Tuple of (list of AuditLog entries, total count).
        """
        return await self.query_logs(
            user_id=user_id,
            page=page,
            page_size=page_size,
        )

    async def get_logs_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """
        Get all audit logs for a specific resource.

        Args:
            resource_type: Type of resource.
            resource_id: Identifier of the resource.
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Tuple of (list of AuditLog entries, total count).
        """
        return await self.query_logs(
            resource_type=resource_type,
            resource_id=resource_id,
            page=page,
            page_size=page_size,
        )

    async def get_logs_by_tenant(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """
        Get all audit logs for a specific tenant.

        Args:
            tenant_id: UUID of the tenant.
            page: Page number (1-indexed).
            page_size: Items per page.

        Returns:
            Tuple of (list of AuditLog entries, total count).
        """
        return await self.query_logs(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
        )

    async def cleanup_old_logs(
        self,
        retention_days: int = 365,
    ) -> int:
        """
        Delete audit logs older than the specified retention period.

        Args:
            retention_days: Number of days to retain logs (default: 365).

        Returns:
            Number of deleted log entries.
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=retention_days)

        stmt = delete(AuditLog).where(AuditLog.created_at < cutoff_date)
        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount

    async def get_stats(
        self,
        *,
        tenant_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Get audit log statistics.

        Args:
            tenant_id: Filter by tenant UUID.
            start_date: Filter logs after this date.
            end_date: Filter logs before this date.

        Returns:
            Dict with statistics: total_logs, actions_by_type, etc.
        """

        # Count total
        count_query = select(func.count(AuditLog.id))
        if tenant_id is not None:
            count_query = count_query.where(AuditLog.tenant_id == tenant_id)
        if start_date is not None:
            count_query = count_query.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            count_query = count_query.where(AuditLog.created_at <= end_date)
        total_result = await self.session.execute(count_query)
        total_logs = total_result.scalar() or 0

        # Count by action type
        action_query = select(
            AuditLog.action,
            func.count(AuditLog.id).label("count"),
        )
        if tenant_id is not None:
            action_query = action_query.where(AuditLog.tenant_id == tenant_id)
        if start_date is not None:
            action_query = action_query.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            action_query = action_query.where(AuditLog.created_at <= end_date)
        action_query = action_query.group_by(AuditLog.action)
        action_result = await self.session.execute(action_query)

        actions_by_type: dict[str, int] = {}
        for row in action_result:
            action_val = row.action.value if hasattr(row.action, "value") else str(row.action)
            actions_by_type[action_val] = row.count

        # Count by resource type
        resource_query = select(
            AuditLog.resource_type,
            func.count(AuditLog.id).label("count"),
        )
        if tenant_id is not None:
            resource_query = resource_query.where(AuditLog.tenant_id == tenant_id)
        if start_date is not None:
            resource_query = resource_query.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            resource_query = resource_query.where(AuditLog.created_at <= end_date)
        resource_query = resource_query.group_by(AuditLog.resource_type)
        resource_result = await self.session.execute(resource_query)

        resources: dict[str, int] = {}
        for row in resource_result:
            resources[str(row.resource_type)] = row.count

        return {
            "total_logs": int(total_logs),
            "actions_by_type": actions_by_type,
            "resources": resources,
        }


__all__ = [
    "AuditLogNotFoundError",
    "AuditService",
]
