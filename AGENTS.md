# AGENTS.md - Multi-Agent Unified Directive for BlueHub Platform

This file establishes the cross-agent runtime standard for AI Coding Assistants working on the BlueHub Platform. It defines the operational roles, collaborative tasks, and boundaries when navigating the codebase.

---

## 1. Dual-Engine Architecture (Gemini + DeepSeek)

To optimize resource consumption, speed, and execution accuracy, the developer maintains two distinct active engines. AI agents must dynamically allocate subtasks based on their specialized capabilities:

### 🧠 Engine Alpha: Gemini (Context & Architecture Master)
- **Primary Role**: High-level code comprehension, massive context scanning, system architecture queries, and reading the comprehensive 150+ page specification.
- **When to Use**: 
  - Reading and cross-referencing `design.md`, `requirements.md`, and `tasks.md`.
  - Analyzing database schema changes (`shared/models/` or Alembic migrations).
  - Formulating multi-tenant domain routing strategies.
  - Validating Phase boundaries and system compatibility.
- **Instruction to Agent**: If you are currently performing a deep code-generation task but need a holistic architecture check, explicitly prompt the user: *"Please temporarily switch my active engine to Gemini to analyze the context window of this phase."*

### ⚡ Engine Beta: DeepSeek (Logic, Coding & Debugging Master)
- **Primary Role**: Dense code generation, refactoring, writing algorithms, logical reasoning, and resolving bugs.
- **When to Use**:
  - Writing FastAPI routes and database query layers.
  - Implementing `aiogram` Telegram bot handlers.
  - Creating Next.js 15 pages and custom Hooks.
  - Executing migrations via Alembic.
  - Isolating runtime errors and writing unit tests.
- **Instruction to Agent**: When writing high-quality scripts, ensure you are running on the DeepSeek engine. If you detect complex reasoning is needed for an algorithm, ask the user to switch active settings to DeepSeek.

---

## 2. Directory Scopes & Boundaries

Agents must operate within distinct folder boundaries to prevent code regression:

| Directory | Scope | Write Permissions | Rule |
|-----------|-------|-------------------|------|
| `/core` | Platform Core Engine | Restricted | No service-specific code allowed here. Must remain generic. |
| `/modules` | Service-Specific Plugins | Full | Must contain isolated `models.py`, `services.py`, `api.py`, `tasks.py`, `metadata.py`. |
| `/api` | REST Router Layer | Full | Dynamically imports endpoints from modules. Do not write business logic. |
| `/bot` | Telegram Bot UI | Full | Thin presentation layer. Must call API endpoints only. No direct DB access. |
| `/web` | Admin & Client Portals | Full | UI only. Must call API endpoints only. No direct DB access. |

---

## 3. Communication Protocols
- **Proactive Interrogation**: Do not make assumptions about external services. If a connection configuration for Proxmox, Paymenter, or WireGuard is unclear, search the `.blue/decisions/` folder or prompt the user.
- **Commit Etiquette**: All Git commits executed by the agent must follow Conventional Commits format:
  - `feat(module): description` for new features.
  - `fix(module): description` for bug fixes.
  - `docs(module): description` for documentation updates.
  - `refactor(module): description` for code cleanups.