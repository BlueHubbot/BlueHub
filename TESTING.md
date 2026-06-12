# BlueHub Automated Testing Pipeline

This pipeline acts as the automated gatekeeper and quality assurance framework for the **BlueHub Platform**. It provides isolated, Docker-based testing to prevent system regression across all phases of implementation.

---

## 1. Pipeline Architecture & Lifecycle

[Developer Trigger]
                           │
                 [Makefile: test-docker]
                           │
              [Docker Build: Dockerfile.test]
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    [Stage 1: Ruff Linter]     [Stage 2: Pytest Unit]
             │                           │
             ├───────────────────────────┤
             ▼                           ▼
[Stage 3: Pytest Integration]   [Stage 4: Smoke Test Handshake]
             │                           │
             └─────────────┬─────────────┘
                           ▼
              [Stage 5: Report Compiler]
                           │
                [test-reports/latest.json]
                [test-reports/SUMMARY.txt]

- **Isolation**: The entire runtime environment is contained inside a lightweight Python 3.12-slim image, protecting host system dependencies.
- **Sequential Execution**: Tests run sequentially from fast static linting to unit tests, API integration tests, and simulated service handshakes.
- **Exit Gates**: If any stage fails, the pipeline immediately flags the defect and exits with exit code `1`. Only a 100% green pass unlocks transitions to the next phase.

---

## 2. Phase-Based Pipeline Evolution

The testing footprint automatically adapts and scales across the project's life cycle:

- **Phase 0 & 1 (Setup & Core)**: High emphasis on **Linter rules**, **authentication middleware**, and **JWT encryption integrity**. Unit tests mock user and tenant context boundaries.
- **Phase 2 (VPN Module)**: Integration tests expand to verify WireGuard configuration file generation, QR code rendering payload structures, and Xray-core VLESS JSON routing configurations.
- **Phase 3 (Admin Panel)**: Web client mock tests check cross-origin routing policies and validation rules for multi-tenant billing schemas.
- **Phase 4 (VPS Module)**: Integration of Proxmox VE mocks to assert cloning, snapshot creation, and network sizing states through `proxmoxer`.
- **Phase 6 (Production)**: Automated load benchmarks run under simulated traffic thresholds (asserting 1000+ request signatures/second with latencies strictly limited to `< 200ms`).

---

## 3. Writing New Test Footprints

When writing new capabilities, add tests into their respective directories matching standard patterns.

### Writing a Unit Test (e.g., `tests/unit/test_vpn_helpers.py`)
```python
import pytest

def sanitize_peer_address(address: str) -> str:
    return address.strip().lower()

def test_sanitize_peer_address():
    assert sanitize_peer_address("  10.0.0.1  ") == "10.0.0.1"

