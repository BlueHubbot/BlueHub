"""
BlueHub Audit Log Model
=========================
SQLAlchemy ORM model for immutable audit trail of all system actions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin
from shared.models.enums import AuditAction

if TYPE_CHECKING:
    from shared.models.tenant import Tenant
    from shared.models.user import User


class AuditLog(UUIDMixin, TimestampMixin, CoreBase):
    """
    Immutable audit log entry for tracking all user and system actions.
    Used for security monitoring, compliance, and debugging.
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Foreign key to users table (nullable for system actions)",
    )
    tenant_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Foreign key to tenants table",
    )
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, name="auditaction", create_type=False),
        nullable=False,
        index=True,
        doc="Type of action performed",
    )
    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Type of resource affected (service, user, tenant, product, etc.)",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Identifier of the affected resource",
    )
    details: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        doc="Arbitrary metadata/context about the action",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="Client IP address (supports IPv6)",
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="User-Agent string from the request",
    )

    # Relationships
    user: Mapped[User | None] = relationship(
        "User",
        back_populates="audit_logs",
        lazy="selectin",
    )
    tenant: Mapped[Tenant | None] = relationship(
        "Tenant",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(action={self.action.value!r}, "
            f"resource_type={self.resource_type!r})>"
        )


__all__ = ["AuditLog"]
