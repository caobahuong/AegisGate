"""Load Benchmark for AegisGate.

Submits N executions at a specified concurrency limit against the running
FastAPI backend and calculates p50, p95 latency, throughput, and DB size.
"""

import asyncio
import os
import statistics
import time
from pathlib import Path
import httpx

API_URL = "http://127.0.0.1:8000/api/monitor/executions"
SETTINGS_URL = "http://127.0.0.1:8000/api/settings/auto-mode"
DB_PATH = Path("data/aegisgate.db")


async def run_benchmark(num_requests: int = 100, concurrency: int = 20):
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Enable Auto Approval Mode
        resp = await client.post(SETTINGS_URL, json={"enabled": True})
        assert resp.status_code == 200, f"Failed to enable auto mode: {resp.text}"

        db_size_before = DB_PATH.stat().st_size if DB_PATH.exists() else 0

        # Semaphores for concurrency
        sem = asyncio.Semaphore(concurrency)
        latencies = []

        async def worker(idx: int):
            query = f"SELECT OrderID, TotalAmount FROM dbo.Orders WHERE OrderID = {1000 + idx};"
            payload = {
                "target_id": "sqlserver_prod",
                "query": query,
                "reasoning": f"Load benchmark query #{idx}",
            }
            async with sem:
                t0 = time.perf_counter()
                r = await client.post(API_URL, json=payload)
                t1 = time.perf_counter()
                latency_ms = (t1 - t0) * 1000
                assert r.status_code in (200, 201), f"Request failed: {r.status_code} - {r.text}"
                latencies.append(latency_ms)

        start_time = time.perf_counter()
        tasks = [worker(i) for i in range(num_requests)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

        db_size_after = DB_PATH.stat().st_size if DB_PATH.exists() else 0

        latencies.sort()
        p50 = statistics.median(latencies)
        p95 = latencies[int(len(latencies) * 0.95)]
        throughput = num_requests / total_time

        print("=== LOAD BENCHMARK RESULTS ===")
        print(f"Total Requests: {num_requests}")
        print(f"Concurrency:    {concurrency}")
        print(f"Total Time:     {total_time:.2f} s")
        print(f"Throughput:     {throughput:.2f} req/s")
        print(f"p50 Latency:    {p50:.2f} ms")
        print(f"p95 Latency:    {p95:.2f} ms")
        print(f"DB Size Before: {db_size_before:,} bytes")
        print(f"DB Size After:  {db_size_after:,} bytes")
        print(f"DB Delta:       +{db_size_after - db_size_before:,} bytes")


if __name__ == "__main__":
    asyncio.run(run_benchmark(100, 20))
