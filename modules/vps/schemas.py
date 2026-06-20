"""
BlueHub VPS Schemas
===================
Pydantic request/response schemas for VPS (Proxmox-managed VM) operations.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ------------------------------------------------------------------
# Enums as literal strings (matches DB enum values)
# ------------------------------------------------------------------
from modules.vps.models import VpsPowerStatus


# ------------------------------------------------------------------
# Base / shared fields
# ------------------------------------------------------------------
class VpsInstanceBase(BaseModel):
    """Common fields shared across VPS instance schemas."""

    proxmox_node: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["pve-node1"],
        description="Proxmox cluster node name hosting this VM",
    )
    cores: int = Field(
        default=1,
        ge=1,
        le=128,
        description="Number of vCPU cores allocated",
    )
    memory_mb: int = Field(
        default=1024,
        ge=128,
        le=1048576,
        description="RAM allocated in megabytes",
    )
    disk_gb: int = Field(
        default=10,
        ge=1,
        le=65536,
        description="Root disk size in gigabytes",
    )
    storage_pool: str = Field(
        default="local-lvm",
        max_length=100,
        description="Proxmox storage pool name (e.g. local-lvm, ceph-pool)",
    )
    network_bridge: str = Field(
        default="vmbr0",
        max_length=50,
        description="Proxmox bridge interface for the primary NIC",
    )
    network_model: str = Field(
        default="virtio",
        max_length=20,
        description="Network driver model (virtio, e1000, rtl8139)",
    )
    ostype: str = Field(
        default="l26",
        max_length=20,
        description="Guest OS type string for Proxmox (l26=Linux 2.6+, win10, etc.)",
    )
    ostemplate: str | None = Field(
        default=None,
        max_length=255,
        description="Proxmox container/VM template path (e.g. local:vztmpl/ubuntu-22.04...)",
    )
    iso_image: str | None = Field(
        default=None,
        max_length=255,
        description="ISO image path for OS install (e.g. local:iso/ubuntu-22.04.iso)",
    )
    ip_address: str | None = Field(
        default=None,
        max_length=45,
        description="Assigned public/private IP address",
    )
    root_password: str | None = Field(
        default=None,
        max_length=255,
        description="Initial root password (stored encrypted in DB)",
    )
    ssh_keys: str | None = Field(
        default=None,
        description="SSH public keys for cloud-init (newline separated)",
    )
    boot_delay: int = Field(
        default=0,
        ge=0,
        le=300,
        description="Boot delay in seconds before OS starts",
    )
    extra_config: dict | None = Field(
        default=None,
        description="Additional Proxmox config as key-value dict",
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Admin notes",
    )


# ------------------------------------------------------------------
# Create
# ------------------------------------------------------------------
class VpsInstanceCreate(VpsInstanceBase):
    """Schema for provisioning a new VPS instance."""

    service_id: UUID = Field(..., description="Associated billing service ID")
    vmid: int | None = Field(
        default=None,
        ge=100,
        le=999999999,
        description="Desired Proxmox VMID (auto-assigned if omitted)",
    )
    start_after_create: bool = Field(
        default=True,
        description="Start the VM immediately after creation",
    )


# ------------------------------------------------------------------
# Update
# ------------------------------------------------------------------
class VpsInstanceUpdate(BaseModel):
    """Schema for updating a VPS instance configuration."""

    proxmox_node: str | None = Field(
        default=None, max_length=100, description="Target Proxmox node"
    )
    cores: int | None = Field(default=None, ge=1, le=128)
    memory_mb: int | None = Field(default=None, ge=128, le=1048576)
    disk_gb: int | None = Field(default=None, ge=1, le=65536)
    storage_pool: str | None = Field(default=None, max_length=100)
    network_bridge: str | None = Field(default=None, max_length=50)
    network_model: str | None = Field(default=None, max_length=20)
    ostype: str | None = Field(default=None, max_length=20)
    ip_address: str | None = Field(default=None, max_length=45)
    root_password: str | None = Field(default=None, max_length=255)
    ssh_keys: str | None = None
    boot_delay: int | None = Field(default=None, ge=0, le=300)
    extra_config: dict | None = None
    notes: str | None = Field(default=None, max_length=2000)


# ------------------------------------------------------------------
# Power action request
# ------------------------------------------------------------------
class VpsPowerAction(BaseModel):
    """Request to change VM power state."""

    action: str = Field(
        ...,
        pattern=r"^(start|stop|shutdown|reboot|reset|suspend|resume)$",
        description="Power action to execute",
    )
    timeout_seconds: int = Field(
        default=60,
        ge=1,
        le=600,
        description="Timeout for graceful shutdown/stop operations",
    )
    node: str | None = Field(
        default=None,
        max_length=100,
        description="Proxmox node name (auto-detected if omitted)",
    )


# ------------------------------------------------------------------
# Response
# ------------------------------------------------------------------
class VpsInstanceResponse(VpsInstanceBase):
    """Full VPS instance response returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    proxmox_vmid: int | None = None
    power_status: VpsPowerStatus
    vnc_port: int | None = None
    created_at: datetime
    updated_at: datetime


class VpsInstanceSummary(BaseModel):
    """Lightweight VPS instance representation for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    service_id: UUID
    proxmox_vmid: int | None
    proxmox_node: str
    cores: int
    memory_mb: int
    disk_gb: int
    ostype: str
    ip_address: str | None
    power_status: VpsPowerStatus
    created_at: datetime


# ------------------------------------------------------------------
# Proxmox task result
# ------------------------------------------------------------------
class ProxmoxTaskResponse(BaseModel):
    """Response returned after triggering a Proxmox async operation."""

    upid: str = Field(..., description="Proxmox unique task ID")
    node: str = Field(..., description="Node where the task ran")
    status: str = Field(..., description="Final task status ('stopped')")
    exitstatus: str | None = Field(
        default=None, description="Exit status ('OK' on success)"
    )
    success: bool = Field(default=False, description="Did the task complete successfully?")


# ------------------------------------------------------------------
# Snapshot schemas
# ------------------------------------------------------------------
class VpsSnapshotCreate(BaseModel):
    """Request to create a VM snapshot."""

    snapshot_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$",
        description="Proxmox snapshot name (alphanumeric, dots, hyphens, underscores)",
    )
    description: str | None = Field(
        default=None, max_length=500, description="Human-readable description"
    )
    include_ram: bool = Field(
        default=False, description="Include RAM state in snapshot (Proxmox vmstate flag)"
    )
    node: str | None = Field(default=None, max_length=100)


class VpsSnapshotResponse(BaseModel):
    """Snapshot metadata returned to API consumers."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vps_instance_id: UUID
    snapshot_name: str
    description: str | None = None
    size_bytes: int | None = None
    is_ram_included: bool
    snapshot_taken_at: datetime | None = None
    parent_snapshot_id: UUID | None = None
    created_at: datetime


class VpsSnapshotListResponse(BaseModel):
    """Wrapper for listing snapshots."""

    vps_instance_id: UUID
    snapshots: list[VpsSnapshotResponse]


# ------------------------------------------------------------------
# Console / VNC
# ------------------------------------------------------------------
class VpsVncResponse(BaseModel):
    """VNC/noVNC console access details."""

    vmid: int
    node: str
    port: int
    ticket: str = Field(..., description="One-time VNC authentication ticket")
    websocket_path: str | None = Field(
        default=None,
        description="noVNC websocket path for browser-based console",
    )


# ------------------------------------------------------------------
# VM status detail
# ------------------------------------------------------------------
class VpsStatusDetail(BaseModel):
    """Detailed live status of a VM fetched from Proxmox."""

    vmid: int
    name: str
    node: str
    status: str  # 'running' | 'stopped' | 'paused' | 'suspended'
    cpus: int
    max_memory_bytes: int
    memory_used_bytes: int
    memory_usage_pct: float
    max_disk_bytes: int
    uptime_seconds: int
    template_os: str | None = None
    vnc_port: int | None = None


__all__ = [
    # Create/Update
    "VpsInstanceCreate",
    "VpsInstanceUpdate",
    # Power
    "VpsPowerAction",
    # Responses
    "VpsInstanceResponse",
    "VpsInstanceSummary",
    "ProxmoxTaskResponse",
    # Snapshots
    "VpsSnapshotCreate",
    "VpsSnapshotResponse",
    "VpsSnapshotListResponse",
    # Console
    "VpsVncResponse",
    # Status
    "VpsStatusDetail",
]
