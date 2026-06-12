# Current State - BlueHub Platform

## 🛠️ Active Tech Stack
- **Backend**: FastAPI (Python 3.12+), SQLAlchemy 2.0 (Async), Alembic.
- **Database**: PostgreSQL 16 (Targeting TimescaleDB extension for partitioned tables).
- **Cache/Queue**: Redis 7, Celery 5.x.
- **Frontend**: Next.js 15 (React 19, Tailwind CSS, Shadcn UI, Tanstack Query).
- **Bot Framework**: aiogram 3.x (Async Telegram SDK).

## 📁 Directory Structure Verification
- `/core`: Authentication, tenant middleware, database sessions, and configuration settings are successfully placed.
- `/modules`: Folder layout created for service plugins (`vpn`, `vps`, `smartdns`, `streaming`, `game`).
- `/api`: Base routes under development.

## ⚙️ Active Decisions
- Domain routing enabled in development (`TenantMiddleware`).
- Encryption of environment variables planned for production deployment via Sealed Secrets.