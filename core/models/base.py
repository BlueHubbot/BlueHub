"""
BlueHub Base ORM Models
=========================
SQLAlchemy 2.0 declarative base with common mixins
for all database models.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, registry

# Create a custom registry with the type_annotation_map pre-configured.
_annotation_map: dict[type, Any] = {
    str: String(255),
    datetime: DateTime(timezone=True),
    uuid.UUID: UUID(as_uuid=True),
}
bluehub_registry = registry(type_annotation_map=_annotation_map)


class Base(DeclarativeBase):
    """
    Base class for all BlueHub ORM models.
    Provides common table configuration and type annotations.
    """

    __abstract__ = True

    # Use the pre-configured registry with type_annotation_map
    registry = bluehub_registry

    @classmethod
    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Auto-generate tablename if not set."""
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "__tablename__") or cls.__tablename__ is None:
            # Convert CamelCase to snake_case for table name
            name = cls.__name__
            snake = "".join(
                f"_{c.lower()}" if c.isupper() else c for c in name
            ).lstrip("_")
            cls.__tablename__ = snake + "s"  # pluralize


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at timestamp columns.
    Automatically manages timestamps on create and update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        sort_order=999,
        doc="Timestamp when the record was created",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        sort_order=1000,
        doc="Timestamp when the record was last updated",
    )


class SoftDeleteMixin:
    """
    Mixin that adds soft-delete functionality.
    Records are marked as deleted rather than physically removed.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        sort_order=1001,
        doc="Timestamp when the record was soft-deleted",
    )

    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        sort_order=1002,
        doc="Soft delete flag",
    )

    def soft_delete(self) -> None:
        """Mark the record as deleted."""
        self.deleted_at = datetime.now(timezone.utc)
        self.is_deleted = True

    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.is_deleted = False

    @property
    def is_active(self) -> bool:
        """Check if the record is not deleted."""
        return not self.is_deleted


class UUIDMixin:
    """
    Mixin that adds a UUID primary key.
    Uses PostgreSQL native UUID type.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        sort_order=0,
        doc="Primary key (UUID v4)",
    )


class IDMixin:
    """
    Mixin that adds an auto-incrementing integer primary key.
    """

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        sort_order=0,
        doc="Primary key (auto-increment)",
    )


__all__ = [
    "Base",
    "IDMixin",
    "SoftDeleteMixin",
    "TimestampMixin",
    "UUIDMixin",
]
