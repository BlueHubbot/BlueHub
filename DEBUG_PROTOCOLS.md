# DEBUG_PROTOCOLS.md - Advanced Diagnosis & Recovery Framework

This document defines the strict, step-by-step diagnostic protocol that the AI Coding Agent must execute whenever a test fails, a compiler error is raised, or a runtime bug is detected on the BlueHub Platform.

---

## 1. Pre-Modification Isolation Steps

### 🔍 Step 1: Read the Logs Directly
- **Rule**: Do not speculate on the cause of an error. You must explicitly read the logs.
- **Action**: Execute terminal commands to retrieve standard error traces or read active logs in `/var/log/bluehub/`.
- **Verify**: Inspect trace boundaries, call-stack offsets, and exception class names.

### 🌐 Step 2: Cross-Reference Architectural Integrity
- **Rule**: Any fix must not damage system architecture (Multi-tenancy, Multi-language, or Modularity).
- **Action**: Verify that your proposed solution:
  - Does not hardcode localized strings (must use `t()` translation keys).
  - Does not execute raw PostgreSQL queries bypassing tenant-isolation filters (`WHERE tenant_id = ...`).
  - Does not import from `/modules/` into the `/core` directory.
  - Does not bypass existing Circuit Breakers for Paymenter or Proxmox VE.

### 📝 Step 3: Document in the Bug Tracker
- **Rule**: You must write down the bug context before modifying source code.
- **Action**: Open `memory/BUGS.md` and log the active issue, including stack trace summaries, hypothesized causes, and proposed fixes.

---

## 2. Modification Rules

### 💬 Rule 2.1: Write a Diagnostic Comment
- **Before writing any patch**, you MUST add a short explanation comment directly above the code lines you are about to modify. This keeps a record of the diagnostic context inside the code history.
- **Format**:
  ```python
  # DIAGNOSIS [AI Agent]: [Brief explanation of what broke and why this patch fixes it]
  # See: memory/BUGS.md