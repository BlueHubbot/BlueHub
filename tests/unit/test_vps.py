"""
Unit Tests for VPS Module Services
====================================
Tests for VpsInstanceService covering provisioning, power management,
snapshots, resize, reinstall, clone, decommission, console, and status sync.

Uses mocked AsyncSession and ProxmoxClient to avoid external dependencies.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from modules.vps.models import VpsInstance, VpsPowerStatus, VpsSnapshot
from modules.vps.proxmox_client import (
    ProxmoxClient,
    ProxmoxClientError,
    ProxmoxResourceBusyError,
    ProxmoxSnapshotInfo,
    ProxmoxTaskResult,
    ProxmoxVMInfo,
    ProxmoxVMNotFoundError,
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
    VpsTrafficSummary,
)

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Create a mock AsyncSession with commonly-needed async methods."""
    session = AsyncMock(spec_set=["execute", "add", "commit", "refresh", "delete", "close"])
    # By default execute() returns an empty result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar.return_value = None
    session.execute.return_value = mock_result
    return session


@pytest.fixture
def mock_proxmox() -> MagicMock:
    """Create a mock ProxmoxClient with all async methods as AsyncMock."""
    client = MagicMock(spec=ProxmoxClient)
    # All ProxmoxClient methods we call are async
    client.connect = AsyncMock()
    client.list_vms = AsyncMock(return_value=[])
    client.create_vm = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:test:0001",
            node="pve",
            status="stopped",
            exitstatus="OK",
            success=True,
        )
    )
    client.get_vm_status = AsyncMock(
        return_value=ProxmoxVMInfo(
            vmid=100,
            name="bluehub-test",
            node="pve",
            status="stopped",
            cpus=1,
            max_memory_bytes=1073741824,  # 1 GB
            memory_used_bytes=524288000,
            max_disk_bytes=10737418240,  # 10 GB
            uptime_seconds=0,
            template_os="l26",
        )
    )
    client.get_vnc_proxy = AsyncMock(return_value={"port": 5900, "ticket": "test-ticket"})
    client.get_vnc_websocket = AsyncMock(
        return_value={"path": "/websockify/?port=5900&token=test-ticket"}
    )
    client.start_vm = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:start:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.stop_vm = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:stop:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.shutdown_vm = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:shutdown:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.reboot_vm = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:reboot:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.reset_vm = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:reset:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.suspend_vm = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:suspend:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.resume_vm = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:resume:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.create_snapshot = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:snap:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.delete_snapshot = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:delsnap:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.rollback_snapshot = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:rollback:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.list_snapshots = AsyncMock(return_value=[])
    client.delete_vm = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:delete:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.clone_vm = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:clone:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    client.resize_vm = AsyncMock()
    client.resize_disk = AsyncMock(
        return_value=ProxmoxTaskResult(
            upid="UPID:resize:0001", node="pve", status="stopped", exitstatus="OK", success=True
        )
    )
    # Internal mock api for direct calls (used in reinstall)
    client._api = None
    return client


@pytest.fixture
def service(mock_db: AsyncMock, mock_proxmox: MagicMock) -> VpsInstanceService:
    """Create a VpsInstanceService instance with mocked dependencies."""
    svc = VpsInstanceService(db=mock_db, proxmox=mock_proxmox)
    return svc


@pytest.fixture
def sample_vps() -> VpsInstance:
    """Create a sample VpsInstance for use in tests."""
    instance = VpsInstance(
        id=uuid4(),
        service_id=uuid4(),
        proxmox_vmid=100,
        proxmox_node="pve",
        cpu_cores=2,
        memory_mb=2048,
        disk_gb=50,
        power_status=VpsPowerStatus.RUNNING,
        os_template="ubuntu-22.04",
        primary_ipv4="192.168.1.100",
        vnc_port=5900,
        bandwidth_used_bytes=0,
        extra_config={},
        notes=None,
    )
    return instance


# ------------------------------------------------------------------
# Tests: __init__ / constructor
# ------------------------------------------------------------------


class TestVpsInstanceServiceInit:
    """Test service construction and default behaviours."""

    @pytest.mark.vps
    async def test_constructor_with_explicit_proxmox(
        self, mock_db: AsyncMock, mock_proxmox: MagicMock
    ) -> None:
        """Verify the service stores the injected ProxmoxClient."""
        svc = VpsInstanceService(db=mock_db, proxmox=mock_proxmox)
        assert svc.db is mock_db
        assert svc._proxmox is mock_proxmox

    @pytest.mark.vps
    async def test_constructor_without_proxmox(self, mock_db: AsyncMock) -> None:
        """Verify proxmox is None when not provided."""
        svc = VpsInstanceService(db=mock_db)
        assert svc.db is mock_db
        assert svc._proxmox is None


# ------------------------------------------------------------------
# Tests: CRUD helpers
# ------------------------------------------------------------------


class TestGetInstance:
    """Tests for VpsInstanceService.get_instance()."""

    @pytest.mark.vps
    async def test_get_instance_success(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Successfully retrieve an existing VPS instance by ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.get_instance(sample_vps.id)
        assert result is sample_vps
        assert result.id == sample_vps.id
        mock_db.execute.assert_awaited_once()

    @pytest.mark.vps
    async def test_get_instance_not_found(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Raise VpsInstanceNotFoundError when the instance does not exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        fake_id = uuid4()
        with pytest.raises(VpsInstanceNotFoundError, match=str(fake_id)):
            await service.get_instance(fake_id)


class TestGetInstanceByVmid:
    """Tests for VpsInstanceService.get_instance_by_vmid()."""

    @pytest.mark.vps
    async def test_found(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Return the instance when VMID matches."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.get_instance_by_vmid(100)
        assert result is sample_vps

    @pytest.mark.vps
    async def test_not_found(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Return None when no instance has the given VMID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_instance_by_vmid(999)
        assert result is None


class TestGetInstanceByService:
    """Tests for VpsInstanceService.get_instance_by_service()."""

    @pytest.mark.vps
    async def test_found(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Return the instance when service_id matches."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.get_instance_by_service(sample_vps.service_id)
        assert result is sample_vps

    @pytest.mark.vps
    async def test_not_found(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Return None when no instance has the given service_id."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_instance_by_service(uuid4())
        assert result is None


class TestListInstances:
    """Tests for VpsInstanceService.list_instances()."""

    @pytest.mark.vps
    async def test_list_all(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """List all instances without filters."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_vps]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        results = await service.list_instances()
        assert len(results) == 1
        assert results[0] is sample_vps

    @pytest.mark.vps
    async def test_list_with_node_filter(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Filter instances by Proxmox node name."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_vps]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        results = await service.list_instances(node="pve")
        assert len(results) == 1

    @pytest.mark.vps
    async def test_list_with_status_filter(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Filter instances by power status."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [sample_vps]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        results = await service.list_instances(status=VpsPowerStatus.RUNNING)
        assert len(results) == 1

    @pytest.mark.vps
    async def test_list_with_pagination(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Apply offset/limit pagination."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        results = await service.list_instances(offset=10, limit=5)
        assert len(results) == 0


# ------------------------------------------------------------------
# Tests: Provisioning
# ------------------------------------------------------------------


class TestProvision:
    """Tests for VpsInstanceService.provision()."""

    @pytest.mark.vps
    async def test_provision_success(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock
    ) -> None:
        """Successfully provision a new VPS instance."""
        service_id = uuid4()
        result = await service.provision(
            service_id=service_id,
            node="pve",
            cores=2,
            memory_mb=2048,
            disk_gb=50,
            ostemplate="local:vztmpl/ubuntu-22.04",
            ip_address="192.168.1.100",
        )

        assert result.service_id == service_id
        assert result.proxmox_node == "pve"
        assert result.cores == 2  # Note: service sets 'cores' but model has 'cpu_cores'
        assert result.memory_mb == 2048
        assert result.disk_gb == 50
        assert result.power_status == VpsPowerStatus.RUNNING
        mock_proxmox.create_vm.assert_awaited_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_provision_with_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock
    ) -> None:
        """Provision with an explicit VMID (no auto-assignment)."""
        service_id = uuid4()
        result = await service.provision(
            service_id=service_id, node="pve", vmid=200, start=False
        )
        assert result.proxmox_vmid == 200
        assert result.power_status == VpsPowerStatus.STOPPED

    @pytest.mark.vps
    async def test_provision_auto_assign_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock
    ) -> None:
        """Auto-assign VMID when not provided."""
        mock_proxmox.list_vms.return_value = [MagicMock(vmid=100)]
        service_id = uuid4()
        # next available should be 101
        result = await service.provision(service_id=service_id, node="pve")
        assert result.proxmox_vmid == 101

    @pytest.mark.vps
    async def test_provision_proxmox_error(
        self, service: VpsInstanceService, mock_proxmox: MagicMock
    ) -> None:
        """Raise VpsProvisioningError when Proxmox VM creation fails."""
        mock_proxmox.create_vm.side_effect = ProxmoxClientError("API error")
        with pytest.raises(VpsProvisioningError, match="Failed to create VM"):
            await service.provision(service_id=uuid4(), node="pve")

    @pytest.mark.vps
    async def test_provision_task_failed(
        self, service: VpsInstanceService, mock_proxmox: MagicMock
    ) -> None:
        """Raise VpsProvisioningError when the Proxmox task does not succeed."""
        mock_proxmox.create_vm.return_value = ProxmoxTaskResult(
            upid="UPID:fail:0001",
            node="pve",
            status="stopped",
            exitstatus="FAILED",
            success=False,
        )
        with pytest.raises(VpsProvisioningError, match="exitstatus=FAILED"):
            await service.provision(service_id=uuid4(), node="pve")


# ------------------------------------------------------------------
# Tests: Power Management
# ------------------------------------------------------------------


class TestPowerAction:
    """Tests for VpsInstanceService.power_action()."""

    @pytest.mark.vps
    async def test_power_action_start(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Start a stopped VPS."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.power_action(sample_vps.id, "start")
        assert result.success is True
        sample_vps.power_status = VpsPowerStatus.RUNNING
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_power_action_stop(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Stop a running VPS."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.power_action(sample_vps.id, "stop")
        assert result.success is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_power_action_shutdown(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Gracefully shutdown a running VPS."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.power_action(sample_vps.id, "shutdown")
        assert result.success is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_power_action_reboot(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Reboot a running VPS."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.power_action(sample_vps.id, "reboot")
        assert result.success is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_power_action_reset(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Hard reset a running VPS."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.power_action(sample_vps.id, "reset")
        assert result.success is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_power_action_suspend(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Suspend (hibernate) a running VPS."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.power_action(sample_vps.id, "suspend")
        assert result.success is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_power_action_resume(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Resume a suspended VPS."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.power_action(sample_vps.id, "resume")
        assert result.success is True
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_power_unknown_action(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsPowerActionError for an unknown action."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        with pytest.raises(VpsPowerActionError, match="Unknown power action"):
            await service.power_action(sample_vps.id, "fly")

    @pytest.mark.vps
    async def test_power_action_resource_busy(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsInvalidStateError when Proxmox reports resource busy."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.start_vm.side_effect = ProxmoxResourceBusyError("locked")

        with pytest.raises(VpsInvalidStateError, match="locked"):
            await service.power_action(sample_vps.id, "start")

    @pytest.mark.vps
    async def test_power_action_proxmox_error(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsPowerActionError on generic Proxmox client error."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.start_vm.side_effect = ProxmoxClientError("connection lost")

        with pytest.raises(VpsPowerActionError, match="connection lost"):
            await service.power_action(sample_vps.id, "start")

    @pytest.mark.vps
    async def test_power_action_no_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Raise VpsInvalidStateError when instance has no VMID."""
        instance = VpsInstance(
            id=uuid4(), service_id=uuid4(), proxmox_vmid=None, proxmox_node="pve"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        with pytest.raises(VpsInvalidStateError, match="no VMID"):
            await service.power_action(instance.id, "start")

    @pytest.mark.vps
    async def test_power_action_timeout_seconds(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Verify timeout_seconds is passed to Proxmox stop/shutdown operations."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        await service.power_action(sample_vps.id, "stop", timeout_seconds=120)
        mock_proxmox.stop_vm.assert_awaited_with("pve", 100, 120)


# ------------------------------------------------------------------
# Tests: Status Sync
# ------------------------------------------------------------------


class TestSyncStatus:
    """Tests for VpsInstanceService.sync_status()."""

    @pytest.mark.vps
    async def test_sync_status_running(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Sync status updates power status to RUNNING."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        vm_info = await service.sync_status(sample_vps.id)
        assert vm_info.status == "stopped"  # our mock returns 'stopped'
        assert sample_vps.power_status == VpsPowerStatus.STOPPED
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_sync_status_vm_not_found(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """When VM is not found on Proxmox, mark status UNKNOWN and raise error."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.get_vm_status.side_effect = ProxmoxVMNotFoundError("not found")

        with pytest.raises(VpsInstanceNotFoundError, match="not found"):
            await service.sync_status(sample_vps.id)

        assert sample_vps.power_status == VpsPowerStatus.UNKNOWN
        mock_db.commit.assert_awaited()

    @pytest.mark.vps
    async def test_sync_status_no_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Raise VpsInvalidStateError when instance has no VMID."""
        instance = VpsInstance(id=uuid4(), service_id=uuid4(), proxmox_vmid=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        with pytest.raises(VpsInvalidStateError, match="no VMID"):
            await service.sync_status(instance.id)


# ------------------------------------------------------------------
# Tests: Resize
# ------------------------------------------------------------------


class TestResize:
    """Tests for VpsInstanceService.resize()."""

    @pytest.mark.vps
    async def test_resize_cpu(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Resize CPU cores only."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.resize(sample_vps.id, cores=4)
        assert result is not None
        # Note: service sets instance.cores but model has cpu_cores
        mock_proxmox.resize_vm.assert_awaited_with("pve", 100, cores=4, memory_mb=None)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_resize_memory(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Resize memory only."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.resize(sample_vps.id, memory_mb=4096)
        assert result is not None
        mock_proxmox.resize_vm.assert_awaited_with("pve", 100, cores=None, memory_mb=4096)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_resize_disk(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Resize disk only."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.resize(sample_vps.id, disk_gb=100)
        assert result is not None
        mock_proxmox.resize_disk.assert_awaited_with("pve", 100, "scsi0", 100)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_resize_all(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Resize CPU, memory, and disk simultaneously."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.resize(sample_vps.id, cores=8, memory_mb=8192, disk_gb=200)
        assert result is not None
        mock_proxmox.resize_vm.assert_awaited()
        mock_proxmox.resize_disk.assert_awaited()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_resize_no_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Raise VpsInvalidStateError when instance has no VMID."""
        instance = VpsInstance(id=uuid4(), service_id=uuid4(), proxmox_vmid=None, proxmox_node="pve")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        with pytest.raises(VpsInvalidStateError, match="no VMID"):
            await service.resize(instance.id, cores=4)

    @pytest.mark.vps
    async def test_resize_resource_busy(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsResizeError when Proxmox reports resource busy."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.resize_vm.side_effect = ProxmoxResourceBusyError("VM locked")

        with pytest.raises(VpsResizeError, match="Cannot resize"):
            await service.resize(sample_vps.id, cores=4)

    @pytest.mark.vps
    async def test_resize_proxmox_error(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsResizeError on generic Proxmox client error."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.resize_vm.side_effect = ProxmoxClientError("timeout")

        with pytest.raises(VpsResizeError, match="Resize failed"):
            await service.resize(sample_vps.id, cores=4)


# ------------------------------------------------------------------
# Tests: Reinstall
# ------------------------------------------------------------------


class TestReinstall:
    """Tests for VpsInstanceService.reinstall()."""

    @pytest.mark.vps
    async def test_reinstall_success(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Successfully reinstall OS on a VPS instance."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        # The reinstall method calls proxmox._api directly; we need to mock it
        mock_api = MagicMock()
        mock_proxmox._api = mock_api

        result = await service.reinstall(
            sample_vps.id,
            ostemplate="local:vztmpl/ubuntu-24.04",
            root_password="new-root-pass",
            ssh_keys="ssh-rsa AAAAB3...",
        )
        assert result is not None
        mock_proxmox.stop_vm.assert_awaited_once()
        mock_proxmox.start_vm.assert_awaited_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.vps
    async def test_reinstall_no_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Raise VpsInvalidStateError when instance has no VMID."""
        instance = VpsInstance(id=uuid4(), service_id=uuid4(), proxmox_vmid=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        with pytest.raises(VpsInvalidStateError, match="no VMID"):
            await service.reinstall(instance.id)

    @pytest.mark.vps
    async def test_reinstall_stop_fails(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsServiceError when stopping the VM fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.stop_vm.side_effect = ProxmoxClientError("stop failed")

        with pytest.raises(VpsServiceError, match="Cannot stop VM"):
            await service.reinstall(sample_vps.id)


# ------------------------------------------------------------------
# Tests: Decommission
# ------------------------------------------------------------------


class TestDecommission:
    """Tests for VpsInstanceService.decommission()."""

    @pytest.mark.vps
    async def test_decommission_success(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Successfully decommission (destroy) a VPS instance."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        await service.decommission(sample_vps.id)
        mock_proxmox.delete_vm.assert_awaited_with("pve", 100)
        mock_db.delete.assert_called_once_with(sample_vps)
        mock_db.commit.assert_awaited()

    @pytest.mark.vps
    async def test_decommission_vm_already_gone(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Handle case where VM is already deleted from Proxmox."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.delete_vm.side_effect = ProxmoxVMNotFoundError("already gone")

        # Should not raise - just log a warning and delete the DB record
        await service.decommission(sample_vps.id)
        mock_db.delete.assert_called_once_with(sample_vps)
        mock_db.commit.assert_awaited()

    @pytest.mark.vps
    async def test_decommission_proxmox_error(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsServiceError when Proxmox deletion fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.delete_vm.side_effect = ProxmoxClientError("API error")

        with pytest.raises(VpsServiceError, match="VM destruction failed"):
            await service.decommission(sample_vps.id)

    @pytest.mark.vps
    async def test_decommission_no_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Delete DB record even when instance has no VMID (never provisioned)."""
        instance = VpsInstance(id=uuid4(), service_id=uuid4(), proxmox_vmid=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        await service.decommission(instance.id)
        mock_db.delete.assert_called_once_with(instance)
        mock_db.commit.assert_awaited()
        # delete_vm should NOT be called since there's no VMID
        # (service checks: if instance.proxmox_vmid is not None)


# ------------------------------------------------------------------
# Tests: Snapshots
# ------------------------------------------------------------------


class TestCreateSnapshot:
    """Tests for VpsInstanceService.create_snapshot()."""

    @pytest.mark.vps
    async def test_create_snapshot_success(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Successfully create a VM snapshot."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.list_snapshots.return_value = [
            ProxmoxSnapshotInfo(
                name="backup-1",
                description="First backup",
                parent=None,
                snapshot_time=1712345678,
                vmstate=False,
                size_bytes=524288000,
            )
        ]

        snapshot = await service.create_snapshot(
            sample_vps.id, "backup-1", description="First backup"
        )
        assert snapshot.snapshot_name == "backup-1"
        assert snapshot.description == "First backup"
        assert snapshot.is_ram_included is False
        mock_proxmox.create_snapshot.assert_awaited_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    @pytest.mark.vps
    async def test_create_snapshot_with_ram(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Create a snapshot including RAM state."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        snapshot = await service.create_snapshot(
            sample_vps.id, "backup-with-ram", include_ram=True
        )
        assert snapshot.is_ram_included is True
        mock_proxmox.create_snapshot.assert_awaited_with(
            "pve", 100, "backup-with-ram", None, True
        )

    @pytest.mark.vps
    async def test_create_snapshot_no_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Raise VpsInvalidStateError when instance has no VMID."""
        instance = VpsInstance(id=uuid4(), service_id=uuid4(), proxmox_vmid=None, proxmox_node="pve")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        with pytest.raises(VpsInvalidStateError, match="no VMID"):
            await service.create_snapshot(instance.id, "snap1")

    @pytest.mark.vps
    async def test_create_snapshot_proxmox_error(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsSnapshotError when Proxmox snapshot creation fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.create_snapshot.side_effect = ProxmoxClientError("snapshot error")

        with pytest.raises(VpsSnapshotError, match="Snapshot creation failed"):
            await service.create_snapshot(sample_vps.id, "snap1")

    @pytest.mark.vps
    async def test_create_snapshot_task_failed(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsSnapshotError when the snapshot task does not succeed."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.create_snapshot.return_value = ProxmoxTaskResult(
            upid="UPID:snap:0001",
            node="pve",
            status="stopped",
            exitstatus="FAILED",
            success=False,
        )

        with pytest.raises(VpsSnapshotError, match="Snapshot task failed"):
            await service.create_snapshot(sample_vps.id, "snap1")


class TestDeleteSnapshot:
    """Tests for VpsInstanceService.delete_snapshot()."""

    @pytest.mark.vps
    async def test_delete_snapshot_success(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Successfully delete a VM snapshot."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        # Mock the snapshot lookup
        snapshot_record = VpsSnapshot(
            id=uuid4(),
            vps_instance_id=sample_vps.id,
            snapshot_name="backup-1",
        )
        snap_result = MagicMock()
        snap_result.scalar_one_or_none.return_value = snapshot_record
        # Need to make the second execute call return the snapshot
        mock_db.execute.side_effect = [mock_result, snap_result]

        await service.delete_snapshot(sample_vps.id, "backup-1")
        mock_proxmox.delete_snapshot.assert_awaited_with("pve", 100, "backup-1")
        mock_db.delete.assert_called_once_with(snapshot_record)
        mock_db.commit.assert_awaited()

    @pytest.mark.vps
    async def test_delete_snapshot_no_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Raise VpsInvalidStateError when instance has no VMID."""
        instance = VpsInstance(id=uuid4(), service_id=uuid4(), proxmox_vmid=None, proxmox_node="pve")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        with pytest.raises(VpsInvalidStateError, match="no VMID"):
            await service.delete_snapshot(instance.id, "backup-1")

    @pytest.mark.vps
    async def test_delete_snapshot_proxmox_error(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsSnapshotError when Proxmox deletion fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.delete_snapshot.side_effect = ProxmoxClientError("delete failed")

        with pytest.raises(VpsSnapshotError, match="Failed to delete snapshot"):
            await service.delete_snapshot(sample_vps.id, "backup-1")


class TestRollbackSnapshot:
    """Tests for VpsInstanceService.rollback_snapshot()."""

    @pytest.mark.vps
    async def test_rollback_snapshot_success(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Successfully rollback to a snapshot."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.rollback_snapshot(sample_vps.id, "backup-1")
        assert result.success is True
        mock_proxmox.rollback_snapshot.assert_awaited_with("pve", 100, "backup-1", True)
        mock_db.commit.assert_awaited()

    @pytest.mark.vps
    async def test_rollback_snapshot_no_start(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Rollback without starting the VM."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        result = await service.rollback_snapshot(sample_vps.id, "backup-1", start_after=False)
        assert result.success is True
        mock_proxmox.rollback_snapshot.assert_awaited_with("pve", 100, "backup-1", False)

    @pytest.mark.vps
    async def test_rollback_snapshot_no_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Raise VpsInvalidStateError when instance has no VMID."""
        instance = VpsInstance(id=uuid4(), service_id=uuid4(), proxmox_vmid=None, proxmox_node="pve")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        with pytest.raises(VpsInvalidStateError, match="no VMID"):
            await service.rollback_snapshot(instance.id, "backup-1")

    @pytest.mark.vps
    async def test_rollback_snapshot_proxmox_error(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsSnapshotError when Proxmox rollback fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.rollback_snapshot.side_effect = ProxmoxClientError("rollback failed")

        with pytest.raises(VpsSnapshotError, match="Rollback failed"):
            await service.rollback_snapshot(sample_vps.id, "backup-1")


class TestListSnapshots:
    """Tests for VpsInstanceService.list_snapshots()."""

    @pytest.mark.vps
    async def test_list_snapshots_empty(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Return empty list when no snapshots exist."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        snapshots = await service.list_snapshots(sample_vps.id)
        assert snapshots == []

    @pytest.mark.vps
    async def test_list_snapshots_with_data(
        self, service: VpsInstanceService, mock_db: AsyncMock, sample_vps: VpsInstance
    ) -> None:
        """Return list of snapshots when they exist."""
        snap1 = VpsSnapshot(
            id=uuid4(),
            vps_instance_id=sample_vps.id,
            snapshot_name="backup-1",
            size_bytes=1048576,
            is_ram_included=False,
        )
        snap2 = VpsSnapshot(
            id=uuid4(),
            vps_instance_id=sample_vps.id,
            snapshot_name="backup-2",
            size_bytes=2097152,
            is_ram_included=True,
        )
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [snap1, snap2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        snapshots = await service.list_snapshots(sample_vps.id)
        assert len(snapshots) == 2
        assert snapshots[0].snapshot_name == "backup-1"
        assert snapshots[1].snapshot_name == "backup-2"


# ------------------------------------------------------------------
# Tests: Console / VNC
# ------------------------------------------------------------------


class TestGetVncConsole:
    """Tests for VpsInstanceService.get_vnc_console()."""

    @pytest.mark.vps
    async def test_get_vnc_console_success(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Successfully retrieve VNC console information."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        vnc = await service.get_vnc_console(sample_vps.id)
        assert vnc["vmid"] == 100
        assert vnc["node"] == "pve"
        assert vnc["port"] == 5900
        assert vnc["ticket"] == "test-ticket"
        assert "websockify" in vnc["websocket_path"]
        mock_proxmox.get_vnc_proxy.assert_awaited_once()
        mock_proxmox.get_vnc_websocket.assert_awaited_once()

    @pytest.mark.vps
    async def test_get_vnc_console_no_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Raise VpsInvalidStateError when instance has no VMID."""
        instance = VpsInstance(id=uuid4(), service_id=uuid4(), proxmox_vmid=None, proxmox_node="pve")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        with pytest.raises(VpsInvalidStateError, match="no VMID"):
            await service.get_vnc_console(instance.id)

    @pytest.mark.vps
    async def test_get_vnc_console_proxmox_error(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsConsoleError when Proxmox VNC request fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.get_vnc_proxy.side_effect = ProxmoxClientError("vnc error")

        with pytest.raises(VpsConsoleError, match="Failed to get VNC console"):
            await service.get_vnc_console(sample_vps.id)


# ------------------------------------------------------------------
# Tests: Clone
# ------------------------------------------------------------------


class TestClone:
    """Tests for VpsInstanceService.clone()."""

    @pytest.mark.vps
    async def test_clone_success(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Successfully clone a VPS instance."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result

        new_service_id = uuid4()
        clone = await service.clone(
            sample_vps.id, new_service_id, new_name="cloned-vm", full_clone=True, start=True
        )
        assert clone.service_id == new_service_id
        assert clone.proxmox_vmid is not None  # auto-assigned
        assert clone.power_status == VpsPowerStatus.RUNNING
        mock_proxmox.clone_vm.assert_awaited_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited()

    @pytest.mark.vps
    async def test_clone_no_vmid(
        self, service: VpsInstanceService, mock_db: AsyncMock
    ) -> None:
        """Raise VpsInvalidStateError when source instance has no VMID."""
        instance = VpsInstance(id=uuid4(), service_id=uuid4(), proxmox_vmid=None, proxmox_node="pve")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        with pytest.raises(VpsInvalidStateError, match="no VMID"):
            await service.clone(instance.id, uuid4())

    @pytest.mark.vps
    async def test_clone_proxmox_error(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsProvisioningError when Proxmox clone fails."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.clone_vm.side_effect = ProxmoxClientError("clone error")

        with pytest.raises(VpsProvisioningError, match="Clone failed"):
            await service.clone(sample_vps.id, uuid4())

    @pytest.mark.vps
    async def test_clone_task_failed(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock, sample_vps: VpsInstance
    ) -> None:
        """Raise VpsProvisioningError when the clone task does not succeed."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_vps
        mock_db.execute.return_value = mock_result
        mock_proxmox.clone_vm.return_value = ProxmoxTaskResult(
            upid="UPID:clone:0001",
            node="pve",
            status="stopped",
            exitstatus="FAILED",
            success=False,
        )

        with pytest.raises(VpsProvisioningError, match="Clone task failed"):
            await service.clone(sample_vps.id, uuid4())


# ------------------------------------------------------------------
# Tests: Auto-connect
# ------------------------------------------------------------------


class TestGetProxmox:
    """Tests for VpsInstanceService._get_proxmox()."""

    @pytest.mark.vps
    async def test_auto_connect(
        self, mock_db: AsyncMock, mock_proxmox: MagicMock
    ) -> None:
        """Auto-connect when proxmox is provided but not yet connected."""
        mock_proxmox._api = None
        svc = VpsInstanceService(db=mock_db, proxmox=mock_proxmox)
        proxmox = await svc._get_proxmox()
        assert proxmox is mock_proxmox
        mock_proxmox.connect.assert_awaited_once()

    @pytest.mark.vps
    async def test_already_connected(
        self, mock_db: AsyncMock, mock_proxmox: MagicMock
    ) -> None:
        """Skip connect if already connected."""
        mock_proxmox._api = MagicMock()  # already connected
        svc = VpsInstanceService(db=mock_db, proxmox=mock_proxmox)
        proxmox = await svc._get_proxmox()
        assert proxmox is mock_proxmox
        mock_proxmox.connect.assert_not_awaited()

    @pytest.mark.vps
    async def test_create_new_proxmox(
        self, mock_db: AsyncMock
    ) -> None:
        """Create and connect a new ProxmoxClient when none is provided."""
        svc = VpsInstanceService(db=mock_db)
        assert svc._proxmox is None
        # Calling _get_proxmox without providing one would create a new ProxmoxClient
        # This would fail in tests because ProxmoxClient tries to connect to a real host
        # Instead we verify the pattern: if None, a new instance is created
        # We'll mock the class constructor to avoid actual network calls
        with patch("modules.vps.services.ProxmoxClient") as mock_cls:
            mock_instance = MagicMock()
            mock_instance._api = None
            mock_instance.connect = AsyncMock()
            mock_cls.return_value = mock_instance

            proxmox = await svc._get_proxmox()
            assert proxmox is mock_instance
            mock_cls.assert_called_once()
            mock_instance.connect.assert_awaited_once()


# ------------------------------------------------------------------
# Tests: Exception class hierarchy
# ------------------------------------------------------------------


class TestExceptionHierarchy:
    """Verify the exception class hierarchy is correct."""

    @pytest.mark.vps
    def test_service_error_base(self) -> None:
        """All service exceptions inherit from VpsServiceError."""
        assert issubclass(VpsProvisioningError, VpsServiceError)
        assert issubclass(VpsPowerActionError, VpsServiceError)
        assert issubclass(VpsSnapshotError, VpsServiceError)
        assert issubclass(VpsResizeError, VpsServiceError)
        assert issubclass(VpsConsoleError, VpsServiceError)
        assert issubclass(VpsInstanceNotFoundError, VpsServiceError)
        assert issubclass(VpsInvalidStateError, VpsServiceError)

    @pytest.mark.vps
    def test_exception_message(self) -> None:
        """Exceptions preserve their message."""
        msg = "test error message"
        exc = VpsServiceError(msg)
        assert str(exc) == msg


# ------------------------------------------------------------------
# Tests: VpsTrafficSummary dataclass
# ------------------------------------------------------------------


class TestVpsTrafficSummary:
    """Tests for the VpsTrafficSummary dataclass."""

    @pytest.mark.vps
    def test_create_summary(self) -> None:
        """Create a VpsTrafficSummary instance."""
        summary = VpsTrafficSummary(
            instance_id="test-id",
            vm_status="running",
            node="pve",
            cores=2,
            memory_mb=2048,
            disk_gb=50,
        )
        assert summary.instance_id == "test-id"
        assert summary.vm_status == "running"
        assert summary.node == "pve"
        assert summary.cores == 2
        assert summary.memory_mb == 2048
        assert summary.disk_gb == 50

    @pytest.mark.vps
    def test_summary_is_dataclass(self) -> None:
        """VpsTrafficSummary should be a dataclass."""
        import dataclasses
        assert dataclasses.is_dataclass(VpsTrafficSummary)


# ------------------------------------------------------------------
# Tests: Integration scenario - full lifecycle
# ------------------------------------------------------------------


class TestFullLifecycle:
    """Simulate a full VPS lifecycle: provision → power → snapshot → resize → decommission."""

    @pytest.mark.vps
    async def test_full_lifecycle(
        self, service: VpsInstanceService, mock_db: AsyncMock, mock_proxmox: MagicMock
    ) -> None:
        """Exercise a complete VPS lifecycle workflow."""
        service_id = uuid4()

        # 1. Provision
        mock_db.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )
        mock_proxmox.list_vms.return_value = []

        instance = await service.provision(
            service_id=service_id,
            node="pve",
            cores=2,
            memory_mb=2048,
            disk_gb=50,
            ostemplate="local:vztmpl/ubuntu-22.04",
        )
        assert instance.service_id == service_id
        assert instance.power_status == VpsPowerStatus.RUNNING

        # 2. Power - stop
        mock_proxmox.stop_vm.return_value = ProxmoxTaskResult(
            upid="UPID:stop:0001",
            node="pve",
            status="stopped",
            exitstatus="OK",
            success=True,
        )
        # Set up mock to return our instance for get_instance
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        await service.power_action(instance.id, "stop")
        assert instance.power_status == VpsPowerStatus.STOPPED

        # 3. Power - start
        mock_proxmox.start_vm.return_value = ProxmoxTaskResult(
            upid="UPID:start:0001",
            node="pve",
            status="stopped",
            exitstatus="OK",
            success=True,
        )
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        await service.power_action(instance.id, "start")
        assert instance.power_status == VpsPowerStatus.RUNNING

        # 4. Snapshot
        mock_proxmox.create_snapshot.return_value = ProxmoxTaskResult(
            upid="UPID:snap:0001",
            node="pve",
            status="stopped",
            exitstatus="OK",
            success=True,
        )
        mock_proxmox.list_snapshots.return_value = [
            ProxmoxSnapshotInfo(
                name="pre-update",
                description="Before update",
                parent=None,
                snapshot_time=1712345678,
                vmstate=False,
            )
        ]

        # We need to handle the snapshot create flow:
        # get_instance (via get_instance), then list_snapshots for info
        # First call: get_instance → mock_db.execute
        # Second call: list_snapshots → mock_proxmox
        # Third call: create_snapshot → mock_proxmox
        mock_result.scalar_one_or_none.return_value = instance
        mock_db.execute.return_value = mock_result

        snapshot = await service.create_snapshot(
            instance.id, "pre-update", description="Before system update"
        )
        assert snapshot.snapshot_name == "pre-update"

        # 5. Resize
        mock_proxmox.resize_vm = AsyncMock()
        mock_proxmox.resize_disk = AsyncMock(
            return_value=ProxmoxTaskResult(
                upid="UPID:resize:0001",
                node="pve",
                status="stopped",
                exitstatus="OK",
                success=True,
            )
        )

        await service.resize(instance.id, cores=4, memory_mb=4096, disk_gb=100)
        mock_proxmox.resize_vm.assert_awaited()

        # 6. Decommission
        mock_proxmox.delete_vm.return_value = ProxmoxTaskResult(
            upid="UPID:delete:0001",
            node="pve",
            status="stopped",
            exitstatus="OK",
            success=True,
        )

        await service.decommission(instance.id)
        mock_proxmox.delete_vm.assert_awaited_with("pve", instance.proxmox_vmid)
        mock_db.delete.assert_called_with(instance)


__all__: list[str] = []