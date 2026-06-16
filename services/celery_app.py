"""
BlueHub Celery Application
===========================
Celery configuration with Redis broker, task autodiscovery,
and Celery Beat scheduler setup.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from core.config import settings

# ── Celery Application ──────────────────────────────────────────────────────

celery_app = Celery(
    "bluehub",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "services.tasks.heartbeat",
        "services.tasks.maintenance",
        "services.tasks.monitoring",
        "services.tasks.vpn",
    ],
)

# ── Configuration ───────────────────────────────────────────────────────────

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_EAGER_PROPAGATES,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_TIME_LIMIT - 60,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
    worker_max_memory_per_child=150000,  # 150 MB
    beat_schedule_filename=settings.CELERY_BEAT_SCHEDULE_FILENAME,
    result_expires=86400,  # 24 hours
    # Default retry policy for all tasks
    task_default_retry_delay=60,
    task_max_retries=settings.CELERY_MAX_RETRIES,
    task_retry_backoff=True,
    task_retry_backoff_max=600,  # max 10 minutes between retries
    task_retry_jitter=True,
)

# ── Celery Beat Schedule ────────────────────────────────────────────────────

celery_app.conf.beat_schedule = {
    # Health check heartbeat every 5 minutes
    "heartbeat-every-5-minutes": {
        "task": "services.tasks.heartbeat.heartbeat_check",
        "schedule": 300.0,  # 5 minutes
        "args": (),
    },
    # Monitor service health every minute
    "monitor-health-every-minute": {
        "task": "services.tasks.monitoring.check_service_health",
        "schedule": 60.0,  # 1 minute
        "args": (),
    },
    # Database cleanup daily at 3 AM
    "cleanup-database-daily": {
        "task": "services.tasks.maintenance.database_cleanup",
        "schedule": crontab(hour=3, minute=0),
        "args": (),
    },
    # Audit log cleanup daily at 4 AM
    "cleanup-audit-logs-daily": {
        "task": "services.tasks.maintenance.cleanup_audit_logs",
        "schedule": crontab(hour=4, minute=0),
        "args": (),
    },
    # ── VPN Tasks ────────────────────────────────────────────────────────
    # Sync WireGuard connections every 2 minutes
    "vpn-sync-connections-every-2-minutes": {
        "task": "services.tasks.vpn.sync_wg_connections",
        "schedule": 120.0,  # 2 minutes
        "args": (),
    },
    # Poll WireGuard traffic every 5 minutes
    "vpn-sync-wg-traffic-every-5-minutes": {
        "task": "services.tasks.vpn.sync_wg_traffic",
        "schedule": 300.0,  # 5 minutes
        "args": (),
    },
    # Poll Xray traffic every 5 minutes
    "vpn-sync-xray-traffic-every-5-minutes": {
        "task": "services.tasks.vpn.sync_xray_traffic",
        "schedule": 300.0,  # 5 minutes
        "args": (),
    },
    # Check exceeded data limits every 10 minutes
    "vpn-check-exceeded-every-10-minutes": {
        "task": "services.tasks.vpn.check_exceeded_traffic",
        "schedule": 600.0,  # 10 minutes
        "args": (),
    },
    # Cleanup stale VPN sessions daily at 2 AM
    "vpn-cleanup-stale-sessions-daily": {
        "task": "services.tasks.vpn.cleanup_stale_sessions",
        "schedule": crontab(hour=2, minute=0),
        "args": (),
    },
    # Renew peer configs daily at 1 AM
    "vpn-renew-peer-configs-daily": {
        "task": "services.tasks.vpn.renew_peer_configs",
        "schedule": crontab(hour=1, minute=0),
        "args": (),
    },
    # Check VPN server health every 5 minutes
    "vpn-check-server-health-every-5-minutes": {
        "task": "services.tasks.vpn.check_vpn_server_health",
        "schedule": 300.0,  # 5 minutes
        "args": (),
    },
}

# ── Task Autodiscovery ──────────────────────────────────────────────────────

# Use on_after_finalize signal to avoid circular imports during module loading
@celery_app.on_after_finalize.connect
def autodiscover_tasks_after_finalize(sender: Celery, **kwargs) -> None:
    """Autodiscover tasks after Celery app is fully initialized."""
    sender.autodiscover_tasks(
        packages=[
            "services.tasks",
            "modules",
        ],
        related_name="tasks",
        force=True,
    )


def get_celery_app() -> Celery:
    """Get the configured Celery application instance."""
    return celery_app


__all__ = [
    "celery_app",
    "get_celery_app",
]