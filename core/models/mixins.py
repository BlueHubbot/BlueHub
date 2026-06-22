"""
BlueHub Model Mixins
======================
Additional mixins for domain-specific model behavior:
audit trails, versioning, ownership, and status tracking.
"""

from __future__ import annotations

import uuid
from datetime import timezone, datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class AuditMixin:
    """
    Mixin for full audit trail tracking.
    Records creator, updater, and IP address for compliance.
    """

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        sort_order=997,
        doc="User ID who created the record",
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        sort_order=998,
        doc="User ID who last updated the record",
    )

    created_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        sort_order=999,
        doc="IP address of the creator",
    )

    updated_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        sort_order=1000,
        doc="IP address of the last updater",
    )


class VersionMixin:
    """
    Mixin for optimistic concurrency control.
    Uses version counter for conflict detection.
    """

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        sort_order=1003,
        doc="Version counter for optimistic locking",
    )

    def increment_version(self) -> None:
        """Increment the version counter."""
        self.version += 1


class StatusMixin:
    """
    Mixin for status tracking with timestamps.
    Useful for workflow states (active/inactive/suspended/banned).
    """

    status: Mapped[str] = mapped_column(
        String(50),
        default="active",
        nullable=False,
        index=True,
        sort_order=995,
        doc="Current status of the record",
    )

    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        sort_order=996,
        doc="Timestamp of last status change",
    )

    def set_status(self, new_status: str) -> None:
        """
        Change the status and update the timestamp.

        Args:
            new_status: New status value
        """
        self.status = new_status
        self.status_changed_at = datetime.now(UTC)


class ExpirableMixin:
    """
    Mixin for records with expiration dates.
    Useful for subscriptions, trials, and time-limited resources.
    """

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        sort_order=997,
        doc="Expiration timestamp",
    )

    @property
    def is_expired(self) -> bool:
        """Check if the record has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    @property
    def days_until_expiry(self) -> int | None:
        """Get days remaining until expiration."""
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.now(UTC)
        return max(0, delta.days)


class OrderableMixin:
    """
    Mixin for models that need ordering/positioning.
    """

    position: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        sort_order=999,
        doc="Display/ordering position",
    )


class DescribableMixin:
    """
    Mixin for models with name, slug, and description fields.
    Common pattern for configurable entities.
    """

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        sort_order=1,
        doc="Human-readable name",
    )

    slug: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        sort_order=2,
        doc="URL-friendly unique identifier",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        sort_order=3,
        doc="Detailed description",
    )


class PriceMixin:
    """
    Mixin for models with pricing information.
    """

    price: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        sort_order=10,
        doc="Monetary price value",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
        sort_order=11,
        doc="ISO 4217 currency code",
    )

    is_free: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        sort_order=12,
        doc="Flag indicating if the item is free",
    )


__all__ = [
    "AuditMixin",
    "DescribableMixin",
    "ExpirableMixin",
    "OrderableMixin",
    "PriceMixin",
    "StatusMixin",
    "VersionMixin",
]
