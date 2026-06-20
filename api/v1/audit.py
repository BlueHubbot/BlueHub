"""
BlueHub Audit API Endpoints
=============================
FastAPI router for audit log management:
querying, viewing, and statistics for the immutable audit trail.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import AuditService
from core.audit.schemas import (
    AuditLogListResponse,
    AuditLogResponse,
    AuditLogStatsResponse,
)
from core.audit.service import AuditLogNotFoundError
from core.database import db_manager
from dependencies.auth import get_current_user_payload

router = APIRouter(prefix="/audit", tags=["Audit"])


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────


def _require_admin(token_payload: dict) -> None:
    """Check if the authenticated user has admin privileges."""
    role = token_payload.get("role", "user")
    if role not in ("admin", "superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────


@router.get("/logs", response_model=AuditLogListResponse)
async def query_audit_logs(
    action: str | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    tenant_id: str | None = Query(None, description="Filter by tenant UUID"),
    user_id: str | None = Query(None, description="Filter by user UUID"),
    start_date: str | None = Query(None, description="Filter logs after this date (ISO format)"),
    end_date: str | None = Query(None, description="Filter logs before this date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Query audit logs with optional filters and pagination.

    Requires admin privileges. Returns a paginated list of audit log entries
    matching the provided filter criteria, ordered by most recent first.
    """
    _require_admin(token_payload)

    service = AuditService(session)
    entries, total = await service.query_logs(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=tenant_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    total_pages = max(1, (total + page_size - 1) // page_size)

    items = []
    for entry in entries:
        items.append(
            AuditLogResponse(
                id=str(entry.id),
                action=entry.action.value if hasattr(entry.action, "value") else str(entry.action),
                resource_type=entry.resource_type,
                resource_id=str(entry.resource_id) if entry.resource_id else None,
                tenant_id=str(entry.tenant_id) if entry.tenant_id else None,
                user_id=str(entry.user_id) if entry.user_id else None,
                details=entry.details,
                ip_address=entry.ip_address,
                user_agent=entry.user_agent,
                timestamp=entry.timestamp,
                created_at=entry.created_at,
            )
        )

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Get a single audit log entry by ID.

    Requires admin privileges.
    """
    _require_admin(token_payload)

    service = AuditService(session)
    try:
        entry = await service.get_log(log_id)
    except AuditLogNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return AuditLogResponse(
        id=str(entry.id),
        action=entry.action.value if hasattr(entry.action, "value") else str(entry.action),
        resource_type=entry.resource_type,
        resource_id=str(entry.resource_id) if entry.resource_id else None,
        tenant_id=str(entry.tenant_id) if entry.tenant_id else None,
        user_id=str(entry.user_id) if entry.user_id else None,
        details=entry.details,
        ip_address=entry.ip_address,
        user_agent=entry.user_agent,
        timestamp=entry.timestamp,
        created_at=entry.created_at,
    )


@router.get("/logs/user/{user_id}", response_model=AuditLogListResponse)
async def get_logs_by_user(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Get all audit logs for a specific user.

    Requires admin privileges.
    """
    _require_admin(token_payload)

    service = AuditService(session)
    entries, total = await service.get_logs_by_user(
        user_id=user_id,
        page=page,
        page_size=page_size,
    )

    total_pages = max(1, (total + page_size - 1) // page_size)

    items = []
    for entry in entries:
        items.append(
            AuditLogResponse(
                id=str(entry.id),
                action=entry.action.value if hasattr(entry.action, "value") else str(entry.action),
                resource_type=entry.resource_type,
                resource_id=str(entry.resource_id) if entry.resource_id else None,
                tenant_id=str(entry.tenant_id) if entry.tenant_id else None,
                user_id=str(entry.user_id) if entry.user_id else None,
                details=entry.details,
                ip_address=entry.ip_address,
                user_agent=entry.user_agent,
                timestamp=entry.timestamp,
                created_at=entry.created_at,
            )
        )

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/logs/resource/{resource_type}/{resource_id}", response_model=AuditLogListResponse)
async def get_logs_by_resource(
    resource_type: str,
    resource_id: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Get all audit logs for a specific resource.

    Requires admin privileges.
    """
    _require_admin(token_payload)

    service = AuditService(session)
    entries, total = await service.get_logs_by_resource(
        resource_type=resource_type,
        resource_id=resource_id,
        page=page,
        page_size=page_size,
    )

    total_pages = max(1, (total + page_size - 1) // page_size)

    items = []
    for entry in entries:
        items.append(
            AuditLogResponse(
                id=str(entry.id),
                action=entry.action.value if hasattr(entry.action, "value") else str(entry.action),
                resource_type=entry.resource_type,
                resource_id=str(entry.resource_id) if entry.resource_id else None,
                tenant_id=str(entry.tenant_id) if entry.tenant_id else None,
                user_id=str(entry.user_id) if entry.user_id else None,
                details=entry.details,
                ip_address=entry.ip_address,
                user_agent=entry.user_agent,
                timestamp=entry.timestamp,
                created_at=entry.created_at,
            )
        )

    return AuditLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/stats", response_model=AuditLogStatsResponse)
async def get_audit_stats(
    tenant_id: str | None = Query(None, description="Filter by tenant UUID"),
    start_date: str | None = Query(None, description="Filter logs after this date (ISO format)"),
    end_date: str | None = Query(None, description="Filter logs before this date (ISO format)"),
    token_payload: dict = Depends(get_current_user_payload),
    session: AsyncSession = Depends(db_manager.get_async_session),
) -> Any:
    """
    Get audit log statistics.

    Requires admin privileges. Returns total log count and breakdowns
    by action type and resource type.
    """
    _require_admin(token_payload)

    service = AuditService(session)
    stats = await service.get_stats(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    return AuditLogStatsResponse(
        total_logs=stats["total_logs"],
        actions_by_type=stats["actions_by_type"],
        resources=stats["resources"],
    )


__all__ = ["router"]
