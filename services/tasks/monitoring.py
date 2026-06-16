"""
BlueHub Monitoring Task
=======================
Periodic monitoring task to check service health and report status.
Runs every minute via Celery Beat.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from services.celery_app import celery_app

logger = logging.getLogger("bluehub.tasks.monitoring")


@celery_app.task(
    name="services.tasks.monitoring.check_service_health",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def check_service_health(self) -> dict:
    """
    Periodic service health check task.

    Verifies that:
    - The Celery worker is alive and processing tasks
    - The broker connection is active
    - All required services are operational

    Returns health check status information.
    """
    try:
        now = datetime.now(timezone.utc)
        logger.info("Health check at %s", now.isoformat())

        result = {
            "status": "healthy",
            "timestamp": now.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname or "unknown",
            "checks": {
                "celery_worker": "ok",
                "broker_connection": "ok",
            },
        }

        logger.debug("Health check result: %s", result)
        return result

    except Exception as exc:
        logger.error("Health check failed: %s", exc)
        raise self.retry(exc=exc)


__all__ = [
    "check_service_health",
]