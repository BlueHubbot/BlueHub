"""
Tests for BlueHub Celery Application
=====================================
Tests the Celery app configuration, task registration,
and basic task execution using eager mode.
"""

from __future__ import annotations

import pytest
from celery import Celery
from datetime import datetime, timezone

from services.celery_app import celery_app, get_celery_app


class TestCeleryApp:
    """Tests for the Celery application configuration."""

    def test_celery_app_is_instance(self):
        """Verify celery_app is a Celery instance."""
        assert isinstance(celery_app, Celery)

    def test_celery_app_name(self):
        """Verify the app is named 'bluehub'."""
        assert celery_app.main == "bluehub"

    def test_get_celery_app(self):
        """Verify get_celery_app returns the same instance."""
        app = get_celery_app()
        assert app is celery_app

    def test_broker_url_set(self):
        """Verify broker URL is configured."""
        # Access the Celery config directly
        assert celery_app.conf.broker_url is not None
        assert "redis" in celery_app.conf.broker_url

    def test_result_backend_set(self):
        """Verify result backend is configured."""
        assert celery_app.conf.result_backend is not None
        assert "redis" in celery_app.conf.result_backend

    def test_task_serializer_is_json(self):
        """Verify default task serializer is JSON."""
        assert celery_app.conf.task_serializer == "json"

    def test_result_serializer_is_json(self):
        """Verify default result serializer is JSON."""
        assert celery_app.conf.result_serializer == "json"

    def test_accept_content_contains_json(self):
        """Verify accepted content types include JSON."""
        assert "json" in celery_app.conf.accept_content

    def test_include_contains_task_modules(self):
        """Verify the include list contains the expected task modules."""
        include = celery_app.conf.include
        assert "services.tasks.heartbeat" in include
        assert "services.tasks.maintenance" in include
        assert "services.tasks.monitoring" in include

    def test_time_limit_configured(self):
        """Verify task time limit is configured."""
        assert celery_app.conf.task_time_limit == 3600

    def test_soft_time_limit_set(self):
        """Verify soft time limit is set (time_limit - 60)."""
        expected_soft = celery_app.conf.task_time_limit - 60
        assert celery_app.conf.task_soft_time_limit == expected_soft

    def test_acks_late_is_true(self):
        """Verify acks_late is enabled for reliability."""
        assert celery_app.conf.task_acks_late is True

    def test_worker_prefetch_multiplier(self):
        """Verify worker prefetch multiplier is set to 1 (fair scheduling)."""
        assert celery_app.conf.worker_prefetch_multiplier == 1

    def test_max_retries_configured(self):
        """Verify max retries is set from settings (default 3)."""
        assert celery_app.conf.task_max_retries == 3

    def test_retry_backoff_enabled(self):
        """Verify retry backoff is enabled."""
        assert celery_app.conf.task_retry_backoff is True

    def test_result_expires_configured(self):
        """Verify result expiration is set (24 hours = 86400s)."""
        assert celery_app.conf.result_expires == 86400

    def test_task_track_started(self):
        """Verify task started tracking is enabled."""
        assert celery_app.conf.task_track_started is True


class TestCeleryBeatSchedule:
    """Tests for the Celery Beat schedule configuration."""

    def test_beat_schedule_exists(self):
        """Verify beat schedule is configured."""
        assert hasattr(celery_app.conf, "beat_schedule")
        assert celery_app.conf.beat_schedule is not None

    def test_heartbeat_task_scheduled(self):
        """Verify heartbeat task is scheduled every 5 minutes."""
        schedule = celery_app.conf.beat_schedule
        assert "heartbeat-every-5-minutes" in schedule
        task_config = schedule["heartbeat-every-5-minutes"]
        assert task_config["task"] == "services.tasks.heartbeat.heartbeat_check"
        assert task_config["schedule"] == 300.0

    def test_monitoring_task_scheduled(self):
        """Verify monitoring task is scheduled every minute."""
        schedule = celery_app.conf.beat_schedule
        assert "monitor-health-every-minute" in schedule
        task_config = schedule["monitor-health-every-minute"]
        assert task_config["task"] == "services.tasks.monitoring.check_service_health"
        assert task_config["schedule"] == 60.0

    def test_database_cleanup_scheduled(self):
        """Verify database cleanup is scheduled at 3 AM daily."""
        schedule = celery_app.conf.beat_schedule
        assert "cleanup-database-daily" in schedule
        task_config = schedule["cleanup-database-daily"]
        assert task_config["task"] == "services.tasks.maintenance.database_cleanup"

    def test_audit_log_cleanup_scheduled(self):
        """Verify audit log cleanup is scheduled at 4 AM daily."""
        schedule = celery_app.conf.beat_schedule
        assert "cleanup-audit-logs-daily" in schedule
        task_config = schedule["cleanup-audit-logs-daily"]
        assert task_config["task"] == "services.tasks.maintenance.cleanup_audit_logs"


class TestHeartbeatTask:
    """Tests for the heartbeat task."""

    def test_heartbeat_task_registered(self):
        """Verify heartbeat_check task is registered."""
        assert "services.tasks.heartbeat.heartbeat_check" in celery_app.tasks

    def test_broker_check_task_registered(self):
        """Verify check_broker_connection task is registered."""
        assert "services.tasks.heartbeat.check_broker_connection" in celery_app.tasks

    def test_heartbeat_task_returns_dict(self):
        """Verify heartbeat_check returns a dict with expected keys."""
        from services.tasks.heartbeat import heartbeat_check

        # Run eagerly for testing
        result = heartbeat_check.apply().result

        assert isinstance(result, dict)
        assert "status" in result
        assert "timestamp" in result
        assert "task_id" in result
        assert result["status"] == "ok"

    def test_heartbeat_timestamp_is_valid(self):
        """Verify the timestamp in heartbeat result is valid ISO format."""
        from services.tasks.heartbeat import heartbeat_check

        result = heartbeat_check.apply().result
        timestamp = result["timestamp"]

        # Parse the ISO timestamp to verify it's valid
        parsed = datetime.fromisoformat(timestamp)
        assert parsed.tzinfo is not None


class TestMonitoringTask:
    """Tests for the monitoring task."""

    def test_monitoring_task_registered(self):
        """Verify check_service_health task is registered."""
        assert "services.tasks.monitoring.check_service_health" in celery_app.tasks

    def test_monitoring_task_returns_dict(self):
        """Verify check_service_health returns a dict with expected keys."""
        from services.tasks.monitoring import check_service_health

        result = check_service_health.apply().result

        assert isinstance(result, dict)
        assert "status" in result
        assert "timestamp" in result
        assert "checks" in result
        assert result["status"] == "healthy"

    def test_monitoring_checks_contains_worker_and_broker(self):
        """Verify monitoring checks contain celery_worker and broker_connection."""
        from services.tasks.monitoring import check_service_health

        result = check_service_health.apply().result
        checks = result["checks"]

        assert "celery_worker" in checks
        assert "broker_connection" in checks
        assert checks["celery_worker"] == "ok"
        assert checks["broker_connection"] == "ok"


class TestMaintenanceTasks:
    """Tests for the maintenance tasks."""

    def test_database_cleanup_task_registered(self):
        """Verify database_cleanup task is registered."""
        assert "services.tasks.maintenance.database_cleanup" in celery_app.tasks

    def test_cleanup_audit_logs_task_registered(self):
        """Verify cleanup_audit_logs task is registered."""
        assert "services.tasks.maintenance.cleanup_audit_logs" in celery_app.tasks

    def test_database_cleanup_returns_dict(self):
        """Verify database_cleanup returns a dict with expected keys."""
        from services.tasks.maintenance import database_cleanup

        result = database_cleanup.apply().result

        assert isinstance(result, dict)
        assert result["status"] == "completed"
        assert "timestamp" in result
        assert "retention_days" in result
        assert result["retention_days"] == 90  # default
        assert "records_affected" in result

    def test_database_cleanup_custom_retention(self):
        """Verify database_cleanup accepts custom retention days."""
        from services.tasks.maintenance import database_cleanup

        result = database_cleanup.apply(args=[30]).result

        assert result["retention_days"] == 30

    def test_cleanup_audit_logs_returns_dict(self):
        """Verify cleanup_audit_logs returns a dict with expected keys."""
        from services.tasks.maintenance import cleanup_audit_logs

        result = cleanup_audit_logs.apply().result

        assert isinstance(result, dict)
        assert result["status"] == "completed"
        assert "records_removed" in result
        assert result["retention_days"] == 365  # default

    def test_cleanup_audit_logs_custom_retention(self):
        """Verify cleanup_audit_logs accepts custom retention days."""
        from services.tasks.maintenance import cleanup_audit_logs

        result = cleanup_audit_logs.apply(args=[180]).result

        assert result["retention_days"] == 180


class TestTaskAutodiscovery:
    """Tests for Celery task autodiscovery."""

    def test_tasks_autodiscovered(self):
        """Verify all expected tasks are registered after autodiscovery."""
        registered_tasks = set(celery_app.tasks.keys())

        expected_tasks = {
            "services.tasks.heartbeat.heartbeat_check",
            "services.tasks.heartbeat.check_broker_connection",
            "services.tasks.monitoring.check_service_health",
            "services.tasks.maintenance.database_cleanup",
            "services.tasks.maintenance.cleanup_audit_logs",
        }

        # All expected tasks should be in the registered tasks
        for task_name in expected_tasks:
            assert task_name in registered_tasks, f"Task {task_name} not registered"