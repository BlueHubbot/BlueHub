AGENTS.md - Multi-Agent Unified Directive for BlueHub Platform
This file establishes the cross-agent runtime standard for AI Coding Assistants working on the BlueHub Platform. It defines the operational roles, collaborative tasks, and boundaries when navigating the codebase.

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

## 7. AUTOMATIC TASK EXECUTION

After completing each task successfully:

1. Read `tasks.md` and identify the next task whose dependencies are satisfied
2. Automatically start working on the next task without asking the user
3. Continue until all tasks are completed or an error occurs
4. Never ask "shall I continue?" — just continue

## 8. Docker Configuration

Docker path: `C:\Program Files\Docker\Docker\resources\bin\docker`

If daemon is not running, notify user but continue code generation. Do not block tasks on Docker availability.