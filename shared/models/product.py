"""
BlueHub Product & Commission Models
======================================
SQLAlchemy ORM models for product catalog, tenant-specific pricing, and reseller commissions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin
from shared.models.enums import BillingCycle, CommissionStatus

if TYPE_CHECKING:
    from shared.models.service import Service
    from shared.models.tenant import Tenant
    from shared.models.user import User


class Product(UUIDMixin, TimestampMixin, CoreBase):
    """
    Product catalog model with i18n support.
    Products define service types (VPN, VPS, etc.) with pricing and specs.
    """

    __tablename__ = "products"

    module_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Module this product belongs to (vpn, vps, smartdns, etc.)",
    )
    product_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        doc="Unique product key (e.g. vpn-premium-monthly)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Product display name",
    )
    description_i18n: Mapped[dict[str, str] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        doc="JSONB map of language_code -> description text",
    )
    base_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Base price in default currency",
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        SAEnum(BillingCycle, name="billingcycle", create_type=False),
        default=BillingCycle.MONTHLY,
        nullable=False,
        doc="Billing cycle type",
    )
    billing_cycle_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Number of days in billing cycle",
    )
    specs: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        doc="JSONB product specifications (traffic, speed, RAM, etc.)",
    )
    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Display order for sorting",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the product is available for purchase",
    )

    # Relationships
    services: Mapped[list[Service]] = relationship(
        "Service",
        back_populates="product",
        lazy="selectin",
    )
    tenant_pricing: Mapped[list[TenantProductPricing]] = relationship(
        "TenantProductPricing",
        back_populates="product",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Product(key={self.product_key!r}, price={self.base_price})>"


class TenantProductPricing(UUIDMixin, TimestampMixin, CoreBase):
    """
    Tenant-specific product pricing overrides.
    Allows resellers to set custom prices for specific products.
    """

    __tablename__ = "tenant_product_pricing"

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
    price_override: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Custom price for this tenant",
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship(
        "Tenant",
        back_populates="custom_pricing",
        lazy="selectin",
    )
    product: Mapped[Product] = relationship(
        "Product",
        back_populates="tenant_pricing",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<TenantProductPricing(tenant={self.tenant_id}, product={self.product_id}, price={self.price_override})>"


class ResellerCommission(UUIDMixin, TimestampMixin, CoreBase):
    """
    Commission tracking for reseller referrals.
    Tracks commissions earned by resellers on service purchases.
    """

    __tablename__ = "reseller_commissions"

    reseller_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to reseller user",
    )
    service_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        doc="Foreign key to the purchased service",
    )
    commission_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Commission rate as decimal (e.g. 0.10 = 10%%)",
    )
    commission_amount: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Calculated commission amount",
    )
    status: Mapped[CommissionStatus] = mapped_column(
        SAEnum(CommissionStatus, name="commissionstatus", create_type=False),
        default=CommissionStatus.PENDING,
        nullable=False,
        doc="Commission payout status",
    )
    paid_at: Mapped[str | None] = mapped_column(
        nullable=True,
        doc="Timestamp when commission was paid out",
    )

    # Relationships
    reseller: Mapped[User] = relationship(
        "User",
        back_populates="commissions",
        lazy="selectin",
        foreign_keys=[reseller_id],
    )
    service: Mapped[Service] = relationship(
        "Service",
        back_populates="commission",
        lazy="selectin",
        foreign_keys=[service_id],
    )

    def __repr__(self) -> str:
        return f"<ResellerCommission(reseller={self.reseller_id}, amount={self.commission_amount}, status={self.status.value})>"


__all__ = [
    "Product",
    "ResellerCommission",
    "TenantProductPricing",
]
