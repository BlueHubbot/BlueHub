"""
BlueHub VPS API Endpoints
==========================
FastAPI router for VPS (Proxmox VM) management: provisioning,
power management, snapshots, console access, resize, clone,
and status monitoring.

Covers both admin and client-facing endpoints for the VPS module.
"""

from __future__ import annotations

from datetime import timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.auth import get_current_user
from dependencies.db import get_async_session
from modules.vps.models import VpsInstance, VpsPowerStatus, VpsSnapshot
from modules.vps.schemas import (
    ProxmoxTaskResponse,
    VpsInstanceCreate,
    VpsInstanceResponse,
    VpsInstanceSummary,
    VpsInstanceUpdate,
    VpsPowerAction,
    VpsSnapshotCreate,
    VpsSnapshotListResponse,
    VpsSnapshotResponse,
    VpsStatusDetail,
    VpsVncResponse,
)
from modules.vps.services import (
    VpsConsoleError,
    VpsInstanceNotFoundError,
    VpsInstanceService,
    VpsInvalidStateError,
    VpsPowerActionError,
    VpsProvisioningError,
    VpsResizeError,
    VpsServiceError,
    VpsSnapshotError,
)
from shared.models.product import Product
from shared.models.service import Service, ServiceStatus
from shared.models.user import User

router = APIRouter(prefix="/vps", tags=["VPS"])


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────


def _require_admin(current_user: User) -> None:
    """Check if the authenticated user has admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )


def _build_instance_response(instance: VpsInstance) -> VpsInstanceResponse:
    """Build a VpsInstanceResponse from a VpsInstance model instance."""
    return VpsInstanceResponse(
        id=instance.id,
        service_id=instance.service_id,
        proxmox_node=instance.proxmox_node,
        proxmox_vmid=instance.proxmox_vmid,
        cores=instance.cores,
        memory_mb=instance.memory_mb,
        disk_gb=instance.disk_gb,
        storage_pool=instance.storage_pool,
        network_bridge=instance.network_bridge,
        network_model=instance.network_model,
        ostype=instance.ostype,
        ostemplate=instance.ostemplate,
        iso_image=instance.iso_image,
        ip_address=instance.ip_address,
        root_password=instance.root_password,
        ssh_keys=instance.ssh_keys,
        boot_delay=instance.boot_delay,
        extra_config=instance.extra_config,
        notes=instance.notes,
        power_status=instance.power_status,
        vnc_port=instance.vnc_port,
        created_at=instance.created_at,
        updated_at=instance.updated_at,
    )


def _build_summary_response(instance: VpsInstance) -> VpsInstanceSummary:
    """Build a lightweight VpsInstanceSummary from a VpsInstance."""
    return VpsInstanceSummary(
        id=instance.id,
        service_id=instance.service_id,
        proxmox_vmid=instance.proxmox_vmid,
        proxmox_node=instance.proxmox_node,
        cores=instance.cores,
        memory_mb=instance.memory_mb,
        disk_gb=instance.disk_gb,
        ostype=instance.ostype,
        ip_address=instance.ip_address,
        power_status=instance.power_status,
        created_at=instance.created_at,
    )


def _build_snapshot_response(snapshot: VpsSnapshot) -> VpsSnapshotResponse:
    """Build a VpsSnapshotResponse from a VpsSnapshot model."""
    return VpsSnapshotResponse(
        id=snapshot.id,
        vps_instance_id=snapshot.vps_instance_id,
        snapshot_name=snapshot.snapshot_name,
        description=snapshot.description,
        size_bytes=snapshot.size_bytes,
        is_ram_included=snapshot.is_ram_included,
        snapshot_taken_at=snapshot.snapshot_taken_at,
        parent_snapshot_id=snapshot.parent_snapshot_id,
        created_at=snapshot.created_at,
    )


async def _check_instance_ownership(
    instance: VpsInstance,
    session: AsyncSession,
    current_user: User,
) -> None:
    """Raise 403 if the current user does not own the service tied to this instance."""
    if current_user.is_admin:
        return
    service = await session.get(Service, instance.service_id)
    if service is None or str(service.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: you do not own this VPS instance",
        )


# ──────────────────────────────────────────────
# VPS Instance CRUD
# ──────────────────────────────────────────────


@router.post(
    "/instances",
    response_model=VpsInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vps_instance(
    body: VpsInstanceCreate,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpsInstanceResponse:
    """
    Provision a new VPS instance (VM) on Proxmox.

    Creates the VM with specified resources and returns the instance record.
    Requires admin privileges.
    """
    _require_admin(current_user)

    vps_service = VpsInstanceService(session)
    try:
        instance = await vps_service.provision(
            service_id=body.service_id,
            node=body.proxmox_node,
            cores=body.cores,
            memory_mb=body.memory_mb,
            disk_gb=body.disk_gb,
            storage=body.storage_pool,
            network_bridge=body.network_bridge,
            network_model=body.network_model,
            ostype=body.ostype,
            ostemplate=body.ostemplate,
            iso_image=body.iso_image,
            ip_address=body.ip_address,
            root_password=body.root_password,
            ssh_keys=body.ssh_keys,
            vmid=body.vmid,
            start=body.start_after_create,
            extra_config=body.extra_config,
            notes=body.notes,
        )
    except VpsProvisioningError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _build_instance_response(instance)


@router.get("/instances", response_model=list[VpsInstanceSummary])
async def list_vps_instances(
    node: str | None = Query(None, description="Filter by Proxmox node"),
    status_filter: str | None = Query(None, alias="status", description="Filter by power status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[VpsInstanceSummary]:
    """
    List VPS instances with optional filters.

    Admin: sees all instances. Client: sees only their own services' instances.
    """
    vps_service = VpsInstanceService(session)

    # Resolve status enum if provided
    power_status: VpsPowerStatus | None = None
    if status_filter:
        try:
            power_status = VpsPowerStatus(status_filter)
        except ValueError:
            power_status = None

    instances = await vps_service.list_instances(
        node=node,
        status=power_status,
        offset=offset,
        limit=limit,
    )

    # Non-admins can only see instances tied to their own services
    if not current_user.is_admin:
        user_services_stmt = select(Service.id).where(
            Service.user_id == str(current_user.id)
        )
        result = await session.execute(user_services_stmt)
        user_service_ids = {str(row[0]) for row in result.all()}
        instances = [
            i for i in instances if str(i.service_id) in user_service_ids
        ]

    return [_build_summary_response(i) for i in instances]


@router.get("/instances/{instance_id}", response_model=VpsInstanceResponse)
async def get_vps_instance(
    instance_id: UUID,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpsInstanceResponse:
    """
    Get a single VPS instance by ID with full details.
    """
    vps_service = VpsInstanceService(session)
    try:
        instance = await vps_service.get_instance(instance_id)
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await _check_instance_ownership(instance, session, current_user)
    return _build_instance_response(instance)


@router.patch("/instances/{instance_id}", response_model=VpsInstanceResponse)
async def update_vps_instance(
    instance_id: UUID,
    body: VpsInstanceUpdate,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpsInstanceResponse:
    """
    Update a VPS instance's metadata and configuration.

    Does NOT trigger Proxmox changes — use dedicated resize,
    reinstall, and power endpoints for live changes.
    Requires admin privileges.
    """
    _require_admin(current_user)

    vps_service = VpsInstanceService(session)
    try:
        instance = await vps_service.get_instance(instance_id)
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(instance, field):
            setattr(instance, field, value)

    from datetime import datetime

    instance.updated_at = datetime.now(tz=timezone.utc)
    await session.commit()
    await session.refresh(instance)

    return _build_instance_response(instance)


@router.delete("/instances/{instance_id}")
async def delete_vps_instance(
    instance_id: UUID,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
):
    """
    Decommission a VPS instance.

    Destroys the VM on Proxmox and removes the database record.
    Requires admin privileges.
    """
    _require_admin(current_user)

    vps_service = VpsInstanceService(session)
    try:
        await vps_service.decommission(instance_id)
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VpsServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


# ──────────────────────────────────────────────
# Power Actions
# ──────────────────────────────────────────────


@router.post(
    "/instances/{instance_id}/power",
    response_model=ProxmoxTaskResponse,
)
async def power_action_instance(
    instance_id: UUID,
    body: VpsPowerAction,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ProxmoxTaskResponse:
    """
    Execute a power action on a VPS instance.

    Supported actions: start, stop, shutdown, reboot, reset, suspend, resume.
    Requires admin privileges.
    """
    _require_admin(current_user)

    vps_service = VpsInstanceService(session)
    try:
        result = await vps_service.power_action(
            instance_id=instance_id,
            action=body.action,
            timeout_seconds=body.timeout_seconds,
        )
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VpsInvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except VpsPowerActionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ProxmoxTaskResponse(
        upid=result.upid,
        node=result.node,
        status=result.status,
        exitstatus=result.exitstatus,
        success=result.success,
    )


# ──────────────────────────────────────────────
# Status Sync
# ──────────────────────────────────────────────


@router.post(
    "/instances/{instance_id}/sync",
    response_model=VpsStatusDetail,
)
async def sync_instance_status(
    instance_id: UUID,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpsStatusDetail:
    """
    Sync the status of a VPS instance from Proxmox to the database.

    Fetches live VM info (CPU, memory, uptime, status) and updates the DB record.
    """
    vps_service = VpsInstanceService(session)

    try:
        # Check instance exists
        instance = await vps_service.get_instance(instance_id)
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await _check_instance_ownership(instance, session, current_user)

    try:
        vm_info = await vps_service.sync_status(instance_id)
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return VpsStatusDetail(
        vmid=vm_info.vmid,
        name=vm_info.name,
        node=vm_info.node,
        status=vm_info.status,
        cpus=vm_info.cpus,
        max_memory_bytes=vm_info.max_memory_bytes,
        memory_used_bytes=vm_info.memory_used_bytes,
        memory_usage_pct=vm_info.memory_usage_pct,
        max_disk_bytes=vm_info.max_disk_bytes,
        uptime_seconds=vm_info.uptime_seconds,
        template_os=vm_info.template_os,
        vnc_port=vm_info.vnc_port,
    )


# ──────────────────────────────────────────────
# Resize
# ──────────────────────────────────────────────


@router.post(
    "/instances/{instance_id}/resize",
    response_model=VpsInstanceResponse,
)
async def resize_instance(
    instance_id: UUID,
    cores: int | None = Query(None, ge=1, le=128, description="New vCPU count"),
    memory_mb: int | None = Query(None, ge=128, le=1048576, description="New RAM in MB"),
    disk_gb: int | None = Query(None, ge=1, le=65536, description="New disk size in GB"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpsInstanceResponse:
    """
    Resize a VPS instance's resources (CPU, RAM, Disk).

    CPU and memory changes are applied live; disk resize may require a VM restart.
    Requires admin privileges.
    """
    _require_admin(current_user)

    if cores is None and memory_mb is None and disk_gb is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of cores, memory_mb, or disk_gb must be provided",
        )

    vps_service = VpsInstanceService(session)
    try:
        instance = await vps_service.resize(
            instance_id=instance_id,
            cores=cores,
            memory_mb=memory_mb,
            disk_gb=disk_gb,
        )
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VpsResizeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _build_instance_response(instance)


# ──────────────────────────────────────────────
# Reinstall OS
# ──────────────────────────────────────────────


@router.post(
    "/instances/{instance_id}/reinstall",
    response_model=VpsInstanceResponse,
)
async def reinstall_instance(
    instance_id: UUID,
    ostemplate: str | None = Query(None, description="New OS template path"),
    iso_image: str | None = Query(None, description="New ISO image path"),
    root_password: str | None = Query(None, description="New root password"),
    ssh_keys: str | None = Query(None, description="New SSH public keys"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpsInstanceResponse:
    """
    Reinstall the operating system on a VPS instance.

    Stops the VM, updates OS configuration, and restarts.
    Requires admin privileges.
    """
    _require_admin(current_user)

    vps_service = VpsInstanceService(session)
    try:
        instance = await vps_service.reinstall(
            instance_id=instance_id,
            ostemplate=ostemplate,
            iso_image=iso_image,
            root_password=root_password,
            ssh_keys=ssh_keys,
        )
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VpsServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _build_instance_response(instance)


# ──────────────────────────────────────────────
# Clone
# ──────────────────────────────────────────────


@router.post(
    "/instances/{instance_id}/clone",
    response_model=VpsInstanceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def clone_instance(
    instance_id: UUID,
    new_service_id: UUID = Query(..., description="Service ID for the cloned instance"),
    new_name: str | None = Query(None, description="Name for the cloned VM"),
    storage: str = Query("local-lvm", description="Storage pool for the clone"),
    full_clone: bool = Query(True, description="Create a full clone (vs linked)"),
    start: bool = Query(True, description="Start the clone after creation"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpsInstanceResponse:
    """
    Clone an existing VPS instance to create a new one.

    Creates a full or linked clone on the same node.
    Requires admin privileges.
    """
    _require_admin(current_user)

    vps_service = VpsInstanceService(session)
    try:
        clone = await vps_service.clone(
            instance_id=instance_id,
            new_service_id=new_service_id,
            new_name=new_name,
            storage=storage,
            full_clone=full_clone,
            start=start,
        )
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VpsProvisioningError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _build_instance_response(clone)


# ──────────────────────────────────────────────
# Snapshots
# ──────────────────────────────────────────────


@router.post(
    "/instances/{instance_id}/snapshots",
    response_model=VpsSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_snapshot(
    instance_id: UUID,
    body: VpsSnapshotCreate,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpsSnapshotResponse:
    """
    Create a snapshot of a VPS instance.

    Optionally includes RAM state.
    Requires admin privileges.
    """
    _require_admin(current_user)

    vps_service = VpsInstanceService(session)
    try:
        snapshot = await vps_service.create_snapshot(
            instance_id=instance_id,
            snapshot_name=body.snapshot_name,
            description=body.description,
            include_ram=body.include_ram,
        )
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VpsSnapshotError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return _build_snapshot_response(snapshot)


@router.get(
    "/instances/{instance_id}/snapshots",
    response_model=VpsSnapshotListResponse,
)
async def list_snapshots(
    instance_id: UUID,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpsSnapshotListResponse:
    """
    List all snapshots for a VPS instance.
    """
    vps_service = VpsInstanceService(session)

    try:
        # Verify instance exists and user has access
        instance = await vps_service.get_instance(instance_id)
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await _check_instance_ownership(instance, session, current_user)

    snapshots = await vps_service.list_snapshots(instance_id)
    return VpsSnapshotListResponse(
        vps_instance_id=instance_id,
        snapshots=[_build_snapshot_response(s) for s in snapshots],
    )


@router.delete(
    "/instances/{instance_id}/snapshots/{snapshot_name}",
)
async def delete_snapshot(
    instance_id: UUID,
    snapshot_name: str,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
):
    """
    Delete a snapshot of a VPS instance by name.
    Requires admin privileges.
    """
    _require_admin(current_user)

    vps_service = VpsInstanceService(session)
    try:
        await vps_service.delete_snapshot(
            instance_id=instance_id,
            snapshot_name=snapshot_name,
        )
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VpsSnapshotError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "/instances/{instance_id}/snapshots/{snapshot_name}/rollback",
    response_model=ProxmoxTaskResponse,
)
async def rollback_snapshot(
    instance_id: UUID,
    snapshot_name: str,
    start_after: bool = Query(True, description="Start the VM after rollback"),
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> ProxmoxTaskResponse:
    """
    Rollback a VPS instance to a specific snapshot.

    This will revert the VM disk and optionally RAM state.
    Requires admin privileges.
    """
    _require_admin(current_user)

    vps_service = VpsInstanceService(session)
    try:
        result = await vps_service.rollback_snapshot(
            instance_id=instance_id,
            snapshot_name=snapshot_name,
            start_after=start_after,
        )
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except VpsSnapshotError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ProxmoxTaskResponse(
        upid=result.upid,
        node=result.node,
        status=result.status,
        exitstatus=result.exitstatus,
        success=result.success,
    )


# ──────────────────────────────────────────────
# VNC Console Access
# ──────────────────────────────────────────────


@router.get(
    "/instances/{instance_id}/console",
    response_model=VpsVncResponse,
)
async def get_vnc_console(
    instance_id: UUID,
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> VpsVncResponse:
    """
    Get VNC/noVNC console access details for a VPS instance.

    Returns a one-time ticket and websocket path for browser-based
    console access.
    """
    vps_service = VpsInstanceService(session)

    try:
        instance = await vps_service.get_instance(instance_id)
    except VpsInstanceNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    await _check_instance_ownership(instance, session, current_user)

    try:
        vnc_info = await vps_service.get_vnc_console(instance_id)
    except VpsConsoleError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return VpsVncResponse(
        vmid=vnc_info["vmid"],
        node=vnc_info["node"],
        port=vnc_info["port"],
        ticket=vnc_info["ticket"],
        websocket_path=vnc_info.get("websocket_path"),
    )


# ──────────────────────────────────────────────
# VPS Products (Client-facing)
# ──────────────────────────────────────────────


@router.get("/products")
async def list_vps_products(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> list[dict[str, Any]]:
    """
    List available VPS products for purchase.

    Returns public product details including pricing tiers.
    """
    stmt = select(Product).where(
        Product.module == "vps",
        Product.is_active.is_(True),
    )
    result = await session.execute(stmt)
    products = result.scalars().all()

    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "cores": p.features.get("cores", 1) if p.features else 1,
            "memory_mb": p.features.get("memory_mb", 1024) if p.features else 1024,
            "disk_gb": p.features.get("disk_gb", 10) if p.features else 10,
            "bandwidth_mbps": p.features.get("bandwidth_mbps") if p.features else None,
            "traffic_tb": p.features.get("traffic_tb") if p.features else None,
            "price_monthly": float(p.price_monthly) if p.price_monthly else None,
            "price_quarterly": float(p.price_quarterly) if p.price_quarterly else None,
            "price_semi_annually": float(p.price_semi_annually) if p.price_semi_annually else None,
            "price_annually": float(p.price_annually) if p.price_annually else None,
            "is_active": p.is_active,
        }
        for p in products
    ]


# ──────────────────────────────────────────────
# VPS Services (User-facing list)
# ──────────────────────────────────────────────


@router.get("/services")
async def list_my_vps_services(
    session: AsyncSession = Depends(get_async_session),  # noqa: B008
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> dict[str, Any]:
    """
    List the current user's VPS services with associated instances and status.

    Returns active and suspended VPS services owned by the authenticated user.
    """
    from sqlalchemy.orm import selectinload

    stmt = (
        select(Service)
        .options(selectinload(Service.vps_instances))
        .where(
            Service.user_id == str(current_user.id),
            Service.status.in_([ServiceStatus.ACTIVE, ServiceStatus.SUSPENDED]),
        )
        .order_by(Service.created_at.desc())
    )
    result = await session.execute(stmt)
    services = result.scalars().all()

    items: list[dict[str, Any]] = []
    for svc in services:
        for inst in svc.vps_instances or []:
            items.append({
                "service_id": str(svc.id),
                "instance_id": str(inst.id),
                "vmid": inst.proxmox_vmid,
                "node": inst.proxmox_node,
                "cores": inst.cores,
                "memory_mb": inst.memory_mb,
                "disk_gb": inst.disk_gb,
                "ostype": inst.ostype,
                "ip_address": inst.ip_address,
                "power_status": inst.power_status.value if hasattr(inst.power_status, "value") else str(inst.power_status),
                "vnc_port": inst.vnc_port,
                "service_status": svc.status.value if hasattr(svc.status, "value") else str(svc.status),
                "expires_at": svc.expires_at,
                "created_at": inst.created_at,
            })
        # If service has no instances yet, still show the service
        if not svc.vps_instances:
            items.append({
                "service_id": str(svc.id),
                "instance_id": None,
                "vmid": None,
                "node": None,
                "cores": None,
                "memory_mb": None,
                "disk_gb": None,
                "ostype": None,
                "ip_address": None,
                "power_status": "pending",
                "vnc_port": None,
                "service_status": svc.status.value if hasattr(svc.status, "value") else str(svc.status),
                "expires_at": svc.expires_at,
                "created_at": svc.created_at,
            })

    return {"services": items, "total": len(items)}


__all__ = ["router"]
