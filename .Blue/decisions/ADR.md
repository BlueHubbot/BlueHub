# Architectural Decision Records (ADRs)

This document records the architectural decisions made for the BlueHub Platform, detailing the context, decisions, and consequences of each major design choice.

---

## ADR-001: Selection of FastAPI (API-First Strategy)

- **Context**: The BlueHub Platform requires high-performance, stateless routing across multiple customer clients (Telegram Bot, Admin Panel, and Web client portal).
- **Decision**: We selected FastAPI (Python 3.12+) as the core backend engine instead of traditional frameworks like Django or Flask.
- **Consequences**:
  - Automatic generation of standard OpenAPI documentation reduces client-side integration friction.
  - Exceptional asynchronous support (`async/await`) minimizes worker blockage during provisioning calls to Proxmox and Paymenter.
  - Strict type validation via Pydantic v2 prevents corrupt payloads from reaching the database.

---

## ADR-002: TimescaleDB Partitioning for Time-Series Tables

- **Context**: Tables tracking active VPN sessions (`vpn_sessions`) and tenant operation logs (`audit_logs`) will scale to millions of rows rapidly, causing severe index bloat and query degradation on PostgreSQL over time.
- **Decision**: We chose to implement database partitioning using TimescaleDB hypertables, chunking partitions automatically on a monthly schedule based on `connected_at` and `created_at` timestamp ranges.
- **Consequences**:
  - Storage footprints are optimized via automated compression policies on chunks older than 30 days, resulting in a 60-70% reduction in disk space.
  - High query velocities are preserved through constraint exclusion (partition pruning).
  - Historical data can be safely dropped by discarding entire partition tables rather than executing expensive `DELETE` queries.

---

## ADR-003: Bidirectional Webhook Sync with Paymenter

- **Context**: The billing lifecycle is managed externally by the Paymenter system, but BlueHub must react instantly when a subscription is paid or canceled without constant database polling.
- **Decision**: Implement a bidirectional sync architecture using cryptographically verified webhook receivers (`POST /webhooks/paymenter/*`) verified with a shared HMAC-SHA256 secret. This is backed by a celery task that polls unpaid orders every 5 minutes as a fallback.
- **Consequences**:
  - Decoupled application architecture where Billing resides safely in a separate PHP environment.
  - Instant auto-provisioning of VPN/VPS services within seconds of payment approval.
  - Strong resiliency against missed HTTP payloads through the Celery sync queue.

---

## ADR-004: Multi-Tenant Middleware Routing

- **Context**: White-label resellers must be isolated dynamically. Each tenant can configure their own domains, color schemes, pricing structures, and Telegram bots on a single installation.
- **Decision**: We designed custom `TenantMiddleware` to intercept every incoming REST call and extract the hostname from Host headers, query local tenant definitions from cache, and set `request.state.tenant_id` for use throughout the lifecycle of the request.
- **Consequences**:
  - Secure logical isolation; database schemas use row-level filters (`WHERE tenant_id = ...`) on all operations.
  - Branding resources (images, custom CSS variables, and copy) are dynamically injected based on the active domain.
  - High speed preserved via Redis caching of the domain-to-tenant mapping with a 5-minute TTL.

---

## ADR-005: Proxmox VE for VPS Virtualization

- **Context**: The VPS module must dynamically provision, clone, size, snapshot, and control Linux VMs across bare-metal colocation clusters.
- **Decision**: Use Proxmox VE clusters with shared Ceph storage as the hypervisor layer, communicating securely via the `proxmoxer` library using REST API tokens.
- **Consequences**:
  - Automated provisioning via customized Cloud-init configs injected at VM clone stage.
  - Exceptional redundancy with Ceph's 3x replication model protecting active disks.
  - No expensive commercial licensing fees, preserving project margin.