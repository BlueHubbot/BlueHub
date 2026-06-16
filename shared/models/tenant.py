"""
BlueHub Tenant Model
======================
SQLAlchemy ORM model for multi-tenant organizations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.product import TenantProductPricing
    from shared.models.service import Service
    from shared.models.user import User


class Tenant(UUIDMixin, TimestampMixin, CoreBase):
    """
    Multi-tenant organization model.
    Each tenant represents a brand/reseller with isolated data.
    """

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Tenant/brand display name",
    )
    domain: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Tenant's primary domain (unique)",
    )
    logo_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="URL to tenant's logo image",
    )
    branding_config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        doc="JSONB branding configuration (colors, fonts, theme)",
    )
    telegram_bot_token: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Telegram bot token for tenant-specific bot",
    )
    license_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique license/identification key",
    )
    signature: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Email signature or legal footer text",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the tenant is active",
    )

    # Relationships
    users: Mapped[list[User]] = relationship(
        "User",
        back_populates="tenant",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    custom_pricing: Mapped[list[TenantProductPricing]] = relationship(
        "TenantProductPricing",
        back_populates="tenant",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    services: Mapped[list[Service]] = relationship(
        "Service",
        back_populates="tenant",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tenant(name={self.name!r}, domain={self.domain!r}, active={self.active})>"


__all__ = ["Tenant"]
