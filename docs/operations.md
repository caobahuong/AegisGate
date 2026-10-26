# AegisGate Operations & Multi-Process Deployment Guide

This operational guide provides deployment, clustering, performance tuning, and maintenance runbooks for AegisGate in production and team environments.

---

## 1. Multi-Process Deployment Architecture

AegisGate can run as a single developer process or scale out across multiple Uvicorn worker processes on a single host or clustered across container nodes.

### Single-Process vs. Multi-Process Modes

| Feature | Single-Process Mode (`EVENT_BUS=memory`) | Multi-Process Mode (`EVENT_BUS=db`) |
| :--- | :--- | :--- |
| **Ideal For** | Local single-user developer desktop | Shared team servers, CI clusters, high-concurrency |
| **Event Bus** | RAM ring buffer (200 items) | Distributed `event_outbox` table (monotonic IDs) |
| **Worker Synchronization** | Single process memory | Heartbeats + cross-process `execution_control` |
| **Abort Routing** | Local worker thread/SPID kill | Cross-process control polling + local worker kill |
| **Failover Janitor** | Not needed | `DistributedLock` single-leader cron |
| **Database** | SQLite default | SQLite in WAL mode or PostgreSQL |

---

## 2. Running Multiple Worker Processes

To launch a cluster behind a local reverse proxy (e.g. Nginx, Caddy, or Envoy):

### Process A (Primary API + Frontend Gateway):
```bash
python -m uvicorn core.main:app --host 127.0.0.1 --port 8000
```

### Process B (Secondary Worker Process):
```bash
python -m uvicorn core.main:app --host 127.0.0.1 --port 8002
```

Both processes connect to the shared database specified in `.env`:
```ini
EVENT_BUS=db
DATABASE_URL=sqlite:///data/aegisgate.db
PLUGIN_MAX_CONCURRENCY=8
PLUGIN_QUEUE_TIMEOUT_SECONDS=30.0
PLUGIN_QUEUE_MAXSIZE=100
HEARTBEAT_INTERVAL_SECONDS=3.0
HEARTBEAT_TIMEOUT_SECONDS=30.0
```

---

## 3. Database Engine & SQLite WAL Tuning

When running multiple processes against SQLite:
1. **WAL Journaling**: AegisGate automatically executes `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL`. This allows concurrent read operations to proceed uninterrupted while another worker is writing.
2. **Busy Timeout**: `PRAGMA busy_timeout=20000` (20.0s) is enforced on all connections so transactions queue rather than throwing immediate database locked errors.
3. **Memory & Cache Optimizations**:
   - `PRAGMA cache_size=-64000` (64 MB page cache in memory)
   - `PRAGMA temp_store=MEMORY` (in-memory temporary tables and indices)
   - `PRAGMA mmap_size=268435456` (256 MB memory-mapped I/O for high read throughput)
4. **Connection Pooling**: SQLAlchemy `QueuePool` is tuned for high concurrency with:
   - `pool_size=50`
   - `max_overflow=150`
   - `pool_timeout=15.0`

### Database Schema Migrations (Alembic)
Schema migrations are handled programmatically at startup via Alembic:
```bash
# Check migration history
python -m alembic history

# Upgrade to latest revision manually if needed
python -m alembic upgrade head
```

---

## 4. Data Lifecycle Management & Pruning

Over time, audit records accumulate large query strings and result sets. AegisGate includes an automated retention and archival system.

### Running Prune via CLI
```bash
# Simulate pruning without making changes (DRY-RUN)
python scripts/tasks.py prune --dry-run

# Execute prune with default retention policies (30-day logs, 7-day results)
python scripts/tasks.py prune

# Custom retention windows
python scripts/tasks.py prune --log-days 60 --result-days 14
```

### Archival Output Format
Pruned execution records are exported to compressed NDJSON archives partitioned by month:
```
data/archive/
  ├── 2026-09.ndjson.gz
  ├── 2026-10.ndjson.gz
  └── 2026-11.ndjson.gz
```
Each line in the gzip archive contains the full JSON serialized `ExecutionLog` model.

### Automated Cron / Task Scheduler Setup
On Linux/macOS crontab:
```cron
# Run data pruning daily at 02:00 AM
0 2 * * * cd /opt/aegisgate && python scripts/tasks.py prune >> /var/log/aegisgate_prune.log 2>&1
```

On Windows Task Scheduler:
```powershell
# Create scheduled task running daily
schtasks /create /tn "AegisGatePrune" /tr "python G:\1-Personal\Projects\AegisGate\scripts\tasks.py prune" /sc daily /st 02:00
```

---

## 5. Failover, Crash Recovery & Janitor

### What Happens If a Worker Process Crashes?
1. Every process renews its lease in `process_heartbeat` every 3 seconds (`HEARTBEAT_INTERVAL_SECONDS`).
2. If a process experiences an unhandled crash or `kill -9`, its heartbeat row ceases updating.
3. The cluster **Janitor** (elected via `DistributedLock`) checks for orphaned executions every 5 seconds.
4. Any execution left in status `EXECUTING` whose owning process has had no heartbeat for > 30 seconds is transitioned to `FAILED` with error message `"owner process died"`.
5. An `execution_failed` SSE event is broadcast so all connected dashboard clients reflect the failure immediately.

---

## 6. Troubleshooting Runbook

### Symptom: `database is locked` in SQLite
- **Cause**: An external tool or unindexed table scan is holding an exclusive write lock.
- **Remedy**:
  - Verify SQLite WAL mode is active: `sqlite3 data/aegisgate.db "PRAGMA journal_mode;"` (should return `wal`).
  - Ensure no SQLite GUI browsers (DB Browser for SQLite, DBeaver) have an open uncommitted transaction.
  - Restart the backend to clean up dead file locks: `python scripts/tasks.py clean`.

### Symptom: Dashboard shows `Reconnecting...` on SSE stream
- **Cause**: Network drop or backend restart.
- **Remedy**:
  - The Next.js dashboard will automatically reconnect with exponential backoff.
  - Upon reconnection, it passes `Last-Event-ID`, and `DbOutboxBus` will replay all missed events seamlessly.
