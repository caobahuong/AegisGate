# AegisGate Verification & Testing Suite

AegisGate includes a comprehensive three-tier testing suite covering Backend Unit Tests, Frontend Component Tests, and Anti-Gravity Browser Automation via Chrome Debugging (Port 9222).

---

## 🧪 Test Architecture

```text
tests/
├── test_phase1.py              # Phase 1: Models, SQLite DB, KnowledgeStore, RuleStore, LogStore
├── test_phase2.py              # Phase 2: Governance Engine, Timeout Guards, State Machine, REST API
├── test_phase3.py              # Phase 3: SQL Server Plugin direct methods & Stdio Subprocess IPC
├── browser_verification.py     # Interactive Playwright browser automation
└── system_verification.py      # Comprehensive QA runner with Chrome Debugging on Port 9222
```

---

## 🏃 Running the Tests

### 1. Backend Unit Tests (`pytest`)
Executes all 29 backend test cases across Phase 1, Phase 2, and Phase 3:
```bash
python -m pytest -v
```

### 2. Frontend Component Tests (`Vitest`)
Executes component tests for Header, Sidebar, and AuditLogs:
```bash
cd frontend
npm test
```

### 3. Anti-Gravity Browser Quality Assurance (Chrome Debugging Port 9222)
Launches the automated browser test suite that verifies:
- Dark theme computed styles (`rgb(2, 6, 23)` / `#020617`) and typography.
- Tab switching across all 4 dashboard views.
- "Add New Plugin" modal with instant reactive updates to tabs and sidebar.
- State Machine AI request simulations (Manual Review flow, Forbidden JOIN rule rejection, and Auto Approval execution).
- DevTools Console inspection confirming **0 JavaScript console errors** and clean SSE lifecycle.

```bash
# Ensure Backend (port 8000) and Frontend (port 3000) are running, then run:
python tests/system_verification.py
```

All visual verification screenshots are captured and saved to [`report/screenshots/`](../report/screenshots/).
