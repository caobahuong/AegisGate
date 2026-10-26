"""Unit tests for bounded plugin concurrency limiter, queue backpressure, and non-blocking submissions."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from core.database import ExecutionLog, utc_now
from core.engine.concurrency_limiter import PluginConcurrencyLimiter
from core.exceptions import ExecutionTimeoutError, PluginQueueFullError


@pytest.mark.asyncio
async def test_concurrency_limiter_queueing_and_release(db_session: Session) -> None:
    """When concurrency slots are full, subsequent executions wait in QUEUED state until a slot frees up."""
    limiter = PluginConcurrencyLimiter(target_id="test_target", max_concurrency=1, max_queue_size=10)

    log1 = ExecutionLog(
        id="exec_slot_1",
        target_id="test_target",
        query="SELECT 1;",
        query_type="READ",
        status="EXECUTING",
        created_at=utc_now(),
    )
    log2 = ExecutionLog(
        id="exec_slot_2",
        target_id="test_target",
        query="SELECT 2;",
        query_type="READ",
        status="EXECUTING",
        created_at=utc_now(),
    )
    db_session.add(log1)
    db_session.add(log2)
    db_session.commit()

    order: list[str] = []

    async def _run1() -> None:
        async with limiter.acquire_slot(db_session, log1):
            order.append("log1_start")
            await asyncio.sleep(0.1)
            order.append("log1_end")

    async def _run2() -> None:
        # Give run1 a head start to acquire the slot
        await asyncio.sleep(0.02)
        async with limiter.acquire_slot(db_session, log2):
            order.append("log2_start")

    await asyncio.gather(_run1(), _run2())

    assert order == ["log1_start", "log1_end", "log2_start"]


@pytest.mark.asyncio
async def test_concurrency_limiter_backpressure_queue_full(db_session: Session) -> None:
    """When backlog exceeds max_queue_size, PluginQueueFullError is raised immediately."""
    limiter = PluginConcurrencyLimiter(target_id="test_target_full", max_concurrency=1, max_queue_size=1)

    log1 = ExecutionLog(
        id="exec_full_1",
        target_id="test_target_full",
        query="SELECT 1;",
        query_type="READ",
        status="EXECUTING",
        created_at=utc_now(),
    )
    log2 = ExecutionLog(
        id="exec_full_2",
        target_id="test_target_full",
        query="SELECT 2;",
        query_type="READ",
        status="EXECUTING",
        created_at=utc_now(),
    )
    db_session.add(log1)
    db_session.add(log2)
    db_session.commit()

    # Slot 1 acquired, queue depth becomes 1 (which equals max_queue_size)
    async with limiter.acquire_slot(db_session, log1):
        # Now 2nd request should exceed max_queue_size
        with pytest.raises(PluginQueueFullError) as exc_info:
            async with limiter.acquire_slot(db_session, log2):
                pass
        assert "is full" in str(exc_info.value.message)


@pytest.mark.asyncio
async def test_concurrency_limiter_queue_wait_timeout(db_session: Session) -> None:
    """When waiting for a slot longer than timeout_seconds, ExecutionTimeoutError is raised."""
    limiter = PluginConcurrencyLimiter(target_id="test_timeout", max_concurrency=1, max_queue_size=5)

    log1 = ExecutionLog(
        id="exec_to_1",
        target_id="test_timeout",
        query="SELECT 1;",
        query_type="READ",
        status="EXECUTING",
        created_at=utc_now(),
    )
    log2 = ExecutionLog(
        id="exec_to_2",
        target_id="test_timeout",
        query="SELECT 2;",
        query_type="READ",
        status="EXECUTING",
        created_at=utc_now(),
    )
    db_session.add(log1)
    db_session.add(log2)
    db_session.commit()

    async def _holder() -> None:
        async with limiter.acquire_slot(db_session, log1):
            await asyncio.sleep(0.3)

    async def _waiter() -> None:
        await asyncio.sleep(0.02)
        with pytest.raises(ExecutionTimeoutError):
            async with limiter.acquire_slot(db_session, log2, timeout_seconds=0.08):
                pass

    await asyncio.gather(_holder(), _waiter())
    db_session.refresh(log2)
    assert log2.status == "TIMEOUT"


def test_non_blocking_submit_execution(api_client: TestClient, sim_plugin_profile) -> None:
    """Submitting an execution with wait=false returns HTTP 201 immediately with DRY_RUN status."""
    payload = {
        "target_id": "sqlserver_prod",
        "query": "SELECT 1;",
        "reasoning": "Non-blocking submit test",
    }
    response = api_client.post("/api/monitor/executions?wait=false", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("exec_")
    assert data["status"] in ("DRY_RUN", "EXECUTING", "COMPLETED", "PAUSED_FOR_REVIEW")
