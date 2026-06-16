"""
BlueHub Service Model
======================
SQLAlchemy ORM model for customer services with polymorphic module extensions.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin
from shared.models.enums import ServiceStatus

if TYPE_CHECKING:
    from modules.vpn.models import VpnAccount
    from modules.vps.models import VpsInstance
    from shared.models.product import Product, ResellerCommission
    from shared.models.tenant import Tenant
    from shared.models.user import User


class Service(UUIDMixin, TimestampMixin, CoreBase):
    """
    Core service model for all product types (VPN, VPS, SmartDNS, Streaming, Game).
    Polymorphic base for module-specific service extensions.
    """

    __tablename__ = "services"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to users table",
    )
    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to tenants table",
    )
    product_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to products table",
    )
    module_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Module identifier (vpn, vps, smartdns, streaming, game)",
    )
    status: Mapped[ServiceStatus] = mapped_column(
        default=ServiceStatus.PENDING,
        nullable=False,
        index=True,
        doc="Current service lifecycle status",
    )
    price_paid: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Actual price paid for this service instance",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Service expiration timestamp",
    )
    provisioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the service was provisioned/activated",
    )
    suspended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the service was suspended",
    )
    suspension_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Reason for service suspension",
    )
    service_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        doc="Module-specific metadata as JSONB",
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User",
        back_populates="services",
        lazy="selectin",
    )
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="services",
        lazy="selectin",
    )
    product: Mapped[Product] = relationship(
        "Product",
        back_populates="services",
        lazy="selectin",
    )
    commission: Mapped[list[ResellerCommission]] = relationship(
        "ResellerCommission",
        back_populates="service",
        lazy="selectin",
    )

    # Module-specific polymorphic relationships
    vpn_account: Mapped[VpnAccount | None] = relationship(
        "VpnAccount",
        back_populates="service",
        lazy="selectin",
        uselist=False,
    )
    vps_instance: Mapped[VpsInstance | None] = relationship(
        "VpsInstance",
        back_populates="service",
        lazy="selectin",
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Service(id={self.id}, module={self.module_name!r}, "
            f"status={self.status.value})>"
        )


__all__ = ["Service"]
