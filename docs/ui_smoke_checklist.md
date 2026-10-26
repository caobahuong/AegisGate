# AegisGate UI Smoke Test Checklist (S1 – S11)

This checklist defines the manual and automated quality verification procedures for the AegisGate Next.js Web Dashboard. It ensures that critical user journeys, state machine feedback, and governance controls remain operational across releases.

---

## Smoke Test Matrix

| Step ID | Verification Scenario | Target Component / View | Expected Outcome | Automation Status |
| :--- | :--- | :--- | :--- | :--- |
| **S1** | **Initial Load & Default Theme** | Global Layout / Theme Provider | App loads in **Light Mode** by default (`bg-slate-50`). Toggling switch changes to **Dark Mode** (`bg-slate-950`) and toggling back restores Light Mode without contrast regressions. | Automated (`ui_smoke.py`) |
| **S2** | **Navigation Sidebar & Views** | Sidebar Component | Sidebar remains fixed on the left. Clicking **Targets**, **Knowledge & Rules**, **Live Monitor**, and **Audit Logs** activates each tab reactively. | Automated (`ui_smoke.py`) |
| **S3** | **Pluggable Targets View** | `PluginManagement.tsx` | Target plugin cards render with live badges (`active`, `certified`), latency metrics, active session counters, and custom card preview tables. | Automated (`ui_smoke.py`) |
| **S4** | **Add Plugin Modal** | `PluginManagement.tsx` | Clicking "+ Add Target Plugin" opens the modal. Displays options for ZIP file upload or Git URL installation. Form validation warns on invalid input. | Automated (`ui_smoke.py`) |
| **S5** | **Dynamic UI Schema & Configuration** | `PluginManagement.tsx` | Clicking "Edit Configuration" on a plugin card renders fields dynamically generated from `ui_schema` (text, select, boolean). Changes save and reflect on the card. | Automated (`ui_smoke.py`) |
| **S6** | **Knowledge & Rules Scoping** | `KnowledgeAndRules.tsx` | Displays target filter dropdown ("All Targets", "sqlserver_prod"). Shows governance rules with badges (`Global Scope` or target-scoped). | Automated (`ui_smoke.py`) |
| **S7** | **Governance Rule Creation** | `KnowledgeAndRules.tsx` | Clicking "Create Rule" opens modal. Form validates rule type (`FORBID_JOIN`, `FORBID_TABLE_SCAN`, `REDACT_FIELD`, `REMOVE_FIELD`), target scope, and expression. Submitting persists rule. | Automated (`ui_smoke.py`) |
| **S8** | **Live Execution Monitor (Safe Query)** | `LiveExecutionMonitor.tsx` | Three-column layout displays Input, Real-time Timeline, and State Inspector. When Auto Approval is ON, submitting a safe `SELECT` query transitions directly to `COMPLETED`. | Automated (`ui_smoke.py`) |
| **S9** | **Governance Rejection (Forbidden Join)** | `LiveExecutionMonitor.tsx` | Submitting a forbidden cross-join query (e.g. `Orders` + `AuditLogs`) transitions immediately to `REJECTED`, highlighting rule violation cards. | Automated (`ui_smoke.py`) |
| **S10** | **Manual Review & Approval Flow** | `LiveExecutionMonitor.tsx` | With Auto Approval OFF, submitting a query transitions state to `PAUSED_FOR_REVIEW`. Clicking "Approve & Execute" resumes execution to `COMPLETED`. | Automated (`ui_smoke.py`) |
| **S11** | **Audit Logs & MCP Configuration Modal** | `AuditLogs.tsx` / `Header.tsx` | Audit Logs displays execution history table with status filters. Header MCP button opens modal showing JSON client snippets for Claude, Cursor, and Cline. | Automated (`ui_smoke.py`) |

---

## Execution Instructions

### Running Automated UI Smoke Tests

Automated smoke tests covering S1 through S11 use Playwright:

```bash
# Ensure dev servers are running and demo data is seeded
python scripts/seed_demo.py

# In a separate terminal or background task:
python scripts/tasks.py dev

# Run the Playwright smoke suite
python -m pytest tests/e2e/test_ui_smoke.py -v
```

All verification screenshots are saved to: `report/screenshots/phase2_s{1..11}_<description>.png`.
