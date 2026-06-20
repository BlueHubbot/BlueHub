"""
BlueHub Audit Schemas
======================
Pydantic schemas for audit log API: response models,
query parameters, and statistics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    """Schema for a single audit log entry response."""

    id: str = Field(..., description="UUID of the audit log entry")
    action: str = Field(..., description="Type of action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: str | None = Field(None, description="Identifier of the affected resource")
    tenant_id: str | None = Field(None, description="Tenant UUID associated with the action")
    user_id: str | None = Field(None, description="User UUID who performed the action")
    details: dict[str, Any] | None = Field(None, description="Arbitrary metadata about the action")
    ip_address: str | None = Field(None, description="Client IP address")
    user_agent: str | None = Field(None, description="User-Agent string from the request")
    timestamp: datetime = Field(..., description="When the action occurred")
    created_at: datetime = Field(..., description="When the log entry was created")

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Schema for paginated list of audit log entries."""

    items: list[AuditLogResponse] = Field(..., description="List of audit log entries")
    total: int = Field(..., description="Total number of entries matching the query")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class AuditLogQueryParams(BaseModel):
    """Schema for query parameters when filtering audit logs."""

    action: str | None = Field(None, description="Filter by action type")
    resource_type: str | None = Field(None, description="Filter by resource type")
    resource_id: str | None = Field(None, description="Filter by resource ID")
    tenant_id: str | None = Field(None, description="Filter by tenant UUID")
    user_id: str | None = Field(None, description="Filter by user UUID")
    start_date: str | None = Field(None, description="Filter logs after this date (ISO format)")
    end_date: str | None = Field(None, description="Filter logs before this date (ISO format)")
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(50, ge=1, le=100, description="Items per page (max 100)")


class AuditLogStatsResponse(BaseModel):
    """Schema for audit log statistics."""

    total_logs: int = Field(..., description="Total number of audit log entries")
    actions_by_type: dict[str, int] = Field(
        ..., description="Count of logs grouped by action type"
    )
    resources: dict[str, int] = Field(
        ..., description="Count of logs grouped by resource type"
    )


__all__ = [
    "AuditLogQueryParams",
    "AuditLogListResponse",
    "AuditLogResponse",
    "AuditLogStatsResponse",
]
