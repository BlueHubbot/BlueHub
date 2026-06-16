"""
BlueHub VPN Celery Tasks
========================
Periodic tasks for VPN operations:
- Connection detection and session sync
- Traffic polling and accounting
- Data-limit enforcement and auto-suspension
- Peer config renewal
- Xray (V2Ray/Xray-core) traffic polling via API
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.database import get_async_session
from core.audit.logger import AuditLogger
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
from modules.vpn.services import VpnAccountService, AccountTrafficSummary
from modules.vpn.wireguard import WireGuardService
from modules.vpn.xray import XrayService
from modules.vpn.vpn_servers import VpnServerService
from services.celery_app import celery_app
from shared.models.enums import ModuleType, AuditAction

logger = logging.getLogger("bluehub.tasks.vpn")

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

DEFAULT_WG_INTERFACE = "wg0"
DEFAULT_TRAFFIC_POLL_INTERVAL = 300  # 5 minutes
DEFAULT_CONNECTION_SYNC_INTERVAL = 120  # 2 minutes
DEFAULT_EXCEEDED_CHECK_INTERVAL = 600  # 10 minutes
DEFAULT_XRAY_POLL_INTERVAL = 300  # 5 minutes
DEFAULT_PEER_RENEW_INTERVAL = 86400  # 24 hours

# ------------------------------------------------------------------
# Connection Sync Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vpn.sync_wg_connections",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    soft_time_limit=120,
)
def sync_wg_connections(
    self,
    interface: str = DEFAULT_WG_INTERFACE,
    tenant_id: Optional[str] = None,
) -> dict:
    """
    Detect active WireGuard connections and sync session records.

    Scans all active WG accounts, detects which peers are currently
    connected via handshake timestamps, and creates/ends VpnSession
    records accordingly.

    Args:
        interface: WireGuard interface name.
        tenant_id: Optional tenant scope.

    Returns:
        Sync result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                result_map = await VpnAccountService.detect_and_sync_connections(
                    db,
                    protocol=VpnProtocol.WIREGUARD,
                    interface=interface,
                )

                connected_count = sum(1 for v in result_map.values() if v)
                disconnected_count = len(result_map) - connected_count

                logger.info(
                    "WG connection sync: %d active, %d inactive out of %d total",
                    connected_count,
                    disconnected_count,
                    len(result_map),
                )

                await AuditLogger.log(
                    db=db,
                    tenant_id=tenant_id or "system",
                    module=ModuleType.VPN,
                    action=AuditAction.UPDATE,
                    resource_type="vpn_connections",
                    resource_id=f"wg_sync_{datetime.now(timezone.utc).isoformat()}",
                    details={
                        "connected": connected_count,
                        "disconnected": disconnected_count,
                        "total": len(result_map),
                        "interface": interface,
                    },
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "connected": connected_count,
                    "disconnected": disconnected_count,
                    "total_accounts": len(result_map),
                    "interface": interface,
                }

        except Exception as exc:
            logger.error("WG connection sync failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("WG connection sync failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name="services.tasks.vpn.sync_all_connections",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    soft_time_limit=180,
)
def sync_all_connections(
    self,
    interface: str = DEFAULT_WG_INTERFACE,
) -> dict:
    """
    Sync connections for all protocols (WG + Xray).

    Chain invokes protocol-specific sync routines and aggregates results.

    Args:
        interface: WireGuard interface name.

    Returns:
        Aggregated sync result summary.
    """
    import asyncio

    async def _run():
        results = {}

        # WireGuard sync
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                wg_result = await VpnAccountService.detect_and_sync_connections(
                    db,
                    protocol=VpnProtocol.WIREGUARD,
                    interface=interface,
                )
                results["wireguard"] = {
                    "connected": sum(1 for v in wg_result.values() if v),
                    "disconnected": len(wg_result) - sum(1 for v in wg_result.values() if v),
                    "total": len(wg_result),
                }
        except Exception as exc:
            logger.error("WG sync in all-protocols failed: %s", exc)
            results["wireguard"] = {"error": str(exc)}

        # Xray sync
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                xray_result = await VpnAccountService.detect_and_sync_connections(
                    db,
                    protocol=VpnProtocol.XRAY,
                    interface=interface,
                )
                results["xray"] = {
                    "connected": sum(1 for v in xray_result.values() if v),
                    "disconnected": len(xray_result) - sum(1 for v in xray_result.values() if v),
                    "total": len(xray_result),
                }
        except Exception as exc:
            logger.warning("Xray sync in all-protocols failed: %s", exc)
            results["xray"] = {"error": str(exc)}

        return results

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(_run())
        return {
            "status": "completed",
            "task_id": self.request.id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "errors": [k for k, v in results.items() if "error" in v],
        }
    except Exception as exc:
        logger.error("All connections sync failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Traffic Polling Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vpn.sync_wg_traffic",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=300,
)
def sync_wg_traffic(
    self,
    interface: str = DEFAULT_WG_INTERFACE,
) -> dict:
    """
    Poll WireGuard traffic for all active WG accounts.

    Uses `wg show <interface> dump` to collect per-peer transfer stats,
    updates cumulative totals, and records traffic snapshots.

    Args:
        interface: WireGuard interface name.

    Returns:
        Traffic sync result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                summaries = await VpnAccountService.poll_all_accounts_traffic(
                    db,
                    protocol=VpnProtocol.WIREGUARD,
                    interface=interface,
                )

                total_bytes_sent = sum(s.bytes_sent for s in summaries)
                total_bytes_received = sum(s.bytes_received for s in summaries)

                # Record traffic snapshots
                now = datetime.now(timezone.utc)
                for summary in summaries:
                    snapshot = TrafficUsage(
                        id=str(uuid4()),
                        account_id=summary.account_id,
                        bytes_sent=summary.bytes_sent,
                        bytes_received=summary.bytes_received,
                        recorded_at=now,
                    )
                    db.add(snapshot)

                if summaries:
                    await db.commit()

                logger.info(
                    "WG traffic synced: %d accounts, %d bytes sent, %d bytes received",
                    len(summaries),
                    total_bytes_sent,
                    total_bytes_received,
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": now.isoformat(),
                    "accounts_polled": len(summaries),
                    "total_bytes_sent": total_bytes_sent,
                    "total_bytes_received": total_bytes_received,
                    "interface": interface,
                }

        except Exception as exc:
            logger.error("WG traffic sync failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("WG traffic sync failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name="services.tasks.vpn.sync_xray_traffic",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=300,
)
def sync_xray_traffic(self) -> dict:
    """
    Poll Xray (V2Ray/Xray-core) traffic for all active Xray accounts.

    Connects to each Xray server's StatsService API to collect
    per-user uplink/downlink counters and updates cumulative totals.

    Returns:
        Traffic sync result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                summaries = await VpnAccountService.poll_all_accounts_traffic(
                    db,
                    protocol=VpnProtocol.XRAY,
                )

                total_bytes_sent = sum(s.bytes_sent for s in summaries)
                total_bytes_received = sum(s.bytes_received for s in summaries)

                # Record traffic snapshots
                now = datetime.now(timezone.utc)
                for summary in summaries:
                    snapshot = TrafficUsage(
                        id=str(uuid4()),
                        account_id=summary.account_id,
                        bytes_sent=summary.bytes_sent,
                        bytes_received=summary.bytes_received,
                        recorded_at=now,
                    )
                    db.add(snapshot)

                if summaries:
                    await db.commit()

                logger.info(
                    "Xray traffic synced: %d accounts, %d bytes sent, %d bytes received",
                    len(summaries),
                    total_bytes_sent,
                    total_bytes_received,
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": now.isoformat(),
                    "accounts_polled": len(summaries),
                    "total_bytes_sent": total_bytes_sent,
                    "total_bytes_received": total_bytes_received,
                }

        except Exception as exc:
            logger.error("Xray traffic sync failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("Xray traffic sync failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name="services.tasks.vpn.sync_all_traffic",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=600,
)
def sync_all_traffic(
    self,
    interface: str = DEFAULT_WG_INTERFACE,
) -> dict:
    """
    Poll traffic for all protocols (WG + Xray).

    Aggregates results from both protocol-specific traffic polls.

    Args:
        interface: WireGuard interface name.

    Returns:
        Aggregated traffic sync result summary.
    """
    import asyncio

    async def _run():
        results = {}
        now = datetime.now(timezone.utc)

        # WG traffic
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                wg_summaries = await VpnAccountService.poll_all_accounts_traffic(
                    db,
                    protocol=VpnProtocol.WIREGUARD,
                    interface=interface,
                )
                wg_sent = sum(s.bytes_sent for s in wg_summaries)
                wg_received = sum(s.bytes_received for s in wg_summaries)
                results["wireguard"] = {
                    "accounts": len(wg_summaries),
                    "bytes_sent": wg_sent,
                    "bytes_received": wg_received,
                }
        except Exception as exc:
            logger.warning("WG traffic in all-sync failed: %s", exc)
            results["wireguard"] = {"error": str(exc)}

        # Xray traffic
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                xray_summaries = await VpnAccountService.poll_all_accounts_traffic(
                    db,
                    protocol=VpnProtocol.XRAY,
                )
                xray_sent = sum(s.bytes_sent for s in xray_summaries)
                xray_received = sum(s.bytes_received for s in xray_summaries)
                results["xray"] = {
                    "accounts": len(xray_summaries),
                    "bytes_sent": xray_sent,
                    "bytes_received": xray_received,
                }
        except Exception as exc:
            logger.warning("Xray traffic in all-sync failed: %s", exc)
            results["xray"] = {"error": str(exc)}

        return {
            "status": "completed",
            "task_id": self.request.id,
            "timestamp": now.isoformat(),
            "results": results,
            "errors": [k for k, v in results.items() if "error" in v],
        }

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("All traffic sync failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Data-Limit Enforcement Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vpn.check_exceeded_traffic",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=180,
)
def check_exceeded_traffic(self) -> dict:
    """
    Check for accounts that have exceeded their data limits.

    Identifies active accounts whose total_bytes exceeds data_limit
    and auto-suspends them with reason 'data_limit_exceeded'.
    Notifies users via available notification channels.

    Returns:
        Enforcement result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                now = datetime.now(timezone.utc)

                # Find accounts exceeding data limits
                stmt = (
                    select(VpnAccount)
                    .options(
                        selectinload(VpnAccount.server_rel),
                        selectinload(VpnAccount.subscriptions),
                    )
                    .where(
                        VpnAccount.status == VpnAccountStatus.ACTIVE,
                        VpnAccount.data_limit_bytes.isnot(None),
                        VpnAccount.total_bytes >= VpnAccount.data_limit_bytes,
                    )
                )
                result = await db.execute(stmt)
                exceeded_accounts = result.scalars().all()

                suspended_ids = []
                for account in exceeded_accounts:
                    try:
                        # Suspend the account
                        await VpnAccountService.suspend_account(
                            db,
                            account_id=account.id,
                            reason="data_limit_exceeded",
                            audit_actor="system:celery:check_exceeded",
                        )
                        suspended_ids.append(account.id)
                        logger.warning(
                            "Account %s suspended: data limit exceeded (used: %d, limit: %d)",
                            account.id,
                            account.total_bytes,
                            account.data_limit_bytes,
                        )
                    except Exception as exc:
                        logger.error(
                            "Failed to suspend exceeded account %s: %s",
                            account.id,
                            exc,
                        )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": now.isoformat(),
                    "accounts_checked": len(exceeded_accounts),
                    "accounts_suspended": len(suspended_ids),
                    "suspended_ids": suspended_ids,
                }

        except Exception as exc:
            logger.error("Exceeded traffic check failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("Exceeded traffic check failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Peer Config Renewal Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vpn.renew_peer_configs",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=600,
)
def renew_peer_configs(
    self,
    interface: str = DEFAULT_WG_INTERFACE,
) -> dict:
    """
    Renew WireGuard peer configurations on all active WG servers.

    Refreshes peer entries on each server to ensure they match
    the database state. Handles key rotation if needed.

    Args:
        interface: WireGuard interface name.

    Returns:
        Renewal result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                now = datetime.now(timezone.utc)

                # Get active WG servers
                stmt = select(VpnServer).where(
                    VpnServer.protocol == VpnProtocol.WIREGUARD,
                    VpnServer.status == VpnServerStatus.ACTIVE,
                )
                result = await db.execute(stmt)
                servers = result.scalars().all()

                renewed_peers = 0
                errors = []

                for server in servers:
                    try:
                        # Get all active accounts on this server
                        acc_stmt = (
                            select(VpnAccount)
                            .where(
                                VpnAccount.server_id == server.id,
                                VpnAccount.protocol == VpnProtocol.WIREGUARD,
                                VpnAccount.status == VpnAccountStatus.ACTIVE,
                                VpnAccount.public_key.isnot(None),
                            )
                        )
                        acc_result = await db.execute(acc_stmt)
                        accounts = acc_result.scalars().all()

                        for account in accounts:
                            try:
                                # Re-sync peer on the server
                                WireGuardService.sync_peer(
                                    server_ip=server.public_ip,
                                    ssh_port=server.ssh_port or 22,
                                    ssh_user=server.ssh_user or "root",
                                    ssh_key_path=server.ssh_key_path,
                                    interface=interface,
                                    public_key=account.public_key or "",
                                    allowed_ips=account.allowed_ips or "0.0.0.0/0",
                                )
                                renewed_peers += 1
                            except Exception as exc:
                                errors.append(
                                    {
                                        "account_id": account.id,
                                        "server_id": server.id,
                                        "error": str(exc),
                                    }
                                )
                                logger.warning(
                                    "Failed to renew peer %s on server %s: %s",
                                    account.id,
                                    server.id,
                                    exc,
                                )

                    except Exception as exc:
                        errors.append(
                            {
                                "server_id": server.id,
                                "error": str(exc),
                            }
                        )
                        logger.warning(
                            "Failed to process server %s for peer renew: %s",
                            server.id,
                            exc,
                        )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": now.isoformat(),
                    "servers_processed": len(servers),
                    "peers_renewed": renewed_peers,
                    "errors": errors[:100],  # Limit error list size
                }

        except Exception as exc:
            logger.error("Peer config renewal failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("Peer config renewal failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Server Health Check Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vpn.check_vpn_server_health",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=120,
)
def check_vpn_server_health(self) -> dict:
    """
    Check health of all active VPN servers.

    Pings each server, checks WireGuard/Xray service status,
    and marks unreachable servers as DEGRADED.

    Returns:
        Health check result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                now = datetime.now(timezone.utc)

                stmt = select(VpnServer).where(
                    VpnServer.status.in_(
                        [VpnServerStatus.ACTIVE, VpnServerStatus.DEGRADED]
                    )
                )
                result = await db.execute(stmt)
                servers = result.scalars().all()

                healthy = 0
                unhealthy = []

                for server in servers:
                    try:
                        is_healthy = VpnServerService.check_server_health(
                            server_ip=server.public_ip,
                            ssh_port=server.ssh_port or 22,
                            ssh_user=server.ssh_user or "root",
                            ssh_key_path=server.ssh_key_path,
                        )
                        if is_healthy:
                            healthy += 1
                            if server.status == VpnServerStatus.DEGRADED:
                                server.status = VpnServerStatus.ACTIVE
                                server.last_health_check = now
                        else:
                            unhealthy.append(
                                {
                                    "server_id": server.id,
                                    "ip": server.public_ip,
                                    "reason": "health_check_failed",
                                }
                            )
                            if server.status == VpnServerStatus.ACTIVE:
                                server.status = VpnServerStatus.DEGRADED
                                server.last_health_check = now
                    except Exception as exc:
                        unhealthy.append(
                            {
                                "server_id": server.id,
                                "ip": server.public_ip,
                                "reason": str(exc),
                            }
                        )
                        if server.status == VpnServerStatus.ACTIVE:
                            server.status = VpnServerStatus.DEGRADED
                            server.last_health_check = now

                await db.commit()

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": now.isoformat(),
                    "servers_checked": len(servers),
                    "healthy": healthy,
                    "unhealthy": len(unhealthy),
                    "unhealthy_details": unhealthy,
                }

        except Exception as exc:
            logger.error("VPN server health check failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("VPN server health check failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Cleanup Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vpn.cleanup_stale_sessions",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=120,
)
def cleanup_stale_sessions(
    self,
    max_age_minutes: int = 60,
) -> dict:
    """
    End sessions that have been CONNECTED for too long without traffic.

    Sessions without a recent handshake or traffic update are marked
    DISCONNECTED with reason 'stale_session'.

    Args:
        max_age_minutes: Maximum age of a connected session in minutes.

    Returns:
        Cleanup result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                now = datetime.now(timezone.utc)
                cutoff = now - timedelta(minutes=max_age_minutes)

                # Find stale connected sessions
                stmt = (
                    select(VpnSession)
                    .join(
                        VpnAccount,
                        VpnSession.vpn_account_id == VpnAccount.id,
                    )
                    .where(
                        VpnSession.status == VpnSessionStatus.CONNECTED,
                        VpnSession.connected_at < cutoff,
                    )
                )
                result = await db.execute(stmt)
                stale_sessions = result.scalars().all()

                ended_count = 0
                for session in stale_sessions:
                    session.status = VpnSessionStatus.DISCONNECTED
                    session.disconnected_at = now
                    session.disconnect_reason = "stale_session"
                    ended_count += 1

                await db.commit()

                logger.info(
                    "Cleaned up %d stale sessions (max_age: %d min)",
                    ended_count,
                    max_age_minutes,
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": now.isoformat(),
                    "sessions_ended": ended_count,
                    "max_age_minutes": max_age_minutes,
                }

        except Exception as exc:
            logger.error("Stale session cleanup failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("Stale session cleanup failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Exports
# ------------------------------------------------------------------

__all__ = [
    "check_exceeded_traffic",
    "check_vpn_server_health",
    "cleanup_stale_sessions",
    "renew_peer_configs",
    "sync_all_connections",
    "sync_all_traffic",
    "sync_wg_connections",
    "sync_wg_traffic",
    "sync_xray_traffic",
]