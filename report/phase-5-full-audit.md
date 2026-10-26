# PHASE 5 of 5 — Full-System Independent Quality Audit & Defect Report

**Date of Audit:** October 26, 2026
**Auditor Role:** Independent Senior QA & Reliability Engineer
**System:** AegisGate AI Execution Proxy & Pluggable Harness Platform
**Target Repository:** `g:\1-Personal\Projects\AegisGate`
**Git Branch:** `phase-5-audit` (base commit: `00599d138573300b5bc619270004603bef841962`)
**Operating System:** Windows 11 Enterprise (x64)
**Runtimes:** Python 3.13.5, Node.js 20.18.0, npm 10.8.2
**Database Engines:** SQLite 3.45.1 (WAL Mode), Microsoft SQL Server 2019 Express (localhost:1433)

---

## 1. Executive Summary

### 1.1 Defect Counts by Severity & Type

| Severity | Count | Primary Impact |
| :--- | :---: | :--- |
| **S1 (Blocker)** | **0** | No crashes causing unrecoverable data loss or bypass of strict hard blocks. |
| **S2 (Major)** | **5** | Clean-clone onboarding failure, broken CI checks, runtime rule omission, SDK abort deadlock, and critical accessibility violations. |
| **S3 (Minor)** | **5** | Malformed ZIP crash, missing MCP error field, cursor silent 200 fallback, inequality tautology bypass, and light-theme contrast ratios. |
| **S4 (Cosmetic / Docs)** | **2** | MongoDB mock driver documentation clarity, and minor docstring nuances. |
| **Total Defects** | **12** | **100% reproducible (3/3 repro rate for every filed defect).** |

#### Defect Distribution by Category
```
DevEx / Build / CI:   3 (D-001, D-002, D-003)
Functional:           3 (D-004, D-007, D-011)
Robustness:           3 (D-005, D-006, D-009)
Accessibility (WCAG): 2 (D-008, D-012)
Docs / Truthfulness:  1 (D-010)
```

### 1.2 Top 10 Identified Risks

1. **New Contributor Onboarding Blocked ([D-001](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-001)):** Running `python scripts/tasks.py seed` on a pristine clone crashes with exit code 1 because the seeder queries the plugin table prior to plugin registry discovery.
2. **Pull Request CI Pipelines Broken ([D-002](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-002), [D-003](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-003)):** The committed repository fails `.github/workflows/ci.yml` on both `api-types` drift check (due to uncommitted Phase 4 TypeScript interfaces) and `Prettier Format Check` (due to unformatted lines in `LiveExecutionMonitor.tsx` and `SessionCard.tsx`).
3. **Ignored Governance Policy Rule ([D-004](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-004)):** Governance rules configured with type `MAX_EXECUTION_TIME` (such as the default 15s/5s rules) have **zero effect** at runtime; `GovernanceEngine` has no evaluation branch, and `ExecutionStateMachine` never forwards the custom limit to `TimeoutGuard`.
4. **Third-Party SDK Emergency Abort Deadlock ([D-005](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-005)):** Plugins authored with `aegisgate_sdk.PluginServer` execute requests sequentially on a single thread. When a query is running, the plugin cannot read incoming `abort` signals on `sys.stdin` until the execution finishes.
5. **Critical Accessibility Inaccessibility ([D-008](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-008)):** Axe-core detected critical violations including `<select>` controls missing accessible names and invalid `aria-controls` targets on MCP configuration tabs.
6. **Unhandled 500 Server Crash on Malformed Plugin ZIP ([D-006](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-006)):** Uploading a ZIP archive with an empty or NUL-truncated entry causes `PluginInstaller` to attempt opening the destination directory as a binary file, triggering an unhandled `PermissionError` (HTTP 500).
7. **AI Client Blindness on Execution Failure ([D-007](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-007)):** When an execution fails with the newly introduced Phase 4 status `FAILED`, `submit_execution` in `mcp_server.py` omits the `error_message` payload, depriving the AI model of the failure cause.
8. **Silent Pagination Loop on Corrupt Cursor ([D-009](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-009)):** Suppressing decoding exceptions in `GET /api/executions/page` causes invalid cursor tokens to silently reset to page 1 rather than returning HTTP 400 Bad Request.
9. **Heuristic Tautology Bypass ([D-011](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-011)):** While `WHERE 1=1` and `WHERE 'a'='a'` are caught, arithmetic inequalities (`WHERE 1 < 2`) and string `LIKE` tautologies (`WHERE 'x' LIKE 'x'`) bypass `is_unbounded_scan` and allow unbounded queries past `FORBID_TABLE_SCAN`.
10. **Light-Theme Contrast Deficiencies ([D-012](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-012)):** Inactive navigation tabs and sidebar elements exhibit washed-out contrast ratios as low as 1.23:1 on white backgrounds, failing WCAG 2.1 AA.

### 1.3 Release-Readiness Verdict

**VERDICT: CONDITIONAL PASS (NOT READY FOR PRODUCTION WITHOUT S2 RESOLUTIONS)**

- **Core Engine & Multi-Process Concurrency:** **EXCELLENT.** The multi-process scale infrastructure (Alembic WAL mode, `QueuePool(20, 30)`, `DbOutboxBus`, cross-process abort routing, heartbeat janitor, and bounded concurrency queues) withstood a sustained soak test at **100.09 req/s** with 0 errors, sub-70ms p99 latency, and flat memory curves.
- **Why Release is Blocked:**
  1. A new developer following `README.md` will crash on `python scripts/tasks.py seed` ([D-001](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-001)).
  2. Any automated CI pull request check will fail immediately on `api-types` drift ([D-002](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-002)) and Prettier formatting ([D-003](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-003)).
  3. Administrators relying on `MAX_EXECUTION_TIME` governance rules will have their query timeout policies silently ignored ([D-004](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-004)).
  4. External plugin developers using `aegisgate_sdk` cannot abort long-running queries ([D-005](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-005)).

Remediation of the 5 Major (S2) defects is straightforward and requires zero architectural redesign. Once those 5 items are patched and formatted, the system will achieve full Release Candidate status.

---

## 2. Environment & Audit Setup

- **Host Machine:** Windows 11 Enterprise (Version 10.0.26100, x64)
- **Active Workspace:** `G:\1-Personal\Projects\AegisGate`
- **Git HEAD SHA:** `00599d138573300b5bc619270004603bef841962`
- **Python Environment:** Python 3.13.5 (CPython 64-bit), pip 25.0.1
- **Node Environment:** Node.js v20.18.0, npm 10.8.2
- **Testing Frameworks:** Pytest 8.4.2 (with pytest-asyncio 0.24, pytest-cov 6.3), Vitest 2.1.8, Playwright 1.46.0
- **Database Servers:**
  - Local SQLite 3.45.1 (WAL mode, busy_timeout=15000)
  - Microsoft SQL Server 2019 Express (RTM - 15.0.2000.5 x64) on `localhost:1433` (ODBC Driver 18 for SQL Server, Windows Auth)
- **Environment Variables Used During Audit:**
  - `EVENT_BUS=db`
  - `AEGISGATE_TEST_MSSQL_SERVER=localhost`
  - `AEGISGATE_TEST_MSSQL_AUTH=windows`
  - `AEGISGATE_TEST_MSSQL_TRUST=true`
  - `AEGISGATE_API_URL=http://127.0.0.1:8000`
  - `AEGISGATE_FRONTEND_URL=http://localhost:3000`

---

## 3. Coverage Matrix

| Track | Track Name | Planned Scope | Execution Status | Passed | Failed | Blocked / Notes |
| :---: | :--- | :--- | :---: | :---: | :---: | :--- |
| **T0** | **Baseline & Reproducibility** | Clean worktree clone, Quick Start commands, CI local verification, Doc link checking, config drift | **EXECUTED** | Partial | 3 | Failed on clean clone seeding (D-001), API types drift (D-002), and Prettier format (D-003). |
| **T1** | **Backend Functional** | 75+ SQL governance catalog, MAX_EXECUTION_TIME rule, OutputMasker casing/aliases/nesting, CAS State Machine, REST fuzzing, Data lifecycle & gzip archival, Knowledge store path traversal | **EXECUTED** | Passed | 3 | Found MAX_EXECUTION_TIME ignored (D-004), pagination cursor swallow (D-009), and tautology bypass (D-011). |
| **T2** | **Plugins & Installer** | Zip Slip, ADS, drive letters, entrypoint injection, requirements.txt attack, Git URL attack, SDK abort concurrency, real SQL Server suite (11 tests), MongoDB audit | **EXECUTED** | Passed | 3 | Found SDK abort deadlock (D-005), empty ZIP entry crash (D-006), and MongoDB mock driver (D-010). All 11 real MSSQL tests passed. |
| **T3** | **MCP End-to-End** | 4 tools (`get_catalog`, `get_knowledge`, `submit_execution`, `check_execution_status`), offline API handling, status payloads, polling | **EXECUTED** | Passed | 1 | Found missing error_message on status `FAILED` in `submit_execution` (D-007). |
| **T4** | **Concurrency & Multi-Process Soak** | 200+ concurrent requests, 2 uvicorn processes on ephemeral ports, SQLite WAL, outbox sync, cross-process aborts, janitor death failover, 45s soak | **EXECUTED** | Passed | 0 | 4,504 executions processed at **100.09 req/s** with 0 errors. Flat RSS growth (+5.36 MB). |
| **T5** | **Frontend Automated** | Vitest 25 tests, TypeScript `tsc`, ESLint, Prettier format check, `next build` bundle size | **EXECUTED** | Passed | 1 | 25 tests passed. `next build` clean (46.4 kB first load JS). Failed on `format:check` (D-003). |
| **T6** | **UI End-to-End & Playwright** | S1-S11 smoke checklist, 6 responsive viewports (1920 to 390), Axe-core WCAG AA, XSS probes, MCP copy, Light/Dark theme | **EXECUTED** | Passed | 2 | Zero XSS execution. Zero viewport scroll overflow. Found critical select-name, aria-valid-attr-value (D-008), and contrast ratios (D-012). |
| **T7** | **Regression Pack** | Re-verify previously fixed bugs (comments, comma joins, CAS transitions, abort ordering, dry-run fail-closed) | **EXECUTED** | Passed | 0 | All 201 backend unit tests and previously hardened behaviors confirmed intact. |

---

## 4. Performance & Operational Metrics

### 4.1 Multi-Process Soak Test Benchmark (T4)
Metrics captured during two-process concurrent load test (`report/phase-5-audit/t4_soak_metrics.csv`):

- **Duration:** 45.0 seconds
- **Concurrent Request Workers:** 8 continuous client loops
- **Total Requests Completed:** **4,504 executions**
- **Failed / Dropped Requests:** **0 (0.00% error rate)**
- **System Throughput:** **100.09 requests / second**
- **Latency Distribution:**
  - **p50 Latency:** **0.0268 s (26.8 ms)**
  - **p95 Latency:** **0.0525 s (52.5 ms)**
  - **p99 Latency:** **0.0697 s (69.7 ms)**
  - **Max Latency:** 0.1240 s (124 ms)
- **Memory Stability:**
  - Process A (port 8801) RSS: 86.91 MB initial -> 89.65 MB final (+2.74 MB)
  - Process B (port 8802) RSS: 86.79 MB initial -> 89.41 MB final (+2.62 MB)
  - Combined RSS Growth: **5.36 MB total across 4,504 executions**
- **Subprocess Workers:** Remained strictly at 2 (1 worker per process); 0 orphan python processes leaked.
- **Database Scale:** Database grew from 144.0 KB to 6,400.0 KB in WAL mode with 0 locking errors.

### 4.2 Frontend Bundle & UI Interaction Metrics (T5 & T6)
- **Next.js Production Build Size:**
  - Route `/`: **46.4 kB** (134 kB First Load JS shared)
  - Route `/_not-found`: 873 B
- **Console Errors / Unhandled Exceptions:** **0 page errors** detected during exploratory Playwright session.
- **Viewport Scroll Overflow:** **0 px horizontal overflow** across all 6 audited viewports (1920x1080 down to 390x844).

---

## 5. Comprehensive Defect List (Sorted by Severity)

### [D-001] tasks.py seed crashes on fresh clone due to uninitialized plugin registry
- **Severity:** S2 (Major)
- **Type:** DevEx/Build
- **Tags:** `Onboarding`, `DevEx`
- **Area / Component:** `scripts/seed_demo.py`
- **Environment:** Windows 11, Python 3.13, empty database / fresh git worktree
- **Steps to Reproduce:**
  1. Create a pristine worktree: `git worktree add -d ../aegisgate-temp-audit HEAD`
  2. Open directory: `cd ../aegisgate-temp-audit`
  3. Execute seed command as instructed in README: `python scripts/tasks.py seed`
- **Expected Result:** Database runs migrations and populates demonstration schema catalogs, rules, and simulated executions.
- **Actual Result:** Process terminates with `SystemExit 1`:
  ```
  2026-10-26 12:35:25,058 [INFO] Fresh database detected; running full migrations from head...
  Target plugin 'sqlserver_prod' not found in database. Ensure plugins are discovered.
  ```
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [t0_baseline_seed_failure.txt](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-audit/t0_baseline_seed_failure.txt)
- **Suspected Cause:** `scripts/seed_demo.py:59-62` queries `select(PluginProfile).where(PluginProfile.id == "sqlserver_prod")` directly after `init_db()`. In a fresh clone, plugins have not yet been discovered by `PluginRegistry`.
- **Suggested Direction:** Add `PluginRegistry(engine).discover_and_register()` prior to querying `target_id` in `seed_demo.py`.
- **Related Defects:** None

---

### [D-002] CI workflow api-types drift check fails due to uncommitted Phase 4 TypeScript types
- **Severity:** S2 (Major)
- **Type:** DevEx/Build
- **Tags:** `CI`, `DevEx`
- **Area / Component:** `frontend/src/types/api.generated.ts`
- **Environment:** GitHub Actions CI / Local Ubuntu & Windows
- **Steps to Reproduce:**
  1. `python scripts/gen_api_types.py`
  2. `cd frontend && npm run gen:types`
  3. `git diff --exit-code src/types/api.generated.ts`
- **Expected Result:** `git diff --exit-code` exits with code 0 indicating no uncommitted API schema drift.
- **Actual Result:** `git diff --exit-code` exits with code 1 showing 100+ lines of uncommitted changes (`/api/executions/page`, `PaginatedExecutionsResponse`, `wait`, `last_event_id`).
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [t0_api_types_drift.diff](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-audit/t0_api_types_drift.diff)
- **Suspected Cause:** In Phase 4, scale endpoints and query parameters were added to the FastAPI backend, but `api.generated.ts` was not regenerated and committed.
- **Suggested Direction:** Run `cd frontend && npm run gen:types` and commit the updated `api.generated.ts`.
- **Related Defects:** None

---

### [D-003] Frontend CI step Prettier Format Check fails on LiveExecutionMonitor.tsx and SessionCard.tsx
- **Severity:** S2 (Major)
- **Type:** DevEx/Build
- **Tags:** `CI`, `Frontend`
- **Area / Component:** `frontend/src/features/monitor/`
- **Environment:** GitHub Actions CI / Local Node 20
- **Steps to Reproduce:**
  1. `cd frontend`
  2. `npm run format:check`
- **Expected Result:** All source files pass Prettier formatting check and command exits with code 0.
- **Actual Result:** Command exits with code 1:
  ```
  [warn] src/features/monitor/components/LiveExecutionMonitor.tsx
  [warn] src/features/monitor/components/SessionCard.tsx
  [warn] Code style issues found in 2 files. Run Prettier with --write to fix.
  ```
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [t0_prettier_check.log](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-audit/t0_prettier_check.log)
- **Suspected Cause:** `scripts/tasks.py check` runs ESLint, tsc, and vitest, but omits `npm run format:check`, allowing formatting inconsistencies to pass locally.
- **Suggested Direction:** Run `cd frontend && npm run format` and add `npm run format:check` into `scripts/tasks.py check`.
- **Related Defects:** None

---

### [D-004] Governance rule type MAX_EXECUTION_TIME is completely ignored at runtime
- **Severity:** S2 (Major)
- **Type:** Functional
- **Tags:** `Governance`, `Timeout`
- **Area / Component:** `core/engine/governance.py` and `core/engine/state_machine.py`
- **Environment:** FastAPI Core Gateway, Python 3.13
- **Steps to Reproduce:**
  1. Configure an active rule: `rule_type="MAX_EXECUTION_TIME", expression="2.0"`.
  2. Submit query `SELECT 1;` through `POST /api/monitor/executions`.
  3. Inspect `GovernanceEngine.inspect_query_and_plan` and `TimeoutGuard.get_timeout_for_query`.
- **Expected Result:** Query is evaluated against the 2.0s limit or `TimeoutGuard` configures execution timeout to 2.0s.
- **Actual Result:** `GovernanceEngine` contains no evaluation branch for `MAX_EXECUTION_TIME`, and `state_machine.py:354` calls `TimeoutGuard.get_timeout_for_query(log.query_type)` without passing custom limits, defaulting to 15.0s.
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [test_audit_t1_backend.py](file:///g:/1-Personal/Projects/AegisGate/tests/audit/test_audit_t1_backend.py#L210-L235)
- **Suspected Cause:** The rule type was defined in `schemas.py` and `database.py` but the evaluation logic in `governance.py` and parameter pass-through in `state_machine.py` were never implemented.
- **Suggested Direction:** Read active `MAX_EXECUTION_TIME` rules in `state_machine.py` and supply the minimum configured limit as `custom_limit` to `TimeoutGuard.get_timeout_for_query`.
- **Related Defects:** None

---

### [D-005] Plugins built with aegisgate_sdk.PluginServer cannot be aborted while executing
- **Severity:** S2 (Major)
- **Type:** Robustness
- **Tags:** `SDK`, `Concurrency`
- **Area / Component:** `sdk/aegisgate_sdk/server.py`
- **Environment:** Plugin Subprocess, Python 3.13
- **Steps to Reproduce:**
  1. Create a `BasePlugin` subclass whose `execute()` method takes 5 seconds.
  2. Start worker using `PluginServer(plugin).run()`.
  3. Send an `execute` JSON-RPC line on `sys.stdin`, followed immediately by an `abort` line.
- **Expected Result:** `PluginServer` processes the `abort` command concurrently to terminate the active execution session.
- **Actual Result:** `PluginServer.run()` executes line 1 in a blocking synchronous loop on the main thread, and cannot read `sys.stdin` for line 2 until `execute()` completes.
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [test_audit_t2_plugins_installer.py](file:///g:/1-Personal/Projects/AegisGate/tests/audit/test_audit_t2_plugins_installer.py#L150-L190)
- **Suspected Cause:** `sdk/aegisgate_sdk/server.py:106-110` uses a simple `for raw_line in self.stdin:` without multithreading or asynchronous I/O.
- **Suggested Direction:** Port the concurrent `ThreadPoolExecutor` and dedicated `abort` thread architecture from `plugins/sqlserver_plugin/adapter.py:961` into `PluginServer`.
- **Related Defects:** None

---

### [D-006] PluginInstaller._safe_extract crashes with unhandled PermissionError on empty/NUL entry name
- **Severity:** S3 (Minor)
- **Type:** Robustness
- **Tags:** `Input-handling`, `Security`
- **Area / Component:** `core/engine/plugin_installer.py`
- **Environment:** FastAPI Core Gateway, Windows 11 / Linux
- **Steps to Reproduce:**
  1. Create a ZIP archive containing a file entry with name `""` or `"\x00malicious.py"`.
  2. Upload via `POST /api/plugins/install/zip` or call `installer._safe_extract(zf, dest)`.
- **Expected Result:** Archive is rejected with `PluginInstallerError("Unsafe or empty path in ZIP")` (HTTP 400).
- **Actual Result:** `target` resolves to the extraction root directory itself; `open(target, "wb")` crashes with `PermissionError: [Errno 13] Permission denied` (HTTP 500).
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [test_audit_t2_plugins_installer.py](file:///g:/1-Personal/Projects/AegisGate/tests/audit/test_audit_t2_plugins_installer.py#L35-L75)
- **Suspected Cause:** `core/engine/plugin_installer.py:223-238` validates directory traversal and special characters, but omits a check for `if not name or not name.strip(): raise PluginInstallerError(...)`.
- **Suggested Direction:** Add an explicit guard rejecting empty or whitespace-only entry filenames.
- **Related Defects:** None

---

### [D-007] mcp_server.py submit_execution drops error_message when status is FAILED
- **Severity:** S3 (Minor)
- **Type:** Functional
- **Tags:** `MCP`
- **Area / Component:** `core/gateway/mcp_server.py`
- **Environment:** FastMCP Stdio Gateway, Python 3.13
- **Steps to Reproduce:**
  1. Trigger an execution that results in status `FAILED` (e.g. killed worker or janitor reaping).
  2. Submit query via MCP tool `submit_execution()`.
- **Expected Result:** Returned JSON payload includes `"status": "FAILED"` and `"error_message": "..."`.
- **Actual Result:** Payload includes `"status": "FAILED"`, but `"error_message"` is omitted.
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [test_audit_t3_mcp.py](file:///g:/1-Personal/Projects/AegisGate/tests/audit/test_audit_t3_mcp.py#L50-L80)
- **Suspected Cause:** `core/gateway/mcp_server.py:206` only checks `if ex["status"] in ("REJECTED", "TIMEOUT", "ABORTED"):` and missed the new `FAILED` status introduced in Phase 4.
- **Suggested Direction:** Append `"FAILED"` to the tuple on line 206.
- **Related Defects:** None

---

### [D-008] Critical and Serious WCAG 2.1 AA accessibility violations across Dashboard, Tabs and MCP Modal
- **Severity:** S2 (Major)
- **Type:** Accessibility
- **Tags:** `Accessibility`, `WCAG`, `Frontend`
- **Area / Component:** `frontend/src/components/`, `frontend/src/features/`
- **Environment:** Next.js 14, Playwright Chromium, axe-core 4.14
- **Steps to Reproduce:**
  1. Load `http://localhost:3000` in browser.
  2. Inject axe-core and run `axe.run()`.
  3. Inspect results for rules `select-name`, `aria-valid-attr-value`, and `label-content-name-mismatch`.
- **Expected Result:** Zero Critical or Serious violations.
- **Actual Result:**
  - `[CRITICAL] select-name`: Filter `<select>` elements in Live Execution Monitor and Governance Rules lack `<label>` or `aria-label`.
  - `[CRITICAL] aria-valid-attr-value`: In MCP Modal, tab `#tab-claude` declares `aria-controls="tabpanel-claude"`, but no element with ID `tabpanel-claude` exists in the DOM.
  - `[SERIOUS] label-content-name-mismatch`: Header MCP button visible text is `"MCP Config"`, but `aria-label` is `"View and Copy MCP JSON configuration"`, violating WCAG 2.5.3.
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [t6_ui_audit_evidence.json](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-audit/t6_ui_audit_evidence.json)
- **Suspected Cause:** Form controls and tabs were rendered without explicit accessibility labels or matching tabpanel element IDs.
- **Suggested Direction:** Add `aria-label` to all `<select>` tags, ensure `aria-controls` targets existing IDs, and match button `aria-label` with visible text.
- **Related Defects:** None

---

### [D-009] GET /api/executions/page silently swallows malformed cursor and returns HTTP 200 first page
- **Severity:** S3 (Minor)
- **Type:** Robustness
- **Tags:** `Input-handling`, `API`
- **Area / Component:** `core/storage/log_store.py`
- **Environment:** FastAPI REST API, Python 3.13
- **Steps to Reproduce:**
  1. Submit HTTP request: `GET /api/executions/page?cursor=INVALID_BASE64_GARBAGE`
- **Expected Result:** API returns `HTTP 400 Bad Request` with an error indicating an invalid cursor.
- **Actual Result:** `LogStore.paginate_logs` suppresses the decoding exception with `contextlib.suppress(Exception)` and returns `HTTP 200 OK` with page 1.
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [test_audit_t1_backend.py](file:///g:/1-Personal/Projects/AegisGate/tests/audit/test_audit_t1_backend.py#L355-L365)
- **Suspected Cause:** `core/storage/log_store.py:131` wraps cursor base64 decoding in `with contextlib.suppress(Exception):`.
- **Suggested Direction:** Raise a custom `InvalidCursorError` on decode failure and map to `HTTPException(400)` in `api_routes.py`.
- **Related Defects:** None

---

### [D-010] mongodb_plugin is purely simulated mock but requirements.txt and docs imply real driver
- **Severity:** S4 (Cosmetic / Docs)
- **Type:** Docs
- **Tags:** `Docs`, `KnownLimitation`
- **Area / Component:** `plugins/mongodb_plugin/`
- **Environment:** Repository plugins folder
- **Steps to Reproduce:**
  1. Inspect `plugins/mongodb_plugin/adapter.py`.
  2. Inspect `plugins/mongodb_plugin/requirements.txt`.
- **Expected Result:** If plugin is a simulation mock, documentation clearly states this fact (as is done for `sqlserver_plugin` simulation mode).
- **Actual Result:** `requirements.txt` specifies `pymongo>=4.0.0`, but `adapter.py` never imports `pymongo` and returns hardcoded documents and schemas.
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [test_audit_t2_plugins_installer.py](file:///g:/1-Personal/Projects/AegisGate/tests/audit/test_audit_t2_plugins_installer.py#L195-L215)
- **Suspected Cause:** The plugin was created as an architectural design reference for non-relational document databases.
- **Suggested Direction:** Add a banner to `plugins/mongodb_plugin/README.md` clarifying that the MongoDB adapter is currently a reference mock.
- **Related Defects:** None

---

### [D-011] is_unbounded_scan heuristic does not detect arithmetic inequality or LIKE tautologies
- **Severity:** S3 (Minor)
- **Type:** Functional
- **Tags:** `Governance`, `Security`, `KnownLimitation`
- **Area / Component:** `plugins/sql_inspector.py`
- **Environment:** Lightweight SQL Inspector, Python 3.13
- **Steps to Reproduce:**
  1. `from plugins.sql_inspector import is_unbounded_scan`
  2. `is_unbounded_scan("SELECT * FROM Users WHERE 1 < 2")`
  3. `is_unbounded_scan("SELECT * FROM Users WHERE 'x' LIKE 'x'")`
- **Expected Result:** Constant boolean tautologies are flagged as unbounded scans (`True`).
- **Actual Result:** Both evaluate to `False` (bypassing `FORBID_TABLE_SCAN`).
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [t1_sql_governance_catalog_results.json](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-audit/t1_sql_governance_catalog_results.json)
- **Suspected Cause:** `plugins/sql_inspector.py:317-326` checks equality/inequality only when operands match identically (`same = left.kind == right.kind and left.text == right.text`), ignoring constant comparisons like `1 < 2` or `LIKE`.
- **Suggested Direction:** Enhance `_is_tautology` to evaluate literal numeric comparisons and identical `LIKE` string literals.
- **Related Defects:** None

---

### [D-012] Inactive Navigation Tabs and Sidebar items fail WCAG AA color contrast in Light mode
- **Severity:** S3 (Minor)
- **Type:** Accessibility
- **Tags:** `Accessibility`, `WCAG`, `Frontend`
- **Area / Component:** `frontend/src/components/Sidebar.tsx` and `Tabs.tsx`
- **Environment:** Next.js 14, Light Mode, Chrome / Chromium
- **Steps to Reproduce:**
  1. Open dashboard in Light theme.
  2. Measure color contrast ratio of inactive tab labels (`#tab-plugins`, `#tab-knowledge`, `#tab-logs`) against `#ffffff`.
  3. Measure color contrast ratio of sidebar targets.
- **Expected Result:** Color contrast ratio >= 4.5:1.
- **Actual Result:** Inactive tab labels compute to `#94a3b8` on `#ffffff` (ratio **2.56:1**); sidebar items compute to `#e2e8f0` on `#ffffff` (ratio **1.23:1**).
- **Reproduction Rate:** 3/3 (100%)
- **Evidence Link:** [t6_ui_audit_evidence.json](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-audit/t6_ui_audit_evidence.json)
- **Suspected Cause:** Inverted Tailwind slate color mappings in Light mode cause slate-400 and slate-500 tokens to lack sufficient contrast on white.
- **Suggested Direction:** In `globals.css` Light Mode Contrast Overrides, increase inactive text contrast to `#475569` (slate-600) or `#334155` (slate-700).
- **Related Defects:** [D-008](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-full-audit.md#d-008)

---

## 6. Known Limitations Observed (Design Intent, Not Defects)

1. **Lightweight Token-Based SQL Parser:**
   - As documented in `plugins/sql_inspector.py`, the inspector is a conservative heuristic tokenizer, not an AST-building SQL parser. Complex constructs like `OPENQUERY(REMOTE_LINK, 'DELETE FROM users')` or encrypted stored procedures cannot be statically inspected.
2. **Column Alias Bypassing Field Masking:**
   - In `OutputMasker.apply()`, fields are masked based on dictionary keys returned from the database adapter. If a user queries `SELECT Password AS pwd_alias`, the database returns column name `pwd_alias`. If the rule is configured for `password`, `pwd_alias` will not be redacted unless aliased in the rule.
3. **OS-Level Permissions for Plugins:**
   - Per design, database plugins run with Core's OS privileges. Process isolation is enforced via JSON-RPC stdio subprocess boundaries, but arbitrary OS isolation (sandboxing) requires containerization (Docker/cgroups).
4. **PostgreSQL Portability Opt-In Requirement:**
   - Integration tests against PostgreSQL are opt-in and require `AEGISGATE_TEST_PG_URL`. When omitted, PostgreSQL integration tests skip gracefully.

---

## 7. Flaky Tests List

- **Pytest Suite:** 3 consecutive runs of the default backend suite produced **zero flakes** (201 passed, 1 skipped consistently).
- **Vitest Suite:** 3 consecutive runs of the frontend test suite produced **zero flakes** (25 passed consistently).
- **Observed Warning:** Python 3.13 on Windows occasionally emits `PytestUnraisableExceptionWarning` regarding closed Proactor base pipe transport during subprocess loop teardown. This is a known Python 3.13 Windows asyncio cleanup artifact and does not affect test outcomes.

---

## 8. Untested Areas and Why

1. **Live PostgreSQL Cluster Under High Concurrency:**
   - **Reason:** No live PostgreSQL cluster connection string (`AEGISGATE_TEST_PG_URL`) was provided in the local environment. Schema portability hooks were verified via code audit, but live concurrency against PG was skipped per policy.
2. **Hardware Clock Changes (Time Jumps):**
   - **Reason:** Operating on a physical Windows 11 host without hypervisor isolation; altering system hardware clock could disrupt active credentials, tokens, and background OS services.
3. **Physical Network Cable Disconnection:**
   - **Reason:** Local audit environment. Network disconnection was simulated via process kills, socket refusal, and `httpx.ConnectError` injection rather than physical NIC disabling.

---

## 9. Appendix: Raw Evidence Index

All raw audit scripts, traces, CSV data, and full-resolution screenshots are stored in the repository:

- **Audit Test Scripts:**
  - Track T1 Backend: [`tests/audit/test_audit_t1_backend.py`](file:///g:/1-Personal/Projects/AegisGate/tests/audit/test_audit_t1_backend.py)
  - Track T2 Plugins & Installer: [`tests/audit/test_audit_t2_plugins_installer.py`](file:///g:/1-Personal/Projects/AegisGate/tests/audit/test_audit_t2_plugins_installer.py)
  - Track T3 MCP Server: [`tests/audit/test_audit_t3_mcp.py`](file:///g:/1-Personal/Projects/AegisGate/tests/audit/test_audit_t3_mcp.py)
  - Track T4 Multi-Process Soak: [`tests/audit/run_t4_soak.py`](file:///g:/1-Personal/Projects/AegisGate/tests/audit/run_t4_soak.py)
  - Track T6 Browser UI & Axe: [`tests/audit/run_t6_ui_audit.py`](file:///g:/1-Personal/Projects/AegisGate/tests/audit/run_t6_ui_audit.py)
- **Raw Evidence Logs & Data:**
  - SQL Governance Catalog (75 queries): [`report/phase-5-audit/t1_sql_governance_catalog_results.json`](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-audit/t1_sql_governance_catalog_results.json)
  - Soak Metrics CSV: [`report/phase-5-audit/t4_soak_metrics.csv`](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-audit/t4_soak_metrics.csv)
  - Soak Summary JSON: [`report/phase-5-audit/t4_soak_summary.json`](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-audit/t4_soak_summary.json)
  - UI Accessibility & Viewports JSON: [`report/phase-5-audit/t6_ui_audit_evidence.json`](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-audit/t6_ui_audit_evidence.json)
  - Machine-Readable Defects JSON: [`report/phase-5-defects.json`](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-defects.json)
  - Machine-Readable Defects CSV: [`report/phase-5-defects.csv`](file:///g:/1-Personal/Projects/AegisGate/report/phase-5-defects.csv)
- **High-Resolution Audit Screenshots:**
  - S1 Dashboard (Light): [`report/screenshots/phase5_t6_s1_dashboard_light.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_s1_dashboard_light.png)
  - S2 Dashboard (Dark): [`report/screenshots/phase5_t6_s2_dashboard_dark.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_s2_dashboard_dark.png)
  - S3 Tab Plugins: [`report/screenshots/phase5_t6_s3_tab_plugins.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_s3_tab_plugins.png)
  - S3 Tab Governance Rules: [`report/screenshots/phase5_t6_s3_tab_rules.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_s3_tab_rules.png)
  - S3 Tab Audit Logs: [`report/screenshots/phase5_t6_s3_tab_audit.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_s3_tab_audit.png)
  - S4 MCP Configuration Modal: [`report/screenshots/phase5_t6_s4_modal_mcp.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_s4_modal_mcp.png)
  - S4 In-App User Guide Modal: [`report/screenshots/phase5_t6_s4_modal_user_guide.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_s4_modal_user_guide.png)
  - U1 Desktop 1920x1080 Viewport: [`report/screenshots/phase5_t6_u1_desktop_1920.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_u1_desktop_1920.png)
  - U1 Laptop 1366x768 Viewport: [`report/screenshots/phase5_t6_u1_laptop_1366.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_u1_laptop_1366.png)
  - U1 Tablet Landscape 1024x768: [`report/screenshots/phase5_t6_u1_tablet_landscape_1024.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_u1_tablet_landscape_1024.png)
  - U1 Tablet Portrait 768x1024: [`report/screenshots/phase5_t6_u1_tablet_portrait_768.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_u1_tablet_portrait_768.png)
  - U1 Foldable 600x900 Viewport: [`report/screenshots/phase5_t6_u1_foldable_600.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_u1_foldable_600.png)
  - U1 Mobile 390x844 Viewport: [`report/screenshots/phase5_t6_u1_mobile_390.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_u1_mobile_390.png)
  - U7 XSS Rendering Escaping: [`report/screenshots/phase5_t6_u7_xss_rendering.png`](file:///g:/1-Personal/Projects/AegisGate/report/screenshots/phase5_t6_u7_xss_rendering.png)
