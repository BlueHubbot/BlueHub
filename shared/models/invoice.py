"""
BlueHub Invoice Model
======================
SQLAlchemy ORM model for invoice records.
Tracks billing invoices issued to users for services.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.service import Service
    from shared.models.user import User


class Invoice(UUIDMixin, TimestampMixin, CoreBase):
    """
    Invoice model for billing records.
    Each invoice tracks a charge for a service or wallet top-up.
    """

    __tablename__ = "invoices"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to users table",
    )
    service_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Foreign key to services table (nullable for wallet top-ups)",
    )
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        doc="Unique human-readable invoice number",
    )
    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Invoice amount in default currency",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        doc="Invoice status: pending, paid, overdue, cancelled, refunded",
    )
    due_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Invoice due date",
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when invoice was paid",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Invoice description or notes",
    )
    line_items: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        doc="JSONB array of line items (description, amount, quantity)",
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        lazy="selectin",
    )
    service: Mapped[Service | None] = relationship(
        "Service",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice(number={self.invoice_number!r}, "
            f"amount={self.amount}, status={self.status!r})>"
        )


__all__ = ["Invoice"]
