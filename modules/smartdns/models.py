"""
BlueHub SmartDNS ORM Models
============================
SQLAlchemy models for smartdns_profiles and dns_records tables.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base

if TYPE_CHECKING:
    from shared.models.service import Service


class SmartDnsProfile(Base):
    """SmartDNS profile linked to a billing service (one-to-one)."""

    __tablename__ = "smartdns_profiles"

    id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
    )
    service_id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    profile_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="provisioning",
    )
    pdns_zone_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pdns_zone_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    upstream_dns: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        default="8.8.8.8",
    )
    geo_region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    allowed_ips: Mapped[list[str] | None] = mapped_column(JSONB(), nullable=True, default=list)
    max_queries_per_second: Mapped[int | None] = mapped_column(Integer(), nullable=True, default=100)
    enable_dnssec: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    enable_logging: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    enable_ad_blocking: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    total_queries: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    stats_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_config: Mapped[dict[str, object] | None] = mapped_column(JSONB(), nullable=True, default=dict)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    service: Mapped["Service"] = relationship(
        "Service",
        back_populates="smartdns_profile",
        lazy="selectin",
        uselist=False,
    )
    records: Mapped[list["DnsRecord"]] = relationship(
        "DnsRecord",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<SmartDnsProfile id={self.id!r} name={self.profile_name!r}>"


class DnsRecord(Base):
    """Individual DNS record belonging to a SmartDNS profile."""

    __tablename__ = "dns_records"

    id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=_uuid.uuid4,
    )
    profile_id: Mapped[_uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("smartdns_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    record_type: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    ttl: Mapped[int] = mapped_column(Integer(), nullable=False, default=300)
    priority: Mapped[int | None] = mapped_column(Integer(), nullable=True, default=0)
    pdns_record_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    synced: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    profile: Mapped["SmartDnsProfile"] = relationship(
        "SmartDnsProfile",
        back_populates="records",
    )

    def __repr__(self) -> str:
        return f"<DnsRecord id={self.id!r} type={self.record_type!r} name={self.name!r}>"


__all__ = [
    "SmartDnsProfile",
    "DnsRecord",
]