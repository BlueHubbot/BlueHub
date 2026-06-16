# BlueHub Platform

A comprehensive multi-tenant platform for selling and managing VPN, VPS, SmartDNS, Streaming, and Game services with Telegram bot integration.

## Architecture

- **API-First:** All business logic in FastAPI REST API
- **Modular:** Plug-and-play service modules
- **Multi-Tenant:** Single installation serves multiple brands
- **White-Label:** Custom branding per tenant
- **Multilingual:** Built-in i18n (Persian, English)
- **Secure:** JWT, RBAC, 2FA, audit logging

## Tech Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy, Alembic
- **Bot:** aiogram (Telegram Bot API)
- **Frontend:** Next.js (web/client), React Admin (web/admin)
- **Billing:** Paymenter integration
- **Task Queue:** Celery + Redis
- **Database:** PostgreSQL
- **Infrastructure:** Docker Compose

## Project Structure

```
BlueHub/
├── api/            # FastAPI route handlers
├── bot/            # Telegram bot (aiogram)
├── core/           # Business logic modules
├── modules/        # Service modules (VPN, VPS, SmartDNS, etc.)
├── shared/         # Shared models and utilities
├── services/       # Celery tasks and background services
├── web/            # Frontend applications
├── tests/          # Test suite
├── infrastructure/ # Docker and deployment configs
├── alembic/        # Database migrations
└── config/         # Configuration and locales
```

## Setup

### Prerequisites
- Python 3.12+
- Docker and Docker Compose
- PostgreSQL (or use Docker)
- Redis (or use Docker)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bluehub
```

2. Copy environment file:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Install dependencies:
```bash
pip install -e .
```

4. Run with Docker Compose:
```bash
docker-compose up -d
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the API server:
```bash
uvicorn main:app --reload
```

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

See [LICENSE](LICENSE) for details.