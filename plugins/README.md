# AegisGate Pluggable Target Architecture

In AegisGate, every third-party database or storage system (SQL Server, MongoDB, PostgreSQL, Elasticsearch) is implemented as an **isolated, embeddable Plugin**.

The Core Platform does not contain direct database drivers or vendor-specific code. All vendor interactions occur through **isolated child processes communicating via JSON-RPC 2.0 over standard I/O (Stdio)**.

---

## 🛡️ Core Philosophy: Process Isolation & Neutrality

1. **Process Isolation:** If a plugin crashes, deadlocks, or hangs, the Core Engine remains completely unaffected. The Core's `TimeoutGuard` can safely kill the child process and clean up resources.
2. **Language Agnostic:** Plugins can be authored in **Python, Go, C#, Rust, or Node.js** as long as they adhere to the JSON-RPC 2.0 over Stdio contract.
3. **No Orphan Processes:** Every Subprocess execution is strictly managed inside `try...finally` blocks, ensuring that `stdin`/`stdout` pipes are closed and processes are terminated immediately upon error or timeout.

---

## 📜 The Standard 4-Port Plugin Contract

Every plugin must implement the following 4 methods defined in [`plugins/plugin_contract.py`](./plugin_contract.py):

| Method | Request Payload | Response Payload | Description |
| :--- | :--- | :--- | :--- |
| `sync_knowledge` | `{"config": {...}}` | `{"partitions": [...], "target_id": "...", "timestamp": "..."}` | Scans target schema, chunks tables into logical partitions (`Sales`, `Inventory`, `Finance`), returns tables, columns, data types, and indexes. |
| `dry_run` | `{"query": "...", "rules": [...]}` | `{"is_valid": bool, "violations": [...], "explain_plan": {...}, "estimated_time_ms": float, "query_type": "READ"\|"WRITE"}` | Pre-inspects query execution plan (e.g. `SET SHOWPLAN_XML ON`), matches against governance rules (cấm JOIN, cấm Table Scan), returns plan and violation list. |
| `execute` | `{"execution_id": "...", "query": "...", "timeout_seconds": 15.0}` | `{"data": [...], "rows_affected": int, "execution_time_ms": float, "spid": int}` | Executes query with assigned SPID/session ID within the specified timeout guard. Returns output rows and latency. |
| `abort` | `{"execution_id": "..."}` | `{"success": bool, "message": "..."}` | Urgently kills the running session/SPID on the target database (e.g. `KILL {spid}`). |

---

## 📦 Reference Plugin: SQL Server (`sqlserver_plugin/`)

The SQL Server reference plugin demonstrates full compliance with the contract:

```text
plugins/sqlserver_plugin/
├── plugin_manifest.json  # Metadata & configuration parameters
├── adapter.py            # Implements IPluginAdapter with Stdio JSON-RPC 2.0 loop
└── requirements.txt      # Plugin dependencies (pyodbc, pydantic)
```

### `plugin_manifest.json` Format:
```json
{
  "id": "sqlserver_prod",
  "name": "SQL Server Enterprise Gateway",
  "version": "1.0.0",
  "driver": "pyodbc/mssql",
  "entrypoint": "python plugins/sqlserver_plugin/adapter.py",
  "dry_run_command": "SET SHOWPLAN_XML ON",
  "abort_command": "KILL {spid}",
  "default_config": {
    "server": "localhost",
    "port": 1433,
    "database": "EnterpriseSales",
    "username": "sa"
  },
  "supported_rules": [
    "FORBID_JOIN",
    "FORBID_TABLE_SCAN",
    "MAX_EXECUTION_TIME"
  ]
}
```

---

## 🛠️ How to Add a New Plugin (e.g., MongoDB)

To add a new plugin:

1. Create a directory: `plugins/mongodb_plugin/`
2. Create `plugin_manifest.json`:
   ```json
   {
     "id": "mongodb_prod",
     "name": "MongoDB Analytics Cluster",
     "version": "1.0.0",
     "driver": "pymongo",
     "entrypoint": "python plugins/mongodb_plugin/adapter.py",
     "dry_run_command": ".explain('executionStats')",
     "abort_command": "db.killOp(opid)"
   }
   ```
3. Implement `adapter.py` inheriting from `IPluginAdapter`:
   ```python
   from plugins.plugin_contract import IPluginAdapter, SyncKnowledgeResult, DryRunResult, ExecuteResult, AbortResult

   class MongoAdapter(IPluginAdapter):
       def sync_knowledge(self, params): ...
       def dry_run(self, params): ...
       def execute(self, params): ...
       def abort(self, params): ...
   ```
4. On startup, AegisGate Core automatically scans `plugins/*/plugin_manifest.json` and registers the target in the database and UI! Alternatively, administrators can register plugins dynamically using the **"Add Pluggable Target"** modal on the Frontend Dashboard.

---

## 🧪 Testing Plugins

```bash
# Run unit tests and Subprocess Stdio IPC tests
python -m pytest tests/test_phase3.py -v
```

---

## Persistent workers (`--serve`) and real Stop/Kill

If a plugin entrypoint contains `--serve` (e.g. `python plugins/sqlserver_plugin/adapter.py --serve`),
the Core starts **one long-lived process** per plugin instead of one process per call:

- newline-delimited JSON-RPC over stdio, multiplexed by request `id`;
- the Core pushes the plugin configuration with `reinit` on start (and again after a restart or a config change);
  a `--serve` plugin must refuse to work until it received it;
- requests must be handled concurrently (threads/async): `abort` arrives while `execute` is still running;
- a client-side timeout never kills the worker, so the running query stays abortable;
- on stdin EOF the plugin must cancel whatever it is still running.

Plugins without `--serve` keep the legacy one-shot behaviour (read one request, answer, exit).

### SQL Server plugin

`use_simulation = "false"` connects through pyodbc (ODBC Driver 17/18). `"true"` serves demo data only.

| Port | Real implementation |
|---|---|
| `dry_run` | `SET SHOWPLAN_XML ON` - the statement is compiled, never executed (needs `SHOWPLAN` permission) |
| `execute` | One connection per execution, `@@SPID` recorded, server-side query timeout, row cap (`max_rows`), READ queries are rolled back and use `readonly_username` if configured |
| `abort` | `SQLCancel` on the running cursor, then `KILL <spid>` from a second connection after verifying `spid` + `login_time` |
| `sync_knowledge` | `sys.tables / columns / indexes / partition_stats / extended_properties`, split into partitions per schema |

Extra config keys: `driver`, `encrypt`, `trust_server_certificate`, `readonly_username`, `readonly_password`,
`max_rows`, `max_cell_chars`, `max_tables`, `max_estimated_cost`, `kill_on_abort`, `login_timeout`.

Integration tests against a real server are opt-in: see the header of `tests/test_sqlserver_integration.py`.

### Installing plugins (ZIP / Git)

The installer enforces: `^[a-z0-9][a-z0-9_-]{0,63}$` plugin ids, safe ZIP extraction (no `..`, absolute paths,
symlinks, ADS, size/entry limits), entrypoint `python <relative.py> [--flags]` only, plain `requirements.txt`
(no pip options/URLs), HTTPS Git URLs on `PLUGIN_GIT_ALLOWED_HOSTS` only, and rollback if replacing a plugin fails.
A plugin is still arbitrary Python running with the Core's privileges - install only code you trust.
