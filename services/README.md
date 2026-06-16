# Services

Background services and task workers for the BlueHub platform.

## Components

- **celery_app.py** - Celery application configuration with Redis broker
- **tasks/** - Celery task definitions
  - `vpn.py` - VPN provisioning and monitoring tasks
  - `vps.py` - VPS lifecycle management tasks
  - `heartbeat.py` - Service health check tasks
  - `monitoring.py` - Resource usage monitoring tasks
  - `maintenance.py` - Scheduled maintenance tasks

## Task Scheduler

Tasks are scheduled via Celery Beat:
- VPN usage polling: every 5 minutes
- Service expiration check: daily
- Health heartbeat: every 30 seconds
- Resource monitoring: every 15 minutes

## Usage

```bash
# Start Celery worker
celery -A services.celery_app worker -l info

# Start Celery Beat scheduler
celery -A services.celery_app beat -l info