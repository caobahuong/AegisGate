# AegisGate

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.2+-black.svg?logo=next.js&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4+-38B2AC.svg?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/Unit_Tests-32%20Passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **AegisGate** is an enterprise AI Execution Proxy and Pluggable Harness Platform that stands securely between **AI Agents** and **Third-Party Systems** (SQL Server, MongoDB, PostgreSQL, internal databases).

Built around the core architectural philosophy of **"Total Decoupling & Process Isolation (Core độc lập - Plugin cắm rời)"**, the AegisGate Core is completely vendor-agnostic. All vendor-specific operations (connection pooling, transactions, explain plans, query execution, and emergency termination) are encapsulated within independent, pluggable modules communicating via **JSON-RPC 2.0 over Stdio**.

---

## 🏛 Conceptual Architecture

```text
+-----------------------------------------------------------------------------------+
|                                  AI AGENTS LAYER                                  |
|               (Connects via Model Context Protocol (MCP), REST, SDK)              |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               AEGISGATE CORE PLATFORM (AI PROXY & PLUGGABLE HARNESS)              |
|                   *Completely Agnostic of Third-Party Dialects*                   |
|                                                                                   |
|  +---------------------------+   +---------------------------------------------+  |
|  |   Hybrid Knowledge Store  |   |     State Machine Execution Gatekeeper      |  |
|  | - SQLite Schema Metadata  |   | - Dry-Run -> Pause/Auto -> Execute -> Log   |  |
|  | - Markdown doc.md & Skills|   | - Controls: Approve / Reject / Stop (Kill)  |  |
|  | - Governance Rule Store   |   | - Timeout Guards: 15s (Read) / 30s (Write)  |  |
|  +-------------+-------------+   +----------------------+----------------------+  |
|                ^                                        ^                         |
|                | (Chunked Schema Ingest)                | (Plan, Output, Log Sink)|
|  ==============+========================================+=======================  |
|  |        STANDARD PLUGIN CONTRACT INTERFACES (JSON-RPC 2.0 OVER STDIO)        |  |
+--+-----------------------------------------------------------------------------+--+
   ^                                      ^                                      ^
   | (Subprocess IPC)                     | (Subprocess IPC)                     | (Subprocess IPC)
   v                                      v                                      v
+-----------------------+              +-----------------------+              +-----------------------+
|  PLUGIN: SQL SERVER   |              |    PLUGIN: MONGODB    |              | PLUGIN: ANY 3RD-PARTY |
|  (Process Isolation)  |              |  (Process Isolation)  |              |  (Process Isolation)  |
| - Manages Credentials |              | - Manages Credentials |              | - Manages Connection  |
| - Scans Tables & Index|              | - Scans Collections   |              | - Scans Schema        |
| - SET SHOWPLAN_XML ON |              | - .explain() Stats    |              | - Dry-Run Engine      |
| - Forbids Bad JOINs   |              | - Custom Rules Engine |              | - Enforces Constraints|
| - Timeout -> KILL SPID|              | - Timeout -> db.killOp|              | - Timeout -> Kill Op  |
+-----------+-----------+              +-----------+-----------+              +-----------+-----------+
            |                                      |                                      |
            v                                      v                                      v
   [Microsoft SQL Server]                 [MongoDB Cluster]                     [Other Target System]
```

---

## ✨ Key Features & Capabilities

1. **Zero-Touch AI Discovery (Cached Hybrid Knowledge Store):**
   - AI Agents explore schema, tables, columns, and indexes from AegisGate's local SQLite cache without directly touching or stressing third-party databases.
   - Enriched with human-authored Markdown business context (`doc.md`) and standard query templates (`skills.md`).
2. **Pre-Execution Dry-Run & Governance Rule Engine:**
   - Pre-inspects queries against platform rules before execution.
   - Automatically detects and blocks dangerous queries (e.g. Forbidden JOIN between high-volume tables, unbounded Table Scans without `WHERE`).
3. **Execution State Machine & Human-in-the-Loop:**
   - **Auto Mode ON:** Queries that pass dry-run inspection execute automatically.
   - **Auto Mode OFF (Manual Review):** Queries transition to `PAUSED_FOR_REVIEW`, presenting the execution plan to administrators for one-click `Approve & Run` or `Reject`.
4. **Strict Timeout Guards (15s / 30s) & Emergency Kill:**
   - Read queries: Maximum 15.0 seconds.
   - Write queries: Maximum 30.0 seconds.
   - If timeout is exceeded or an admin clicks **Stop**, the Core dispatches an emergency abort command (`KILL {spid}` / `killOp`) directly to the target system.
5. **Real-Time Dark-First Dashboard (Next.js App Router):**
   - 3-Column balanced monitor layout conforming strictly to [`design.md`](./docs/ui_design_system_frontend_architecture_rulebook.md).
   - Real-time Server-Sent Events (SSE) updates without polling.
   - Two-Card Layout for Pluggable Targets and dynamic "Add New Plugin" modal.
   - Audit log ledger with query inspection drawer.
6. **Model Context Protocol (MCP) Server:**
   - Built-in FastMCP server exposing 4 standard tools (`get_catalog`, `get_knowledge`, `submit_execution`, `check_execution_status`).

---

## 📂 Project Directory Structure

```text
AegisGate/
├── core/                        # Backend Core Platform (FastAPI & MCP)
│   ├── config.py                # Central pydantic-settings configuration
│   ├── database.py              # SQLModel SQLite entities & session management
│   ├── exceptions.py            # Custom domain exceptions
│   ├── main.py                  # FastAPI application entrypoint & CORS
│   ├── engine/                  # State Machine & Execution Gatekeeper
│   │   ├── state_machine.py     # Dry-Run -> Pause/Auto -> Execute -> Log flow
│   │   ├── governance.py        # Governance Rule Inspector (cấm JOIN, table scan)
│   │   ├── timeout_guard.py     # 15s/30s async timeout guards
│   │   ├── plugin_registry.py   # Manifest discovery & target profiles
│   │   └── plugin_client.py     # JSON-RPC 2.0 Stdio client with try...finally cleanup
│   ├── gateway/                 # AI & Dashboard Gateways
│   │   ├── api_routes.py        # Clean REST API routes
│   │   ├── services.py          # Service layer separating business logic
│   │   ├── schemas.py           # Strictly-typed Pydantic request/response models
│   │   ├── sse_broadcaster.py   # Server-Sent Events (SSE) broadcaster
│   │   └── mcp_server.py        # FastMCP Server exposing 4 AI tools
│   └── storage/                 # Storage Layer
│       ├── knowledge_store.py   # Hybrid SQLite + Markdown storage
│       ├── rule_store.py        # Rule CRUD persistence
│       ├── log_store.py         # Execution audit log store
│       └── setting_store.py     # Auto mode & runtime settings
│
├── plugins/                     # Independent Pluggable Targets
│   ├── plugin_contract.py       # JSON-RPC 2.0 Protocol & 4-Port Interface
│   └── sqlserver_plugin/        # SQL Server Reference Plugin
│       ├── plugin_manifest.json # Target metadata & configuration
│       ├── adapter.py           # Implements Sync, DryRun, Execute, Abort
│       └── requirements.txt     # Plugin dependencies (pyodbc, pydantic)
│
├── frontend/                    # Next.js 14 Dashboard (Dark Theme)
│   ├── src/app/                 # App Router (layout.tsx, page.tsx, globals.css)
│   ├── src/components/          # Modular UI components (Header, Sidebar, Monitor, etc.)
│   ├── src/lib/                 # Typed API client & utilities
│   ├── src/types/               # TypeScript interfaces (Zero `any` policy)
│   └── package.json             # Frontend dependencies & scripts
│
├── data/                        # Internal Core Storage
│   ├── aegisgate.db             # Central SQLite database
│   └── knowledge_docs/          # Markdown documents (doc.md, skills.md)
│
├── tests/                       # Comprehensive Testing Suite
│   ├── test_phase1.py           # Phase 1: Core models & storage tests
│   ├── test_phase2.py           # Phase 2: Engine, State Machine & REST API tests
│   ├── test_phase3.py           # Phase 3: Plugin adapter & Stdio IPC tests
│   ├── browser_verification.py  # Playwright browser automation
│   └── system_verification.py   # Anti-Gravity Browser QA over Chrome Debugging (Port 9222)
│
├── report/                      # Quality Assurance Reports & Screenshots
│   ├── execution_report.md      # Official verification & completion report
│   └── screenshots/             # Visual verification screenshots
│
└── docs/                        # Architectural Rulebooks & Specifications
    ├── project_architecture_business_plan.md   # plan.md
    ├── tech.md                                 # Technical specification
    ├── ui_design_system_frontend_architecture_rulebook.md # design.md
    ├── python_clean_code_skill.md              # Python standards
    └── typescript_clean_code_skill.md          # TypeScript standards
```

---

## ⚡ Quick Start Guide

### Prerequisites
- Python 3.11+
- Node.js 18+ & npm 9+
- Git

### 1. Backend Core Setup
From the repository root:
```bash
# Install Python dependencies
pip install fastapi uvicorn sqlmodel pydantic pydantic-settings mcp sse-starlette pytest playwright psutil

# Start the Backend Core Server
python -m uvicorn core.main:app --host 127.0.0.1 --port 8000 --reload
```
- **Swagger REST API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Real-Time SSE Stream:** [http://127.0.0.1:8000/api/monitor/events](http://127.0.0.1:8000/api/monitor/events)

### 2. Frontend Dashboard Setup
In a new terminal:
```bash
cd frontend

# Install Node dependencies
npm install

# Run the development server
npm run dev

# Or build and run for production
npm run build
npm run start
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Testing & Verification

AegisGate enforces rigorous testing across all architectural layers:

```bash
# 1. Run all Backend Unit Tests (29 tests)
python -m pytest -v

# 2. Run Frontend Component Tests (Vitest)
cd frontend
npm test

# 3. Run Anti-Gravity Browser Quality Assurance (Chrome Debugging Port 9222)
python tests/system_verification.py
```

### Verification Highlights:
- **Backend Tests:** 29/29 Passed (Models, Hybrid Store, Rule Matching, Timeout Guards, State Machine, REST Endpoints, and Subprocess Stdio IPC).
- **Frontend Tests:** 3/3 Passed (Header toggle, Sidebar tab navigation, Audit Log search/filtering).
- **Anti-Gravity Browser QA:** 100% Passed with **0 DevTools Console Errors**, zero orphan subprocesses, and verified dark-first tokens (`#020617`).
- **QA Screenshots:** 21 high-resolution verification screenshots captured in [`report/screenshots/`](./report/screenshots/).

---

## 🔌 Standard Plugin Contract (JSON-RPC 2.0 over Stdio)

Any system can be connected to AegisGate by implementing 4 standard ports:

```json
// 1. Sync Knowledge
{"jsonrpc": "2.0", "method": "sync_knowledge", "params": {"config": {}}, "id": 1}

// 2. Pre-Check & Dry-Run
{"jsonrpc": "2.0", "method": "dry_run", "params": {"query": "SELECT * FROM Orders", "rules": []}, "id": 2}

// 3. Supervised Execution
{"jsonrpc": "2.0", "method": "execute", "params": {"execution_id": "exec_1", "query": "...", "timeout_seconds": 15.0}, "id": 3}

// 4. Emergency Kill / Abort
{"jsonrpc": "2.0", "method": "abort", "params": {"execution_id": "exec_1"}, "id": 4}
```

See [`plugins/README.md`](./plugins/README.md) for step-by-step guides on authoring plugins for MongoDB, PostgreSQL, and custom internal systems.

---

## 📖 Sub-Module Documentation

- [Backend Core Documentation](core/README.md)
- [Plugin Architecture Documentation](plugins/README.md)
- [Frontend Dashboard Documentation](frontend/README.md)
- [Testing & Quality Assurance Suite](tests/README.md)
- [Official Execution Report](report/execution_report.md)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
