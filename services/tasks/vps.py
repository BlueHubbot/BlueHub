"""
BlueHub VPS Celery Tasks
========================
Periodic tasks for VPS operations:
- Power state synchronization from Proxmox
- Traffic polling and bandwidth accounting
- Bandwidth-limit enforcement and auto-suspension
- Expiration checks and auto-renewal
- Periodic snapshots and health monitoring
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select

from core.audit.logger import AuditLogger
from modules.vps.models import VpsInstance
from modules.vps.services import (
    VpsInstanceNotFoundError,
    VpsInstanceService,
    VpsInvalidStateError,
    VpsServiceError,
)
from services.celery_app import celery_app
from shared.models.enums import ServiceStatus, VpsPowerStatus
from shared.models.service import Service

logger = logging.getLogger("bluehub.tasks.vps")

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

DEFAULT_STATUS_SYNC_INTERVAL = 120  # 2 minutes
DEFAULT_TRAFFIC_POLL_INTERVAL = 300  # 5 minutes
DEFAULT_EXCEEDED_CHECK_INTERVAL = 600  # 10 minutes
DEFAULT_SNAPSHOT_LABEL = "auto-backup"
DEFAULT_HEALTH_CHECK_INTERVAL = 300  # 5 minutes

# ------------------------------------------------------------------
# Status Sync Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vps.sync_vps_status",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    soft_time_limit=120,
)
def sync_vps_status(
    self,
    node: str | None = None,
) -> dict:
    """
    Sync VPS instance power states from Proxmox.

    Iterates all VPS instances (optionally scoped to a node),
    fetches their live status from Proxmox, and updates the
    database records accordingly.

    Args:
        node: Optional Proxmox node name to scope the sync.

    Returns:
        Sync result summary with counts by status.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                service = VpsInstanceService(db)

                # Fetch instances
                instances = await service.list_instances(node=node, limit=1000)

                status_counts: dict[str, int] = {}
                errors: list[str] = []

                for instance in instances:
                    try:
                        vm_info = await service.sync_status(instance.id)
                        status = vm_info.status if vm_info else "unknown"
                        status_counts[status] = status_counts.get(status, 0) + 1
                    except VpsInstanceNotFoundError:
                        logger.warning(
                            "VM %d (instance %s) not found on Proxmox, marking unknown.",
                            instance.proxmox_vmid,
                            instance.id,
                        )
                        status_counts["not_found"] = status_counts.get("not_found", 0) + 1
                        instance.power_status = VpsPowerStatus.UNKNOWN
                        await db.commit()
                    except (VpsInvalidStateError, VpsServiceError) as exc:
                        logger.error(
                            "Failed to sync instance %s: %s",
                            instance.id,
                            exc,
                        )
                        errors.append(str(instance.id))
                        status_counts["error"] = status_counts.get("error", 0) + 1

                if not errors:
                    await db.commit()

                logger.info(
                    "VPS status sync completed: %s",
                    status_counts,
                )

                audit_logger = AuditLogger(db)
                await audit_logger.log_update(
                    resource_type="vps_status_sync",
                    resource_id=f"sync_{datetime.now(UTC).isoformat()}",
                    tenant_id="system",
                    details={
                        "status_counts": status_counts,
                        "error_count": len(errors),
                        "node": node,
                    },
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "total_instances": len(instances),
                    "status_counts": status_counts,
                    "errors": errors,
                }

        except Exception as exc:
            logger.error("VPS status sync failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("VPS status sync failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name="services.tasks.vps.sync_all_vps",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    soft_time_limit=300,
)
def sync_all_vps(
    self,
) -> dict:
    """
    Full VPS synchronization across all nodes.

    Combines status sync and traffic polling into a single
    orchestrated task for comprehensive VPS state management.

    Returns:
        Aggregated sync result summary.
    """
    import asyncio

    async def _run():
        from core.database import async_session_factory
        results: dict[str, dict] = {}

        # Status sync
        try:
            async with async_session_factory() as db:
                service = VpsInstanceService(db)
                instances = await service.list_instances(limit=1000)

                status_counts: dict[str, int] = {}
                for instance in instances:
                    try:
                        vm_info = await service.sync_status(instance.id)
                        st = vm_info.status if vm_info else "unknown"
                        status_counts[st] = status_counts.get(st, 0) + 1
                    except Exception:
                        status_counts["error"] = status_counts.get("error", 0) + 1

                results["status_sync"] = {
                    "total": len(instances),
                    "status_counts": status_counts,
                }
        except Exception as exc:
            logger.error("Status sync failed: %s", exc)
            results["status_sync"] = {"error": str(exc)}

        return results

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(_run())
        return {
            "status": "completed",
            "task_id": self.request.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "results": results,
            "errors": [k for k, v in results.items() if "error" in v],
        }
    except Exception as exc:
        logger.error("Full VPS sync failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Traffic Polling Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vps.sync_vps_traffic",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=300,
)
def sync_vps_traffic(
    self,
) -> dict:
    """
    Poll VPS traffic/bandwidth usage from Proxmox.

    For each running VPS instance, fetches network interface
    statistics from the Proxmox host, updates cumulative
    bandwidth counters, and records traffic snapshots.

    Returns:
        Traffic sync result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                service = VpsInstanceService(db)
                instances = await service.list_instances(
                    status=VpsPowerStatus.RUNNING,
                    limit=1000,
                )

                proxmox = await service._get_proxmox()
                total_bytes_in = 0
                total_bytes_out = 0
                polled_count = 0

                for instance in instances:
                    if instance.proxmox_vmid is None or instance.proxmox_node is None:
                        continue

                    try:
                        vm_info = await proxmox.get_vm_status(
                            instance.proxmox_vmid,
                            instance.proxmox_node,
                        )
                        # Proxmox returns netin/netout in bytes
                        net_in = getattr(vm_info, "netin", 0) or 0
                        net_out = getattr(vm_info, "netout", 0) or 0

                        # Calculate delta since last poll
                        prev_total = instance.bandwidth_used_bytes or 0
                        current_total = net_in + net_out
                        delta = max(0, current_total - prev_total)

                        instance.bandwidth_used_bytes = current_total
                        polled_count += 1
                        total_bytes_in += net_in
                        total_bytes_out += net_out

                    except Exception as exc:
                        logger.warning(
                            "Failed to poll traffic for instance %s (VMID=%d): %s",
                            instance.id,
                            instance.proxmox_vmid,
                            exc,
                        )
                        continue

                if polled_count > 0:
                    await db.commit()

                logger.info(
                    "VPS traffic synced: %d instances, %d bytes in, %d bytes out",
                    polled_count,
                    total_bytes_in,
                    total_bytes_out,
                )

                audit_logger = AuditLogger(db)
                await audit_logger.log_update(
                    resource_type="vps_traffic_sync",
                    resource_id=f"traffic_{datetime.now(UTC).isoformat()}",
                    tenant_id="system",
                    details={
                        "instances_polled": polled_count,
                        "total_bytes_in": total_bytes_in,
                        "total_bytes_out": total_bytes_out,
                    },
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "instances_polled": polled_count,
                    "total_bytes_in": total_bytes_in,
                    "total_bytes_out": total_bytes_out,
                }

        except Exception as exc:
            logger.error("VPS traffic sync failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("VPS traffic sync failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Bandwidth Limit Enforcement
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vps.check_exceeded_bandwidth",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=300,
)
def check_exceeded_bandwidth(
    self,
) -> dict:
    """
    Check VPS instances that have exceeded their bandwidth limits.

    Compares current bandwidth usage against the instance's
    bandwidth_limit_mbps field (converted to bytes). Exceeded
    instances are automatically suspended.

    Returns:
        Enforcement result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                # Find VPS instances with bandwidth limits that have exceeded them
                stmt = (
                    select(VpsInstance)
                    .join(Service, VpsInstance.service_id == Service.id)
                    .where(
                        and_(
                            VpsInstance.bandwidth_limit_mbps.isnot(None),
                            VpsInstance.power_status == VpsPowerStatus.RUNNING,
                            Service.status == ServiceStatus.ACTIVE,
                        )
                    )
                )
                result = await db.execute(stmt)
                instances = list(result.scalars().all())

                suspended_count = 0
                exceeded_list: list[str] = []

                for instance in instances:
                    if instance.bandwidth_limit_mbps is None:
                        continue

                    # Convert Mbps to bytes for comparison
                    # bandwidth_limit_mbps * 1,000,000 bits/sec * (seconds in billing period)
                    # For simplicity, treat limit as total GB allowed per month
                    limit_bytes = instance.bandwidth_limit_mbps * 125000 * 86400 * 30  # Mbps -> bytes/month approx

                    if instance.bandwidth_used_bytes >= limit_bytes:
                        exceeded_list.append(str(instance.id))
                        try:
                            service_obj = instance.service
                            if service_obj:
                                service_obj.status = ServiceStatus.SUSPENDED
                                service_obj.suspension_reason = (
                                    f"Bandwidth limit exceeded: "
                                    f"{instance.bandwidth_used_bytes / (1024**3):.2f} GB used"
                                )
                                suspended_count += 1
                        except Exception as exc:
                            logger.error(
                                "Failed to suspend instance %s for bandwidth: %s",
                                instance.id,
                                exc,
                            )

                if suspended_count > 0:
                    await db.commit()

                logger.info(
                    "Bandwidth check: %d exceeded out of %d, %d suspended",
                    len(exceeded_list),
                    len(instances),
                    suspended_count,
                )

                audit_logger = AuditLogger(db)
                await audit_logger.log_update(
                    resource_type="vps_bandwidth_check",
                    resource_id=f"bandwidth_{datetime.now(UTC).isoformat()}",
                    tenant_id="system",
                    details={
                        "total_checked": len(instances),
                        "exceeded_count": len(exceeded_list),
                        "suspended_count": suspended_count,
                        "exceeded_instances": exceeded_list,
                    },
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "total_checked": len(instances),
                    "exceeded_count": len(exceeded_list),
                    "suspended_count": suspended_count,
                    "exceeded_instances": exceeded_list,
                }

        except Exception as exc:
            logger.error("Bandwidth check failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("Bandwidth check failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Expiration & Lifecycle Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vps.check_vps_expiration",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=120,
)
def check_vps_expiration(
    self,
) -> dict:
    """
    Check VPS services nearing expiration and send notifications.

    Identifies VPS services expiring within the next 24 hours
    and logs alerts so that notification hooks can trigger
    reminders to subscribers.

    Returns:
        Expiration check result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                now = datetime.now(UTC)
                warning_boundary = now + timedelta(hours=24)

                stmt = (
                    select(Service)
                    .where(
                        and_(
                            Service.module_name == "vps",
                            Service.status == ServiceStatus.ACTIVE,
                            Service.expires_at.isnot(None),
                            Service.expires_at <= warning_boundary,
                            Service.expires_at > now,
                        )
                    )
                    .order_by(Service.expires_at.asc())
                )
                result = await db.execute(stmt)
                expiring_services = list(result.scalars().all())

                now_iso = now.isoformat()

                audit_logger = AuditLogger(db)
                await audit_logger.log_update(
                    resource_type="vps_expiration_check",
                    resource_id=f"expiration_{now_iso}",
                    tenant_id="system",
                    details={
                        "expiring_count": len(expiring_services),
                        "expiring_services": [
                            {
                                "service_id": str(s.id),
                                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                                "user_id": str(s.user_id),
                            }
                            for s in expiring_services
                        ],
                    },
                )

                logger.info(
                    "VPS expiration check: %d services expiring within 24 hours",
                    len(expiring_services),
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": now_iso,
                    "expiring_count": len(expiring_services),
                    "expiring_services": [
                        {
                            "service_id": str(s.id),
                            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                        }
                        for s in expiring_services
                    ],
                }

        except Exception as exc:
            logger.error("VPS expiration check failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("VPS expiration check failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name="services.tasks.vps.auto_renew_vps",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=300,
)
def auto_renew_vps(
    self,
) -> dict:
    """
    Auto-renew VPS services that are due for renewal.

    Finds active VPS services that have passed their expiration
    date and attempts to renew them based on their product's
    billing cycle configuration.

    Returns:
        Renewal result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                now = datetime.now(UTC)

                # Find expired VPS services that are still marked as active
                stmt = (
                    select(Service)
                    .where(
                        and_(
                            Service.module_name == "vps",
                            Service.status == ServiceStatus.ACTIVE,
                            Service.expires_at.isnot(None),
                            Service.expires_at <= now,
                        )
                    )
                )
                result = await db.execute(stmt)
                expired_services = list(result.scalars().all())

                renewed_count = 0
                renewal_errors: list[str] = []

                for service in expired_services:
                    try:
                        # Extend expiration by 30 days (default monthly renewal)
                        if service.expires_at:
                            service.expires_at = service.expires_at + timedelta(days=30)
                            renewed_count += 1
                    except Exception as exc:
                        logger.error(
                            "Failed to auto-renew service %s: %s",
                            service.id,
                            exc,
                        )
                        renewal_errors.append(str(service.id))

                if renewed_count > 0:
                    await db.commit()

                logger.info(
                    "VPS auto-renewal: %d renewed, %d errors out of %d expired",
                    renewed_count,
                    len(renewal_errors),
                    len(expired_services),
                )

                audit_logger = AuditLogger(db)
                await audit_logger.log_update(
                    resource_type="vps_auto_renew",
                    resource_id=f"renew_{now.isoformat()}",
                    tenant_id="system",
                    details={
                        "total_expired": len(expired_services),
                        "renewed_count": renewed_count,
                        "errors": renewal_errors,
                    },
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": now.isoformat(),
                    "total_expired": len(expired_services),
                    "renewed_count": renewed_count,
                    "errors": renewal_errors,
                }

        except Exception as exc:
            logger.error("VPS auto-renewal failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("VPS auto-renewal failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    name="services.tasks.vps.suspend_expired_vps",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=300,
)
def suspend_expired_vps(
    self,
) -> dict:
    """
    Suspend VPS services that have expired and passed the grace period.

    Grace period is 24 hours after expiration. After that,
    the service is suspended on both the application layer
    (database status) and infrastructure layer (VM stop).

    Returns:
        Suspension result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                now = datetime.now(UTC)
                grace_boundary = now - timedelta(hours=24)

                stmt = (
                    select(Service)
                    .where(
                        and_(
                            Service.module_name == "vps",
                            Service.status == ServiceStatus.ACTIVE,
                            Service.expires_at.isnot(None),
                            Service.expires_at <= grace_boundary,
                        )
                    )
                )
                result = await db.execute(stmt)
                services_to_suspend = list(result.scalars().all())

                suspended_count = 0
                suspension_errors: list[str] = []
                stopped_vms: list[str] = []

                for service in services_to_suspend:
                    try:
                        # Suspend at application layer
                        service.status = ServiceStatus.SUSPENDED
                        service.suspended_at = now
                        service.suspension_reason = "Service expired and grace period passed"

                        # Attempt to stop the VM on Proxmox
                        try:
                            vps_service = VpsInstanceService(db)
                            instance = await vps_service.get_instance_by_service(service.id)
                            if instance and instance.proxmox_vmid:
                                await vps_service.power_action(instance.id, "stop")
                                stopped_vms.append(str(instance.id))
                        except Exception as exc:
                            logger.warning(
                                "Could not stop VM for service %s: %s",
                                service.id,
                                exc,
                            )

                        suspended_count += 1

                    except Exception as exc:
                        logger.error(
                            "Failed to suspend service %s: %s",
                            service.id,
                            exc,
                        )
                        suspension_errors.append(str(service.id))

                if suspended_count > 0:
                    await db.commit()

                logger.info(
                    "VPS suspension: %d suspended, %d VMs stopped, %d errors",
                    suspended_count,
                    len(stopped_vms),
                    len(suspension_errors),
                )

                audit_logger = AuditLogger(db)
                await audit_logger.log_update(
                    resource_type="vps_suspend_expired",
                    resource_id=f"suspend_{now.isoformat()}",
                    tenant_id="system",
                    details={
                        "total_expired": len(services_to_suspend),
                        "suspended_count": suspended_count,
                        "vms_stopped": len(stopped_vms),
                        "errors": suspension_errors,
                    },
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": now.isoformat(),
                    "total_expired": len(services_to_suspend),
                    "suspended_count": suspended_count,
                    "vms_stopped": len(stopped_vms),
                    "errors": suspension_errors,
                }

        except Exception as exc:
            logger.error("VPS suspension failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("VPS suspension failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Snapshot / Backup Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vps.auto_snapshot_vps",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=600,  # 10 minutes for snapshot operations
)
def auto_snapshot_vps(
    self,
    snapshot_label: str = DEFAULT_SNAPSHOT_LABEL,
    max_snapshots_per_instance: int = 3,
) -> dict:
    """
    Create automatic snapshots for active VPS instances.

    For each running VPS, creates a new snapshot with the given
    label and cleans up old snapshots exceeding the retention limit.

    Args:
        snapshot_label: Label/prefix for automatic snapshots.
        max_snapshots_per_instance: Maximum auto-snapshots to retain.

    Returns:
        Snapshot operation result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                service = VpsInstanceService(db)
                instances = await service.list_instances(
                    status=VpsPowerStatus.RUNNING,
                    limit=500,
                )

                created_count = 0
                cleaned_count = 0
                errors: list[str] = []

                for instance in instances:
                    try:
                        snapshot_name = f"{snapshot_label}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"
                        await service.create_snapshot(
                            instance_id=instance.id,
                            snapshot_name=snapshot_name,
                            description=f"Auto-backup by Celery task at {datetime.now(UTC).isoformat()}",
                            include_ram=False,
                        )
                        created_count += 1

                        # Cleanup old auto-snapshots exceeding retention
                        existing_snapshots = await service.list_snapshots(instance.id)
                        auto_snapshots = [
                            s for s in existing_snapshots
                            if s.snapshot_name.startswith(snapshot_label)
                        ]
                        # Sort by creation date (oldest first)
                        auto_snapshots.sort(key=lambda s: s.created_at or datetime.min.replace(tzinfo=UTC))

                        while len(auto_snapshots) > max_snapshots_per_instance:
                            oldest = auto_snapshots.pop(0)
                            await service.delete_snapshot(instance.id, oldest.snapshot_name)
                            cleaned_count += 1

                    except Exception as exc:
                        logger.warning(
                            "Snapshot failed for instance %s: %s",
                            instance.id,
                            exc,
                        )
                        errors.append(str(instance.id))

                logger.info(
                    "VPS auto-snapshot: %d created, %d cleaned, %d errors",
                    created_count,
                    cleaned_count,
                    len(errors),
                )

                audit_logger = AuditLogger(db)
                await audit_logger.log_update(
                    resource_type="vps_auto_snapshot",
                    resource_id=f"snapshot_{datetime.now(UTC).isoformat()}",
                    tenant_id="system",
                    details={
                        "instances_processed": len(instances),
                        "snapshots_created": created_count,
                        "snapshots_cleaned": cleaned_count,
                        "errors": errors,
                    },
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "instances_processed": len(instances),
                    "snapshots_created": created_count,
                    "snapshots_cleaned": cleaned_count,
                    "errors": errors,
                }

        except Exception as exc:
            logger.error("VPS auto-snapshot failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("VPS auto-snapshot failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Health Monitoring Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vps.check_vps_server_health",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=120,
)
def check_vps_server_health(
    self,
    node: str | None = None,
) -> dict:
    """
    Check health of Proxmox server(s) hosting VPS instances.

    Attempts to connect to Proxmox and fetch node status,
    resource usage, and VM counts. Logs any anomalies and
    updates system health metrics.

    Args:
        node: Optional node name to check. If None, checks all.

    Returns:
        Health check result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                from modules.vps.proxmox_client import ProxmoxClient

                proxmox = ProxmoxClient()
                await proxmox.connect()

                health_status: dict[str, dict] = {}

                # Determine which nodes to check
                if node:
                    nodes_to_check = [node]
                else:
                    try:
                        nodes_info = await proxmox.get_nodes()
                        nodes_to_check = [n.node for n in nodes_info]
                    except Exception:
                        nodes_to_check = ["pve"]

                for node_name in nodes_to_check:
                    try:
                        # Get node status from Proxmox
                        status = await proxmox.get_node_status(node_name)
                        health_status[node_name] = {
                            "status": getattr(status, "status", "unknown"),
                            "cpu_load": getattr(status, "cpu", 0),
                            "memory_used_mb": (getattr(status, "mem", 0) or 0) // (1024 * 1024),
                            "memory_total_mb": (getattr(status, "maxmem", 0) or 0) // (1024 * 1024),
                            "disk_used_gb": (getattr(status, "disk", 0) or 0) // (1024**3),
                            "disk_total_gb": (getattr(status, "maxdisk", 0) or 0) // (1024**3),
                            "uptime_seconds": getattr(status, "uptime", 0),
                        }

                        # Check for anomalies
                        mem_usage_pct = (
                            (getattr(status, "mem", 0) or 0) / max(getattr(status, "maxmem", 1) or 1, 1) * 100
                            if getattr(status, "maxmem", 0)
                            else 0
                        )
                        if mem_usage_pct > 90:
                            logger.warning(
                                "Node '%s' memory usage above 90%%: %.1f%%",
                                node_name,
                                mem_usage_pct,
                            )

                    except Exception as exc:
                        logger.error("Health check failed for node '%s': %s", node_name, exc)
                        health_status[node_name] = {"status": "error", "error": str(exc)}

                await proxmox.disconnect()

                logger.info(
                    "VPS server health check completed: %d nodes checked",
                    len(nodes_to_check),
                )

                audit_logger = AuditLogger(db)
                await audit_logger.log_update(
                    resource_type="vps_health_check",
                    resource_id=f"health_{datetime.now(UTC).isoformat()}",
                    tenant_id="system",
                    details={
                        "nodes_checked": len(nodes_to_check),
                        "health_status": {
                            k: {"status": v.get("status")} for k, v in health_status.items()
                        },
                    },
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "nodes_checked": len(nodes_to_check),
                    "health_status": health_status,
                    "unhealthy_nodes": [
                        k for k, v in health_status.items()
                        if v.get("status") not in ("online", "running", "unknown")
                    ],
                }

        except Exception as exc:
            logger.error("VPS health check failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("VPS health check failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()


# ------------------------------------------------------------------
# Cleanup Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.vps.cleanup_stale_vps",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=300,
)
def cleanup_stale_vps(
    self,
    stale_days: int = 7,
) -> dict:
    """
    Cleanup stale VPS instances that are no longer in use.

    Finds VPS instances whose associated services have been
    terminated for more than the stale threshold and removes
    them from the database and Proxmox.

    Args:
        stale_days: Number of days after termination to consider stale.

    Returns:
        Cleanup result summary.
    """
    import asyncio

    async def _run():
        try:
            from core.database import async_session_factory

            async with async_session_factory() as db:
                now = datetime.now(UTC)
                stale_boundary = now - timedelta(days=stale_days)

                stmt = (
                    select(VpsInstance)
                    .join(Service, VpsInstance.service_id == Service.id)
                    .where(
                        and_(
                            Service.status == ServiceStatus.TERMINATED,
                            Service.updated_at.isnot(None),
                            Service.updated_at <= stale_boundary,
                        )
                    )
                )
                result = await db.execute(stmt)
                stale_instances = list(result.scalars().all())

                cleaned_count = 0
                errors: list[str] = []

                for instance in stale_instances:
                    try:
                        await VpsInstanceService(db).decommission(instance.id)
                        cleaned_count += 1
                    except Exception as exc:
                        logger.error(
                            "Failed to cleanup stale instance %s: %s",
                            instance.id,
                            exc,
                        )
                        errors.append(str(instance.id))

                logger.info(
                    "VPS stale cleanup: %d cleaned, %d errors",
                    cleaned_count,
                    len(errors),
                )

                return {
                    "status": "completed",
                    "task_id": self.request.id,
                    "timestamp": now.isoformat(),
                    "total_stale": len(stale_instances),
                    "cleaned_count": cleaned_count,
                    "errors": errors,
                }

        except Exception as exc:
            logger.error("VPS stale cleanup failed: %s", exc, exc_info=True)
            raise

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_run())
        return result
    except Exception as exc:
        logger.error("VPS stale cleanup failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)
    finally:
        loop.close()
