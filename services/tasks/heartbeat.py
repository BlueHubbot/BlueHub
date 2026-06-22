"""
BlueHub Heartbeat Task
=======================
Periodic task to check system health and report status.
Runs every 5 minutes via Celery Beat.
"""

from __future__ import annotations

import logging
from datetime import timezone, datetime

from services.celery_app import celery_app

logger = logging.getLogger("bluehub.tasks.heartbeat")


@celery_app.task(
    name="services.tasks.heartbeat.heartbeat_check",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def heartbeat_check(self) -> dict:
    """
    Periodic health check task.

    Verifies that:
    - The Celery worker is alive and processing tasks
    - The broker connection is active
    - The task queue is responsive

    Returns heartbeat status information.
    """
    try:
        now = datetime.now(UTC)
        logger.info("Heartbeat check at %s", now.isoformat())

        result = {
            "status": "ok",
            "timestamp": now.isoformat(),
            "task_id": self.request.id,
            "worker": self.request.hostname or "unknown",
        }

        logger.debug("Heartbeat result: %s", result)
        return result

    except Exception as exc:
        logger.error("Heartbeat check failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(
    name="services.tasks.heartbeat.check_broker_connection",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def check_broker_connection(self) -> dict:
    """
    Verify broker (Redis) connection is healthy.
    Used by monitoring tasks to ensure the messaging layer is operational.
    """
    try:
        # The broker connection is implicitly verified by Celery
        # when this task is received and executed
        result = {
            "status": "connected",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        logger.debug("Broker connection check: %s", result["status"])
        return result

    except Exception as exc:
        logger.error("Broker connection check failed: %s", exc)
        raise self.retry(exc=exc)


__all__ = [
    "heartbeat_check",
    "check_broker_connection",
]
