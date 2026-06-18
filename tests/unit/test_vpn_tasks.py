"""Tests for services.tasks.vpn - VPN Celery tasks."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Pre-register optional VPS dependencies to avoid ImportError when modules.vps is loaded
sys.modules["pybreaker"] = MagicMock()
sys.modules["proxmoxer"] = MagicMock()
sys.modules["proxmoxer.backends"] = MagicMock()

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from modules.vpn.models import (
    VpnAccount,
    VpnAccountStatus,
    VpnProtocol,
    VpnServer,
    VpnServerStatus,
    VpnSession,
    VpnSessionStatus,
    TrafficUsage,
)
from modules.vpn.services import AccountTrafficSummary, VpnAccountService
from modules.vpn.wireguard import WireGuardService
from modules.vps.models import VpsInstance  # noqa: F401 - ensure VpsInstance is registered for Service mapper
from services.tasks.vpn import (
    check_exceeded_traffic,
    check_vpn_server_health,
    cleanup_stale_sessions,
    renew_peer_configs,
    sync_all_connections,
    sync_all_traffic,
    sync_wg_connections,
    sync_wg_traffic,
    sync_xray_traffic,
)

# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    """Mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_wg_accounts():
    """Create sample WG VpnAccount objects for testing."""
    now = datetime.now(timezone.utc)
    server = VpnServer(
        id=str(uuid4()),
        name="test-wg-server",
        public_ip="10.0.0.1",
        port=51820,
        protocol=VpnProtocol.WIREGUARD,
        status=VpnServerStatus.ACTIVE,
    )

    accounts = []
    for i in range(3):
        acc = VpnAccount(
            id=str(uuid4()),
            service_id=str(uuid4()),
            server_id=server.id,
            protocol=VpnProtocol.WIREGUARD,
            status=VpnAccountStatus.ACTIVE,
            public_key=f"test_pubkey_{i}",
            private_key=f"test_privkey_{i}",
            assigned_ip=f"10.0.0.{i+2}/32",
            bandwidth_limit_bytes=1_000_000_000,
            bandwidth_used_bytes=500_000_000,
            created_at=now,
            updated_at=now,
            server_rel=server,
            sessions=[],
        )
        accounts.append(acc)

    return accounts


@pytest.fixture
def sample_traffic_summaries(sample_wg_accounts):
    """Create sample AccountTrafficSummary objects."""
    now = datetime.now(timezone.utc)
    return [
        AccountTrafficSummary(
            account_id=acc.id,
            public_key=acc.public_key,
            bytes_sent=100_000,
            bytes_received=200_000,
            total_bytes=acc.bandwidth_used_bytes or 0,
            last_handshake=now - timedelta(seconds=30),
            is_connected=True,
            active_sessions=1,
        )
        for acc in sample_wg_accounts
    ]


# ── sync_wg_connections ──────────────────────────────────────────────────


class TestSyncWgConnections:
    """Tests for sync_wg_connections task."""

    @patch(
        "services.tasks.vpn.VpnAccountService.detect_and_sync_connections",
        new_callable=AsyncMock,
    )
    @patch("core.database.async_session_factory")
    def test_sync_connections_success(
        self, mock_factory, mock_detect, mock_db
    ):
        """Should successfully sync WG connections and return summary."""
        mock_factory.return_value.__aenter__.return_value = mock_db
        mock_detect.return_value = {
            "acc1": True,
            "acc2": False,
            "acc3": True,
        }

        # Run the sync
        result = sync_wg_connections.apply(args=["wg0", "test_tenant"]).get()

        assert result["status"] == "completed"
        assert result["connected"] == 2
        assert result["disconnected"] == 1
        assert result["total_accounts"] == 3
        assert result["interface"] == "wg0"

    @patch(
        "services.tasks.vpn.VpnAccountService.detect_and_sync_connections",
        new_callable=AsyncMock,
    )
    @patch("core.database.async_session_factory")
    def test_sync_empty_universe(
        self, mock_factory, mock_detect, mock_db
    ):
        """Should handle zero accounts gracefully."""
        mock_factory.return_value.__aenter__.return_value = mock_db
        mock_detect.return_value = {}

        result = sync_wg_connections.apply(args=["wg0"]).get()

        assert result["connected"] == 0
        assert result["disconnected"] == 0
        assert result["total_accounts"] == 0

    @patch(
        "services.tasks.vpn.VpnAccountService.detect_and_sync_connections",
        new_callable=AsyncMock,
    )
    @patch("core.database.async_session_factory")
    def test_sync_failure_retries(
        self, mock_factory, mock_detect, mock_db
    ):
        """Verify task retries on exception."""
        mock_factory.return_value.__aenter__.return_value = mock_db
        mock_detect.side_effect = RuntimeError("WireGuard not found")

        with pytest.raises(RuntimeError):
            sync_wg_connections.apply(args=["wg0"]).get()


# ── sync_wg_traffic ──────────────────────────────────────────────────────


class TestSyncWgTraffic:
    """Tests for sync_wg_traffic task."""

    @patch(
        "services.tasks.vpn.VpnAccountService.poll_all_accounts_traffic",
        new_callable=AsyncMock,
    )
    @patch("core.database.async_session_factory")
    @patch("services.tasks.vpn.TrafficUsage")
    def test_poll_traffic_success(
        self,
        mock_traffic_usage_cls,
        mock_factory,
        mock_poll,
        mock_db,
        sample_traffic_summaries,
    ):
        """Should poll WG traffic and return summary."""
        mock_factory.return_value.__aenter__.return_value = mock_db
        mock_poll.return_value = sample_traffic_summaries

        result = sync_wg_traffic.apply(args=["wg0"]).get()

        assert result["status"] == "completed"
        assert result["accounts_polled"] == 3
        assert result["total_bytes_sent"] == 300_000  # 3 * 100_000
        assert result["total_bytes_received"] == 600_000  # 3 * 200_000
        assert result["interface"] == "wg0"

    @patch(
        "services.tasks.vpn.VpnAccountService.poll_all_accounts_traffic",
        new_callable=AsyncMock,
    )
    @patch("core.database.async_session_factory")
    def test_poll_no_accounts(self, mock_factory, mock_poll, mock_db):
        """Should handle zero accounts gracefully."""
        mock_factory.return_value.__aenter__.return_value = mock_db
        mock_poll.return_value = []

        result = sync_wg_traffic.apply(args=["wg0"]).get()

        assert result["accounts_polled"] == 0
        assert result["total_bytes_sent"] == 0
        assert result["total_bytes_received"] == 0


# ── sync_xray_traffic ───────────────────────────────────────────────────


class TestSyncXrayTraffic:
    """Tests for sync_xray_traffic task."""

    @patch(
        "services.tasks.vpn.VpnAccountService.poll_all_accounts_traffic",
        new_callable=AsyncMock,
    )
    @patch("core.database.async_session_factory")
    @patch("services.tasks.vpn.TrafficUsage")
    def test_poll_xray_traffic_success(
        self,
        mock_traffic_usage_cls,
        mock_factory,
        mock_poll,
        mock_db,
        sample_traffic_summaries,
    ):
        """Should poll Xray traffic and return summary."""
        mock_factory.return_value.__aenter__.return_value = mock_db
        mock_poll.return_value = sample_traffic_summaries

        result = sync_xray_traffic.apply(args=[]).get()

        assert result["status"] == "completed"
        assert result["accounts_polled"] == 3
        assert result["total_bytes_sent"] == 300_000
        assert result["total_bytes_received"] == 600_000

    @patch(
        "services.tasks.vpn.VpnAccountService.poll_all_accounts_traffic",
        new_callable=AsyncMock,
    )
    @patch("core.database.async_session_factory")
    def test_poll_xray_no_accounts(self, mock_factory, mock_poll, mock_db):
        """Should handle zero Xray accounts gracefully."""
        mock_factory.return_value.__aenter__.return_value = mock_db
        mock_poll.return_value = []

        result = sync_xray_traffic.apply(args=[]).get()

        assert result["accounts_polled"] == 0
        assert result["total_bytes_sent"] == 0
        assert result["total_bytes_received"] == 0


# ── check_exceeded_traffic ──────────────────────────────────────────────


class TestCheckExceededTraffic:
    """Tests for check_exceeded_traffic task."""

    @patch.object(VpnAccountService, "suspend_account", new_callable=AsyncMock)
    @patch("core.database.async_session_factory")
    def test_exceeded_accounts_suspended(
        self,
        mock_factory,
        mock_suspend,
        mock_db,
        sample_wg_accounts,
    ):
        """Should suspend accounts that exceeded data limits."""
        mock_factory.return_value.__aenter__.return_value = mock_db

        # Make accounts exceed their limits
        for acc in sample_wg_accounts:
            acc.bandwidth_used_bytes = 2_000_000_000  # exceeds 1_000_000_000 limit

        # Mock the query chain
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = sample_wg_accounts
        mock_db.execute.return_value = mock_result

        result = check_exceeded_traffic.apply(args=[]).get()

        assert result["status"] == "completed"
        assert result["accounts_suspended"] == 3
        assert result["suspended_ids"] == [a.id for a in sample_wg_accounts]
        assert mock_suspend.call_count == 3

    @patch("core.database.async_session_factory")
    def test_no_exceeded_accounts(self, mock_factory, mock_db):
        """Should not suspend accounts that are within limits."""
        mock_factory.return_value.__aenter__.return_value = mock_db

        # Empty result
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = check_exceeded_traffic.apply(args=[]).get()

        assert result["accounts_checked"] == 0
        assert result["accounts_suspended"] == 0
        assert len(result["suspended_ids"]) == 0


# ── check_vpn_server_health ────────────────────────────────────────────


class TestCheckVpnServerHealth:
    """Tests for check_vpn_server_health task."""

    @patch(
        "services.tasks.vpn.VpnServerService.check_server_health",
        return_value=True,
    )
    @patch("core.database.async_session_factory")
    def test_all_servers_healthy(self, mock_factory, mock_check_health, mock_db):
        """Should mark all servers as healthy."""
        mock_factory.return_value.__aenter__.return_value = mock_db

        servers = [
            VpnServer(
                id="srv1",
                public_ip="10.0.0.1",
                port=51820,
                status=VpnServerStatus.ACTIVE,
            ),
            VpnServer(
                id="srv2",
                public_ip="10.0.0.2",
                port=51820,
                status=VpnServerStatus.ACTIVE,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = servers
        mock_db.execute.return_value = mock_result

        result = check_vpn_server_health.apply(args=[]).get()

        assert result["status"] == "completed"
        assert result["healthy"] == 2
        assert result["unhealthy"] == 0

    @patch(
        "services.tasks.vpn.VpnServerService.check_server_health",
        return_value=False,
    )
    @patch("core.database.async_session_factory")
    def test_servers_unhealthy(self, mock_factory, mock_check_health, mock_db):
        """Should mark unhealthy servers as DEGRADED."""
        mock_factory.return_value.__aenter__.return_value = mock_db

        servers = [
            VpnServer(
                id="srv1",
                public_ip="10.0.0.1",
                port=51820,
                status=VpnServerStatus.ACTIVE,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = servers
        mock_db.execute.return_value = mock_result

        result = check_vpn_server_health.apply(args=[]).get()

        assert result["healthy"] == 0
        assert result["unhealthy"] == 1
        assert servers[0].status == VpnServerStatus.DEGRADED

    @patch(
        "services.tasks.vpn.VpnServerService.check_server_health",
        side_effect=Exception("SSH timeout"),
    )
    @patch("core.database.async_session_factory")
    def test_health_check_exception(
        self, mock_factory, mock_check_health, mock_db
    ):
        """Should handle exceptions during health checks."""
        mock_factory.return_value.__aenter__.return_value = mock_db

        servers = [
            VpnServer(
                id="srv1",
                public_ip="10.0.0.1",
                port=51820,
                status=VpnServerStatus.ACTIVE,
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = servers
        mock_db.execute.return_value = mock_result

        result = check_vpn_server_health.apply(args=[]).get()

        assert result["unhealthy"] == 1
        assert len(result["unhealthy_details"]) == 1


# ── cleanup_stale_sessions ──────────────────────────────────────────────


class TestCleanupStaleSessions:
    """Tests for cleanup_stale_sessions task."""

    @patch("core.database.async_session_factory")
    def test_cleanup_stale_sessions(self, mock_factory, mock_db):
        """Should end stale connected sessions."""
        mock_factory.return_value.__aenter__.return_value = mock_db

        now = datetime.now(timezone.utc)
        stale_session = VpnSession(
            id=str(uuid4()),
            vpn_account_id=str(uuid4()),
            status=VpnSessionStatus.CONNECTED,
            connected_at=now - timedelta(minutes=120),  # 2 hours ago
        )

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [stale_session]
        mock_db.execute.return_value = mock_result

        result = cleanup_stale_sessions.apply(args=[60]).get()

        assert result["status"] == "completed"
        assert result["sessions_ended"] == 1
        assert stale_session.status == VpnSessionStatus.DISCONNECTED
        assert stale_session.disconnect_reason == "stale_session"

    @patch("core.database.async_session_factory")
    def test_no_stale_sessions(self, mock_factory, mock_db):
        """Should handle no stale sessions gracefully."""
        mock_factory.return_value.__aenter__.return_value = mock_db

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = cleanup_stale_sessions.apply(args=[60]).get()

        assert result["sessions_ended"] == 0


# ── renew_peer_configs ──────────────────────────────────────────────────


class TestRenewPeerConfigs:
    """Tests for renew_peer_configs task."""

    @patch.object(WireGuardService, "sync_peer")
    @patch("core.database.async_session_factory")
    def test_renew_peers_success(
        self,
        mock_factory,
        mock_sync_peer,
        mock_db,
        sample_wg_accounts,
    ):
        """Should renew all active WG peer configs."""
        mock_factory.return_value.__aenter__.return_value = mock_db

        # Mock servers query
        servers = [
            VpnServer(
                id="srv1",
                public_ip="10.0.0.1",
                port=51820,
                protocol=VpnProtocol.WIREGUARD,
                status=VpnServerStatus.ACTIVE,
                ssh_port=22,
                ssh_user="root",
                ssh_key_path="/root/.ssh/id_rsa",
            ),
        ]

        # Create two side effects: servers result, then accounts result
        servers_mock = MagicMock()
        servers_mock.scalars.return_value.all.return_value = servers

        accounts_mock = MagicMock()
        accounts_mock.scalars.return_value.all.return_value = sample_wg_accounts

        mock_db.execute.side_effect = [servers_mock, accounts_mock]
        result = renew_peer_configs.apply(args=["wg0"]).get()

        assert result["status"] == "completed"
        assert result["servers_processed"] == 1
        assert result["peers_renewed"] == 3

    @patch("core.database.async_session_factory")
    def test_no_active_servers(self, mock_factory, mock_db):
        """Should handle no active WG servers gracefully."""
        mock_factory.return_value.__aenter__.return_value = mock_db

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = renew_peer_configs.apply(args=["wg0"]).get()

        assert result["servers_processed"] == 0
        assert result["peers_renewed"] == 0


# ── Edge Cases and Error Handling ──────────────────────────────────────────


class TestVpnTasksEdgeCases:
    """Edge case tests for VPN tasks."""

    def test_all_tasks_have_names(self):
        """Ensure all tasks have explicit task names for beat schedule."""
        tasks = [
            sync_wg_connections,
            sync_all_connections,
            sync_wg_traffic,
            sync_xray_traffic,
            sync_all_traffic,
            check_exceeded_traffic,
            check_vpn_server_health,
            cleanup_stale_sessions,
            renew_peer_configs,
        ]
        for task in tasks:
            assert task.name is not None
            assert task.name.startswith("services.tasks.vpn.")

    def test_task_retry_configuration(self):
        """Verify that tasks have retry settings."""
        # All tasks should have retry configuration
        tasks = [
            sync_wg_connections,
            sync_wg_traffic,
            sync_xray_traffic,
            check_exceeded_traffic,
            check_vpn_server_health,
            cleanup_stale_sessions,
            renew_peer_configs,
        ]
        for task in tasks:
            assert task.max_retries >= 2

    def test_soft_time_limits_set(self):
        """Verify that tasks have soft_time_limit set."""
        tasks = [
            sync_wg_connections,
            sync_wg_traffic,
            sync_xray_traffic,
            check_exceeded_traffic,
            check_vpn_server_health,
            cleanup_stale_sessions,
            renew_peer_configs,
        ]
        for task in tasks:
            assert task.soft_time_limit is not None
            assert task.soft_time_limit > 0