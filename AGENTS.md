AGENTS.md - Multi-Agent Unified Directive for BlueHub Platform
This file establishes the cross-agent runtime standard for AI Coding Assistants working on the BlueHub Platform. It defines the operational roles, collaborative tasks, and boundaries when navigating the codebase.
## Deployment Rules

### Server-Only Development
- **All changes go directly to server:** `root@109.199.108.30:/BlueHub`
- **No local development:** Everything is done via SSH
- **SSH key:** Already set up, no password needed

### Workflow
1. SSH to server
2. Make changes
3. Build Docker
4. Deploy
5. Test
6. Report back

## 0. CRITICAL RULES – ABSOLUTE PRIORITY (ADDED)
| Rule | Description |
|------|-------------|
| **0.1 – NO DELETION** | NEVER delete, overwrite, or move any file without EXPLICIT user permission. |
| **0.2 – EXPLANATION REQUIRED** | Before any destructive action (delete, rename, reformat folder), explain WHY and wait for user confirmation. |
| **0.3 – STOP ON TEST FAILURE** | If `make test-docker` fails, STOP. Do not proceed. Fix the code first. |
| **0.4 – ASK BEFORE REWRITE** | When rewriting a file, show the diff and wait for approval. |

## 0.5 Emergency Recovery (ADDED)
If files are accidentally deleted:
1. STOP immediately.
2. Check last GitHub commit: `git log -1`
3. Do NOT write new files until user confirms restore strategy.

## 0.6 Required Environment Variables (ADDED)
- `DEEPSEEK_API_KEY` - for code generation
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - caching

## 0.7 Quick Commands (ADDED)
| Command | Purpose |
|---------|---------|
| `make test-docker` | Run all tests |
| `make lint` | Run ruff linter |
| `make format` | Format code with black |

## 1. Dual-Engine Architecture (Gemini + DeepSeek)
To optimize resource consumption, speed, and execution accuracy, the developer maintains two distinct active engines. AI agents must dynamically allocate subtasks based on their specialized capabilities:

🧠 Engine Alpha: Gemini (Context & Architecture Master)
Primary Role: High-level code comprehension, massive context scanning, system architecture queries, and reading the comprehensive 150+ page specification.
When to Use:
Reading and cross-referencing design.md, requirements.md, and tasks.md.
Analyzing database schema changes (shared/models/ or Alembic migrations).
Formulating multi-tenant domain routing strategies.
Validating Phase boundaries and system compatibility.
Instruction to Agent: If you are currently performing a deep code-generation task but need a holistic architecture check, explicitly prompt the user: "Please temporarily switch my active engine to Gemini to analyze the context window of this phase."

⚡ Engine Beta: DeepSeek (Logic, Coding & Debugging Master)
Primary Role: Dense code generation, refactoring, writing algorithms, logical reasoning, and resolving bugs.
When to Use:
Writing FastAPI routes and database query layers.
Implementing aiogram Telegram bot handlers.
Creating Next.js 15 pages and custom Hooks.
Executing migrations via Alembic.
Isolating runtime errors and writing unit tests.
Instruction to Agent: When writing high-quality scripts, ensure you are running on the DeepSeek engine. If you detect complex reasoning is needed for an algorithm, ask the user to switch active settings to DeepSeek.

## 2. Directory Scopes & Boundaries
Agents must operate within distinct folder boundaries to prevent code regression:

| Directory | Scope | Write Permissions | Rule |
|-----------|-------|-------------------|------|
| `/core` | Platform core (auth, settings, DB base) | RESTRICTED | No service-specific code. Keep generic. |
| `/modules` | Service plugins (vpn, vps, etc.) | FULL | Each module has `models.py`, `services.py`, `api.py`, `tasks.py`. |
| `/api` | REST API routes | FULL | Only routing. No business logic. |
| `/bot` | Telegram bot | FULL | Thin UI. Call API, never direct DB. |
| `/web` | Next.js admin/client | FULL | UI only. Call API, never direct DB. |
| `.Blue/specs/` | Design & tasks | READ-ONLY for agents | Never modify manually. User only. |
| `.Blue/docops/` | Session reports | APPEND ONLY | Add new sessions, never edit old. |
| `/tests` | Unit + integration | FULL | Must mirror `/core` and `/modules` structure. |
| `/test-reports` | Test outputs | GENERATED | Never commit. Ignored by git. |

## 3. Communication Protocols
Proactive Interrogation: Do not make assumptions about external services. If a connection configuration for Proxmox, Paymenter, or WireGuard is unclear, search the .Blue/decisions/ folder (corrected path) or prompt the user.

Commit Etiquette: All Git commits executed by the agent must follow Conventional Commits format:
feat(module): description for new features.
fix(module): description for bug fixes.
docs(module): description for documentation updates.
refactor(module): description for code cleanups.

## 4. Testing Requirements (ADDED)
- After every code change: `make test-docker` MUST pass.
- If test fails, the agent must read the error, fix the code, and retry.
- Never commit with red tests.

## 5. Common Pitfalls (ADDED)
| Problem | Solution |
|---------|----------|
| Docker container exits | Check logs: `docker-compose logs <service>` |
| Agent deletes file by mistake | **Impossible if rule 0.1 is followed.** If happens, restore from git. |

## 6. Final Authority (ADDED)
**User has final authority over all agent actions.**
If any rule conflicts with user command, user command wins – but agent must warn about the conflict before executing.

# BlueHub Platform - Automated Sequential Tasks Blueprint

## 7. AUTOMATIC TASK EXECUTION
After completing each task successfully:
1. Read `tasks.md` and identify the next task whose dependencies are satisfied.
2. Automatically start working on the next task without asking the user.
3. Continue until all tasks are completed or an error occurs.
4. Never ask "shall I continue?" — just continue execution autonomously.

## 8. PRE-TASK CHECKLIST (MANDATORY)
Before starting ANY new task, these steps MUST be followed in strict order:
1. Read `.Blue/specs/tasks.md` fully and identify the next chronological task based on dependencies.
2. Read `.Blue/specs/design.md` to verify architecture compliance for the target task.
3. Execute all existing system tests by running: `make test-docker`
4. If tests are NOT 100% green (**ALL TESTS PASSED, 0 failed, 0 errors**), **DO NOT START** the new task. Fix the failing regressions first.
5. Only proceed to the next task after a verified `ALL TESTS PASSED` output.
6. Immediately after completing the new task, run `make test-docker` again and record the validation status.

## 9. PHASE ORDER & EXECUTION GATES (STRICT)
Task execution order MUST follow this rigid sequence. **Phase 5 must NOT start before both Phase 3 and Phase 4 are 100% complete.**

### 📊 Project Metadata & Status Overview
* **Project Name:** BlueHub Platform
* **Type:** Enterprise Multi-Tenant Internet Services Sales Platform
* **Total Tasks:** 59 Tasks across 7 Phased Milestones
* **Current Core Tech Stack:** FastAPI (Python 12.3), TimescaleDB, Redis, Next.js 15, aiogram 3, OpenRouter (DeepSeek)

---

### 🛠️ Phase 0: Project Setup & Foundation (Week 1)
*Goal: Establish development environment, multi-container orchestration, and billing infrastructure.*

* **TASK-001:** Initialize Git repository architecture with standard branching strategy (`main`, `dev`, `legacy`). ✅ **COMPLETE**
* **TASK-002:** Create Docker Compose local orchestrations (PostgreSQL 16, Redis 7, MinIO) with health-checks. ✅ **COMPLETE**
* **TASK-003:** Deploy and isolate local Paymenter billing system on port `8080` with dedicated MySQL 8. ✅ **COMPLETE**
* **TASK-004:** Establish project macro-directory infrastructure matching architectural blueprints. ✅ **COMPLETE**
* **TASK-005:** Setup Python package definitions via `pyproject.toml` (Poetry) incorporating Black/Ruff rules. 🟡 **IN PROGRESS**

---

### 🧠 Phase 1: Core System & Multi-Tenant Infrastructure (Weeks 2-3)
*Gate: Blocked until Phase 0 is 100% complete.*

* **TASK-006:** Design and write declarative SQLAlchemy core models (Tenants, Users, Products, Services). *[Depends on: TASK-005]*
* **TASK-007:** Configure database state migrations using Alembic and initialize schemas. *[Depends on: TASK-006]*
* **TASK-008:** Implement centralized secure system configurations utilizing validating Pydantic BaseSettings. *[Depends on: TASK-007]*
* **TASK-009:** Build a stateless JWT authentication framework linked with a Redis token blacklist. *[Depends on: TASK-008]*
* **TASK-010:** Deploy decorator-based Role-Based Access Control (RBAC) supporting `@require_role`. *[Depends on: TASK-009]*
* **TASK-011:** Program the internal dictionary-based Translation and Internationalization (`I18nEngine`). *[Depends on: TASK-010]*
* **TASK-012:** Develop a dynamic runtime Module Registry and Feature-Flag gateway. *[Depends on: TASK-011]*
* **TASK-013:** Program the Paymenter secure webhook event receiver using HMAC-SHA256 verification. *[Depends on: TASK-012]*
* **TASK-014:** Initialize the Celery asynchronous worker ecosystem backed by Redis broker. *[Depends on: TASK-013]*
* **TASK-015:** Build a dynamic security Audit Logging module leveraging generic PostgreSQL `JSONB` fields. *[Depends on: TASK-014]*

---

### 🛡️ Phase 2: VPN Service Module (Weeks 3-5)
*Gate: Blocked until Phase 1 is 100% complete.*

* **TASK-016:** Construct module-specific relational schemas (VPN Accounts, Sessions, and Protocol Configs). *[Depends on: TASK-015]*
* **TASK-017:** Implement sub-process automated cryptographic key-pair generation for native WireGuard peers. *[Depends on: TASK-016]*
* **TASK-018:** Code the integration engine for anti-censorship protocols using a standalone Xray-core (VLESS + REALITY). *[Depends on: TASK-017]*
* **TASK-019:** Develop asynchronous business service classes to execute creation, suspension, and renewal. *[Depends on: TASK-018]*
* **TASK-020:** Expose clean REST endpoints (FastAPI routers) for client-facing panels and telemetry. *[Depends on: TASK-019]*
* **TASK-021:** Author Celery jobs to pull bandwidth logs every 5 minutes and compute expirations. *[Depends on: TASK-020]*
* **TASK-022:** Standardize module metadata parameters (`modules/vpn/metadata.py`). 🟡 **CURRENT BREAKPOINT** *[Depends on: TASK-021]*
* **TASK-023:** Initialize the automated Telegram interface bot structure employing the `aiogram 3.x` framework. *[Depends on: TASK-022]*
* **TASK-024:** Code interactive inline bot handlers for browsing products and downloading configurations. *[Depends on: TASK-023]*
* **TASK-025:** Scaffold the Client Portal UI web instance via a Next.js 15 and Tailwind CSS base stack. *[Depends on: TASK-024]*
* **TASK-026:** Build user web authentication forms featuring state-driven loading skeletons. *[Depends on: TASK-025]*
* **TASK-027:** Write functional user asset view dashboards displaying responsive Recharts bandwidth grids. *[Depends on: TASK-026]*
* **TASK-028:** Integrate frontend white-label asset replacement reading the active `TenantMiddleware` context. *[Depends on: TASK-027]*

---
### 💼 Phase 3: Centralized Admin Dashboard (Weeks 6-7)
*Gate: Blocked until Phase 2 is 100% complete.*

---
## دستور العمل اجرایی:

### ۱. منبع (پایه):
مخزن زیر رو به عنوان پایه استفاده کن (فقط برای ساختار و ایده، نه کپی کامل):
https://github.com/arhamkhnz/next-shadcn-admin-dashboard

### ۲. نحوه اجرا:
۱. مخزن رو clone کن یا محتواش رو به `web/admin/` منتقل کن
۲. همه چیز رو برای BlueHub بازنویسی کن:
   - برندینگ: "BlueHub"
   - RTL و فارسی (وزیرمتن)
   - رنگ‌ها: #1a56db (قابل تغییر White-Label)
۳. پنل رو Dockerized کن:
   - Dockerfile در web/admin/
   - docker-compose.yml با سرویس admin-panel

#### **TASK-029: Super-Admin API & Audit Setup**
**هدف:** ایجاد APIهای امن برای مدیریت چند-برندی و ممیزی

**زیرتسک‌ها:**
- [ ] ایجاد `api/v1/admin/audit.py` با endpointهای:
  - `GET /admin/audit/logs` - مشاهده تمام لاگ‌های سیستم
  - `GET /admin/audit/tenants/{tenant_id}` - لاگ‌های یک تیننت خاص
  - `POST /admin/audit/export` - خروجی گرفتن از لاگ‌ها
- [ ] اضافه کردن `AdminPermission` در RBAC
- [ ] تست امنیت: فقط SuperAdmin دسترسی داشته باشد

**فایل‌های مورد نیاز:**
api/v1/admin/audit.py
api/v1/admin/permissions.py
core/admin/audit_service.py
esponsive and mobile-friendly
Customizable theme presets (light/dark modes with color schemes like Tangerine, Brutalist, and more)
Flexible layouts (collapsible sidebar, variable content widths)
Authentication flows and screens
Prebuilt dashboards (Default, CRM, Finance, Analytics, Productivity) plus legacy variants
Role-Based Access Control (RBAC) with config-driven UI and multi-tenant support 

text

---

#### **TASK-030: Scaffold Admin Panel (Next.js)**
**هدف:** راه‌اندازی پروژه Next.js برای پنل ادمین

**زیرتسک‌ها:**
- [ ] ایجاد `web/admin/` با Next.js 14 + TypeScript
- [ ] نصب و تنظیم Tailwind CSS + shadcn/ui
- [ ] ایجاد `Dockerfile` با multi-stage build
- [ ] تنظیم `docker-compose.yml` برای سرویس `admin-panel`

**فایل‌های مورد نیاز:**
web/admin/Dockerfile
web/admin/next.config.js
web/admin/package.json
web/admin/tailwind.config.js
web/admin/src/app/layout.tsx
web/admin/src/app/page.tsx

text

Default Dashboard
CRM Dashboard
Finance Dashboard
Analytics Dashboard
Productivity Dashboard
E-commerce Dashboard
Academy Dashboard
Logistics Dashboard
Infrastructure Dashboard
Chat Page
Email Page
Users Management
Roles Management
Kanban Board
Tasks Page
Invoice Page
Calendar Page
Authentication (4 screens)
Legacy: Default v1, CRM v1, Finance v1, Analytics v1
---

#### **TASK-031: Enterprise Metrics Dashboard**
**هدف:** داشبورد اصلی با آمار سیستم و حاشیه سود

**زیرتسک‌ها:**
- [ ] کارت‌های آمار:
  - تعداد کل کاربران
  - تعداد سرویس‌های فعال
  - درآمد کل (ماه جاری)
  - تعداد تیننت‌ها
- [ ] نمودارها با Recharts:
  - رشد کاربران در ۶ ماه اخیر
  - توزیع سرویس‌ها
  - درآمد ماهانه
- [ ] جدول آخرین فعالیت‌ها (Audit Logs)

**فایل‌های مورد نیاز:**
web/admin/src/app/dashboard/page.tsx
web/admin/src/components/dashboard/StatsCards.tsx
web/admin/src/components/dashboard/RevenueChart.tsx
web/admin/src/components/dashboard/ActivityTable.tsx

text

---

#### **TASK-032: Tenant Control Panels**
**هدف:** پنل مدیریت تیننت‌ها (برندهای مستقل)

**زیرتسک‌ها:**
- [ ] لیست تمام تیننت‌ها با صفحه‌بندی
- [ ] ایجاد/ویرایش/حذف تیننت
- [ ] مدیریت برندینگ هر تیننت (رنگ، لوگو، نام)
- [ ] نمایش آمار هر تیننت (کاربران، سرویس‌ها، درآمد)

**فایل‌های مورد نیاز:**
web/admin/src/app/dashboard/tenants/page.tsx
web/admin/src/app/dashboard/tenants/components/TenantFormModal.tsx
web/admin/src/app/dashboard/tenants/components/TenantStats.tsx

text

---

#### **TASK-033: Feature-Flag Management Board**
**هدف:** پنل مدیریت Feature Flags برای ماژول‌ها

**زیرتسک‌ها:**
- [ ] لیست تمام ماژول‌های ثبت‌شده
- [ ] toggle کردن فعال/غیرفعال برای هر ماژول
- [ ] تنظیمات پیشرفته:
  - `stop_new_sales`: توقف فروش جدید
  - `terminate_services`: خاتمه سرویس‌ها
  - `maintenance_mode`: حالت نگهداری
- [ ] نمایش وضعیت هر ماژول با رنگ‌های مختلف

**فایل‌های مورد نیاز:**
web/admin/src/app/dashboard/modules/page.tsx
web/admin/src/app/dashboard/modules/components/ModuleCard.tsx
web/admin/src/app/dashboard/modules/components/ModuleConfigModal.tsx

text

---

#### **TASK-034: Product Catalog Sync**
**هدف:** همگام‌سازی کاتالوگ محصولات با Paymenter

**زیرتسک‌ها:**
- [ ] لیست محصولات با فیلتر ماژول
- [ ] ایجاد/ویرایش/حذف محصول
- [ ] sync با Paymenter (ارسال قیمت‌ها)
- [ ] نمایش وضعیت sync (موفق/ناموفق)

**فایل‌های مورد نیاز:**
web/admin/src/app/dashboard/products/page.tsx
web/admin/src/app/dashboard/products/components/ProductFormModal.tsx
web/admin/src/app/dashboard/products/components/SyncStatus.tsx

text

---

#### **TASK-035: Real-time Admin Logs**
**هدف:** نمایش لاگ‌های سیستمی به صورت لحظه‌ای

**زیرتسک‌ها:**
- [ ] نمایش لاگ‌های Audit با فیلتر (نوع، کاربر، تیننت)
- [ ] جستجو در لاگ‌ها
- [ ] صفحه‌بندی و خروجی CSV
- [ ] WebSocket یا Polling برای به‌روزرسانی لحظه‌ای

**فایل‌های مورد نیاز:**
web/admin/src/app/dashboard/logs/page.tsx
web/admin/src/app/dashboard/logs/components/LogFilter.tsx
web/admin/src/app/dashboard/logs/components/LogTable.tsx

text

---

### **پیش‌نیازهای فنی (قبل از شروع)**

#### ۱. **Dockerize کردن پنل:**

**Dockerfile:**
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
next.config.js:

javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: ['localhost', 'backend'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/api/v1/:path*',
      },
    ];
  },
};
module.exports = nextConfig;
docker-compose.yml (قسمت admin-panel):

yaml
services:
  admin-panel:
    build: ./web/admin
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000/api/v1
    depends_on:
      - backend
    restart: unless-stopped
۲. RTL و فارسی:
layout.tsx:

tsx
import { Vazirmatn } from 'next/font/google';
const vazirmatn = Vazirmatn({ subsets: ['arabic'] });

export default function RootLayout({ children }) {
  return (
    <html lang="fa" dir="rtl" className={vazirmatn.className}>
      <body>{children}</body>
    </html>
  );
}
۳. White-Label (قابل تغییر):
src/lib/branding.ts:

typescript
export const getBranding = () => {
  const tenant = JSON.parse(localStorage.getItem('tenant') || '{}');
  return {
    primaryColor: tenant.branding_config?.primary_color || '#1a56db',
    brandName: tenant.branding_config?.brand_name || 'BlueHub',
    logoUrl: tenant.branding_config?.logo_url || '/logo.png',
  };
};
خروجی نهایی فاز ۳:
docker-compose up -d همه چی رو بالا بیاره

پنل در http://localhost:3000 قابل دسترس باشه

RTL و فارسی درست کار کنه

قابلیت White-Label فعال باشه

همه ۷ تسک کامل شده باشن

تست‌های پنل پاس بشن

### 🖥️ Phase 4: VPS Provisioning Module (Weeks 8-9)
*Gate: Runs in parallel workflow logic after Phase 2, but must finish jointly with Phase 3 before Phase 5 blocks drop.*

* **TASK-036:** Create localized relational schemas for virtual machines, IP pools, and OS templates. *[Depends on: TASK-028]*
* **TASK-037:** Code the external data communications layer talking to Proxmox cluster endpoints via `proxmoxer`. *[Depends on: TASK-036]*
* **TASK-038:** Implement automated ordering workflows to execute provisioning actions after billing validation. *[Depends on: TASK-037]*
* **TASK-039:** Write inline Telegram bot mechanics allowing remote VPS controls (Power, Reboot). *[Depends on: TASK-038]*
* **TASK-040:** Develop the client browser console layout with secure interactive HTML5 noVNC integrations. *[Depends on: TASK-039]*
* **TASK-041:** Design recurring backend worker telemetry tracking core resource usage metrics. *[Depends on: TASK-040]*

---

### 🌐 Phase 5: Supplementary Intelligent Modules (Weeks 10-11)
*Gate: HARD LOCKED. This phase cannot start until BOTH TASK-035 (Phase 3) and TASK-041 (Phase 4) are marked absolute COMPLETE.*

* **TASK-042:** Program the SmartDNS module architecture allowing un-proxied geo-unblocking. *[Depends on: TASK-035, TASK-041]*
* **TASK-043:** Design shared-access routing nodes for streaming networks utilizing backend token switches. *[Depends on: TASK-042]*
* **TASK-044:** Code micro-packet optimization services (Game Module) built to reduce latency and jitter. *[Depends on: TASK-043]*

---

### 🚀 Phase 6: Production Hardening & Deployment Configuration (Weeks 12-13)
*Gate: Blocked until Phase 5 is 100% complete.*

* **TASK-045:** Enforce high-volume monthly table partitioning schemes on TimescaleDB for metrics tables. *[Depends on: TASK-044]*
* **TASK-046:** Implement structural circuit-breaking using `pybreaker` for fallback handlers on core services. *[Depends on: TASK-045]*
* **TASK-047:** Protect API exposed routes with high-speed token-bucket rate limiters (`slowapi`) using Redis. *[Depends on: TASK-046]*
* **TASK-048:** Construct dynamic SSL termination routing and reverse proxy rules utilizing Nginx or Traefik. *[Depends on: TASK-047]*
* **TASK-049:** Write multi-stage Dockerfiles optimizing runtime images and shrinking attack surfaces. *[Depends on: TASK-048]*
* **TASK-050:** Author target-specific orchestration manifests (Kubernetes or Docker Swarm) for production. *[Depends on: TASK-049]*
* **TASK-051:** Deploy multi-tiered observability tracking infrastructure utilizing Prometheus and Grafana. *[Depends on: TASK-050]*
* **TASK-052:** Setup automated database dump routines and state snapshots syncing securely with remote MinIO/S3. *[Depends on: TASK-051]*
* **TASK-053:** Execute end-to-end load testing to verify system behaviors under connection spikes. *[Depends on: TASK-052]*
* **TASK-054:** Execute Next.js asset-optimization pipelines and code-splitting to guarantee performance. *[Depends on: TASK-053]*
* **TASK-055:** Export comprehensive live documentation resources including absolute OpenAPI schemas. *[Depends on: TASK-054]*

---

### 🔐 Phase 7: Advanced Security Features (Strictly Blocked)
*System Guardrail Notice: As stated in section 4 of `.clinerules`, planning or execution on this phase is strictly frozen unless explicit commands are issued by the platform operator.*

* **TASK-056:** Anti-Crack System implementation (binary obfuscation routines and ECDSA client license checks).
* **TASK-057:** AI Adaptive Obfuscation Engine (A²OE) for dynamic protocol shape-shifting.
* **TASK-058:** Distributed Hybrid Peer-to-Peer Relay Network construction.
* **TASK-059:** Deployment of NIST-standardized Quantum-Resistant Encryption algorithms.



## 10. DOCKER CONFIGURATION
Docker path: `C:\Program Files\Docker\Docker\resources\bin\docker`

If the Docker daemon is not running, notify the user immediately but continue core code generation. Do not entirely block software architecture design tasks on local daemon availability.
