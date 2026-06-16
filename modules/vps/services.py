"""
BlueHub VPS Services Layer
===========================
Business-logic orchestration for VPS (Proxmox VM) lifecycle management.
Integrates ProxmoxClient with database persistence via VpsInstance/VpsSnapshot models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from modules.vps.models import VpsInstance, VpsPowerStatus, VpsSnapshot
from modules.vps.proxmox_client import (
    ProxmoxClient,
    ProxmoxClientError,
    ProxmoxConnectionError,
    ProxmoxNodeNotFoundError,
    ProxmoxResourceBusyError,
    ProxmoxTaskError,
    ProxmoxVMInfo,
    ProxmoxVMNotFoundError,
    ProxmoxSnapshotInfo,
    ProxmoxTaskResult,
)
from shared.models.service import Service, ServiceStatus

logger = logging.getLogger("bluehub.modules.vps.services")


# ------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------
class VpsServiceError(Exception):
    """Base exception for VPS service operations."""


class VpsProvisioningError(VpsServiceError):
    """VM provisioning failed on Proxmox side."""


class VpsPowerActionError(VpsServiceError):
    """Power action (start/stop/reboot/etc.) failed."""


class VpsSnapshotError(VpsServiceError):
    """Snapshot operation failed."""


class VpsResizeError(VpsServiceError):
    """VM resize operation failed."""


class VpsConsoleError(VpsServiceError):
    """VNC console access failed."""


class VpsInstanceNotFoundError(VpsServiceError):
    """VPS instance record not found in database."""


class VpsInvalidStateError(VpsServiceError):
    """Operation cannot proceed due to invalid VM state."""


# ------------------------------------------------------------------
# Dataclass for summary responses
# ------------------------------------------------------------------
@dataclass
class VpsTrafficSummary:
    """Traffic/billing summary for a VPS instance (placeholder)."""

    instance_id: str
    vm_status: str
    node: str
    cores: int
    memory_mb: int
    disk_gb: int


# ------------------------------------------------------------------
# VpsInstanceService
# ------------------------------------------------------------------
class VpsInstanceService:
    """
    High-level orchestrator for VPS instance lifecycle.

    Coordinates ProxmoxClient operations with database persistence
    for provisioning, power management, snapshot management, resizing,
    and console access.
    """

    DEFAULT_NODE = "pve"
    DEFAULT_BRIDGE = "vmbr0"
    DEFAULT_STORAGE = "local-lvm"

    def __init__(self, db: AsyncSession, proxmox: ProxmoxClient | None = None) -> None:
        self.db = db
        self._proxmox = proxmox

    async def _get_proxmox(self) -> ProxmoxClient:
        """Return the current ProxmoxClient, connecting if necessary."""
        if self._proxmox is None:
            self._proxmox = ProxmoxClient()
        if self._proxmox._api is None:  # type: ignore[has-type]
            await self._proxmox.connect()
        return self._proxmox

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------
    async def get_instance(self, instance_id: UUID) -> VpsInstance:
        stmt = (
            select(VpsInstance)
            .where(VpsInstance.id == instance_id)
            .options(selectinload(VpsInstance.service))
        )
        result = await self.db.execute(stmt)
        instance = result.scalar_one_or_none()
        if instance is None:
            raise VpsInstanceNotFoundError(f"VPS instance {instance_id} not found.")
        return instance

    async def get_instance_by_vmid(self, vmid: int) -> VpsInstance | None:
        stmt = select(VpsInstance).where(VpsInstance.proxmox_vmid == vmid)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_instance_by_service(self, service_id: UUID) -> VpsInstance | None:
        stmt = select(VpsInstance).where(VpsInstance.service_id == service_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_instances(
        self,
        node: str | None = None,
        status: VpsPowerStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[VpsInstance]:
        stmt = select(VpsInstance).options(selectinload(VpsInstance.service))
        if node:
            stmt = stmt.where(VpsInstance.proxmox_node == node)
        if status:
            stmt = stmt.where(VpsInstance.power_status == status)
        stmt = stmt.order_by(VpsInstance.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Provisioning
    # ------------------------------------------------------------------
    async def provision(
        self,
        service_id: UUID,
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
    ) -> VpsInstance:
        """
        Provision a new VM on Proxmox and create the corresponding
        VpsInstance database record.
        """
        proxmox = await self._get_proxmox()

        # Auto-assign VMID if not provided
        if vmid is None:
            vmid = await self._next_available_vmid(proxmox, node)
            logger.info("Auto-assigned VMID %d for new VPS instance", vmid)

        net0 = f"{network_model},bridge={network_bridge}"
        ipconfig0 = f"ip={ip_address}/24,gw={ip_address.rsplit('.', 1)[0]}.1" if ip_address else None

        try:
            task = await proxmox.create_vm(
                node=node,
                vmid=vmid,
                name=f"bluehub-{str(service_id)[:8]}",
                cores=cores,
                memory_mb=memory_mb,
                disk_gb=disk_gb,
                storage=storage,
                net0=net0,
                ipconfig0=ipconfig0,
                sshkeys=ssh_keys,
                start=start,
                ostemplate=ostemplate,
                extra=extra_config,
            )
        except ProxmoxClientError as exc:
            logger.error("Proxmox VM creation failed: %s", exc)
            raise VpsProvisioningError(f"Failed to create VM on node '{node}': {exc}") from exc

        if not task.success:
            raise VpsProvisioningError(
                f"Proxmox create task failed: exitstatus={task.exitstatus}, upid={task.upid}"
            )

        # Fetch VNC port after creation
        vnc_port: int | None = None
        try:
            vnc_info = await proxmox.get_vnc_proxy(vmid, node)
            vnc_port = vnc_info.get("port")
        except ProxmoxClientError:
            logger.warning("Could not fetch VNC port for VMID %d", vmid)

        # Create DB record
        instance = VpsInstance(
            id=uuid4(),
            service_id=service_id,
            proxmox_node=node,
            proxmox_vmid=vmid,
            cores=cores,
            memory_mb=memory_mb,
            disk_gb=disk_gb,
            storage_pool=storage,
            network_bridge=network_bridge,
            network_model=network_model,
            ostype=ostype,
            ostemplate=ostemplate,
            iso_image=iso_image,
            ip_address=ip_address,
            root_password=root_password,
            ssh_keys=ssh_keys,
            power_status=VpsPowerStatus.RUNNING if start else VpsPowerStatus.STOPPED,
            vnc_port=vnc_port,
            extra_config=extra_config or {},
            notes=notes,
        )
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)

        logger.info(
            "Provisioned VPS instance %s (VMID=%d) on node '%s'",
            instance.id,
            vmid,
            node,
        )
        return instance

    async def _next_available_vmid(self, proxmox: ProxmoxClient, node: str) -> int:
        """Find the next available VMID on the target node."""
        try:
            existing_vms = await proxmox.list_vms(node)
            used_ids = {vm.vmid for vm in existing_vms}
        except ProxmoxClientError:
            used_ids = set()
        # Start from 100, find first gap
        candidate = 100
        while candidate in used_ids:
            candidate += 1
        return candidate

    # ------------------------------------------------------------------
    # Power management
    # ------------------------------------------------------------------
    async def power_action(
        self,
        instance_id: UUID,
        action: str,
        timeout_seconds: int = 60,
    ) -> ProxmoxTaskResult:
        """Execute a power action on a VPS instance."""
        instance = await self.get_instance(instance_id)
        proxmox = await self._get_proxmox()
        vmid = instance.proxmox_vmid
        node = instance.proxmox_node

        if vmid is None:
            raise VpsInvalidStateError(f"Instance {instance_id} has no VMID assigned.")

        try:
            if action == "start":
                task = await proxmox.start_vm(node, vmid)
                new_status = VpsPowerStatus.RUNNING
            elif action == "stop":
                task = await proxmox.stop_vm(node, vmid, timeout_seconds)
                new_status = VpsPowerStatus.STOPPED
            elif action == "shutdown":
                task = await proxmox.shutdown_vm(node, vmid, timeout_seconds)
                new_status = VpsPowerStatus.STOPPED
            elif action == "reboot":
                task = await proxmox.reboot_vm(node, vmid)
                new_status = VpsPowerStatus.RUNNING
            elif action == "reset":
                task = await proxmox.reset_vm(node, vmid)
                new_status = VpsPowerStatus.RUNNING
            elif action == "suspend":
                task = await proxmox.suspend_vm(node, vmid)
                new_status = VpsPowerStatus.SUSPENDED
            elif action == "resume":
                task = await proxmox.resume_vm(node, vmid)
                new_status = VpsPowerStatus.RUNNING
            else:
                raise VpsPowerActionError(f"Unknown power action: {action}")
        except ProxmoxResourceBusyError as exc:
            raise VpsInvalidStateError(str(exc)) from exc
        except ProxmoxClientError as exc:
            raise VpsPowerActionError(f"Power action '{action}' failed: {exc}") from exc

        # Update DB power status
        instance.power_status = new_status
        instance.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        logger.info(
            "Power action '%s' on instance %s (VMID=%d) completed: %s",
            action,
            instance_id,
            vmid,
            "OK" if task.success else f"FAILED ({task.exitstatus})",
        )
        return task

    # ------------------------------------------------------------------
    # Status sync from Proxmox
    # ------------------------------------------------------------------
    async def sync_status(self, instance_id: UUID) -> ProxmoxVMInfo:
        """Fetch live VM status from Proxmox and update DB record."""
        instance = await self.get_instance(instance_id)
        proxmox = await self._get_proxmox()

        if instance.proxmox_vmid is None:
            raise VpsInvalidStateError(f"Instance {instance_id} has no VMID.")

        try:
            vm_info = await proxmox.get_vm_status(
                instance.proxmox_vmid, instance.proxmox_node
            )
        except ProxmoxVMNotFoundError:
            instance.power_status = VpsPowerStatus.UNKNOWN
            await self.db.commit()
            raise VpsInstanceNotFoundError(
                f"VM {instance.proxmox_vmid} not found on Proxmox node '{instance.proxmox_node}'."
            )

        # Map Proxmox status to enum
        status_map = {
            "running": VpsPowerStatus.RUNNING,
            "stopped": VpsPowerStatus.STOPPED,
            "paused": VpsPowerStatus.PAUSED,
            "suspended": VpsPowerStatus.SUSPENDED,
        }
        new_status = status_map.get(vm_info.status, VpsPowerStatus.UNKNOWN)
        instance.power_status = new_status
        instance.cores = vm_info.cpus
        instance.memory_mb = vm_info.max_memory_bytes // (1024 * 1024)
        instance.vnc_port = vm_info.vnc_port
        instance.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        return vm_info

    # ------------------------------------------------------------------
    # Resize
    # ------------------------------------------------------------------
    async def resize(
        self,
        instance_id: UUID,
        cores: int | None = None,
        memory_mb: int | None = None,
        disk_gb: int | None = None,
        disk_target: str = "scsi0",
    ) -> VpsInstance:
        instance = await self.get_instance(instance_id)
        proxmox = await self._get_proxmox()
        vmid = instance.proxmox_vmid
        node = instance.proxmox_node

        if vmid is None:
            raise VpsInvalidStateError("Instance has no VMID.")

        try:
            # CPU/Memory resize (can happen while running)
            if cores is not None or memory_mb is not None:
                await proxmox.resize_vm(node, vmid, cores=cores, memory_mb=memory_mb)
                if cores is not None:
                    instance.cores = cores
                if memory_mb is not None:
                    instance.memory_mb = memory_mb

            # Disk resize
            if disk_gb is not None:
                await proxmox.resize_disk(node, vmid, disk_target, disk_gb)
                instance.disk_gb = disk_gb

        except ProxmoxResourceBusyError as exc:
            raise VpsResizeError(f"Cannot resize instance {instance_id}: {exc}") from exc
        except ProxmoxClientError as exc:
            raise VpsResizeError(f"Resize failed: {exc}") from exc

        instance.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(instance)

        logger.info("Resized instance %s (VMID=%d)", instance_id, vmid)
        return instance

    # ------------------------------------------------------------------
    # Reinstall / reimage
    # ------------------------------------------------------------------
    async def reinstall(
        self,
        instance_id: UUID,
        ostemplate: str | None = None,
        iso_image: str | None = None,
        root_password: str | None = None,
        ssh_keys: str | None = None,
    ) -> VpsInstance:
        """
        Reinstall the OS on a VPS instance.
        Stops the VM, updates config, and restarts.
        """
        instance = await self.get_instance(instance_id)
        proxmox = await self._get_proxmox()
        vmid = instance.proxmox_vmid
        node = instance.proxmox_node

        if vmid is None:
            raise VpsInvalidStateError("Instance has no VMID.")

        # Stop the VM first
        try:
            if instance.power_status == VpsPowerStatus.RUNNING:
                await proxmox.stop_vm(node, vmid)
        except ProxmoxClientError as exc:
            raise VpsServiceError(f"Cannot stop VM for reinstall: {exc}") from exc

        # Update config
        config_updates: dict[str, Any] = {}
        if ostemplate:
            config_updates["ostemplate"] = ostemplate
        if iso_image:
            config_updates["iso"] = iso_image
        if root_password:
            config_updates["cipassword"] = root_password
        if ssh_keys:
            config_updates["sshkeys"] = ssh_keys
        if config_updates:
            try:
                proxmox.api.nodes(node).qemu(vmid).config.set(**config_updates)
            except ProxmoxClientError as exc:
                raise VpsServiceError(f"Reinstall config update failed: {exc}") from exc

        # Start the VM
        try:
            await proxmox.start_vm(node, vmid)
        except ProxmoxClientError as exc:
            raise VpsServiceError(f"Cannot start VM after reinstall: {exc}") from exc

        # Update DB record
        if ostemplate:
            instance.ostemplate = ostemplate
        if iso_image:
            instance.iso_image = iso_image
        if root_password:
            instance.root_password = root_password
        if ssh_keys:
            instance.ssh_keys = ssh_keys
        instance.power_status = VpsPowerStatus.RUNNING
        instance.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(instance)

        logger.info("Reinstalled OS on instance %s (VMID=%d)", instance_id, vmid)
        return instance

    # ------------------------------------------------------------------
    # Delete / decomission
    # ------------------------------------------------------------------
    async def decommission(self, instance_id: UUID) -> None:
        """Destroy the VM on Proxmox and remove the database record."""
        instance = await self.get_instance(instance_id)
        proxmox = await self._get_proxmox()

        if instance.proxmox_vmid is not None:
            try:
                await proxmox.delete_vm(instance.proxmox_node, instance.proxmox_vmid)
            except ProxmoxVMNotFoundError:
                logger.warning(
                    "VM %d already gone on Proxmox, removing DB record.",
                    instance.proxmox_vmid,
                )
            except ProxmoxClientError as exc:
                logger.error("Failed to destroy VM %d: %s", instance.proxmox_vmid, exc)
                raise VpsServiceError(f"VM destruction failed: {exc}") from exc

        await self.db.delete(instance)
        await self.db.commit()
        logger.info("Decommissioned VPS instance %s", instance_id)

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------
    async def create_snapshot(
        self,
        instance_id: UUID,
        snapshot_name: str,
        description: str | None = None,
        include_ram: bool = False,
    ) -> VpsSnapshot:
        instance = await self.get_instance(instance_id)
        proxmox = await self._get_proxmox()
        vmid = instance.proxmox_vmid
        node = instance.proxmox_node

        if vmid is None:
            raise VpsInvalidStateError("Instance has no VMID.")

        try:
            task = await proxmox.create_snapshot(
                node, vmid, snapshot_name, description, include_ram
            )
        except ProxmoxClientError as exc:
            raise VpsSnapshotError(
                f"Snapshot creation failed on VM {vmid}: {exc}"
            ) from exc

        if not task.success:
            raise VpsSnapshotError(
                f"Snapshot task failed: {task.exitstatus}, upid={task.upid}"
            )

        # Fetch snapshot details from Proxmox
        snap_info: ProxmoxSnapshotInfo | None = None
        try:
            snaps = await proxmox.list_snapshots(vmid, node)
            for s in snaps:
                if s.name == snapshot_name:
                    snap_info = s
                    break
        except ProxmoxClientError:
            logger.warning("Could not retrieve snapshot info after creation.")

        # Create DB record
        snapshot = VpsSnapshot(
            id=uuid4(),
            vps_instance_id=instance.id,
            snapshot_name=snapshot_name,
            description=description,
            size_bytes=snap_info.size_bytes if snap_info else None,
            is_ram_included=include_ram,
            snapshot_taken_at=datetime.now(timezone.utc),
        )
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)

        logger.info(
            "Created snapshot '%s' on instance %s (VMID=%d)",
            snapshot_name,
            instance_id,
            vmid,
        )
        return snapshot

    async def delete_snapshot(self, instance_id: UUID, snapshot_name: str) -> None:
        instance = await self.get_instance(instance_id)
        proxmox = await self._get_proxmox()
        vmid = instance.proxmox_vmid
        node = instance.proxmox_node

        if vmid is None:
            raise VpsInvalidStateError("Instance has no VMID.")

        # Delete on Proxmox
        try:
            await proxmox.delete_snapshot(node, vmid, snapshot_name)
        except ProxmoxClientError as exc:
            raise VpsSnapshotError(f"Failed to delete snapshot '{snapshot_name}': {exc}") from exc

        # Delete DB record
        stmt = select(VpsSnapshot).where(
            VpsSnapshot.vps_instance_id == instance.id,
            VpsSnapshot.snapshot_name == snapshot_name,
        )
        result = await self.db.execute(stmt)
        snap_record = result.scalar_one_or_none()
        if snap_record:
            await self.db.delete(snap_record)
            await self.db.commit()

        logger.info(
            "Deleted snapshot '%s' on instance %s (VMID=%d)",
            snapshot_name,
            instance_id,
            vmid,
        )

    async def rollback_snapshot(
        self, instance_id: UUID, snapshot_name: str, start_after: bool = True
    ) -> ProxmoxTaskResult:
        instance = await self.get_instance(instance_id)
        proxmox = await self._get_proxmox()
        vmid = instance.proxmox_vmid
        node = instance.proxmox_node

        if vmid is None:
            raise VpsInvalidStateError("Instance has no VMID.")

        try:
            task = await proxmox.rollback_snapshot(node, vmid, snapshot_name, start_after)
        except ProxmoxClientError as exc:
            raise VpsSnapshotError(f"Rollback failed: {exc}") from exc

        # Update power status after rollback
        instance.power_status = VpsPowerStatus.RUNNING if start_after else VpsPowerStatus.STOPPED
        instance.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        logger.info(
            "Rolled back to snapshot '%s' on instance %s (VMID=%d)",
            snapshot_name,
            instance_id,
            vmid,
        )
        return task

    async def list_snapshots(self, instance_id: UUID) -> list[VpsSnapshot]:
        stmt = (
            select(VpsSnapshot)
            .where(VpsSnapshot.vps_instance_id == instance_id)
            .order_by(VpsSnapshot.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Console / VNC
    # ------------------------------------------------------------------
    async def get_vnc_console(self, instance_id: UUID) -> dict[str, Any]:
        instance = await self.get_instance(instance_id)
        proxmox = await self._get_proxmox()
        vmid = instance.proxmox_vmid
        node = instance.proxmox_node

        if vmid is None:
            raise VpsInvalidStateError("Instance has no VMID.")

        try:
            vnc = await proxmox.get_vnc_proxy(vmid, node)
            ws = await proxmox.get_vnc_websocket(vmid, node)
        except ProxmoxClientError as exc:
            raise VpsConsoleError(f"Failed to get VNC console: {exc}") from exc

        return {
            "vmid": vmid,
            "node": node,
            "port": vnc.get("port", 0),
            "ticket": vnc.get("ticket", ""),
            "websocket_path": ws.get("path", f"/websockify/?port={vnc.get('port')}&token={vnc.get('ticket')}"),
        }

    # ------------------------------------------------------------------
    # Clone
    # ------------------------------------------------------------------
    async def clone(
        self,
        instance_id: UUID,
        new_service_id: UUID,
        new_name: str | None = None,
        storage: str = "local-lvm",
        full_clone: bool = True,
        start: bool = True,
    ) -> VpsInstance:
        """Clone an existing VM to create a new VPS instance."""
        source = await self.get_instance(instance_id)
        proxmox = await self._get_proxmox()

        if source.proxmox_vmid is None:
            raise VpsInvalidStateError("Source instance has no VMID.")

        new_vmid = await self._next_available_vmid(proxmox, source.proxmox_node)
        name = new_name or f"bluehub-clone-{str(new_service_id)[:8]}"

        try:
            task = await proxmox.clone_vm(
                node=source.proxmox_node,
                template_vmid=source.proxmox_vmid,
                new_vmid=new_vmid,
                name=name,
                storage=storage,
                full_clone=full_clone,
            )
        except ProxmoxClientError as exc:
            raise VpsProvisioningError(f"Clone failed: {exc}") from exc

        if not task.success:
            raise VpsProvisioningError(f"Clone task failed: {task.exitstatus}")

        # Start the clone if requested
        if start:
            try:
                await proxmox.start_vm(source.proxmox_node, new_vmid)
            except ProxmoxClientError as exc:
                logger.warning("Could not start cloned VM %d: %s", new_vmid, exc)

        # Create new DB record
        clone = VpsInstance(
            id=uuid4(),
            service_id=new_service_id,
            proxmox_node=source.proxmox_node,
            proxmox_vmid=new_vmid,
            cores=source.cores,
            memory_mb=source.memory_mb,
            disk_gb=source.disk_gb,
            storage_pool=storage,
            network_bridge=source.network_bridge,
            network_model=source.network_model,
            ostype=source.ostype,
            ostemplate=source.ostemplate,
            iso_image=source.iso_image,
            power_status=VpsPowerStatus.RUNNING if start else VpsPowerStatus.STOPPED,
            extra_config=source.extra_config,
            notes=f"Cloned from instance {instance_id}",
        )
        self.db.add(clone)
        await self.db.commit()
        await self.db.refresh(clone)

        logger.info(
            "Cloned instance %s -> %s (new VMID=%d)",
            instance_id,
            clone.id,
            new_vmid,
        )
        return clone


__all__ = [
    "VpsServiceError",
    "VpsProvisioningError",
    "VpsPowerActionError",
    "VpsSnapshotError",
    "VpsResizeError",
    "VpsConsoleError",
    "VpsInstanceNotFoundError",
    "VpsInvalidStateError",
    "VpsTrafficSummary",
    "VpsInstanceService",
]