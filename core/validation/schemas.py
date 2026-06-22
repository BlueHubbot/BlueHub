"""
BlueHub Common Validation Schemas
====================================
Reusable Pydantic v2 schemas for common API patterns:
pagination, error handling, health checks, and standard responses.
"""

from __future__ import annotations

from datetime import timezone, datetime
from typing import Any, TypeVar

from pydantic import Field

from core.validation.base import BaseSchema

DataT = TypeVar("DataT")


class PaginationParams(BaseSchema):
    """
    Query parameters for paginated list endpoints.

    Attributes:
        page: Page number (1-based)
        page_size: Number of items per page (default 20, max 100)
        sort_by: Field to sort by
        sort_order: Sort direction (asc or desc)
    """

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Items per page"
    )
    sort_by: str | None = Field(default=None, description="Sort field")
    sort_order: str = Field(
        default="desc",
        pattern=r"^(asc|desc)$",
        description="Sort direction",
    )


class ErrorDetail(BaseSchema):
    """
    Individual error detail.

    Attributes:
        field: Field name (if field-level error)
        message: Error description
        code: Error code identifier
    """

    field: str | None = Field(default=None, description="Field name")
    message: str = Field(..., description="Error description")
    code: str | None = Field(default=None, description="Error code")


class ErrorResponse(BaseSchema):
    """
    Standard error response body.

    Attributes:
        success: Always False
        error: Error code identifier
        message: Human-readable error message
        details: Detailed error information
        request_id: Request correlation ID
        timestamp: When the error occurred
    """

    success: bool = False
    error: str = Field(default="INTERNAL_ERROR", description="Error code")
    message: str = Field(
        default="An unexpected error occurred",
        description="Error message",
    )
    details: list[ErrorDetail] = Field(
        default_factory=list, description="Error details"
    )
    request_id: str | None = Field(default=None, description="Correlation ID")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Error timestamp"
    )

    @classmethod
    def create(
        cls,
        error: str,
        message: str,
        details: list[ErrorDetail] | None = None,
        request_id: str | None = None,
    ) -> ErrorResponse:
        """Create an error response."""
        return cls(
            error=error,
            message=message,
            details=details or [],
            request_id=request_id,
        )


class HealthResponse(BaseSchema):
    """
    Health check response.

    Attributes:
        status: Overall health status
        version: Application version
        environment: Runtime environment
        uptime: Seconds since startup
        database: Database status
        redis: Redis status
        checks: Detailed component health checks
    """

    status: str = Field(default="healthy", description="Overall status")
    version: str = Field(default="0.1.0", description="App version")
    environment: str = Field(default="dev", description="Runtime environment")
    uptime: float = Field(default=0.0, description="Uptime in seconds")
    database: str = Field(default="unknown", description="Database status")
    redis: str = Field(default="unknown", description="Redis status")
    checks: dict[str, Any] = Field(
        default_factory=dict, description="Health checks"
    )


class MetadataResponse(BaseSchema):
    """
    Generic metadata wrapper for list responses.

    Attributes:
        total: Total record count
        page: Current page
        page_size: Items per page
        total_pages: Total page count
    """

    total: int = Field(default=0, description="Total records")
    page: int = Field(default=1, description="Current page")
    page_size: int = Field(default=20, description="Page size")
    total_pages: int = Field(default=1, description="Total pages")


class ListResponse[DataT](BaseSchema):
    """
    Generic list response with metadata.

    Attributes:
        success: Success indicator
        data: List of items
        metadata: Pagination metadata
    """

    success: bool = True
    data: list[DataT] = Field(default_factory=list, description="Items")
    metadata: MetadataResponse = Field(
        default_factory=MetadataResponse,
        description="Pagination metadata",
    )


class MessageResponse(BaseSchema):
    """
    Simple message response.

    Attributes:
        success: Success indicator
        message: Response message
    """

    success: bool = True
    message: str = Field(default="Operation successful")


__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "ListResponse",
    "MessageResponse",
    "MetadataResponse",
    "PaginationParams",
]
