"""Measure Cold Start Time and First Request Latency in Production Configuration."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

VENV_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
PYTHON_EXE = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

SERVER_URL = "http://127.0.0.1:8000"


def measure_cold_start() -> dict[str, float]:
    """Launch AegisGate production server, measure cold start and first request latency."""
    sub_env = os.environ.copy()
    sub_env["DATABASE_URL"] = f"sqlite:///{BASE_DIR / 'data' / 'perf_test.db'}"
    sub_env["DEBUG"] = "False"
    sub_env["PYTHONUNBUFFERED"] = "1"

    cmd = [
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

    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, env=sub_env)

    t_ready: float | None = None
    try:
        # Poll /health until server responds
        for _ in range(200):
            try:
                resp = httpx.get(f"{SERVER_URL}/health", timeout=0.2)
                if resp.status_code == 200:
                    t_ready = time.perf_counter()
                    break
            except Exception:
                time.sleep(0.02)

        if t_ready is None:
            proc.kill()
            raise RuntimeError("Server failed to start within timeout")

        cold_start_time = t_ready - t0

        # Measure first request latency (full query submission with dry-run and execution)
        payload = {
            "target_id": "sqlserver_prod",
            "query": "SELECT 1;",
            "reasoning": "First request after cold start",
        }
        t_req_start = time.perf_counter()
        first_resp = httpx.post(f"{SERVER_URL}/api/monitor/executions?wait=true", json=payload, timeout=10.0)
        t_req_end = time.perf_counter()

        first_request_latency = t_req_end - t_req_start
        assert first_resp.status_code in (200, 201), f"First request failed: {first_resp.status_code} {first_resp.text}"

        # Measure warm request latency for comparison
        t_warm_start = time.perf_counter()
        warm_resp = httpx.post(f"{SERVER_URL}/api/monitor/executions?wait=true", json=payload, timeout=10.0)
        t_warm_end = time.perf_counter()
        warm_request_latency = t_warm_end - t_warm_start
        assert warm_resp.status_code in (200, 201), f"Warm request failed: {warm_resp.status_code} {warm_resp.text}"

        result = {
            "cold_start_time_seconds": round(cold_start_time, 4),
            "first_request_latency_seconds": round(first_request_latency, 4),
            "warm_request_latency_seconds": round(warm_request_latency, 4),
        }
        print(json.dumps(result, indent=2))
        return result
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    measure_cold_start()
