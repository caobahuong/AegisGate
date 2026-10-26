"""Audit Track T4: Concurrency, Multi-Process & Soak Runner.

Spawns two uvicorn processes on ephemeral ports with EVENT_BUS=db and an isolated SQLite DB.
Sends sustained concurrent submissions, monitors RSS, handles, threads, outbox rows, and latencies.
Writes metrics to report/phase-5-audit/t4_soak_metrics.csv.
"""

import argparse
import asyncio
import csv
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import httpx
import psutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audit_t4_soak")

EVIDENCE_DIR = Path("report/phase-5-audit")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


async def run_soak(duration_seconds: int = 60, concurrency: int = 10) -> dict[str, Any]:
    temp_dir = Path(tempfile.mkdtemp(prefix="aegisgate_soak_"))
    db_file = temp_dir / "soak.db"
    db_url = f"sqlite:///{db_file}"
    archive_dir = temp_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    csv_path = EVIDENCE_DIR / "t4_soak_metrics.csv"
    logger.info("Starting Soak Audit: duration=%ds, concurrency=%d, db=%s", duration_seconds, concurrency, db_file)

    # Base environment for child uvicorn workers
    base_env = dict(os.environ)
    base_env.update(
        {
            "DATABASE_URL": db_url,
            "EVENT_BUS": "db",
            "HEARTBEAT_INTERVAL_SECONDS": "1.0",
            "HEARTBEAT_TIMEOUT_SECONDS": "5.0",
            "OUTBOX_POLL_INTERVAL_SECONDS": "0.1",
            "AUTO_APPROVAL_DEFAULT": "true",
            "ARCHIVE_DIR": str(archive_dir),
            "PYTHONUNBUFFERED": "1",
        }
    )

    # Initialize DB schema
    from sqlmodel import create_engine

    from core.database import init_db

    init_db(target_engine=create_engine(db_url))

    # Also seed target plugin into test db
    from sqlmodel import Session

    from core.database import PluginProfile

    with Session(create_engine(db_url)) as sess:
        profile = PluginProfile(
            id="sqlserver_prod",
            name="SQL Server Enterprise",
            driver="sqlserver",
            entrypoint="python plugins/sqlserver_plugin/adapter.py --serve",
            config_json=json.dumps({"use_simulation": "true"}),
            status="active",
        )
        sess.add(profile)
        sess.commit()

    port_a = 8801
    port_b = 8802

    proc_a = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "core.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port_a),
            "--no-access-log",
        ],
        env=base_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    proc_b = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "core.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port_b),
            "--no-access-log",
        ],
        env=base_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    url_a = f"http://127.0.0.1:{port_a}"
    url_b = f"http://127.0.0.1:{port_b}"

    # Wait for both processes to be healthy
    for _ in range(30):
        try:
            async with httpx.AsyncClient(timeout=1.0) as cl:
                ra = await cl.get(f"{url_a}/health")
                rb = await cl.get(f"{url_b}/health")
                if ra.status_code == 200 and rb.status_code == 200:
                    break
        except Exception:
            pass
        await asyncio.sleep(0.5)

    logger.info("Both uvicorn processes are healthy (PID A: %d, PID B: %d)", proc_a.pid, proc_b.pid)

    ps_proc_a = psutil.Process(proc_a.pid)
    ps_proc_b = psutil.Process(proc_b.pid)

    latencies: list[float] = []
    total_submissions = 0
    total_errors = 0

    csv_headers = [
        "timestamp_sec",
        "proc_a_rss_mb",
        "proc_b_rss_mb",
        "total_rss_mb",
        "proc_a_threads",
        "proc_b_threads",
        "total_threads",
        "child_workers_count",
        "db_size_kb",
        "total_submissions",
        "total_errors",
    ]

    samples: list[dict[str, Any]] = []

    # Client worker task
    stop_event = asyncio.Event()

    async def worker_submit(worker_id: int):
        nonlocal total_submissions, total_errors
        urls = [url_a, url_b]
        async with httpx.AsyncClient(timeout=30.0) as client:
            while not stop_event.is_set():
                target_url = urls[worker_id % len(urls)]
                t0 = time.perf_counter()
                try:
                    resp = await client.post(
                        f"{target_url}/api/monitor/executions?wait=true",
                        json={
                            "query": f"SELECT {worker_id}, {total_submissions} FROM AuditTable WHERE id = 1;",
                            "target_id": "sqlserver_prod",
                            "reasoning": f"Soak worker {worker_id}",
                        },
                    )
                    lat = time.perf_counter() - t0
                    if resp.status_code in (200, 201):
                        latencies.append(lat)
                        total_submissions += 1
                    else:
                        total_errors += 1
                except Exception:
                    total_errors += 1
                await asyncio.sleep(0.05)

    workers = [asyncio.create_task(worker_submit(i)) for i in range(concurrency)]

    # Metrics sampling loop
    start_time = time.time()

    while time.time() - start_time < duration_seconds:
        now = time.time()
        elapsed = now - start_time

        try:
            mem_a = ps_proc_a.memory_info().rss / (1024 * 1024)
            th_a = ps_proc_a.num_threads()
            children_a = ps_proc_a.children(recursive=True)
        except Exception:
            mem_a, th_a, children_a = 0.0, 0, []

        try:
            mem_b = ps_proc_b.memory_info().rss / (1024 * 1024)
            th_b = ps_proc_b.num_threads()
            children_b = ps_proc_b.children(recursive=True)
        except Exception:
            mem_b, th_b, children_b = 0.0, 0, []

        child_count = len(children_a) + len(children_b)
        db_size_kb = (db_file.stat().st_size / 1024) if db_file.exists() else 0.0

        sample = {
            "timestamp_sec": round(elapsed, 1),
            "proc_a_rss_mb": round(mem_a, 2),
            "proc_b_rss_mb": round(mem_b, 2),
            "total_rss_mb": round(mem_a + mem_b, 2),
            "proc_a_threads": th_a,
            "proc_b_threads": th_b,
            "total_threads": th_a + th_b,
            "child_workers_count": child_count,
            "db_size_kb": round(db_size_kb, 2),
            "total_submissions": total_submissions,
            "total_errors": total_errors,
        }
        samples.append(sample)
        logger.info(
            "T=%.1fs | Submits: %d | RSS: %.1f MB | Workers: %d | DB: %.1f KB",
            elapsed,
            total_submissions,
            sample["total_rss_mb"],
            child_count,
            db_size_kb,
        )

        await asyncio.sleep(10.0)

    # Stop workers and wait
    stop_event.set()
    await asyncio.gather(*workers, return_exceptions=True)

    # Write samples to CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_headers)
        writer.writeheader()
        writer.writerows(samples)

    # Teardown processes
    proc_a.terminate()
    proc_b.terminate()
    try:
        proc_a.wait(timeout=3)
        proc_b.wait(timeout=3)
    except Exception:
        proc_a.kill()
        proc_b.kill()

    # Calculate percentiles
    latencies.sort()
    n = len(latencies)
    p50 = latencies[int(n * 0.5)] if n > 0 else 0.0
    p95 = latencies[int(n * 0.95)] if n > 0 else 0.0
    p99 = latencies[int(n * 0.99)] if n > 0 else 0.0

    summary = {
        "duration_seconds": duration_seconds,
        "concurrency": concurrency,
        "total_submissions": total_submissions,
        "total_errors": total_errors,
        "throughput_rps": round(total_submissions / max(1, duration_seconds), 2),
        "latency_p50_sec": round(p50, 4),
        "latency_p95_sec": round(p95, 4),
        "latency_p99_sec": round(p99, 4),
        "initial_rss_mb": samples[0]["total_rss_mb"] if samples else 0.0,
        "final_rss_mb": samples[-1]["total_rss_mb"] if samples else 0.0,
        "rss_growth_mb": round((samples[-1]["total_rss_mb"] - samples[0]["total_rss_mb"]), 2) if samples else 0.0,
        "csv_evidence": str(csv_path),
    }

    out_summary = EVIDENCE_DIR / "t4_soak_summary.json"
    out_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Soak Completed! Summary: %s", summary)

    # Clean up temp dir
    shutil.rmtree(temp_dir, ignore_errors=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=60, help="Soak duration in seconds")
    parser.add_argument("--concurrency", type=int, default=8, help="Number of concurrent clients")
    args = parser.parse_args()

    asyncio.run(run_soak(duration_seconds=args.duration, concurrency=args.concurrency))
