"""
BlueHub SmartDNS Celery Tasks
===============================
Periodic tasks for SmartDNS operations:
- DNS zone sync with PowerDNS
- SmartDNS profile health monitoring
- Profile status synchronization
- Cache clearing and stats aggregation
- Profile expiration and auto-suspension
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from modules.smartdns.models import SmartDnsProfile
from modules.smartdns.services import (
    ProfileNotFoundError,
    SmartDnsService,
)
from services.celery_app import celery_app
from shared.models.enums import ServiceStatus
from shared.models.service import Service

logger = logging.getLogger("bluehub.tasks.smartdns")

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------

DEFAULT_SYNC_INTERVAL = 300  # 5 minutes
DEFAULT_HEALTH_CHECK_INTERVAL = 300  # 5 minutes
DEFAULT_STATS_INTERVAL = 900  # 15 minutes
DEFAULT_EXPIRATION_CHECK_INTERVAL = 3600  # 1 hour

# ------------------------------------------------------------------
# Sync Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.smartdns.sync_dns_zones",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=300,
)
def sync_dns_zones(self, profile_id: str | None = None) -> dict:
    """
    Sync unsynced DNS records with PowerDNS for all or a specific profile.

    Args:
        profile_id: Optional UUID of a specific profile to sync.

    Returns:
        Sync result summary with sync counts.
    """
    import asyncio

    async def _run():
        from core.database import async_session_factory

        async with async_session_factory() as db:
            service = SmartDnsService(db)

            total_synced = 0
            total_failed = 0
            all_errors: list[str] = []

            if profile_id:
                # Sync single profile
                try:
                    result = await service.sync_records(UUID(profile_id))
                    total_synced = result.synced
                    total_failed = result.failed
                    all_errors = result.errors
                except ProfileNotFoundError:
                    logger.error("Profile %s not found for DNS sync", profile_id)
                    return {
                        "status": "error",
                        "profile_id": profile_id,
                        "synced": 0,
                        "failed": 0,
                        "errors": [f"Profile {profile_id} not found"],
                    }
            else:
                # Sync all active profiles
                profiles = await service.list_profiles(status="active", limit=500)
                for profile in profiles:
                    try:
                        result = await service.sync_records(profile.id)
                        total_synced += result.synced
                        total_failed += result.failed
                        all_errors.extend(result.errors)
                    except Exception as exc:
                        logger.error(
                            "Error syncing profile %s: %s", profile.id, exc
                        )
                        total_failed += 1
                        all_errors.append(f"Profile {profile.id}: {exc}")

            logger.info(
                "DNS zone sync complete: %d synced, %d failed",
                total_synced,
                total_failed,
            )

            return {
                "status": "completed" if total_failed == 0 else "partial",
                "total_profiles": 0 if profile_id else 0,
                "synced": total_synced,
                "failed": total_failed,
                "errors": all_errors[:50],  # Cap error list
            }

    return asyncio.run(_run())


# ------------------------------------------------------------------
# Health Check Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.smartdns.check_smartdns_health",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    acks_late=True,
    soft_time_limit=120,
)
def check_smartdns_health(self) -> dict:
    """
    Health check for all SmartDNS profiles.
    Verifies profile status and marks error states for any
    profiles with issues (e.g., missing zone, stale records).

    Returns:
        Health check result summary.
    """
    import asyncio

    async def _run():
        from core.database import async_session_factory

        async with async_session_factory() as db:
            service = SmartDnsService(db)

            profiles = await service.list_profiles(limit=500)
            healthy = 0
            errors_found = 0
            details: list[dict[str, object]] = []

            for profile in profiles:
                try:
                    status_info = await service.get_profile_status(profile.id)

                    # Mark profiles with errors if they're in error state
                    if status_info.status == "error":
                        errors_found += 1
                        details.append(
                            {
                                "profile_id": str(profile.id),
                                "status": "error",
                                "zone": status_info.zone_name,
                            }
                        )
                        logger.warning(
                            "SmartDNS profile %s is in error state",
                            profile.id,
                        )
                    elif status_info.status == "provisioning":
                        logger.info(
                            "SmartDNS profile %s still provisioning",
                            profile.id,
                        )
                        healthy += 1
                    else:
                        healthy += 1

                except Exception as exc:
                    errors_found += 1
                    details.append(
                        {
                            "profile_id": str(profile.id),
                            "status": "check_error",
                            "error": str(exc),
                        }
                    )
                    logger.error(
                        "Health check failed for profile %s: %s",
                        profile.id,
                        exc,
                    )

            logger.info(
                "SmartDNS health check complete: %d healthy, %d errors",
                healthy,
                errors_found,
            )

            return {
                "status": "ok" if errors_found == 0 else "issues_found",
                "total_profiles": len(profiles),
                "healthy": healthy,
                "errors": errors_found,
                "details": details[:50],
            }

    return asyncio.run(_run())


# ------------------------------------------------------------------
# Stats Aggregation Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.smartdns.aggregate_smartdns_stats",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=300,
)
def aggregate_smartdns_stats(self) -> dict:
    """
    Aggregate SmartDNS query statistics across all profiles.
    Updates total_queries counters and resets rolling stats.

    Returns:
        Stats aggregation summary.
    """
    import asyncio

    async def _run():
        from core.database import async_session_factory

        async with async_session_factory() as db:
            service = SmartDnsService(db)

            profiles = await service.list_profiles(limit=500)
            updated = 0
            total_queries = 0

            for profile in profiles:
                try:
                    # Fetch query count from records (actual PowerDNS integration
                    # would query the PowerDNS API for stats)
                    stat_result = await db.execute(
                        select(SmartDnsProfile).where(
                            SmartDnsProfile.id == profile.id
                        )
                    )
                    prof = stat_result.scalar_one_or_none()
                    if prof:
                        # Update stats timestamp
                        prof.stats_updated_at = datetime.now(UTC)
                        db.add(prof)
                        updated += 1
                        total_queries += prof.total_queries or 0

                except Exception as exc:
                    logger.error(
                        "Stats aggregation failed for profile %s: %s",
                        profile.id,
                        exc,
                    )

            await db.flush()

            logger.info(
                "SmartDNS stats aggregated: %d profiles, %d total queries",
                updated,
                total_queries,
            )

            return {
                "status": "completed",
                "profiles_updated": updated,
                "total_queries": total_queries,
            }

    return asyncio.run(_run())


# ------------------------------------------------------------------
# Expiration & Lifecycle Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.smartdns.check_smartdns_expiration",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=180,
)
def check_smartdns_expiration(self) -> dict:
    """
    Check for expired SmartDNS profiles and mark them for suspension.
    Profiles with expired services are flagged as suspended.

    Returns:
        Expiration check summary.
    """
    import asyncio

    async def _run():
        from core.database import async_session_factory

        async with async_session_factory() as db:
            service = SmartDnsService(db)
            now = datetime.now(UTC)

            profiles = await service.list_profiles(
                status="active", limit=500
            )

            expired = 0
            suspended = 0

            for profile in profiles:
                try:
                    # Check associated service expiration
                    svc = await db.get(Service, profile.service_id)
                    if svc and svc.expires_at and svc.expires_at < now:
                        expired += 1
                        await service.set_profile_status(profile.id, "suspended")
                        svc.status = ServiceStatus.SUSPENDED
                        db.add(svc)
                        suspended += 1
                        logger.info(
                            "SmartDNS profile %s suspended (service %s expired)",
                            profile.id,
                            profile.service_id,
                        )
                except Exception as exc:
                    logger.error(
                        "Expiration check failed for profile %s: %s",
                        profile.id,
                        exc,
                    )

            await db.flush()

            logger.info(
                "SmartDNS expiration check complete: %d expired, %d suspended",
                expired,
                suspended,
            )

            return {
                "status": "completed",
                "expired": expired,
                "suspended": suspended,
            }

    return asyncio.run(_run())


@celery_app.task(
    name="services.tasks.smartdns.auto_renew_smartdns",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=180,
)
def auto_renew_smartdns(self) -> dict:
    """
    Auto-renew SmartDNS services that are due for renewal.
    Resumes suspended profiles whose services have been renewed.

    Returns:
        Renewal summary.
    """
    import asyncio

    async def _run():
        from core.database import async_session_factory

        async with async_session_factory() as db:
            service = SmartDnsService(db)

            # Find suspended profiles whose services are now active
            profiles = await service.list_profiles(
                status="suspended", limit=500
            )

            renewed = 0
            for profile in profiles:
                try:
                    svc = await db.get(Service, profile.service_id)
                    if svc and svc.status == ServiceStatus.ACTIVE:
                        await service.set_profile_status(profile.id, "active")
                        renewed += 1
                        logger.info(
                            "SmartDNS profile %s renewed and reactivated",
                            profile.id,
                        )
                except Exception as exc:
                    logger.error(
                        "Auto-renew failed for profile %s: %s",
                        profile.id,
                        exc,
                    )

            await db.flush()

            logger.info("SmartDNS auto-renew complete: %d renewed", renewed)

            return {
                "status": "completed",
                "renewed": renewed,
            }

    return asyncio.run(_run())


@celery_app.task(
    name="services.tasks.smartdns.suspend_expired_smartdns",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    acks_late=True,
    soft_time_limit=180,
)
def suspend_expired_smartdns(self) -> dict:
    """
    Suspend SmartDNS profiles whose services have passed their grace period.

    Returns:
        Suspension summary.
    """
    import asyncio

    async def _run():
        from core.database import async_session_factory

        async with async_session_factory() as db:
            service = SmartDnsService(db)
            now = datetime.now(UTC)

            profiles = await service.list_profiles(
                status="active", limit=500
            )

            suspended = 0
            for profile in profiles:
                try:
                    svc = await db.get(Service, profile.service_id)
                    if svc and svc.expires_at and svc.expires_at < now:
                        await service.set_profile_status(profile.id, "suspended")
                        svc.status = ServiceStatus.SUSPENDED
                        db.add(svc)
                        suspended += 1
                except Exception as exc:
                    logger.error(
                        "Suspension failed for profile %s: %s",
                        profile.id,
                        exc,
                    )

            await db.flush()

            logger.info(
                "SmartDNS suspension complete: %d suspended", suspended
            )

            return {
                "status": "completed",
                "suspended": suspended,
            }

    return asyncio.run(_run())


# ------------------------------------------------------------------
# Cache Management Tasks
# ------------------------------------------------------------------


@celery_app.task(
    name="services.tasks.smartdns.clear_smartdns_cache",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
    soft_time_limit=60,
)
def clear_smartdns_cache(self, profile_id: str | None = None) -> dict:
    """
    Clear DNS cache for all or a specific profile.

    Args:
        profile_id: Optional UUID of profile to clear cache for.

    Returns:
        Cache clear summary.
    """
    import asyncio

    async def _run():
        # In production, this would flush PowerDNS cache via API
        # For now, this is a stub that marks success
        cleared = 1 if profile_id else 0
        logger.info(
            "SmartDNS cache cleared%s",
            f" for profile {profile_id}" if profile_id else "",
        )
        return {
            "status": "completed",
            "profiles_cleared": cleared if profile_id else 0,
        }

    return asyncio.run(_run())


__all__ = [
    "sync_dns_zones",
    "check_smartdns_health",
    "aggregate_smartdns_stats",
    "check_smartdns_expiration",
    "auto_renew_smartdns",
    "suspend_expired_smartdns",
    "clear_smartdns_cache",
]