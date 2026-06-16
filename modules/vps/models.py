"""
VPS Module Database Models
===========================
SQLAlchemy ORM models for VPS services:
- VpsInstance: stores VPS configuration, resource allocation, and Proxmox reference
- VpsSnapshot: stores snapshot metadata for backup and restore
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import CoreBase, TimestampMixin, UUIDMixin
from shared.models.enums import VpsPowerStatus

if TYPE_CHECKING:
    from shared.models.service import Service


class VpsInstance(UUIDMixin, TimestampMixin, CoreBase):
    """
    VPS instance linked one-to-one with a Service record.
    Stores Proxmox VMID, resource allocation, and connection details.
    """

    __tablename__ = "vps_instances"

    service_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="Foreign key to services table (one-to-one)",
    )
    # Proxmox reference
    proxmox_vmid: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        doc="Proxmox Virtual Machine ID assigned by Proxmox VE",
    )
    proxmox_node: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Proxmox node name hosting this VM",
    )
    # Resource allocation
    cpu_cores: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
        doc="Number of virtual CPU cores allocated",
    )
    memory_mb: Mapped[int] = mapped_column(
        default=1024,
        nullable=False,
        doc="RAM allocated in megabytes",
    )
    disk_gb: Mapped[int] = mapped_column(
        default=25,
        nullable=False,
        doc="Disk storage allocated in gigabytes",
    )
    bandwidth_limit_mbps: Mapped[int | None] = mapped_column(
        nullable=True,
        doc="Network bandwidth limit in Mbps (null = unlimited)",
    )
    # Power and status
    power_status: Mapped[VpsPowerStatus] = mapped_column(
        default=VpsPowerStatus.STOPPED,
        nullable=False,
        index=True,
        doc="Current power state of the VPS instance",
    )
    # Networking
    primary_ipv4: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="Primary IPv4 address assigned to this VPS",
    )
    primary_ipv6: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="Primary IPv6 address assigned to this VPS",
    )
    # OS / template info
    os_template: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Operating system template used for provisioning (e.g. ubuntu-22.04)",
    )
    root_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Initial root password (stored encrypted, rotated on first login)",
    )
    # Provisioning metadata
    provisioned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the VPS was provisioned on Proxmox",
    )
    last_power_change_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of the last power state change",
    )
    # Traffic counters
    bandwidth_used_bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        doc="Total bandwidth used by this VPS in bytes",
    )
    # VNC / Console access
    vnc_port: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="VNC console port for remote access",
    )
    vnc_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="VNC console password (stored encrypted)",
    )
    # Extra metadata
    extra_config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        doc="Additional Proxmox configuration as JSONB (e.g. custom cloud-init settings)",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Admin notes for this VPS instance",
    )

    # Relationships
    service: Mapped[Service] = relationship(
        "Service",
        back_populates="vps_instance",
        lazy="selectin",
        uselist=False,
    )
    snapshots: Mapped[list[VpsSnapshot]] = relationship(
        "VpsSnapshot",
        back_populates="vps_instance",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<VpsInstance(id={self.id}, service_id={self.service_id}, "
            f"vmid={self.proxmox_vmid}, power={self.power_status.value})>"
        )


class VpsSnapshot(UUIDMixin, TimestampMixin, CoreBase):
    """
    VPS snapshot metadata for backup and restore operations.
    References the Proxmox snapshot name and creation details.
    """

    __tablename__ = "vps_snapshots"

    vps_instance_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vps_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to vps_instances table",
    )
    snapshot_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Proxmox snapshot name (unique per VM)",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Human-readable snapshot description",
    )
    size_bytes: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        doc="Snapshot storage size in bytes",
    )
    is_ram_included: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        doc="Whether the snapshot includes RAM state (Proxmox vmstate flag)",
    )
    snapshot_taken_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the snapshot was taken on Proxmox",
    )
    # Parent snapshot reference (for incremental snapshots)
    parent_snapshot_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vps_snapshots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Foreign key to parent snapshot for incremental chain",
    )

    # Relationships
    vps_instance: Mapped[VpsInstance] = relationship(
        "VpsInstance",
        back_populates="snapshots",
        lazy="selectin",
    )
    parent_snapshot: Mapped[VpsSnapshot | None] = relationship(
        "VpsSnapshot",
        remote_side="VpsSnapshot.id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<VpsSnapshot(id={self.id}, instance_id={self.vps_instance_id}, "
            f"name={self.snapshot_name!r})>"
        )


__all__ = [
    "VpsInstance",
    "VpsSnapshot",
]