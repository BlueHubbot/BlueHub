# BlueHub Platform Requirements

## Project Overview
**Project Name:** BlueHub  
**Type:** Enterprise-grade Internet Services Sales Platform  
**Legacy Repository:** https://github.com/BlueHubbot/blueHub/tree/archive/legacy-scripts  
**Tech Stack:** Python 3.12+ (FastAPI), Next.js 15, PostgreSQL 16, Redis 7, Celery  
**Architecture:** API-First, Modular, Multi-Tenant, White-Label Ready  

## Core Services
- VPN (WireGuard, VLESS+REALITY, Trojan, Shadowsocks)
- VPS (Virtual Private Server)
- SmartDNS
- Streaming Unblock (Netflix, Disney+, Spotify)
- Game Servers (Minecraft, CS2)

---

## 1. Functional Requirements (EARS Format)

### 1.1 API-First Architecture

**REQ-001:** WHEN any client (Telegram bot, web panel, admin panel, mobile app) needs to perform business logic, THE system SHALL expose that functionality exclusively through FastAPI REST endpoints.

**REQ-002:** WHERE a Telegram bot receives user interaction, THE bot SHALL only handle UI rendering and input collection, THEN forward all business operations to the API layer.

**REQ-003:** WHERE a web client needs to display data, THE client SHALL fetch data exclusively from API endpoints WITHOUT containing any business logic.

**REQ-004:** WHERE an admin panel needs to modify system configuration, THE panel SHALL send requests to API endpoints WITHOUT direct database access.

### 1.2 Modular Architecture (Plug & Play)

**REQ-005:** WHEN a new service type is added to the system, THE system SHALL support adding it as an independent module WITHOUT modifying existing modules.

**REQ-006:** WHERE a module is defined, THE module SHALL contain: `models.py`, `services.py`, `api.py`, `tasks.py`, and `metadata.py` in a self-contained directory structure.

**REQ-007:** WHEN a module is disabled, THE system SHALL continue operating all other modules WITHOUT dependencies or side effects.

**REQ-008:** WHERE modules are stored, THE system SHALL use a directory structure at `modules/{service_name}/` with automatic registration via a module registry.

**REQ-009:** WHEN a new module is created, THE system SHALL allow enabling/disabling it from admin panel WITHOUT code deployment.

### 1.3 Feature Flags (Database-Driven)

**REQ-010:** WHEN an administrator disables a module, THE system SHALL immediately stop accepting new orders for that module WITHOUT requiring application restart.

**REQ-011:** WHERE a module is disabled with "stop new sales only" mode, THE system SHALL continue serving existing active services WHILE rejecting new purchase requests.

**REQ-012:** WHERE a module is disabled with "terminate active services" mode, THE system SHALL suspend all active services for that module AND notify affected users.

**REQ-013:** WHEN feature flags are updated, THE system SHALL cache the state in Redis with TTL of 60 seconds for performance optimization.

**REQ-014:** WHERE API endpoints are called for a disabled module, THE system SHALL return HTTP 403 with a localized message indicating temporary unavailability.

### 1.4 Multi-Tenant & White-Label

**REQ-015:** WHEN the system is deployed, THE system SHALL support multiple tenants (brands/resellers/white-labels) with isolated configurations.

**REQ-016:** WHERE a tenant is created, THE system SHALL allow configuration of: custom domain, logo, color scheme, and dedicated Telegram bot token.

**REQ-017:** WHEN a request arrives, THE system SHALL identify the tenant from the Host header OR X-Tenant-Id header.

**REQ-018:** WHERE pricing is configured, EACH tenant SHALL have the ability to override default product prices via `tenant_product_pricing` table.

**REQ-019:** WHERE branding is applied, THE system SHALL serve tenant-specific logos, colors, and themes to web clients WITHOUT code changes.

**REQ-020:** WHEN a tenant is created, THE system SHALL provide a unique API key and webhook endpoint for integration.

### 1.5 Role-Based Access Control (RBAC)

**REQ-021:** WHERE users are created, THE system SHALL assign one of four roles: `superadmin`, `admin`, `reseller`, or `user`.

**REQ-022:** WHEN a superadmin accesses the system, THE system SHALL grant access to all tenants and all administrative functions.

**REQ-023:** WHERE an admin is assigned to a tenant, THE admin SHALL manage only that tenant's products, users, and abuse reports.

**REQ-024:** WHEN a reseller creates an account, THE reseller SHALL have the ability to sell services with custom commission rates.

**REQ-025:** WHERE a regular user accesses the system, THE user SHALL only manage their own purchased services and profile.

**REQ-026:** WHEN role-based authorization is checked, THE system SHALL use middleware decorators (`@require_role("admin")`) on API endpoints.

### 1.6 Security & Anti-Crack Protection

**REQ-027:** WHERE each tenant is provisioned, THE system SHALL generate a unique `license_key` and cryptographic `signature` (ECDSA or RSA).

**REQ-028:** WHEN client applications (mobile/desktop) are distributed, THE applications SHALL include watermarking and code obfuscation.

**REQ-029:** WHERE crack attempts are detected, THE system SHALL log the incident to `audit_logs` AND initiate graceful degradation or shutdown.

**REQ-030:** WHEN critical operations are performed, THE system SHALL record complete audit trails including: user_id, action, timestamp, IP address, and result.

**REQ-031:** WHERE API authentication is required, THE system SHALL use JWT tokens with configurable expiration and refresh token mechanism.

**REQ-032:** WHEN 2FA is enabled for a user, THE system SHALL require TOTP verification for sensitive operations (password change, service deletion).

### 1.7 Internationalization (i18n/L10n)

**REQ-033:** WHEN the system is deployed, THE system SHALL support multiple languages with initial support for Persian (Farsi) and English.

**REQ-034:** WHERE a user interacts with Telegram bot, THE bot SHALL detect language from Telegram settings OR allow manual selection via settings menu.

**REQ-035:** WHEN a web client loads, THE client SHALL detect browser language OR use user's saved preference from database.

**REQ-036:** WHERE translations are stored, THE system SHALL use JSON/YAML files in `config/locales/{lang_code}.json` structure.

**REQ-037:** WHEN admin adds a new language, THE system SHALL support uploading translation files via admin panel WITHOUT code deployment.

**REQ-038:** WHERE system messages are generated (emails, SMS, push notifications, error messages), ALL messages SHALL be localized based on user's language preference.

**REQ-039:** WHEN API returns error messages, THE system SHALL return errors in the user's preferred language with fallback to English.

---

## 2. Integration Requirements

### 2.1 Paymenter Integration

**REQ-040:** WHEN a user registers in Paymenter, Paymenter SHALL send a webhook to `POST /webhooks/paymenter/user.created` with user details.

**REQ-041:** WHERE a new user webhook is received, THE system SHALL create a local user record with `paymenter_user_id` and default tenant assignment.

**REQ-042:** WHEN a payment is completed in Paymenter, Paymenter SHALL send a webhook to `POST /webhooks/paymenter/payment.succeeded` with order details.

**REQ-043:** WHERE a payment success webhook is received, THE system SHALL:
- Create a service record with `status=pending`
- Queue a Celery task for provisioning
- Update status to `active` after successful provisioning
- Send notification to user via Telegram/Email

**REQ-044:** WHEN webhook authentication is required, THE system SHALL verify webhook signatures using shared secret with Paymenter.

**REQ-045:** WHERE sync is needed, A Celery beat task SHALL run every 5 minutes to check for paid orders that haven't been provisioned.

### 2.2 External Services

**REQ-046:** WHERE VPN services use WireGuard, THE system SHALL integrate with WireGuard management API for key generation and configuration.

**REQ-047:** WHEN VPS provisioning is required, THE system SHALL integrate with Proxmox VE API using `proxmoxer` library.

**REQ-048:** WHERE DNS management is needed for SmartDNS, THE system SHALL integrate with PowerDNS or BIND for record management.

**REQ-049:** WHEN fraud detection is required, THE system SHALL integrate with MaxMind Fraud API for payment verification.

**REQ-050:** WHERE monitoring is implemented, THE system SHALL expose Prometheus metrics endpoint at `/metrics` for Grafana integration.

---

## 3. User Stories

### 3.1 User Journey - VPN Purchase

**US-001:** As a customer, I want to browse available VPN plans in my language (Persian/English), so that I can understand the service offerings.

**US-002:** As a customer, I want to select a VPN protocol (WireGuard, VLESS+REALITY), so that I can choose based on my technical requirements.

**US-003:** As a customer, I want to complete payment through Paymenter, so that I can securely purchase the service.

**US-004:** As a customer, I want to receive VPN configuration automatically after payment, so that I can start using the service immediately.

**US-005:** As a customer, I want to view my data usage in real-time, so that I can monitor my consumption.

**US-006:** As a customer, I want to receive notifications in my preferred language when my service is about to expire, so that I can renew on time.

### 3.2 Admin Journey - Module Management

**US-007:** As a superadmin, I want to enable/disable service modules from admin panel, so that I can control service availability without code deployment.

**US-008:** As a superadmin, I want to choose between "stop new sales" or "terminate services" when disabling a module, so that I can manage service deprecation gracefully.

**US-009:** As an admin, I want to view all active services for my tenant, so that I can monitor business operations.

**US-010:** As an admin, I want to manually suspend a service for abuse, so that I can enforce terms of service.

**US-011:** As an admin, I want to configure custom pricing for my tenant, so that I can implement competitive pricing strategies.

### 3.3 Reseller Journey

**US-012:** As a reseller, I want to create sub-accounts with custom branding (white-label), so that I can sell services under my own brand.

**US-013:** As a reseller, I want to set commission rates for my sales, so that I can earn revenue from referrals.

**US-014:** As a reseller, I want to view sales reports for my tenant, so that I can track business performance.

### 3.4 Developer Journey - Module Development

**US-015:** As a developer, I want to create a new service module by following a standard structure, so that I can extend the platform without modifying core code.

**US-016:** As a developer, I want modules to auto-register via registry pattern, so that I don't need to manually wire up dependencies.

**US-017:** As a developer, I want to define module metadata (UI buttons, translations, icons), so that the bot and web UI automatically adapt.

---

## 4. Non-Functional Requirements

### 4.1 Performance

**REQ-051:** WHERE API endpoints are called, THE system SHALL respond within 200ms for 95th percentile of requests under normal load.

**REQ-052:** WHEN feature flags are checked, THE system SHALL serve from Redis cache to avoid database overhead.

**REQ-053:** WHERE heavy operations are required (VPS provisioning), THE system SHALL use async Celery tasks and return immediate response with task_id.

### 4.2 Scalability

**REQ-054:** WHEN load increases, THE system SHALL support horizontal scaling of FastAPI workers and Celery workers independently.

**REQ-055:** WHERE geographic distribution is needed, THE system SHALL support multiple location nodes with weight-based load balancing.

**REQ-056:** WHEN database queries are executed, THE system SHALL use connection pooling with minimum 10, maximum 50 connections per worker.

### 4.3 Reliability

**REQ-057:** WHERE service provisioning fails, THE system SHALL implement automatic retry with exponential backoff (max 3 retries).

**REQ-058:** WHEN database connections fail, THE system SHALL automatically reconnect with circuit breaker pattern.

**REQ-059:** WHERE critical tasks are queued, THE system SHALL persist task state in Redis to survive worker restarts.

**REQ-060:** WHEN system anomalies are detected (high latency, queue overflow), THE system SHALL send alerts to Telegram admin channel.

### 4.4 Security

**REQ-061:** WHERE passwords are stored, THE system SHALL use bcrypt hashing with minimum 12 rounds.

**REQ-062:** WHEN API keys are generated, THE system SHALL use cryptographically secure random generation (minimum 32 bytes).

**REQ-063:** WHERE sensitive data is logged, THE system SHALL mask or redact passwords, API keys, and payment information.

**REQ-064:** WHEN SQL queries are constructed, THE system SHALL use SQLAlchemy ORM or parameterized queries to prevent SQL injection.

### 4.5 Compliance

**REQ-065:** WHERE GDPR applies, THE system SHALL provide user data export functionality in JSON format.

**REQ-066:** WHEN a user requests data deletion, THE system SHALL delete all related data within 30 days (services, logs, sessions).

**REQ-067:** WHERE audit logs are required, THE system SHALL retain logs for minimum 90 days and maximum 2 years based on configuration.

### 4.6 Migration from Legacy

**REQ-068:** WHEN legacy bot users exist, THE system SHALL provide a `/migrate` command to transfer their data to new system.

**REQ-069:** WHERE migration is in progress, THE system SHALL support running old and new bots in parallel with migration status tracking.

**REQ-070:** WHEN a user is migrated, THE system SHALL preserve their purchase history, active services, and wallet balance.

---

## 5. Technical Constraints

**CONSTRAINT-001:** The system MUST use Python 3.12+ for backend services.

**CONSTRAINT-002:** The system MUST use FastAPI framework for REST API.

**CONSTRAINT-003:** The system MUST use PostgreSQL 16 as primary database.

**CONSTRAINT-004:** The system MUST use Redis 7 for caching and Celery broker.

**CONSTRAINT-005:** The system MUST use aiogram 3 for Telegram bot development.

**CONSTRAINT-006:** The system MUST use Next.js 15 with React for frontend.

**CONSTRAINT-007:** The system MUST use Shadcn UI and Tanstack Query for web UI.

**CONSTRAINT-008:** The system MUST use Docker Compose for development environment.

**CONSTRAINT-009:** The system MUST prepare for Kubernetes deployment in production.

**CONSTRAINT-010:** The system MUST use Alembic for database migrations.

---

## 6. Critical Infrastructure Requirements (NEW)

### 6.1 Disaster Recovery (DR)

**REQ-071:** WHEN a complete data center failure occurs, THE system SHALL recover within 4 hours (RTO) with maximum 1 hour of data loss (RPO).

**REQ-072:** WHERE backups are taken, THE system SHALL maintain copies in at least 2 geographic regions (primary region + AWS S3 or Backblaze B2).

**REQ-073:** WHEN backups are created, THE system SHALL be tested for recoverability at least quarterly with full restore to staging environment.

**REQ-074:** WHERE backup retention is defined, THE system SHALL retain local backups for 30 days, cloud backups for 90 days, and cold storage backups for 1 year.

### 6.2 Rate Limiting & DDoS Protection

**REQ-075:** WHEN API endpoints are called, THE system SHALL implement per-endpoint rate limits with sensible defaults (100 req/min for most, 5 req/min for login).

**REQ-076:** WHERE rate limits are exceeded, THE system SHALL return HTTP 429 with Retry-After header and clear error message in user's language.

**REQ-077:** WHEN DoS attacks are detected, THE system SHALL automatically trigger escalating countermeasures (IP blocking, CAPTCHA, rate limit reduction).

### 6.3 Circuit Breaker Pattern

**REQ-078:** WHEN external services are called (Paymenter, Proxmox, DNS), THE system SHALL implement circuit breaker with automatic fallback.

**REQ-079:** WHERE circuit is open (service unavailable), THE system SHALL queue requests for retry when service recovers, with maximum 1-hour queue retention.

**REQ-080:** WHEN circuit breaker opens, THE system SHALL immediately alert admin via Telegram and log to audit system.

### 6.4 Secret Management

**REQ-081:** WHERE secrets are stored, THE system SHALL use Kubernetes Secrets (with sealed-secrets encryption) or HashiCorp Vault, NOT plaintext environment variables.

**REQ-082:** WHEN JWT secrets are rotated (every 90 days), THE system SHALL support dual-key validation for seamless rotation without user logout.

**REQ-083:** WHERE API keys are exposed, THE system SHALL invalidate all tokens for affected user within 5 minutes and trigger security alert.

### 6.5 Database Partitioning

**REQ-084:** WHERE time-series data is stored (vpn_sessions, audit_logs), THE system SHALL use TimescaleDB hypertables or PostgreSQL range partitioning by month.

**REQ-085:** WHEN old partitions exceed 30 days, THE system SHALL automatically compress data to reduce storage footprint by 60-70%.

**REQ-086:** WHERE query performance is critical, THE system SHALL ensure partition elimination (constraint exclusion) for queries on specific time ranges.

---

## 7. Deferred Features (Phase 7 and beyond)

The following features are intentionally deferred due to complexity, uncertainty, or lack of immediate business need:

### 7.1 Anti-Crack System
- License key generation with ECDSA signatures
- Client watermarking and code obfuscation  
- Deferred until: iOS/Android apps in production
- Estimated effort: 3-4 weeks

### 7.2 AI Adaptive Obfuscation (A²OE)
- ML-based DPI evasion engine
- Traffic pattern analysis and adaptation
- Deferred until: Widespread DPI blocking observed
- Estimated effort: 2-3 months (requires ML team)

### 7.3 Hybrid P2P Relay Network
- Peer-to-peer relay with incentive system
- NAT traversal (STUN/TURN)
- Deferred until: Centralized infrastructure consistently blocked
- Estimated effort: 2-3 months
- Risk: Significant legal/liability concerns

### 7.4 Quantum-Resistant Encryption
- Kyber + Dilithium integration
- Post-quantum cryptography support
- Deferred until: 2030+ when quantum threats materialize
- Estimated effort: 4-6 weeks

### 7.5 Self-Healing Infrastructure
- Predictive node failure detection
- Automated service migration
- Deferred until: Operational maturity reached
- Estimated effort: 3-4 weeks

### 7.6 Local AI Assistant
- LLM-based customer support (Llama 3.1)
- Integrated into Telegram bot
- Deferred until: User support demand requires it
- Estimated effort: 2-3 weeks

---

## 7. Acceptance Criteria Summary

### Phase 1 - Core (Week 1-3)
- [ ] FastAPI project structure with modular architecture
- [ ] Module registry with feature flags working
- [ ] RBAC system with 4 roles implemented
- [ ] i18n system with Persian and English support
- [ ] Paymenter webhook receiver operational
- [ ] 5 basic API endpoints functional
- [ ] **DR backup strategy implemented with S3/B2 sync**
- [ ] **Rate limiting with slowapi on all endpoints**
- [ ] **Circuit breaker for Paymenter integration**
- [ ] **Kubernetes Secrets or HashiCorp Vault configured**

### Phase 2 - VPN Module (Week 4-6)
- [ ] WireGuard protocol fully functional
- [ ] VLESS+REALITY protocol implemented
- [ ] Celery tasks for provisioning and monitoring
- [ ] Telegram bot with multilingual UI
- [ ] Web client portal with white-label support
- [ ] Module can be disabled without affecting other services
- [ ] **TimescaleDB or pg_partman configured for vpn_sessions**

### Phase 3 - Admin Panel (Week 7-8)
- [ ] Admin panel with module management
- [ ] Product creation with JSON pricing formulas
- [ ] Tenant creation with custom branding
- [ ] Abuse management interface
- [ ] Multi-tenant routing working via domain/header

### Phase 4 - VPS Module (Week 9-11)
- [ ] Proxmox VE integration complete
- [ ] VM provisioning from templates
- [ ] Snapshot and backup functionality
- [ ] VPN and VPS modules working simultaneously

### Phase 5 - Additional Modules (Week 12+)
- [ ] SmartDNS module operational
- [ ] Streaming Unblock module operational
- [ ] Game Server module operational

### Phase 6 - Production Ready (Final 2 weeks)
- [ ] Prometheus + Grafana monitoring
- [ ] ELK stack for centralized logging
- [ ] CI/CD pipeline with GitHub Actions
- [ ] Integration tests with >80% coverage
- [ ] Legacy bot migration completed
- [ ] **Quarterly DR drill passed successfully**
- [ ] **Load test passed with 1000+ concurrent users**
- [ ] **Secret rotation tested and automated**

### Phase 7 - Advanced Features (Future)
- [ ] Anti-Crack system (DEFERRED - after mobile apps)
- [ ] AI Adaptive Obfuscation (DEFERRED - after market demand)
- [ ] P2P Relay Network (DEFERRED - after legal review)
- [ ] Quantum-resistant encryption (DEFERRED - 2030+)

---

---

## 8. Glossary

**API-First:** Architecture pattern where all functionality is exposed via API before any client implementation.

**Module Registry:** Central registry that tracks all available service modules and their enabled/disabled state.

**Feature Flags:** Configuration-based toggles that control feature availability without code deployment.

**Multi-Tenant:** System design that serves multiple independent customers (tenants) from a single installation.

**White-Label:** Capability to rebrand the platform with custom logos, colors, and domains for different resellers.

**RBAC:** Role-Based Access Control - security model that restricts access based on user roles.

**i18n/L10n:** Internationalization and Localization - designing software to support multiple languages and regions.

**Celery:** Distributed task queue for Python used for asynchronous background jobs.

**Provisioning:** Automated process of creating and configuring services after purchase.

**EARS:** Easy Approach to Requirements Syntax - structured format for writing requirements (WHEN/WHERE/THEN).

---

*Document Version: 1.0*  
*Last Updated: 2026-06-10*  
*Total Requirements: 77*  
*Total User Stories: 17*  
