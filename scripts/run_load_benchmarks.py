"""AegisGate Automated Load & Performance Benchmark Suite (Phase 5).

Executes headless Locust load tests across 1x, 5x, 10x target loads and breaking point analysis.
Samples real-time server CPU & RSS memory via psutil.
Parses CSV reports and outputs consolidated statistics to `report/benchmark_results.json`.
"""

import argparse
import contextlib
import csv
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import psutil

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
PYTHON_EXE = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

SERVER_URL = "http://127.0.0.1:8000"
REPORT_DIR = BASE_DIR / "report"
REPORT_DIR.mkdir(parents=True, exist_ok=True)


class ResourceMonitor:
    """Samples CPU and RSS memory of a target process in background thread."""

    def __init__(self, pid: int, interval: float = 0.5) -> None:
        self.proc = psutil.Process(pid)
        self.interval = interval
        self.running = False
        self.cpu_samples: list[float] = []
        self.ram_samples: list[float] = []
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.running = True
        self.cpu_samples.clear()
        self.ram_samples.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self) -> None:
        tracked_procs: dict[int, psutil.Process] = {self.proc.pid: self.proc}
        with contextlib.suppress(Exception):
            self.proc.cpu_percent()

        while self.running:
            try:
                try:
                    for child in self.proc.children(recursive=True):
                        if child.pid not in tracked_procs:
                            child.cpu_percent()
                            tracked_procs[child.pid] = child
                except Exception:
                    pass

                cpu_total = 0.0
                ram_total = 0.0
                dead_pids: list[int] = []
                for pid, p in tracked_procs.items():
                    try:
                        cpu_total += p.cpu_percent()
                        ram_total += p.memory_info().rss / (1024 * 1024)
                    except Exception:
                        dead_pids.append(pid)

                for pid in dead_pids:
                    tracked_procs.pop(pid, None)

                if ram_total > 0:
                    self.cpu_samples.append(cpu_total)
                    self.ram_samples.append(ram_total)
            except Exception:
                pass
            time.sleep(self.interval)

    def stop(self) -> dict[str, float]:
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

        avg_cpu = round(sum(self.cpu_samples) / max(1, len(self.cpu_samples)), 2)
        peak_cpu = round(max(self.cpu_samples) if self.cpu_samples else 0.0, 2)
        avg_ram = round(sum(self.ram_samples) / max(1, len(self.ram_samples)), 2)
        peak_ram = round(max(self.ram_samples) if self.ram_samples else 0.0, 2)

        return {
            "avg_cpu_percent": avg_cpu,
            "peak_cpu_percent": peak_cpu,
            "avg_ram_mb": avg_ram,
            "peak_ram_mb": peak_ram,
        }


def parse_locust_stats(csv_prefix: Path) -> dict[str, Any]:
    """Parse Locust generated stats_history and stats CSVs."""
    stats_file = Path(f"{csv_prefix}_stats.csv")
    if not stats_file.exists():
        return {}

    aggregated: dict[str, Any] = {}
    with open(stats_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Name") == "Aggregated":
                aggregated = {
                    "request_count": int(row.get("Request Count", 0)),
                    "failure_count": int(row.get("Failure Count", 0)),
                    "median_response_time": float(row.get("Median Response Time", 0)),
                    "avg_response_time": float(row.get("Average Response Time", 0)),
                    "min_response_time": float(row.get("Min Response Time", 0)),
                    "max_response_time": float(row.get("Max Response Time", 0)),
                    "rps": float(row.get("Requests/s", 0)),
                    "failures_per_s": float(row.get("Failures/s", 0)),
                    "p50": float(row.get("50%", 0)),
                    "p90": float(row.get("90%", 0)),
                    "p95": float(row.get("95%", 0)),
                    "p99": float(row.get("99%", 0)),
                }
                break

    req_count = aggregated.get("request_count", 0)
    fail_count = aggregated.get("failure_count", 0)
    error_rate = round((fail_count / req_count * 100) if req_count > 0 else 0.0, 2)
    aggregated["error_rate_percent"] = error_rate
    return aggregated


def run_benchmark_scenario(
    name: str,
    users: int,
    spawn_rate: int,
    duration_s: int,
    server_pid: int,
) -> dict[str, Any]:
    """Execute a single Locust load test run with live resource monitoring."""
    csv_prefix = REPORT_DIR / f"locust_{name}"

    locust_cmd = [
        PYTHON_EXE,
        "-m",
        "locust",
        "-f",
        str(BASE_DIR / "tests" / "load" / "locustfile.py"),
        "--headless",
        "-u",
        str(users),
        "-r",
        str(spawn_rate),
        "-t",
        f"{duration_s}s",
        "--host",
        SERVER_URL,
        "--csv",
        str(csv_prefix),
        "--only-summary",
    ]

    print(
        f"\n>>> Running Scenario: {name} (Users: {users}, Spawn: {spawn_rate}, Duration: {duration_s}s)...", flush=True
    )

    monitor = ResourceMonitor(server_pid, interval=0.5)
    monitor.start()

    res = subprocess.run(locust_cmd, capture_output=True, text=True)
    metrics = monitor.stop()

    if res.returncode != 0:
        print(f"Locust run warning (code {res.returncode}): {res.stderr[:200]}", flush=True)

    stats = parse_locust_stats(csv_prefix)
    stats.update(metrics)
    stats["scenario"] = name
    stats["users"] = users
    stats["duration_seconds"] = duration_s

    print(
        f"[{name}] RPS: {stats.get('rps', 0):.1f} | Errors: {stats.get('error_rate_percent', 0)}% | "
        f"p50: {stats.get('p50', 0):.1f}ms | p95: {stats.get('p95', 0):.1f}ms | p99: {stats.get('p99', 0):.1f}ms | "
        f"Avg CPU: {stats.get('avg_cpu_percent', 0)}% | Peak RAM: {stats.get('peak_ram_mb', 0)} MB",
        flush=True,
    )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AegisGate Performance Load Benchmarks")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds per scenario (default: 30)")
    args = parser.parse_args()

    # 1. Prepare isolated test database
    prep_cmd = [PYTHON_EXE, str(BASE_DIR / "scripts" / "prepare_perf_db.py")]
    subprocess.run(prep_cmd, check=True)

    # 2. Launch production server
    sub_env = os.environ.copy()
    sub_env["DATABASE_URL"] = f"sqlite:///{BASE_DIR / 'data' / 'perf_test.db'}"
    sub_env["DEBUG"] = "False"
    sub_env["PYTHONUNBUFFERED"] = "1"

    server_cmd = [
        PYTHON_EXE,
        "-m",
        "uvicorn",
        "core.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
        "--backlog",
        "2048",
        "--no-access-log",
    ]

    print("Starting production server for benchmarking...", flush=True)
    server_log = open(REPORT_DIR / "perf_server.log", "w", encoding="utf-8")  # noqa: SIM115
    server_proc = subprocess.Popen(server_cmd, env=sub_env, stdout=server_log, stderr=server_log)

    # Wait for server ready
    ready = False
    for _ in range(50):
        try:
            r = httpx.get(f"{SERVER_URL}/health", timeout=0.2)
            if r.status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.1)

    if not ready:
        server_proc.kill()
        sys.exit("Server failed to start")

    print(f"Server ready at 127.0.0.1:8000 (PID: {server_proc.pid})", flush=True)

    try:
        scenarios_results: list[dict[str, Any]] = []

        # 1x Target Baseline: 50 concurrent users
        r_1x = run_benchmark_scenario(
            "1x_target", users=50, spawn_rate=25, duration_s=args.duration, server_pid=server_proc.pid
        )
        scenarios_results.append(r_1x)

        # 5x Stress Load: 250 concurrent users
        r_5x = run_benchmark_scenario(
            "5x_stress", users=250, spawn_rate=50, duration_s=args.duration, server_pid=server_proc.pid
        )
        scenarios_results.append(r_5x)

        # 10x Spike Load: 500 concurrent users
        r_10x = run_benchmark_scenario(
            "10x_spike", users=500, spawn_rate=50, duration_s=args.duration, server_pid=server_proc.pid
        )
        scenarios_results.append(r_10x)

        # Breaking Point search: 750 and 1000 users
        r_break1 = run_benchmark_scenario(
            "breaking_750", users=750, spawn_rate=75, duration_s=args.duration, server_pid=server_proc.pid
        )
        scenarios_results.append(r_break1)

        r_break2 = run_benchmark_scenario(
            "breaking_1000", users=1000, spawn_rate=100, duration_s=args.duration, server_pid=server_proc.pid
        )
        scenarios_results.append(r_break2)

        # Save consolidated results
        out_file = REPORT_DIR / "benchmark_results.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump({"scenarios": scenarios_results}, f, indent=2)
        print(f"\nAll benchmark scenarios completed! Results saved to {out_file}", flush=True)

    finally:
        print("Stopping production server...", flush=True)
        server_proc.terminate()
        try:
            server_proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        with contextlib.suppress(Exception):
            server_log.close()


if __name__ == "__main__":
    main()
