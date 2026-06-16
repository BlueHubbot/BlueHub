"""
VPS Celery Tasks
================
Asynchronous, retryable tasks for Proxmox VM lifecycle operations.
Used to keep API endpoints responsive for long-running Proxmox actions.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.db import get_async_session_ctx
from modules.vps.models import VpsInstance, VpsPowerStatus, VpsSnapshot
from modules.vps.proxmox_client import (
    ProxmoxClient,
    ProxmoxClientError,
    ProxmoxConnectionError,
    ProxmoxTaskError,
    ProxmoxVMNotFoundError,
    ProxmoxVMInfo,
    ProxmoxTaskResult,
)
from modules.vps.services import (
    VpsConsoleError,
    VpsInstanceNotFoundError,
    VpsInstanceService,
    VpsPowerActionError,
    VpsProvisioningError,
    VpsResizeError,
    VpsServiceError,
    VpsSnapshotError,
)
from shared.models.service import Service, ServiceStatus

logger = logging.getLogger("bluehub.tasks.vps")

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
MAX_RETRIES = 5
DEFAULT_RETRY_DELAY = 10  # seconds


# ------------------------------------------------------------------
# Provisioning
# ------------------------------------------------------------------
@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=DEFAULT_RETRY_DELAY,
    name="vps.provision",
    queue="vps",
    autoretry_for=(ProxmoxConnectionError, ProxmoxTaskError),
    retry_kwargs={"max_retries": MAX_RETRIES},
)
async def provision_vps(
    self: Any,
    service_id: str,
    node: str,
    cores: int = 1,
    memory_mb: int = 1024,
    disk_gb: int = 10,
    storage: str = "local-lvm",
    network_bridge: str = "vmbr0",
    network_model: str = "virtio",
    ostype: str = "l26",
    ostemplate: str | None = None,
    iso_image: str | None = None,
    ip_address: str | None = None,
    root_password: str | None = None,
    ssh_keys: str | None = None,
    vmid: int | None = None,
    start: bool = True,
    extra_config: dict | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    Celery task to provision a new VPS instance asynchronously.

    Called by the billing/provisioning pipeline when a VPS service
    is activated.  Handles retries for transient Proxmox errors.
    """
    service_uuid = UUID(service_id)
    logger.info("Task vps.provision started for service %s", service_id)

    try:
        async with get_async_session_ctx() as db:
            vps_service = VpsInstanceService(db)
            instance = await vps_service.provision(
                service_id=service_uuid,
                node=node,
                cores=cores,
                memory_mb=memory_mb,
                disk_gb=disk_gb,
                storage=storage,
                network_bridge=network_bridge,
                network_model=network_model,
                ostype=ostype,
                ostemplate=ostemplate,
                iso_image=iso_image,
                ip_address=ip_address,
                root_password=root_password,
                ssh_keys=ssh_keys,
                vmid=vmid,
                start=start,
                extra_config=extra_config,
                notes=notes,
            )

            # Update the billing Service status to ACTIVE
            service = await db.get(Service, service_uuid)
            if service:
                service.status = ServiceStatus.ACTIVE
                await db.commit()

            logger.info(
                "Task vps.provision completed: instance_id=%s, vmid=%d",
                instance.id,
                instance.proxmox_vmid,
            )
            return {
                "instance_id": str(instance.id),
                "vmid": instance.proxmox_vmid,
                "node": instance.proxmox_node,
                "status": "provisioned",
            }

    except ProxmoxConnectionError as exc:
        logger.warning("Provisioning retry %d/%d: %s", self.request.retries, MAX_RETRIES, exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Provisioning failed after %d retries", MAX_RETRIES)
            await _mark_service_failed(service_uuid, str(exc))
            raise

    except VpsProvisioningError as exc:
        logger.error("Provisioning failed: %s", exc)
        await _mark_service_failed(service_uuid, str(exc))
        raise


# ------------------------------------------------------------------
# Power management
# ------------------------------------------------------------------
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    name="vps.power_action",
    queue="vps",
    autoretry_for=(ProxmoxConnectionError,),
)
async def power_action_vps(
    self: Any,
    instance_id: str,
    action: str,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """
    Execute a power action (start/stop/reboot/etc.) against a VPS instance.
    """
    logger.info("Task vps.power_action started: instance=%s action=%s", instance_id, action)
    instance_uuid = UUID(instance_id)

    try:
        async with get_async_session_ctx() as db:
            vps_service = VpsInstanceService(db)
            result = await vps_service.power_action(
                instance_uuid,
                action,
                timeout_seconds,
            )
            logger.info(
                "Task vps.power_action completed: instance=%s action=%s success=%s",
                instance_id,
                action,
                result.success,
            )
            return {
                "instance_id": instance_id,
                "action": action,
                "success": result.success,
                "upid": result.upid,
                "exitstatus": result.exitstatus,
            }

    except (VpsPowerActionError, VpsInvalidStateError) as exc:
        logger.error("Power action '%s' failed: %s", action, exc)
        raise
    except ProxmoxConnectionError as exc:
        logger.warning("Power action retry: %s", exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Power action failed after %d retries", MAX_RETRIES)
            raise


# ------------------------------------------------------------------
# Status sync (periodic)
# ------------------------------------------------------------------
@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    name="vps.sync_status",
    queue="vps",
    autoretry_for=(ProxmoxConnectionError,),
)
async def sync_vps_status(
    self: Any,
    instance_id: str | None = None,
    node: str | None = None,
    batch_size: int = 100,
) -> dict[str, Any]:
    """
    Sync VPS instance status from Proxmox to the database.

    If *instance_id* is provided, only that instance is synced.
    Otherwise all active instances (optionally filtered by *node*) are synced.
    """
    logger.info("Task vps.sync_status started (instance=%s, node=%s)", instance_id, node)

    try:
        async with get_async_session_ctx() as db:
            vps_service = VpsInstanceService(db)

            if instance_id:
                try:
                    vm_info = await vps_service.sync_status(UUID(instance_id))
                    return {
                        "synced": 1,
                        "instances": [
                            {
                                "instance_id": instance_id,
                                "vmid": vm_info.vmid,
                                "status": vm_info.status,
                            }
                        ],
                    }
                except VpsInstanceNotFoundError:
                    logger.warning("Instance %s not found during sync", instance_id)
                    return {"synced": 0, "instances": []}

            # Sync all active instances
            instances = await vps_service.list_instances(
                node=node,
                limit=batch_size,
            )
            synced = []
            for inst in instances:
                if inst.proxmox_vmid is None:
                    continue
                try:
                    vm_info = await vps_service.sync_status(inst.id)
                    synced.append(
                        {
                            "instance_id": str(inst.id),
                            "vmid": vm_info.vmid,
                            "status": vm_info.status,
                        }
                    )
                except ProxmoxVMNotFoundError:
                    synced.append(
                        {
                            "instance_id": str(inst.id),
                            "vmid": inst.proxmox_vmid,
                            "status": "not_found",
                        }
                    )
                except VpsInstanceNotFoundError:
                    continue

            logger.info("Task vps.sync_status completed: synced %d instances", len(synced))
            return {"synced": len(synced), "instances": synced}

    except ProxmoxConnectionError as exc:
        logger.warning("Status sync retry: %s", exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Status sync failed after max retries")
            raise


# ------------------------------------------------------------------
# Snapshot operations
# ------------------------------------------------------------------
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="vps.create_snapshot",
    queue="vps",
    autoretry_for=(ProxmoxConnectionError, ProxmoxTaskError),
)
async def create_snapshot_vps(
    self: Any,
    instance_id: str,
    snapshot_name: str,
    description: str | None = None,
    include_ram: bool = False,
) -> dict[str, Any]:
    """Create a VM snapshot asynchronously."""
    instance_uuid = UUID(instance_id)
    logger.info(
        "Task vps.create_snapshot started: instance=%s snapshot=%s",
        instance_id,
        snapshot_name,
    )

    try:
        async with get_async_session_ctx() as db:
            vps_service = VpsInstanceService(db)
            snapshot = await vps_service.create_snapshot(
                instance_uuid,
                snapshot_name,
                description,
                include_ram,
            )
            logger.info(
                "Task vps.create_snapshot completed: snapshot_id=%s",
                snapshot.id,
            )
            return {
                "snapshot_id": str(snapshot.id),
                "snapshot_name": snapshot.snapshot_name,
                "instance_id": instance_id,
            }

    except VpsSnapshotError as exc:
        logger.error("Snapshot creation failed: %s", exc)
        raise
    except (ProxmoxConnectionError, ProxmoxTaskError) as exc:
        logger.warning("Snapshot creation retry: %s", exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Snapshot creation failed after max retries")
            raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="vps.delete_snapshot",
    queue="vps",
    autoretry_for=(ProxmoxConnectionError,),
)
async def delete_snapshot_vps(
    self: Any,
    instance_id: str,
    snapshot_name: str,
) -> dict[str, str]:
    """Delete a VM snapshot asynchronously."""
    instance_uuid = UUID(instance_id)
    logger.info(
        "Task vps.delete_snapshot started: instance=%s snapshot=%s",
        instance_id,
        snapshot_name,
    )

    try:
        async with get_async_session_ctx() as db:
            vps_service = VpsInstanceService(db)
            await vps_service.delete_snapshot(instance_uuid, snapshot_name)
            logger.info("Task vps.delete_snapshot completed")
            return {"status": "deleted", "instance_id": instance_id, "snapshot_name": snapshot_name}

    except VpsSnapshotError as exc:
        logger.error("Snapshot deletion failed: %s", exc)
        raise
    except ProxmoxConnectionError as exc:
        logger.warning("Snapshot deletion retry: %s", exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Snapshot deletion failed after max retries")
            raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="vps.rollback_snapshot",
    queue="vps",
    autoretry_for=(ProxmoxConnectionError, ProxmoxTaskError),
)
async def rollback_snapshot_vps(
    self: Any,
    instance_id: str,
    snapshot_name: str,
    start_after: bool = True,
) -> dict[str, Any]:
    """Rollback to a VM snapshot asynchronously."""
    instance_uuid = UUID(instance_id)
    logger.info(
        "Task vps.rollback_snapshot started: instance=%s snapshot=%s",
        instance_id,
        snapshot_name,
    )

    try:
        async with get_async_session_ctx() as db:
            vps_service = VpsInstanceService(db)
            result = await vps_service.rollback_snapshot(
                instance_uuid,
                snapshot_name,
                start_after,
            )
            logger.info(
                "Task vps.rollback_snapshot completed: success=%s",
                result.success,
            )
            return {
                "instance_id": instance_id,
                "snapshot_name": snapshot_name,
                "success": result.success,
                "upid": result.upid,
            }

    except VpsSnapshotError as exc:
        logger.error("Snapshot rollback failed: %s", exc)
        raise
    except (ProxmoxConnectionError, ProxmoxTaskError) as exc:
        logger.warning("Snapshot rollback retry: %s", exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Snapshot rollback failed after max retries")
            raise


# ------------------------------------------------------------------
# Resize
# ------------------------------------------------------------------
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    name="vps.resize",
    queue="vps",
    autoretry_for=(ProxmoxConnectionError,),
)
async def resize_vps(
    self: Any,
    instance_id: str,
    cores: int | None = None,
    memory_mb: int | None = None,
    disk_gb: int | None = None,
) -> dict[str, Any]:
    """Resize a VPS instance's resources asynchronously."""
    instance_uuid = UUID(instance_id)
    logger.info("Task vps.resize started: instance=%s", instance_id)

    try:
        async with get_async_session_ctx() as db:
            vps_service = VpsInstanceService(db)
            instance = await vps_service.resize(
                instance_uuid,
                cores=cores,
                memory_mb=memory_mb,
                disk_gb=disk_gb,
            )
            logger.info("Task vps.resize completed: instance=%s", instance_id)
            return {
                "instance_id": instance_id,
                "vmid": instance.proxmox_vmid,
                "cores": instance.cores,
                "memory_mb": instance.memory_mb,
                "disk_gb": instance.disk_gb,
            }

    except VpsResizeError as exc:
        logger.error("Resize failed: %s", exc)
        raise
    except ProxmoxConnectionError as exc:
        logger.warning("Resize retry: %s", exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Resize failed after max retries")
            raise


# ------------------------------------------------------------------
# Decommission
# ------------------------------------------------------------------
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="vps.decommission",
    queue="vps",
    autoretry_for=(ProxmoxConnectionError,),
)
async def decommission_vps(
    self: Any,
    instance_id: str,
    service_id: str | None = None,
) -> dict[str, str]:
    """
    Decommission (destroy) a VPS instance asynchronously.
    Called when a VPS service is cancelled/expired.
    """
    instance_uuid = UUID(instance_id)
    logger.info("Task vps.decommission started: instance=%s", instance_id)

    try:
        async with get_async_session_ctx() as db:
            vps_service = VpsInstanceService(db)
            await vps_service.decommission(instance_uuid)

            # Optionally update the billing Service status
            if service_id:
                service = await db.get(Service, UUID(service_id))
                if service:
                    service.status = ServiceStatus.TERMINATED
                    await db.commit()

            logger.info("Task vps.decommission completed: instance=%s", instance_id)
            return {"instance_id": instance_id, "status": "decommissioned"}

    except VpsServiceError as exc:
        logger.error("Decommission failed: %s", exc)
        raise
    except ProxmoxConnectionError as exc:
        logger.warning("Decommission retry: %s", exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Decommission failed after max retries")
            raise


# ------------------------------------------------------------------
# Clone
# ------------------------------------------------------------------
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="vps.clone",
    queue="vps",
    autoretry_for=(ProxmoxConnectionError, ProxmoxTaskError),
)
async def clone_vps(
    self: Any,
    instance_id: str,
    new_service_id: str,
    new_name: str | None = None,
    storage: str = "local-lvm",
    full_clone: bool = True,
    start: bool = True,
) -> dict[str, Any]:
    """Clone a VPS instance asynchronously."""
    source_uuid = UUID(instance_id)
    target_service_uuid = UUID(new_service_id)
    logger.info("Task vps.clone started: source=%s -> service=%s", instance_id, new_service_id)

    try:
        async with get_async_session_ctx() as db:
            vps_service = VpsInstanceService(db)
            clone = await vps_service.clone(
                source_uuid,
                target_service_uuid,
                new_name=new_name,
                storage=storage,
                full_clone=full_clone,
                start=start,
            )
            logger.info(
                "Task vps.clone completed: new_instance=%s, vmid=%d",
                clone.id,
                clone.proxmox_vmid,
            )
            return {
                "source_instance_id": instance_id,
                "new_instance_id": str(clone.id),
                "vmid": clone.proxmox_vmid,
                "node": clone.proxmox_node,
                "status": "cloned",
            }

    except VpsProvisioningError as exc:
        logger.error("Clone failed: %s", exc)
        await _mark_service_failed(target_service_uuid, str(exc))
        raise
    except (ProxmoxConnectionError, ProxmoxTaskError) as exc:
        logger.warning("Clone retry: %s", exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Clone failed after max retries")
            await _mark_service_failed(target_service_uuid, str(exc))
            raise


# ------------------------------------------------------------------
# Reinstall
# ------------------------------------------------------------------
@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=20,
    name="vps.reinstall",
    queue="vps",
    autoretry_for=(ProxmoxConnectionError,),
)
async def reinstall_vps(
    self: Any,
    instance_id: str,
    ostemplate: str | None = None,
    iso_image: str | None = None,
    root_password: str | None = None,
    ssh_keys: str | None = None,
) -> dict[str, Any]:
    """Reinstall the OS on a VPS instance asynchronously."""
    instance_uuid = UUID(instance_id)
    logger.info("Task vps.reinstall started: instance=%s", instance_id)

    try:
        async with get_async_session_ctx() as db:
            vps_service = VpsInstanceService(db)
            instance = await vps_service.reinstall(
                instance_uuid,
                ostemplate=ostemplate,
                iso_image=iso_image,
                root_password=root_password,
                ssh_keys=ssh_keys,
            )
            logger.info("Task vps.reinstall completed: instance=%s", instance_id)
            return {
                "instance_id": instance_id,
                "vmid": instance.proxmox_vmid,
                "status": "reinstalled",
            }

    except VpsServiceError as exc:
        logger.error("Reinstall failed: %s", exc)
        raise
    except ProxmoxConnectionError as exc:
        logger.warning("Reinstall retry: %s", exc)
        try:
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            logger.error("Reinstall failed after max retries")
            raise


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------
async def _mark_service_failed(service_id: UUID, reason: str) -> None:
    """Mark a billing service as FAILED when provisioning cannot complete."""
    try:
        async with get_async_session_ctx() as db:
            service = await db.get(Service, service_id)
            if service:
                service.status = ServiceStatus.FAILED
                service.suspension_reason = reason
                await db.commit()
            logger.warning("Service %s marked as FAILED: %s", service_id, reason)
    except Exception as exc:
        logger.error("Failed to mark service %s as FAILED: %s", service_id, exc)


__all__ = [
    "provision_vps",
    "power_action_vps",
    "sync_vps_status",
    "create_snapshot_vps",
    "delete_snapshot_vps",
    "rollback_snapshot_vps",
    "resize_vps",
    "decommission_vps",
    "clone_vps",
    "reinstall_vps",
]