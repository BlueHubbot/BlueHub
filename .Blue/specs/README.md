# BlueHub Platform Specification

> **Enterprise-grade Internet Services Sales Platform**  
> Multi-Tenant | White-Label | API-First | Modular Architecture

---

## 📋 Overview

BlueHub is a comprehensive platform for selling and managing internet services including VPN, VPS, SmartDNS, Streaming Unblock, and Game Servers. Built with enterprise-grade architecture principles: modularity, multi-tenancy, white-labeling, and security.

### Key Highlights

- **🏗️ API-First:** All business logic in FastAPI, clients are thin layers
- **🧩 Modular:** Plug-and-play service modules with zero interdependency
- **🏢 Multi-Tenant:** Single installation serves multiple brands/resellers
- **🎨 White-Label:** Custom branding per tenant (logo, colors, domain, bot token)
- **🌍 Multilingual:** Built-in i18n system (Persian, English, extensible)
- **🔒 Secure:** JWT authentication, RBAC, audit logging, anti-crack protection
- **📊 Observable:** Prometheus metrics, Grafana dashboards, ELK logging

---

## 📁 Specification Documents

This specification consists of three main documents:

### 1. [requirements.md](./requirements.md)
**Complete requirements specification using EARS format**

- 77 functional requirements with EARS syntax (WHEN/WHERE/THEN)
- 17 user stories covering customer, admin, reseller, and developer journeys
- 10 technical constraints
- 6 unique advanced features (A²OE, P2P Relay, Quantum-resistant VPN)
- 70+ acceptance criteria across 7 phases
- Integration requirements with Paymenter billing system
- Internationalization requirements (i18n/L10n)

### 2. [design.md](./design.md)
**System design with architecture diagrams and database schema**

- High-level architecture overview with technology stack
- 7 Mermaid diagrams:
  - System architecture
  - Service purchase flow
  - Module enable/disable flow
  - Multi-tenant request routing
  - Database ERD (core + module-specific)
  - Production deployment architecture
  - Integration architecture
- Complete database schema (15+ tables with relationships)
- 20+ API endpoint specifications with request/response examples
- Paymenter integration details with webhook handling
- Module registry and feature flags implementation
- i18n system architecture with translation file structure
- Security architecture (JWT, RBAC, anti-crack, audit logging)
- Deployment architecture (Docker Compose for dev, Kubernetes for prod)
- Monitoring and alerting setup (Prometheus, Grafana, ELK)

### 3. [tasks.md](./tasks.md)
**Implementation tasks organized by phases**

- 59 detailed tasks across 7 phases
- Task breakdown: setup → core → modules → production
- Each task includes:
  - Status, priority, estimated time
  - Dependencies
  - Acceptance criteria
  - Technical notes and code examples
- Total estimated time: ~650 hours (16 weeks)
- Dependency graph (Mermaid diagram)
- Statistics by phase, priority, and status

---

## 🗂️ Project Structure

```
/bluehub/
├── core/                    # Core business logic
│   ├── auth/               # JWT, 2FA, login/logout
│   ├── users/              # User, Tenant, Reseller management
│   ├── billing/            # Adapter for Paymenter integration
│   ├── rbac/               # Role-Based Access Control
│   ├── audit/              # Audit logging
│   ├── notifications/      # Email, SMS, Telegram, Push
│   ├── license/            # Anti-crack system
│   ├── i18n/               # Internationalization engine
│   └── registry/           # Module Registry (plug-and-play)
│
├── modules/                # Service modules (plug-and-play)
│   ├── vpn/               # VPN (WireGuard, VLESS+REALITY, Trojan)
│   ├── vps/               # Virtual Private Server (Proxmox)
│   ├── smartdns/          # SmartDNS (Anycast DNS)
│   ├── streaming/         # Streaming Unblock (Netflix, Disney+)
│   └── game/              # Game Servers (Minecraft, CS2)
│
├── api/                    # REST API layer
│   ├── v1/                # API version 1
│   │   ├── core/          # Core endpoints (auth, users, billing)
│   │   └── modules/       # Module endpoints (auto-registered)
│   └── webhooks/          # Webhook receivers (Paymenter)
│
├── web/                    # Frontend applications
│   ├── admin/             # Admin Panel (Next.js 15 + Shadcn)
│   ├── client/            # Client Portal (white-label ready)
│   └── shared/            # Shared UI components
│
├── bot/                    # Telegram bot
│   ├── handlers/          # Command handlers (thin, calls API)
│   ├── keyboards/         # Inline keyboards (from module metadata)
│   ├── locales/           # Bot-specific translations
│   └── middleware/        # i18n, auth middleware
│
├── services/               # Background services
│   ├── celery_app.py      # Celery configuration
│   ├── tasks/             # Celery tasks
│   │   ├── provisioning.py # Auto-provision after payment
│   │   ├── renewal.py      # Auto-renewal
│   │   ├── backup.py       # Database backups
│   │   ├── abuse.py        # Abuse detection
│   │   └── monitoring.py   # Health checks
│   └── workers/           # Worker configurations
│
├── infrastructure/         # Deployment configs
│   ├── terraform/         # Infrastructure as Code
│   ├── ansible/           # Server provisioning
│   └── monitoring/        # Prometheus, Grafana configs
│
├── config/                 # Configuration files
│   ├── settings.py        # Pydantic settings
│   ├── features.yaml      # Feature flags defaults
│   ├── locales/           # Translation files (fa.json, en.json)
│   └── products/          # Product configs (YAML)
│
├── shared/                 # Shared utilities
│   ├── models/            # Base SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── constants.py       # Enums (Protocols, Locations, Status)
│   └── exceptions.py      # Custom exceptions
│
├── alembic/                # Database migrations
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/               # End-to-end tests
│
├── legacy_bluehub/         # Legacy bot (for migration)
├── docker-compose.yml      # Development environment
├── Dockerfile              # Application container
├── main.py                 # FastAPI entry point
├── pyproject.toml          # Python dependencies
└── README.md               # Project README
```

---

## 🛠️ Technology Stack

### Backend
- **API Framework:** FastAPI 0.104+ (Python 3.12+)
- **Database:** PostgreSQL 16 (with JSONB for flexibility)
- **Cache/Queue:** Redis 7 (cache + Celery broker)
- **Task Queue:** Celery 5.x (async background jobs)
- **ORM:** SQLAlchemy 2.0 (async support)
- **Migrations:** Alembic 1.12+

### Frontend
- **Framework:** Next.js 15 (React 18+, TypeScript)
- **UI Library:** Shadcn UI (Tailwind CSS-based)
- **State Management:** Tanstack Query (React Query)
- **Form Handling:** react-hook-form + Zod validation

### Bot
- **Framework:** aiogram 3.x (async Telegram bot)

### Infrastructure
- **Containers:** Docker + Docker Compose (dev), Kubernetes (prod)
- **Object Storage:** MinIO (S3-compatible)
- **Monitoring:** Prometheus + Grafana
- **Logging:** ELK Stack (Elasticsearch, Logstash, Kibana)
- **CI/CD:** GitHub Actions

### External Integrations
- **Billing:** Paymenter (Laravel-based billing system)
- **VPN Backend:** WireGuard, Xray-core (VLESS+REALITY)
- **VPS Management:** Proxmox VE (via proxmoxer library)
- **Fraud Detection:** MaxMind Fraud API

---

## 🚀 Development Roadmap

### Phase 0: Setup (Week 1)
- Repository initialization
- Docker Compose environment
- Paymenter installation
- Project structure creation

### Phase 1: Core System (Week 2-3)
- Database models and migrations
- JWT authentication + RBAC
- i18n system (Persian, English)
- Module registry + feature flags
- Paymenter webhook integration

### Phase 2: VPN Module (Week 3-5)
- WireGuard protocol implementation
- VLESS+REALITY protocol
- Celery tasks (provisioning, monitoring)
- Telegram bot (VPN handlers)
- Web client (VPN pages)

### Phase 3: Admin Panel (Week 6-7)
- Module management interface
- Product creation and pricing
- Tenant management (white-label)
- User management
- Abuse reports

### Phase 4: VPS Module (Week 8-10)
- Proxmox VE integration
- VM provisioning and management
- Snapshots and backups
- API + UI integration

### Phase 5: Additional Modules (Week 11+)
- SmartDNS module
- Streaming Unblock module
- Game Server module

### Phase 6: Production Ready (Week 13-14)
- Monitoring (Prometheus, Grafana)
- Centralized logging (ELK)
- CI/CD pipeline (GitHub Actions)
- Integration tests (>80% coverage)
- Security audit
- Performance testing
- Legacy bot migration

### Phase 7: Advanced Features (Future)
- A²OE (AI Adaptive Obfuscation)
- DAITA-Plus (traffic analysis defense)
- Hybrid P2P relay network
- Quantum-resistant encryption
- Self-healing infrastructure
- Local AI assistant

**Total Estimated Time:** 16 weeks with 1 full-time developer  
**Recommended Team:** 2 backend + 1 frontend + 1 devops = 8-10 weeks

---

## 🔑 Key Features

### 1. API-First Architecture
- All business logic in FastAPI REST API
- Clients (bot, web, mobile) are thin layers
- OpenAPI documentation auto-generated
- Consistent error handling and validation

### 2. Modular Design (Plug & Play)
- Each service is an independent module
- Zero interdependency between modules
- Add new module = create folder + register
- Remove module = disable in admin panel

### 3. Multi-Tenant & White-Label
- Single installation, multiple brands
- Custom domain, logo, colors per tenant
- Dedicated Telegram bot token per tenant
- Tenant-specific pricing overrides

### 4. Feature Flags
- Enable/disable modules without restart
- Two modes: "stop new sales" or "terminate services"
- Redis-cached for performance
- Admin panel toggle with confirmation

### 5. Internationalization (i18n)
- Built-in support for multiple languages
- JSON-based translation files
- Runtime language detection
- Extensible (add new language via admin panel)
- All UIs localized (bot, web, admin, emails)

### 6. Security
- **Authentication:** JWT with access + refresh tokens
- **Authorization:** Role-based (superadmin, admin, reseller, user)
- **2FA:** TOTP support for sensitive operations
- **Audit Logging:** Complete audit trail for compliance
- **Anti-Crack:** License keys with ECDSA signatures
- **Data Protection:** GDPR-compliant (data export, deletion)

### 7. Scalability
- Horizontal scaling of API workers
- Celery workers scale independently
- PostgreSQL primary-replica replication
- Redis cluster for cache
- MinIO distributed mode for storage

### 8. Observability
- Prometheus metrics (latency, errors, business KPIs)
- Grafana dashboards (system, API, business, Celery)
- ELK stack for centralized logging
- Alerts to Telegram and PagerDuty

---

## 📊 Database Schema Highlights

### Core Tables
- `tenants` - Multi-tenant configuration
- `users` - User accounts with RBAC
- `products` - Service products with i18n descriptions
- `services` - Active services (polymorphic base)
- `module_registry` - Feature flags and module config
- `audit_logs` - Complete audit trail

### VPN Module
- `vpn_accounts` - VPN service instances
- `vpn_protocol_configs` - Protocol-specific configs
- `vpn_sessions` - Connection logs

### VPS Module
- `vps_instances` - Virtual machines
- `vps_snapshots` - VM snapshots

### Other Modules
- `smartdns_profiles`, `dns_records`
- `streaming_profiles`
- `game_servers`

**Total Tables:** 15+ with proper indexing and relationships

---

## 🔗 External Integrations

### Paymenter (Billing System)
- **Direction:** Bidirectional
- **Integration Type:** Webhooks + REST API
- **Events:**
  - `user.created` → Create local user
  - `payment.succeeded` → Provision service
  - `subscription.renewed` → Extend expiration
- **Sync Task:** Every 5 minutes for missed webhooks

### Proxmox VE (VPS Management)
- **Direction:** BlueHub → Proxmox
- **Integration Type:** REST API (proxmoxer library)
- **Operations:** Clone VM, start/stop, snapshot, stats

### WireGuard / Xray-core (VPN Backends)
- **Direction:** BlueHub → VPN Servers
- **Integration Type:** Subprocess or API
- **Operations:** Key generation, config update, traffic stats

### MaxMind (Fraud Detection)
- **Direction:** BlueHub → MaxMind
- **Integration Type:** REST API
- **Usage:** Payment fraud detection for new users

---

## 🧪 Testing Strategy

### Unit Tests
- All service functions
- Auth and RBAC logic
- i18n engine
- Target: >90% coverage

### Integration Tests
- API endpoints with test database
- Paymenter webhook handling
- Module enable/disable flow
- Tenant isolation
- Target: >80% coverage

### End-to-End Tests
- Complete purchase flow (bot + API + Paymenter mock)
- VPN provisioning and config download
- VPS creation and management

### Performance Tests
- Load testing with Locust (1000 concurrent users)
- Target: <200ms for 95th percentile

### Security Tests
- OWASP Top 10 checks
- SQL injection, XSS, CSRF
- JWT security
- Penetration testing

---

## 📖 Documentation

### For Developers
- API documentation (OpenAPI/Swagger at `/docs`)
- Architecture decision records (ADR)
- Database schema documentation
- Module development guide

### For Operators
- Deployment guide (Docker, Kubernetes)
- Configuration reference
- Monitoring setup guide
- Backup and restore procedures
- Troubleshooting guide

### For End Users
- Customer guide (purchase, setup, manage services)
- Admin guide (products, users, abuse management)
- Reseller guide (white-label setup)
- Multilingual (Persian, English)

---

## 🤝 Contributing

This is a private enterprise project. For internal team members:

1. Read `CONTRIBUTING.md` for development guidelines
2. Follow the task list in `tasks.md`
3. Create feature branch from `dev`
4. Write tests for new features
5. Ensure CI passes before merging
6. Update documentation as needed

---

## 📝 License

Proprietary - All Rights Reserved  
© 2026 BlueHub Team

---

## 🔍 Quick Links

- **Requirements:** [requirements.md](./requirements.md) - 77 requirements, 17 user stories
- **Design:** [design.md](./design.md) - Architecture, database, API specs
- **Tasks:** [tasks.md](./tasks.md) - 59 tasks, 16-week roadmap
- **Legacy Bot:** https://github.com/BlueHubbot/blueHub/tree/archive/legacy-scripts

---

## 📧 Contact

For questions or clarifications, contact the project lead or open an internal issue.

---

*Last Updated: June 10, 2026*  
*Version: 1.0*  
*Status: Specification Complete - Ready for Implementation*
