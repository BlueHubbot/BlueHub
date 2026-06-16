"""
BlueHub Audit Logger
=====================
Utility functions and decorators for simplified audit logging.
Provides `log_audit()` for direct calls and `@log_audit_event`
decorator for automatic audit logging around functions.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from core.audit.service import AuditService
from shared.models.enums import AuditAction

# Type variable for the decorator
F = TypeVar("F", bound=Callable[..., Any])


class AuditLogger:
    """
    Convenience wrapper around AuditService for logging audit events.

    Provides a simpler interface for common audit logging scenarios
    without needing to instantiate AuditService directly each time.

    Usage:
        logger = AuditLogger(session)
        await logger.log_create("user", user_id="123", actor_id="456")
        await logger.log_login(user_id="123", ip_address="192.168.1.1")
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize the audit logger.

        Args:
            session: SQLAlchemy async session for database operations.
        """
        self._service = AuditService(session)

    async def log_create(
        self,
        resource_type: str,
        *,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Any:
        """Log a resource creation event."""
        return await self._service.log_event(
            action=AuditAction.CREATE,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_read(
        self,
        resource_type: str,
        *,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Any:
        """Log a resource read/access event."""
        return await self._service.log_event(
            action=AuditAction.READ,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_update(
        self,
        resource_type: str,
        *,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Any:
        """Log a resource update event."""
        return await self._service.log_event(
            action=AuditAction.UPDATE,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_delete(
        self,
        resource_type: str,
        *,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Any:
        """Log a resource deletion event."""
        return await self._service.log_event(
            action=AuditAction.DELETE,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_login(
        self,
        *,
        user_id: str | None = None,
        tenant_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Any:
        """Log a user login event."""
        return await self._service.log_event(
            action=AuditAction.LOGIN,
            resource_type="auth",
            resource_id=user_id,
            tenant_id=tenant_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_logout(
        self,
        *,
        user_id: str | None = None,
        tenant_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Any:
        """Log a user logout event."""
        return await self._service.log_event(
            action=AuditAction.LOGOUT,
            resource_type="auth",
            resource_id=user_id,
            tenant_id=tenant_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_payment(
        self,
        *,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Any:
        """Log a payment event."""
        return await self._service.log_event(
            action=AuditAction.PAYMENT,
            resource_type="payment",
            resource_id=resource_id,
            tenant_id=tenant_id,
            user_id=user_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )


def log_audit(
    action: AuditAction | str,
    resource_type: str,
    *,
    get_resource_id: Callable[..., str | None] | None = None,
    get_tenant_id: Callable[..., str | None] | None = None,
    get_user_id: Callable[..., str | None] | None = None,
    get_details: Callable[..., dict[str, Any] | None] | None = None,
    get_ip_address: Callable[..., str | None] | None = None,
    get_user_agent: Callable[..., str | None] | None = None,
) -> Callable[[F], F]:
    """
    Decorator that automatically logs an audit event after a function executes.

    The decorated function must have a ``session`` keyword argument of type
    ``AsyncSession``, or accept ``**kwargs`` that includes it.

    Args:
        action: The audit action type.
        resource_type: The type of resource being acted upon.
        get_resource_id: Optional callable to extract resource_id from args/kwargs.
        get_tenant_id: Optional callable to extract tenant_id from args/kwargs.
        get_user_id: Optional callable to extract user_id from args/kwargs.
        get_details: Optional callable to build details dict from args/kwargs/result.
        get_ip_address: Optional callable to extract ip_address from args/kwargs.
        get_user_agent: Optional callable to extract user_agent from args/kwargs.

    Returns:
        Decorated function that logs an audit event after execution.

    Usage:
        @log_audit(
            AuditAction.CREATE,
            "user",
            get_resource_id=lambda *a, **kw: str(kw.get("user_id", "")),
            get_user_id=lambda *a, **kw: str(kw.get("actor_id", "")),
        )
        async def create_user(session: AsyncSession, user_id: str, actor_id: str, ...):
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Execute the original function
            result = await func(*args, **kwargs)

            # Extract session from kwargs
            session = kwargs.get("session")
            if session is not None and hasattr(session, "execute"):
                service = AuditService(session)
                try:
                    await service.log_event(
                        action=action,
                        resource_type=resource_type,
                        resource_id=get_resource_id(*args, **kwargs) if get_resource_id else None,
                        tenant_id=get_tenant_id(*args, **kwargs) if get_tenant_id else None,
                        user_id=get_user_id(*args, **kwargs) if get_user_id else None,
                        details=get_details(*args, **kwargs) if get_details else None,
                        ip_address=get_ip_address(*args, **kwargs) if get_ip_address else None,
                        user_agent=get_user_agent(*args, **kwargs) if get_user_agent else None,
                    )
                except Exception:
                    # Audit logging should never break the main operation
                    pass

            return result

        return wrapper  # type: ignore[return-value]

    return decorator


__all__ = [
    "AuditLogger",
    "log_audit",
]