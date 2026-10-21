# AegisGate Core Engine

The **Core Engine** is the central orchestration and governance platform of AegisGate. Built with **Python 3.11+ / FastAPI**, it is designed around the core philosophy of **"Total Decoupling & Third-Party Agnosticism"**: the Core has zero direct dependency or embedded knowledge of specific database vendors (SQL Server, MongoDB, etc.). Instead, it operates strictly as an **Execution Proxy, Knowledge Store, State Machine Gatekeeper, and AI Gateway**.

---

## 🏛 Architecture Overview

```text
core/
├── config.py              # Central pydantic-settings configuration (Zero hardcoding)
├── database.py            # SQLite database entities (SQLModel) & session management
├── exceptions.py          # Custom domain exceptions hierarchy
├── main.py                # FastAPI app initialization, CORS, and lifecycle
│
├── engine/                # Core State Machine & Execution Gatekeeper
│   ├── state_machine.py   # State transitions: Dry-Run -> Pause/Auto -> Execute -> Log
│   ├── governance.py      # Governance rules inspector (FORBID_JOIN, Table Scan, Timeout)
│   ├── timeout_guard.py   # Strict 15s (Read) and 30s (Write) async execution guards
│   ├── plugin_registry.py # Manifest discovery & profile management
│   └── plugin_client.py   # JSON-RPC 2.0 over Stdio client with try...finally cleanup
│
├── gateway/               # AI & Dashboard Communication Gateway
│   ├── api_routes.py      # Clean REST API endpoints (Strict Separation of Concerns)
│   ├── services.py        # Gateway business logic service layer
│   ├── schemas.py         # Strictly-typed Pydantic request & response models
│   ├── sse_broadcaster.py # Server-Sent Events (SSE) real-time event distribution
│   └── mcp_server.py      # Official Model Context Protocol (FastMCP) with 4 AI Tools
│
└── storage/               # Hybrid Storage Layer
    ├── knowledge_store.py # SQLite metadata + Markdown docs (doc.md / skills.md)
    ├── rule_store.py      # Governance rules persistence
    ├── log_store.py       # Execution audit log ledger
    └── setting_store.py   # System settings (Auto Approval Mode toggle)
```

---

## ⚙️ Key Modules & Responsibilities

### 1. `config.py` (Central Settings)
- Built with `pydantic-settings.BaseSettings`.
- Enforces the **Zero Magic Numbers** rule from `python_clean_code.md`.
- Default values:
  - `READ_TIMEOUT_SECONDS`: 15.0s
  - `WRITE_TIMEOUT_SECONDS`: 30.0s
  - `AUTO_APPROVAL_DEFAULT`: False
  - `DATABASE_URL`: `sqlite:///./data/aegisgate.db`

### 2. `database.py` (SQLModel SQLite Layer)
- Defines entities:
  - `PluginProfile`: Registered target plugins with adapter directives (`dry_run_command`, `abort_command`, `latency_ms`, `active_sessions_count`).
  - `KnowledgeChunk`: Structural schema partitions (`Sales`, `Inventory`, `Finance`) with file pointers to `doc.md` and `skills.md`.
  - `Rule`: Governance rules (`FORBID_JOIN`, `FORBID_TABLE_SCAN`, `MAX_EXECUTION_TIME`, `CUSTOM`).
  - `ExecutionLog`: Full audit record of query text, query type, explain plans, violations, execution time, and SPID.
  - `SystemSetting`: Global state persistence (`auto_approval_mode`).
- Dependency injection via `get_session()` for all FastAPI routes.

### 3. `engine/state_machine.py` (Execution Lifecycle)
Coordinates the 4-step execution state machine:
```text
Dry-Run (Plugin + Core Rules)
    ├── If Violations Found ────────► REJECTED (Logs saved, reason returned)
    └── If Valid (Zero Violations)
            ├── If Auto Mode ON ────► EXECUTING ─► COMPLETED (with timer & results)
            └── If Auto Mode OFF ───► PAUSED_FOR_REVIEW
                                          ├── Approve ──► EXECUTING ─► COMPLETED
                                          ├── Reject ───► REJECTED
                                          └── Stop ─────► ABORTED (Emergency Kill)
```

### 4. `engine/timeout_guard.py` (Timeout Guards)
- Reads: Maximum 15.0 seconds.
- Writes: Maximum 30.0 seconds.
- Custom rule: Can lower the limit.
- Wraps execution in `asyncio.wait_for`. If threshold is breached, triggers emergency `abort` hook to terminate the target database session (SPID), then raises `ExecutionTimeoutError`.

### 5. `gateway/mcp_server.py` (AI Model Context Protocol)
Exposes 4 standard tools for AI Agents (Claude, Gemini, ChatGPT):
1. `get_catalog(target_id, partition_key)`: Zero-touch structural catalog inspection from cache.
2. `get_knowledge(target_id, partition_key)`: Retrieves `doc.md`, query `skills.md`, and active governance rules.
3. `submit_execution(target_id, query, reasoning)`: Ingests query into AegisGate for dry-run and controlled execution.
4. `check_execution_status(execution_id)`: Checks status, metrics, and data results.

---

## 🚀 Running the Core Engine

```bash
# Start FastAPI Core with Uvicorn
python -m uvicorn core.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check:** `GET http://127.0.0.1:8000/health`
- **Real-time SSE:** `GET http://127.0.0.1:8000/api/monitor/events`

---

## 🧪 Testing

```bash
# Run Core Unit Tests
python -m pytest tests/test_phase1.py tests/test_phase2.py -v
```
