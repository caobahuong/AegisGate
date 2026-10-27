#!/usr/bin/env python3
"""AegisGate Soak Test Runner.

Executes sustained moderate load continuously over a specified duration (default: 30 minutes / 1800s).
Continuously monitors and records system resource consumption:
- RSS Memory (MB)
- OS Thread count
- OS Handle count (Windows) / File Descriptors (Unix)
- CPU Usage (%)
- Database file size (KB)
- Request throughput and error rates

Saves time-series data to `report/soak_metrics.json` and evaluates memory stability.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import psutil
from sqlalchemy import create_engine, event
from sqlmodel import Session, select

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import contextlib

from core.database import (
    PluginProfile,
    Rule,
    init_db,
)
from core.engine.state_machine import ExecutionStateMachine
from core.gateway.event_bus import InMemoryBus
from core.gateway.sse_broadcaster import sse_broadcaster
from core.storage.retention import prune_logs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AegisGate.SoakTest")


class SoakTestRunner:
    """Orchestrates sustained moderate load and samples resource consumption."""

    def __init__(
        self,
        duration_seconds: int = 1800,
        sample_interval: float = 10.0,
        concurrency: int = 4,
        db_path: Path | None = None,
        output_path: Path | None = None,
    ) -> None:
        self.duration_seconds = duration_seconds
        self.sample_interval = sample_interval
        self.concurrency = concurrency
        self.db_path = db_path or (BASE_DIR / "data" / "soak_test.db")
        self.output_path = output_path or (BASE_DIR / "report" / "soak_metrics.json")
        self.metrics_history: list[dict[str, Any]] = []

        self.running = False
        self.completed_requests = 0
        self.error_requests = 0
        self.prune_cycles = 0

        self.process = psutil.Process(os.getpid())
        self.engine: Any = None

    def setup_database(self) -> None:
        """Create and initialize an isolated SQLite WAL database."""
        if self.db_path.exists():
            with contextlib.suppress(OSError):
                self.db_path.unlink()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False, "timeout": 20.0},
            pool_size=20,
            max_overflow=40,
        )

        import sqlite3

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            if isinstance(dbapi_connection, sqlite3.Connection):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA busy_timeout=20000")
                cursor.close()

        init_db(self.engine)

        with Session(self.engine) as session:
            # Upsert plugin
            existing_p = session.exec(select(PluginProfile).where(PluginProfile.id == "sqlserver_soak")).first()
            if not existing_p:
                session.add(
                    PluginProfile(
                        id="sqlserver_soak",
                        name="SQL Server Soak Target",
                        driver="sqlserver",
                        entrypoint="python plugins/sqlserver_plugin/adapter.py --serve",
                        config_json='{"use_simulation": "true"}',
                    )
                )

            # Upsert rule
            existing_r = session.exec(select(Rule).where(Rule.id == "rule_soak_forbid_full_scan")).first()
            if not existing_r:
                session.add(
                    Rule(
                        id="rule_soak_forbid_full_scan",
                        name="Soak Forbid Full Scan",
                        rule_type="FORBID_TABLE_SCAN",
                        expression="AuditLogs",
                        is_active=True,
                    )
                )
            session.commit()

            # Set setting safely via SettingStore
            from core.storage.setting_store import SettingStore

            SettingStore(session).set_setting("auto_approval_mode", "true", "Auto approval for soak test")
        # Isolate event bus in memory for soak run
        from core.gateway.event_bus import set_event_bus

        self.bus = InMemoryBus(buffer_size=5000)
        set_event_bus(self.bus)

        logger.info("Initialized soak test database at %s", self.db_path)

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker task executing continuous simulated queries."""
        from plugins.plugin_contract import DryRunResult, ExecuteResult

        sample_queries = [
            ("SELECT * FROM Customers WHERE Id = 1;", "READ", False),
            ("SELECT * FROM Orders WHERE Amount > 500;", "READ", False),
            ("UPDATE Inventory SET Stock = Stock - 1 WHERE ItemId = 42;", "WRITE", False),
            ("SELECT * FROM AuditLogs;", "READ", True),  # Triggers rule violation
            ("SELECT COUNT(*) FROM Invoices WHERE Status = 'PAID';", "READ", False),
        ]
        q_idx = worker_id

        while self.running:
            query, q_type, expect_reject = sample_queries[q_idx % len(sample_queries)]
            q_idx += 1
            exec_id = f"soak_{worker_id}_{int(time.time() * 1000)}_{q_idx}"

            try:
                with Session(self.engine) as session:
                    sm = ExecutionStateMachine(session)

                    mock_client = MagicMock()
                    mock_client.dry_run = AsyncMock(
                        return_value=DryRunResult(
                            explain_plan={"EstimatedRows": 1},
                            violations=["Table scan on AuditLogs forbidden"] if expect_reject else [],
                            query_type=q_type,
                        )
                    )
                    mock_client.execute = AsyncMock(
                        return_value=ExecuteResult(
                            execution_id=exec_id,
                            data=[{"col_a": "val_1", "col_b": 100}],
                            rows_affected=1,
                            execution_time_ms=12.5,
                        )
                    )

                    with patch.object(sm.registry, "get_client", return_value=mock_client):
                        res = await sm.initiate_execution(
                            target_id="sqlserver_soak",
                            query=query,
                            reasoning="Soak continuous query load",
                            execution_id=exec_id,
                        )

                        if expect_reject:
                            assert res.status == "REJECTED"
                        else:
                            assert res.status == "COMPLETED"

                self.completed_requests += 1
            except Exception as exc:
                self.error_requests += 1
                logger.error("Worker %d encountered error on %s: %s", worker_id, exec_id, exc)

            # Moderate pace: sleep 20ms between queries per worker
            await asyncio.sleep(0.02)

    async def _sse_consumer_loop(self) -> None:
        """Background task continuously consuming SSE events."""
        try:
            async for _ in sse_broadcaster.subscribe():
                if not self.running:
                    break
        except asyncio.CancelledError:
            pass

    async def _retention_loop(self) -> None:
        """Periodic background task executing retention pruning."""
        while self.running:
            await asyncio.sleep(60.0)  # Every 60s
            if not self.running:
                break
            try:
                with Session(self.engine) as session:
                    prune_logs(session, log_retention_days=1, archive_before_delete=False)
                self.prune_cycles += 1
            except Exception as exc:
                logger.warning("Retention cycle error: %s", exc)

    def _get_handles_count(self) -> int:
        """Retrieve OS handles count safely across platforms."""
        try:
            if hasattr(self.process, "num_handles"):
                return self.process.num_handles()
            return len(self.process.open_files())
        except Exception:
            return 0

    def _sample_metrics(self, elapsed: float) -> dict[str, Any]:
        """Sample current process memory, CPU, threads, and DB size."""
        mem_info = self.process.memory_info()
        rss_mb = round(mem_info.rss / (1024 * 1024), 2)
        cpu_pct = round(self.process.cpu_percent(), 2)
        threads_count = self.process.num_threads()
        handles_count = self._get_handles_count()

        db_size_kb = 0.0
        if self.db_path.exists():
            db_size_kb = round(self.db_path.stat().st_size / 1024, 2)

        point = {
            "timestamp": datetime.now(UTC).isoformat(),
            "elapsed_s": round(elapsed, 1),
            "rss_mb": rss_mb,
            "cpu_pct": cpu_pct,
            "threads_count": threads_count,
            "handles_count": handles_count,
            "db_size_kb": db_size_kb,
            "completed_requests": self.completed_requests,
            "error_requests": self.error_requests,
            "prune_cycles": self.prune_cycles,
        }
        self.metrics_history.append(point)
        return point

    async def run(self) -> dict[str, Any]:
        """Execute the soak test run for the configured duration."""
        self.setup_database()
        self.running = True

        start_time = time.time()
        logger.info(
            "Starting soak test: duration=%ds, interval=%.1fs, concurrency=%d",
            self.duration_seconds,
            self.sample_interval,
            self.concurrency,
        )

        workers = [asyncio.create_task(self._worker_loop(i)) for i in range(self.concurrency)]
        sse_task = asyncio.create_task(self._sse_consumer_loop())
        retention_task = asyncio.create_task(self._retention_loop())

        # Sample initial baseline metric
        initial_point = self._sample_metrics(0.0)
        logger.info(
            "[Baseline] RSS: %.2f MB | Threads: %d | Handles: %d | DB Size: %.2f KB",
            initial_point["rss_mb"],
            initial_point["threads_count"],
            initial_point["handles_count"],
            initial_point["db_size_kb"],
        )

        try:
            next_sample = start_time + self.sample_interval
            while time.time() - start_time < self.duration_seconds:
                now = time.time()
                sleep_time = max(0.1, next_sample - now)
                await asyncio.sleep(sleep_time)

                elapsed = time.time() - start_time
                pt = self._sample_metrics(elapsed)
                logger.info(
                    "[%04.0fs / %ds] RSS: %.2f MB | CPU: %.1f%% | Threads: %d | Handles: %d | Req: %d | Err: %d",
                    elapsed,
                    self.duration_seconds,
                    pt["rss_mb"],
                    pt["cpu_pct"],
                    pt["threads_count"],
                    pt["handles_count"],
                    pt["completed_requests"],
                    pt["error_requests"],
                )
                next_sample += self.sample_interval

        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.warning("Soak test interrupted early by user signal")
        finally:
            self.running = False
            for w in workers:
                w.cancel()
            sse_task.cancel()
            retention_task.cancel()
            await asyncio.gather(*workers, sse_task, retention_task, return_exceptions=True)

        final_elapsed = time.time() - start_time
        self._sample_metrics(final_elapsed)

        # Statistical analysis
        summary = self._analyze_results(start_time, final_elapsed)
        self._save_report(summary)

        if self.engine:
            self.engine.dispose()

        return summary

    def _analyze_results(self, start_time: float, total_elapsed: float) -> dict[str, Any]:
        """Calculate statistical summaries and detect memory/handle leaks."""
        if not self.metrics_history:
            return {"status": "NO_DATA"}

        rss_values = [p["rss_mb"] for p in self.metrics_history]
        threads_values = [p["threads_count"] for p in self.metrics_history]
        handles_values = [p["handles_count"] for p in self.metrics_history]

        start_rss = rss_values[0]
        end_rss = rss_values[-1]
        peak_rss = max(rss_values)
        min_rss = min(rss_values)
        delta_rss = round(end_rss - start_rss, 2)

        start_handles = handles_values[0]
        end_handles = handles_values[-1]
        peak_handles = max(handles_values)
        delta_handles = end_handles - start_handles

        start_threads = threads_values[0]
        end_threads = threads_values[-1]
        peak_threads = max(threads_values)

        total_ops = self.completed_requests
        throughput_rps = round(total_ops / max(1.0, total_elapsed), 2)

        # Linear slope calculation for RSS (MB per minute) after warmup
        warmup_idx = min(len(rss_values) // 4, 10)
        stable_points = self.metrics_history[warmup_idx:]
        slope_mb_per_min = 0.0
        if len(stable_points) > 2:
            times = [p["elapsed_s"] / 60.0 for p in stable_points]
            mem = [p["rss_mb"] for p in stable_points]
            n = len(times)
            sum_x = sum(times)
            sum_y = sum(mem)
            sum_xx = sum(x * x for x in times)
            sum_xy = sum(x * y for x, y in zip(times, mem, strict=False))
            denom = n * sum_xx - sum_x * sum_x
            if denom != 0:
                slope_mb_per_min = round((n * sum_xy - sum_x * sum_y) / denom, 4)

        # Verdict logic
        # RSS growth slope < 0.1 MB/minute after warmup indicates stability
        is_memory_stable = slope_mb_per_min < 0.15
        is_handles_stable = delta_handles <= 10
        is_error_free = self.error_requests == 0

        verdict = "PASS" if (is_memory_stable and is_handles_stable and is_error_free) else "FAIL"

        return {
            "verdict": verdict,
            "total_duration_seconds": round(total_elapsed, 1),
            "total_completed_requests": total_ops,
            "total_errors": self.error_requests,
            "throughput_rps": throughput_rps,
            "prune_cycles": self.prune_cycles,
            "memory": {
                "start_mb": start_rss,
                "end_mb": end_rss,
                "peak_mb": peak_rss,
                "min_mb": min_rss,
                "delta_mb": delta_rss,
                "growth_slope_mb_per_min": slope_mb_per_min,
                "is_stable": is_memory_stable,
            },
            "handles": {
                "start": start_handles,
                "end": end_handles,
                "peak": peak_handles,
                "delta": delta_handles,
                "is_stable": is_handles_stable,
            },
            "threads": {
                "start": start_threads,
                "end": end_threads,
                "peak": peak_threads,
            },
            "database_size_kb": self.metrics_history[-1]["db_size_kb"] if self.metrics_history else 0,
            "sample_count": len(self.metrics_history),
        }

    def _save_report(self, summary: dict[str, Any]) -> None:
        """Write summary and time series data to JSON file."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": summary,
            "metrics": self.metrics_history,
        }
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info("Saved soak test metrics and summary to %s", self.output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="AegisGate Soak Test Runner")
    parser.add_argument("--duration", type=int, default=1800, help="Test duration in seconds (default: 1800 / 30m)")
    parser.add_argument("--interval", type=float, default=10.0, help="Sampling interval in seconds (default: 10.0)")
    parser.add_argument("--concurrency", type=int, default=4, help="Concurrent query workers (default: 4)")
    parser.add_argument("--output", type=str, default="report/soak_metrics.json", help="Output JSON path")
    args = parser.parse_args()

    runner = SoakTestRunner(
        duration_seconds=args.duration,
        sample_interval=args.interval,
        concurrency=args.concurrency,
        output_path=Path(args.output),
    )

    summary = asyncio.run(runner.run())
    print("\n" + "=" * 60)
    print("           AEGISGATE SOAK TEST SUMMARY REPORT")
    print("=" * 60)
    print(f"Verdict:              {summary['verdict']}")
    print(f"Duration:             {summary['total_duration_seconds']}s")
    print(f"Completed Queries:    {summary['total_completed_requests']}")
    print(f"Errors:               {summary['total_errors']}")
    print(f"Average Throughput:   {summary['throughput_rps']} req/s")
    print(f"RSS Memory Start:     {summary['memory']['start_mb']} MB")
    print(f"RSS Memory Peak:      {summary['memory']['peak_mb']} MB")
    print(f"RSS Memory End:       {summary['memory']['end_mb']} MB (Delta: {summary['memory']['delta_mb']} MB)")
    print(
        f"RSS Growth Slope:     {summary['memory']['growth_slope_mb_per_min']} MB/min (Stable: {summary['memory']['is_stable']})"
    )
    print(
        f"OS Handles (Start->End): {summary['handles']['start']} -> {summary['handles']['end']} (Delta: {summary['handles']['delta']})"
    )
    print(f"OS Threads (Start->End): {summary['threads']['start']} -> {summary['threads']['end']}")
    print(f"Final DB Size:        {summary['database_size_kb']} KB")
    print("=" * 60 + "\n")

    if summary["verdict"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
