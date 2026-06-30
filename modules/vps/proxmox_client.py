"""
BlueHub Proxmox Client
======================
Connection manager and API client for Proxmox VE using proxmoxer.
Provides a circuit-breaker-protected, connection-pooled ProxmoxAPI wrapper
with structured error handling and node/VM query helpers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

try:
    import backoff  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - only when deps not installed
    backoff = None  # type: ignore[assignment]
try:
    import pybreaker  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - only when deps not installed
    pybreaker = None  # type: ignore[assignment]
try:
    from proxmoxer import (  # type: ignore[import-untyped]
        AuthenticationError,
        ProxmoxAPI,
        ResourceException,
    )
    from proxmoxer.backends import https  # type: ignore[import-untyped]
except ImportError as e:  # pragma: no cover - only when deps not installed
    raise ImportError(
        "proxmoxer is required for VPS Proxmox client. "
        "Install with: pip install proxmoxer"
    ) from e

from core.config import settings

logger = logging.getLogger("bluehub.modules.vps.proxmox")

# ------------------------------------------------------------------
# Circuit breaker for Proxmox connection resilience
# ------------------------------------------------------------------
_proxmox_breaker = (
    pybreaker.CircuitBreaker(
        fail_max=5,
        reset_timeout=60,
        name="proxmox_api",
        exclude=[AuthenticationError],
    )
    if pybreaker is not None
    else None
)


# ------------------------------------------------------------------
# Custom Exceptions
# ------------------------------------------------------------------
class ProxmoxClientError(Exception):
    """Base exception for Proxmox client failures."""


class ProxmoxConnectionError(ProxmoxClientError):
    """Cannot establish connection to Proxmox host."""


class ProxmoxAuthenticationError(ProxmoxClientError):
    """Proxmox authentication failed (invalid credentials or expired token)."""


class ProxmoxNodeNotFoundError(ProxmoxClientError):
    """Requested Proxmox node does not exist."""


class ProxmoxVMNotFoundError(ProxmoxClientError):
    """Requested VM/CT does not exist on the target node."""


class ProxmoxTaskError(ProxmoxClientError):
    """A Proxmox asynchronous task (UPID) failed."""


class ProxmoxResourceBusyError(ProxmoxClientError):
    """Requested operation cannot be performed because the resource is locked."""


class ProxmoxValidationError(ProxmoxClientError):
    """Invalid parameters passed to Proxmox API."""


# ------------------------------------------------------------------
# Data transfer objects
# ------------------------------------------------------------------
@dataclass(slots=True)
class ProxmoxNodeInfo:
    """Summary information about a Proxmox node."""

    name: str
    status: str  # 'online' | 'offline'
    cpu_cores: int
    cpu_usage_pct: float
    memory_total_bytes: int
    memory_used_bytes: int
    memory_free_bytes: int
    uptime_seconds: int
    cpu_model: str = ""


@dataclass(slots=True)
class ProxmoxVMInfo:
    """Summary information about a VM from Proxmox."""

    vmid: int
    name: str
    node: str
    status: str  # 'running' | 'stopped' | 'paused' | 'suspended'
    cpus: int
    max_memory_bytes: int
    memory_used_bytes: int
    max_disk_bytes: int
    uptime_seconds: int
    template_os: str | None = None
    vnc_port: int | None = None
    networks: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProxmoxSnapshotInfo:
    """Summary information about a VM snapshot from Proxmox."""

    name: str
    description: str | None
    parent: str | None
    snapshot_time: int  # Unix timestamp
    vmstate: bool  # RAM included
    size_bytes: int | None = None


@dataclass(slots=True)
class ProxmoxTaskResult:
    """Standardised result of a Proxmox async task."""

    upid: str
    node: str
    status: str  # 'running' | 'stopped'
    exitstatus: str | None = None  # 'OK' on success
    success: bool = False


# ------------------------------------------------------------------
# Helper: extract node from a VMID if not explicitly provided
# ------------------------------------------------------------------
async def _resolve_node(proxmox: ProxmoxAPI, vmid: int, node: str | None) -> str:
    """Find which cluster node a VMID lives on when node is not specified."""
    if node:
        return node
    # Cluster-wide VM search
    for cluster_node in proxmox.nodes.get():
        try:
            proxmox.nodes(cluster_node["node"]).qemu(vmid).status.current.get()
            return cluster_node["node"]
        except ResourceException:
            continue
    raise ProxmoxVMNotFoundError(f"VMID {vmid} not found on any cluster node.")


# ------------------------------------------------------------------
# ProxmoxClient – the main connection manager
# ------------------------------------------------------------------
class ProxmoxClient:
    """
    Thread-safe Proxmox API client with connection caching and retry logic.

    Usage::

        async with ProxmoxClient() as proxmox:
            info = await proxmox.get_vm_status(100)
    """

    __slots__ = (
        "_api",
        "_host",
        "_user",
        "_token_name",
        "_token_value",
        "_verify_ssl",
        "_timeout",
    )

    def __init__(
        self,
        host: str | None = None,
        user: str | None = None,
        token_name: str | None = None,
        token_value: str | None = None,
        verify_ssl: bool | None = None,
        timeout: int = 30,
    ) -> None:
        """
        Parameters
        ----------
        host:
            Proxmox API host (e.g. '192.168.1.100:8006').  Falls back to
            ``settings.PROXMOX_HOST``.
        user:
            Proxmox API user (e.g. 'root@pam').  Falls back to
            ``settings.PROXMOX_USER``.
        token_name:
            API token name. Falls back to ``settings.PROXMOX_TOKEN_NAME``.
        token_value:
            API token secret. Falls back to ``settings.PROXMOX_TOKEN_VALUE``.
        verify_ssl:
            Verify SSL certificates. Defaults to ``settings.PROXMOX_VERIFY_SSL``
            (or *True* if the setting is absent).
        timeout:
            HTTP request timeout in seconds.
        """
        self._host = host or getattr(settings, "PROXMOX_HOST", "127.0.0.1:8006")
        self._user = user or getattr(settings, "PROXMOX_USER", "root@pam")
        self._token_name = token_name or getattr(settings, "PROXMOX_TOKEN_NAME", "")
        self._token_value = token_value or getattr(settings, "PROXMOX_TOKEN_VALUE", "")
        self._verify_ssl = (
            verify_ssl
            if verify_ssl is not None
            else getattr(settings, "PROXMOX_VERIFY_SSL", True)
        )
        self._timeout = timeout
        self._api: ProxmoxAPI | None = None

    # -- connection lifecycle ------------------------------------------------

    async def __aenter__(self) -> ProxmoxClient:
        await self.connect()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.disconnect()

    async def connect(self) -> None:
        """Establish connection to Proxmox host and validate credentials."""
        if self._api is not None:
            return
        try:
            self._api = await self._create_api_connection()
            # Validate immediately by listing nodes
            self._api.nodes.get()
            logger.info("Connected to Proxmox host %s", self._host)
        except AuthenticationError as exc:
            logger.error("Proxmox authentication failed: %s", exc)
            raise ProxmoxAuthenticationError(
                f"Authentication failed for user {self._user}"
            ) from exc
        except Exception as exc:
            logger.error("Proxmox connection failed to %s: %s", self._host, exc)
            raise ProxmoxConnectionError(
                f"Cannot connect to Proxmox host {self._host}: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        self._api = None

    async def _create_api_connection(self) -> ProxmoxAPI:
        """Build a fresh proxmoxer connection with current parameters."""

        @backoff.on_exception(
            backoff.expo,
            (ProxmoxConnectionError,),
            max_tries=3,
            max_time=30,
            logger=logger,
        )
        @_proxmox_breaker
        def _connect_sync() -> ProxmoxAPI:
            backend = https.ProxmoxHttpSession
            return ProxmoxAPI(
                self._host,
                user=self._user,
                token_name=self._token_name,
                token_value=self._token_value,
                verify_ssl=self._verify_ssl,
                timeout=self._timeout,
                backend=backend,
            )

        # proxmoxer is synchronous under the hood; run in thread
        import asyncio

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _connect_sync)

    # -- raw ProxmoxAPI access ----------------------------------------------

    @property
    def api(self) -> ProxmoxAPI:
        """Direct proxmoxer.ProxmoxAPI instance (requires active connection)."""
        if self._api is None:
            raise ProxmoxConnectionError("ProxmoxClient is not connected.")
        return self._api

    # -- node helpers -------------------------------------------------------

    async def list_nodes(self) -> list[ProxmoxNodeInfo]:
        nodes_raw = self.api.nodes.get()
        return [_parse_node_info(n) for n in nodes_raw]

    async def get_node(self, node: str) -> ProxmoxNodeInfo:
        try:
            nodes = self.api.nodes.get()
        except ResourceException as exc:
            raise ProxmoxNodeNotFoundError(f"Node '{node}' not available.") from exc
        for n in nodes:
            if n["node"] == node:
                return _parse_node_info(n)
        raise ProxmoxNodeNotFoundError(f"Node '{node}' not found in cluster.")

    # -- VM lifecycle -------------------------------------------------------

    async def create_vm(
        self,
        node: str,
        vmid: int,
        name: str,
        ostemplate: str | None = None,
        cores: int = 1,
        memory_mb: int = 1024,
        disk_gb: int = 10,
        storage: str = "local-lvm",
        net0: str = "virtio,bridge=vmbr0",
        ipconfig0: str | None = None,
        sshkeys: str | None = None,
        start: bool = True,
        extra: dict[str, Any] | None = None,
    ) -> ProxmoxTaskResult:
        """
        Create a new QEMU/KVM virtual machine.

        Parameters
        ----------
        extra:
            Additional key-value pairs passed directly to the Proxmox create
            API (e.g. ``{"ciuser": "root", "cipassword": "secret"}``).
        """
        config: dict[str, Any] = {
            "vmid": vmid,
            "name": name,
            "cores": cores,
            "memory": memory_mb,
            "net0": net0,
            "scsihw": "virtio-scsi-single",
            "agent": "enabled=1",
            "ostype": "l26",
            "start": start,
        }
        if ostemplate:
            config["ostemplate"] = ostemplate
        if disk_gb > 0:
            config["scsi0"] = f"{storage}:{disk_gb}"
        if ipconfig0:
            config["ipconfig0"] = ipconfig0
        if sshkeys:
            config["sshkeys"] = sshkeys
        if extra:
            config.update(extra)
        return await self._execute_task(node, "qemu", "create", **config)

    async def clone_vm(
        self,
        node: str,
        template_vmid: int,
        new_vmid: int,
        name: str,
        storage: str = "local-lvm",
        full_clone: bool = True,
        extra: dict[str, Any] | None = None,
    ) -> ProxmoxTaskResult:
        """Clone an existing VM (template) to a new VM."""
        config: dict[str, Any] = {
            "newid": new_vmid,
            "name": name,
            "storage": storage,
            "full": full_clone,
        }
        if extra:
            config.update(extra)
        return await self._execute_task(
            node, "qemu", "clone", vmid=template_vmid, **config
        )

    async def delete_vm(
        self,
        node: str,
        vmid: int,
        destroy_unreferenced: bool = True,
        purge: bool = True,
    ) -> ProxmoxTaskResult:
        """Destroy a VM and optionally purge from job configurations."""
        return await self._execute_task(
            node,
            "qemu",
            "destroy",
            vmid=vmid,
            destroy_unreferenced_disks=destroy_unreferenced,
            purge=purge,
        )

    async def start_vm(self, node: str, vmid: int) -> ProxmoxTaskResult:
        self._require_stopped(node, vmid)
        return await self._execute_task(node, "qemu", "start", vmid=vmid)

    async def stop_vm(
        self, node: str, vmid: int, timeout_seconds: int = 60
    ) -> ProxmoxTaskResult:
        self._require_running(node, vmid)
        return await self._execute_task(
            node, "qemu", "stop", vmid=vmid, timeout=timeout_seconds
        )

    async def shutdown_vm(
        self, node: str, vmid: int, timeout_seconds: int = 60
    ) -> ProxmoxTaskResult:
        """
        Graceful ACPI shutdown. Falls back to ``stop`` if the guest agent
        does not respond within *timeout_seconds*.
        """
        return await self._execute_task(
            node, "qemu", "shutdown", vmid=vmid, timeout=timeout_seconds
        )

    async def reboot_vm(self, node: str, vmid: int) -> ProxmoxTaskResult:
        self._require_running(node, vmid)
        return await self._execute_task(node, "qemu", "reboot", vmid=vmid)

    async def reset_vm(self, node: str, vmid: int) -> ProxmoxTaskResult:
        """Hard reset (like pressing the physical reset button)."""
        return await self._execute_task(node, "qemu", "reset", vmid=vmid)

    async def suspend_vm(self, node: str, vmid: int) -> ProxmoxTaskResult:
        """Suspend to disk (hibernate)."""
        self._require_running(node, vmid)
        return await self._execute_task(node, "qemu", "suspend", vmid=vmid)

    async def resume_vm(self, node: str, vmid: int) -> ProxmoxTaskResult:
        self._require_suspended(node, vmid)
        return await self._execute_task(node, "qemu", "resume", vmid=vmid)

    # -- VM querying --------------------------------------------------------

    async def get_vm_status(self, vmid: int, node: str | None = None) -> ProxmoxVMInfo:
        node = await _resolve_node(self.api, vmid, node)
        try:
            status = self.api.nodes(node).qemu(vmid).status.current.get()
        except ResourceException as exc:
            raise ProxmoxVMNotFoundError(f"VM {vmid} not found on node '{node}'.") from exc
        return _parse_vm_info(vmid, node, status)

    async def get_vm_config(self, vmid: int, node: str | None = None) -> dict[str, Any]:
        node = await _resolve_node(self.api, vmid, node)
        try:
            return self.api.nodes(node).qemu(vmid).config.get()
        except ResourceException as exc:
            raise ProxmoxVMNotFoundError(f"VM {vmid} not found on node '{node}'.") from exc

    async def list_vms(
        self, node: str | None = None
    ) -> list[ProxmoxVMInfo]:
        nodes = [node] if node else [n["node"] for n in self.api.nodes.get()]
        result: list[ProxmoxVMInfo] = []
        for n in nodes:
            try:
                vms = self.api.nodes(n).qemu.get()
            except ResourceException:
                continue
            for vm in vms:
                result.append(
                    _parse_vm_info(vm["vmid"], n, vm.get("status", "unknown"))
                )
        return result

    # -- snapshot operations ------------------------------------------------

    async def create_snapshot(
        self,
        node: str,
        vmid: int,
        snapshot_name: str,
        description: str | None = None,
        include_ram: bool = False,
    ) -> ProxmoxTaskResult:
        return await self._execute_task(
            node,
            "qemu",
            "snapshot",
            vmid=vmid,
            snapname=snapshot_name,
            description=description or "",
            vmstate=include_ram,
        )

    async def delete_snapshot(
        self,
        node: str,
        vmid: int,
        snapshot_name: str,
    ) -> ProxmoxTaskResult:
        return await self._execute_task(
            node, "qemu", "delsnapshot", vmid=vmid, snapname=snapshot_name
        )

    async def rollback_snapshot(
        self,
        node: str,
        vmid: int,
        snapshot_name: str,
        start_after: bool = False,
    ) -> ProxmoxTaskResult:
        return await self._execute_task(
            node,
            "qemu",
            "rollback",
            vmid=vmid,
            snapname=snapshot_name,
            start=start_after,
        )

    async def list_snapshots(
        self, vmid: int, node: str | None = None
    ) -> list[ProxmoxSnapshotInfo]:
        node = await _resolve_node(self.api, vmid, node)
        try:
            raw = self.api.nodes(node).qemu(vmid).snapshot.get()
        except ResourceException:
            return []
        return [
            ProxmoxSnapshotInfo(
                name=s["name"],
                description=s.get("description"),
                parent=s.get("parent"),
                snapshot_time=s.get("snaptime", 0),
                vmstate=s.get("vmstate", False),
                size_bytes=s.get("size"),
            )
            for s in raw
        ]

    async def get_snapshot_config(
        self, vmid: int, snapshot_name: str, node: str | None = None
    ) -> dict[str, Any]:
        node = await _resolve_node(self.api, vmid, node)
        return self.api.nodes(node).qemu(vmid).snapshot(snapshot_name).config.get()

    # -- resource update helpers --------------------------------------------

    async def resize_vm(
        self,
        node: str,
        vmid: int,
        cores: int | None = None,
        memory_mb: int | None = None,
        balloon: int | None = None,
    ) -> ProxmoxTaskResult | None:
        """
        Resize CPU cores and/or memory for a running VM.
        Uses the hot-plug ``resize`` endpoint when available; otherwise
        updates config and suggests a reboot.
        """
        # Memory / balloon
        if memory_mb is not None:
            self.api.nodes(node).qemu(vmid).resize.set(
                disk="memory", size=f"{memory_mb}M"
            )
            # Also update config for persistent change
            self.api.nodes(node).qemu(vmid).config.set(memory=memory_mb)
        # CPU cores
        if cores is not None:
            self.api.nodes(node).qemu(vmid).config.set(cores=cores)
        # Optional balloon
        if balloon is not None:
            self.api.nodes(node).qemu(vmid).config.set(balloon=balloon)
        return None  # config-set calls are synchronous

    async def resize_disk(
        self,
        node: str,
        vmid: int,
        disk: str,
        size_gb: int,
    ) -> ProxmoxTaskResult:
        """Resize a virtual disk (e.g. 'scsi0')."""
        return await self._execute_task(
            node,
            "qemu",
            "resize",
            vmid=vmid,
            disk=disk,
            size=f"{size_gb}G",
        )

    # -- VNC / console access -----------------------------------------------

    async def get_vnc_proxy(
        self, vmid: int, node: str | None = None
    ) -> dict[str, Any]:
        """Return VNC proxy ticket and connection details."""
        node = await _resolve_node(self.api, vmid, node)
        return self.api.nodes(node).qemu(vmid).vncproxy.post()

    async def get_vnc_websocket(
        self, vmid: int, node: str | None = None, port: int = 0
    ) -> dict[str, Any]:
        """Return noVNC websocket connection info."""
        node = await _resolve_node(self.api, vmid, node)
        return self.api.nodes(node).qemu(vmid).vncwebsocket(port=port).get()

    # -- internal helpers ---------------------------------------------------

    async def _execute_task(
        self, node: str, resource: str, action: str, **params: Any
    ) -> ProxmoxTaskResult:
        """
        Execute a Proxmox API action that returns an UPID, wait for
        completion, and return a structured result.
        """
        try:
            handler = getattr(self.api.nodes(node), resource)
            method = getattr(handler(vmid=params.pop("vmid", None)), action)
            upid = method.post(**params)
        except ResourceException as exc:
            status_code = getattr(exc, "status_code", 500)
            if status_code == 409 or "already running" in str(exc).lower():
                raise ProxmoxResourceBusyError(
                    f"Resource busy: {resource}/{action} on node '{node}'"
                ) from exc
            if status_code == 404:
                raise ProxmoxVMNotFoundError(
                    f"VM or resource not found for {resource}/{action} on node '{node}'"
                ) from exc
            raise ProxmoxClientError(
                f"Proxmox API error ({status_code}): {exc}"
            ) from exc
        # Wait for task completion
        status = self.api.nodes(node).tasks(upid).status.get()
        return ProxmoxTaskResult(
            upid=upid,
            node=node,
            status=status.get("status", "unknown"),
            exitstatus=status.get("exitstatus"),
            success=status.get("exitstatus") == "OK",
        )

    async def wait_for_task(
        self, node: str, upid: str, poll_interval: float = 1.0, timeout: float = 300.0
    ) -> ProxmoxTaskResult:
        """Wait for a Proxmox UPID task to finish, with timeout."""
        import asyncio
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                status = self.api.nodes(node).tasks(upid).status.get()
            except ResourceException:
                await asyncio.sleep(poll_interval)
                continue
            if status.get("status") == "stopped":
                return ProxmoxTaskResult(
                    upid=upid,
                    node=node,
                    status="stopped",
                    exitstatus=status.get("exitstatus"),
                    success=status.get("exitstatus") == "OK",
                )
            await asyncio.sleep(poll_interval)
        raise ProxmoxTaskError(f"Task {upid} did not complete within {timeout}s.")

    # -- status guards ------------------------------------------------------

    def _require_running(self, node: str, vmid: int) -> None:
        status = self.api.nodes(node).qemu(vmid).status.current.get()
        if status.get("status") != "running":
            raise ProxmoxResourceBusyError(
                f"VM {vmid} must be running for this operation (current: {status.get('status')})"
            )

    def _require_stopped(self, node: str, vmid: int) -> None:
        status = self.api.nodes(node).qemu(vmid).status.current.get()
        if status.get("status") != "stopped":
            raise ProxmoxResourceBusyError(
                f"VM {vmid} must be stopped for this operation (current: {status.get('status')})"
            )

    def _require_suspended(self, node: str, vmid: int) -> None:
        status = self.api.nodes(node).qemu(vmid).status.current.get()
        if status.get("status") != "suspended":
            raise ProxmoxResourceBusyError(
                f"VM {vmid} must be suspended to resume (current: {status.get('status')})"
            )


# ------------------------------------------------------------------
# Parsing helpers
# ------------------------------------------------------------------
def _parse_node_info(raw: dict[str, Any]) -> ProxmoxNodeInfo:
    return ProxmoxNodeInfo(
        name=raw.get("node", ""),
        status=raw.get("status", "unknown"),
        cpu_cores=raw.get("maxcpu", 0),
        cpu_usage_pct=round(raw.get("cpu", 0.0) * 100, 2),
        memory_total_bytes=raw.get("maxmem", 0),
        memory_used_bytes=raw.get("mem", 0),
        memory_free_bytes=raw.get("maxmem", 0) - raw.get("mem", 0),
        uptime_seconds=raw.get("uptime", 0),
        cpu_model=raw.get("cpuinfo", {}).get("model", ""),
    )


def _parse_vm_info(vmid: int, node: str, status: str | dict[str, Any]) -> ProxmoxVMInfo:
    if isinstance(status, str):
        status = {"status": status}
    return ProxmoxVMInfo(
        vmid=vmid,
        name=status.get("name", f"vm-{vmid}"),
        node=node,
        status=status.get("status", "unknown"),
        cpus=status.get("cpus", 0),
        max_memory_bytes=status.get("maxmem", 0),
        memory_used_bytes=status.get("mem", 0),
        max_disk_bytes=status.get("maxdisk", 0),
        uptime_seconds=status.get("uptime", 0),
        template_os=status.get("ostype"),
        vnc_port=status.get("vnc-port"),
    )


__all__ = [
    "ProxmoxClient",
    "ProxmoxClientError",
    "ProxmoxConnectionError",
    "ProxmoxAuthenticationError",
    "ProxmoxNodeNotFoundError",
    "ProxmoxVMNotFoundError",
    "ProxmoxTaskError",
    "ProxmoxResourceBusyError",
    "ProxmoxValidationError",
    "ProxmoxNodeInfo",
    "ProxmoxVMInfo",
    "ProxmoxSnapshotInfo",
    "ProxmoxTaskResult",
    "_resolve_node",
]
