"""Unit tests for ClusterManager heartbeat janitor and distributed lock."""

from datetime import timedelta

import pytest
from sqlmodel import Session, select

from core.database import (
    DistributedLock,
    ExecutionLog,
    ProcessHeartbeat,
    utc_now,
)
from core.engine.cluster import (
    ClusterManager,
    release_lock,
    try_acquire_lock,
)


@pytest.mark.asyncio
async def test_janitor_marks_stale_owner_executions_failed(db_session: Session) -> None:
    """Executions owned by a process whose heartbeat timed out are transitioned to FAILED."""
    now = utc_now()

    # Worker A crashed 45 seconds ago
    db_session.add(
        ProcessHeartbeat(
            owner_id="worker_crashed",
            pid=1111,
            host="node-1",
            last_seen=now - timedelta(seconds=45),
        )
    )

    # Worker B is alive
    db_session.add(
        ProcessHeartbeat(
            owner_id="worker_alive",
            pid=2222,
            host="node-2",
            last_seen=now - timedelta(seconds=2),
        )
    )

    # Execution 1 owned by crashed worker
    exec_crashed = ExecutionLog(
        id="exec_crashed_1",
        target_id="mock_target",
        query="SELECT * FROM big_table;",
        query_type="READ",
        status="EXECUTING",
        owner_id="worker_crashed",
        started_at=now - timedelta(seconds=50),
        created_at=now - timedelta(seconds=50),
    )
    db_session.add(exec_crashed)

    # Execution 2 owned by alive worker
    exec_alive = ExecutionLog(
        id="exec_alive_2",
        target_id="mock_target",
        query="SELECT 1;",
        query_type="READ",
        status="EXECUTING",
        owner_id="worker_alive",
        started_at=now - timedelta(seconds=5),
        created_at=now - timedelta(seconds=5),
    )
    db_session.add(exec_alive)
    db_session.commit()

    cm = ClusterManager(db_engine=db_session.bind, owner_id="worker_janitor")
    await cm._run_janitor_cleanup(db_session)

    db_session.refresh(exec_crashed)
    db_session.refresh(exec_alive)

    assert exec_crashed.status == "FAILED"
    assert exec_crashed.error_message == "owner process died"
    assert exec_alive.status == "EXECUTING"


@pytest.mark.asyncio
async def test_janitor_prunes_stale_heartbeats(db_session: Session) -> None:
    """Heartbeat records older than 120 seconds are purged by the janitor."""
    now = utc_now()

    db_session.add(
        ProcessHeartbeat(
            owner_id="worker_ancient",
            pid=3333,
            host="node-old",
            last_seen=now - timedelta(seconds=150),
        )
    )
    db_session.add(
        ProcessHeartbeat(
            owner_id="worker_recent",
            pid=4444,
            host="node-fresh",
            last_seen=now - timedelta(seconds=10),
        )
    )
    db_session.commit()

    cm = ClusterManager(db_engine=db_session.bind, owner_id="worker_janitor")
    await cm._run_janitor_cleanup(db_session)

    remaining = db_session.exec(select(ProcessHeartbeat)).all()
    remaining_ids = {hb.owner_id for hb in remaining}

    assert "worker_ancient" not in remaining_ids
    assert "worker_recent" in remaining_ids


def test_distributed_lock_lifecycle(db_session: Session) -> None:
    """Verify lock acquisition, exclusion, expiration, and release semantics."""
    lock_name = "test_cron_lock"
    owner_a = "worker_a"
    owner_b = "worker_b"

    # 1. Owner A acquires lock
    assert try_acquire_lock(db_session, lock_name, owner_a, ttl_seconds=5.0) is True

    # 2. Owner B tries to acquire same lock -> denied
    assert try_acquire_lock(db_session, lock_name, owner_b, ttl_seconds=5.0) is False

    # 3. Owner A refreshes its own lock -> allowed
    assert try_acquire_lock(db_session, lock_name, owner_a, ttl_seconds=10.0) is True

    # 4. Simulate lock expiration
    lock_record = db_session.exec(select(DistributedLock).where(DistributedLock.name == lock_name)).one()
    lock_record.expires_at = utc_now() - timedelta(seconds=1)
    db_session.add(lock_record)
    db_session.commit()

    # 5. Owner B acquires expired lock -> allowed
    assert try_acquire_lock(db_session, lock_name, owner_b, ttl_seconds=5.0) is True

    # 6. Release lock
    release_lock(db_session, lock_name, owner_b)
    # Now Owner A can acquire again
    assert try_acquire_lock(db_session, lock_name, owner_a, ttl_seconds=5.0) is True
