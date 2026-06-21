"""
BlueHub Abuse Report Model
============================
SQLAlchemy ORM model for tracking abuse reports, security incidents,
and policy violations across the platform.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.user import User


class AbuseReport(UUIDMixin, TimestampMixin, CoreBase):
    """
    Abuse report for tracking security incidents, policy violations,
    and user-reported abuse across services.
    """

    __tablename__ = "abuse_reports"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the reported user",
    )
    reporter_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Foreign key to the reporting user (null for auto-detected)",
    )
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Report type (spam, phishing, abuse, copyright, malware, etc.)",
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        index=True,
        doc="Severity level (low, medium, high, critical)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        index=True,
        doc="Report status (open, investigating, resolved, dismissed)",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Detailed description of the abuse incident",
    )
    evidence: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Supporting evidence (logs, screenshots, links)",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="IP address associated with the incident (supports IPv6)",
    )
    service_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Associated service identifier if applicable",
    )
    service_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Service type (vpn, vps, smartdns, streaming, game)",
    )
    auto_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether this report was automatically detected by the system",
    )
    resolved_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Foreign key to the admin who resolved this report",
    )
    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Notes about the resolution or dismissal",
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="When the report was resolved or dismissed",
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="abuse_reports",
        lazy="selectin",
    )
    reporter: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[reporter_id],
        lazy="selectin",
    )
    resolver: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[resolved_by],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<AbuseReport(id={self.id}, type={self.type!r}, "
            f"severity={self.severity!r}, status={self.status!r})>"
        )


__all__ = ["AbuseReport"]