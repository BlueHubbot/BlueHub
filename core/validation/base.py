"""
BlueHub Base Validation Schemas
=================================
Base Pydantic v2 schemas with common configuration,
pagination, and response wrappers.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypeVar

from pydantic import AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

T = TypeVar("T")
DataT = TypeVar("DataT")


class BaseSchema(BaseModel):
    """
    Base schema for all BlueHub API schemas.

    Features:
    - CamelCase serialization (API convention)
    - ORM mode for SQLAlchemy model integration
    - Strict type validation
    - JSON serialization
    """

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            alias=to_camel,
            serialization_alias=to_camel,
        ),
        populate_by_name=True,
        from_attributes=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
        },
        extra="ignore",
        strict=False,
    )


class PaginatedResponse[DataT](BaseModel):
    """
    Generic paginated response wrapper.

    Attributes:
        items: List of items for the current page
        total: Total number of items
        page: Current page number
        page_size: Number of items per page
        total_pages: Total number of pages
        has_next: Whether there is a next page
        has_previous: Whether there is a previous page
    """

    items: list[DataT]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            alias=to_camel,
            serialization_alias=to_camel,
        ),
        populate_by_name=True,
    )

    @classmethod
    def create(
        cls,
        items: list[DataT],
        total: int,
        page: int,
        page_size: int,
    ) -> PaginatedResponse[DataT]:
        """
        Create a paginated response from query results.

        Args:
            items: List of items for the current page
            total: Total number of items
            page: Current page number
            page_size: Number of items per page

        Returns:
            PaginatedResponse instance
        """
        total_pages = max(1, (total + page_size - 1) // page_size)
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class SuccessResponse[T](BaseModel):
    """
    Standard success response wrapper.

    Attributes:
        success: Always True
        data: Response payload
        message: Optional success message
    """

    success: bool = True
    data: T | None = None
    message: str | None = None

    model_config = ConfigDict(
        alias_generator=AliasGenerator(
            alias=to_camel,
            serialization_alias=to_camel,
        ),
        populate_by_name=True,
    )


__all__ = [
    "BaseSchema",
    "PaginatedResponse",
    "SuccessResponse",
]


