"""
BlueHub User Model
====================
SQLAlchemy ORM model for platform users with auth fields.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin
from shared.models.enums import UserRole

if TYPE_CHECKING:
    from shared.models.abuse_report import AbuseReport
    from shared.models.audit_log import AuditLog
    from shared.models.product import ResellerCommission
    from shared.models.service import Service
    from shared.models.tenant import Tenant


class User(UUIDMixin, TimestampMixin, CoreBase):
    """
    Platform user model supporting multiple authentication methods.
    Supports email/password and Telegram-based authentication.
    """

    __tablename__ = "users"

    tenant_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Foreign key to tenants table",
    )
    paymenter_user_id: Mapped[int | None] = mapped_column(
        None,
        unique=True,
        nullable=True,
        doc="Paymenter billing system user ID",
    )
    telegram_user_id: Mapped[int | None] = mapped_column(
        None,
        unique=True,
        nullable=True,
        doc="Telegram user ID for bot authentication",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User email address (unique)",
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Bcrypt hashed password",
    )
    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="User's full display name",
    )
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="userrole", create_type=False),
        default=UserRole.USER,
        nullable=False,
        doc="RBAC role",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the user account is active",
    )
    language_code: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
        doc="Preferred language code (e.g. en, fa, ar)",
    )
    two_fa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether 2FA is enabled for this user",
    )
    totp_secret: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="TOTP secret for 2FA authentication",
    )
    wallet_balance: Mapped[Decimal] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Wallet balance in default currency",
    )
    migrated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether user was migrated from legacy system",
    )
    migrated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of migration from legacy system",
    )

    # Relationships
    tenant: Mapped[Tenant | None] = relationship(
        "Tenant",
        back_populates="users",
        lazy="selectin",
    )
    services: Mapped[list[Service]] = relationship(
        "Service",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog",
        back_populates="user",
        lazy="selectin",
    )
    abuse_reports: Mapped[list[AbuseReport]] = relationship(
        "AbuseReport",
        back_populates="user",
        foreign_keys="AbuseReport.user_id",
        lazy="selectin",
    )
    commissions: Mapped[list[ResellerCommission]] = relationship(
        "ResellerCommission",
        back_populates="reseller",
        lazy="selectin",
        foreign_keys="ResellerCommission.reseller_id",
    )

    @property
    def is_superadmin(self) -> bool:
        """Check if user has superadmin role."""
        role_str = self.role.value if hasattr(self.role, 'value') else str(self.role)
        return role_str.upper() == "SUPERADMIN"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin-level privileges."""
        role_str = self.role.value if hasattr(self.role, 'value') else str(self.role)
        return role_str.upper() in ["ADMIN", "SUPERADMIN"]

    @property
    def is_reseller(self) -> bool:
        """Check if user has reseller role."""
        role_str = self.role.value if hasattr(self.role, 'value') else str(self.role)
        return role_str.upper() == "RESELLER"

    def __repr__(self) -> str:
        return f"<User(email={self.email!r}, role={self.role.value})>"


__all__ = ["User"]
