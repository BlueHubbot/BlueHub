"""
BlueHub Transaction Model
==========================
SQLAlchemy ORM model for financial transactions.
Tracks all wallet operations (top-ups, deductions, payments, refunds).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.user import User


class Transaction(UUIDMixin, TimestampMixin, CoreBase):
    """
    Financial transaction record for wallet operations.
    Provides an audit trail for all wallet balance changes.
    """

    __tablename__ = "transactions"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to users table",
    )
    amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Transaction amount (positive for credits, negative for debits)",
    )
    transaction_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        doc="Transaction type: top_up, deduction, payment, refund, commission, adjustment",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Human-readable transaction description",
    )
    reference_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Reference ID (e.g. invoice_id, commission_id, payment gateway txn)",
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(type={self.transaction_type!r}, "
            f"amount={self.amount})>"
        )


__all__ = ["Transaction"]
