"""Comprehensive unit tests for ClusterManager, distributed locks, heartbeats, and failover."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session, select

from core.database import (
    DistributedLock,
    ExecutionControl,
    ProcessHeartbeat,
    utc_now,
)
from core.engine.cluster import (
    ClusterManager,
    get_owner_id,
    release_lock,
    try_acquire_lock,
)
from plugins.plugin_contract import AbortResult
from tests.factories import make_execution_log


def test_distributed_lock_full_lifecycle(db_session: Session):
    """Verify lock acquisition, re-acquisition, expiration takeover, and release."""
    lock_name = "test_mutex"
    owner_a = "worker_node_A"
    owner_b = "worker_node_B"

    # 1. Owner A acquires new lock
    assert try_acquire_lock(db_session, lock_name, owner_a, ttl_seconds=10.0) is True

    # Verify lock record
    lock = db_session.exec(select(DistributedLock).where(DistributedLock.name == lock_name)).first()
    assert lock is not None
    assert lock.owner_id == owner_a

    # 2. Owner B tries to acquire while A holds it -> False
    assert try_acquire_lock(db_session, lock_name, owner_b, ttl_seconds=10.0) is False

    # 3. Owner A refreshes / re-acquires their own lock -> True
    assert try_acquire_lock(db_session, lock_name, owner_a, ttl_seconds=20.0) is True

    # 4. Simulate expiration of Owner A's lock
    lock.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.add(lock)
    db_session.commit()

    # 5. Owner B acquires expired lock -> True (takeover)
    assert try_acquire_lock(db_session, lock_name, owner_b, ttl_seconds=15.0) is True
    db_session.refresh(lock)
    assert lock.owner_id == owner_b

    # 6. Release lock by Owner A (not the current owner) -> Should NOT delete lock
    release_lock(db_session, lock_name, owner_a)
    assert db_session.exec(select(DistributedLock).where(DistributedLock.name == lock_name)).first() is not None

    # 7. Release lock by Owner B (actual owner) -> Deletes lock
    release_lock(db_session, lock_name, owner_b)
    assert db_session.exec(select(DistributedLock).where(DistributedLock.name == lock_name)).first() is None


@pytest.mark.asyncio
async def test_cluster_manager_heartbeat_and_prune(db_engine):
    """Verify ClusterManager writes initial heartbeat and prunes dead worker heartbeats."""
    cm = ClusterManager(db_engine=db_engine, owner_id="test_worker_123")

    # Record heartbeat
    cm._record_heartbeat()

    with Session(db_engine) as session:
        hb = session.exec(select(ProcessHeartbeat).where(ProcessHeartbeat.owner_id == "test_worker_123")).first()
        assert hb is not None
        assert hb.host == cm.hostname
        assert hb.pid == cm.pid

        # Add a simulated dead worker from 1 hour ago (> 120s)
        stale_hb = ProcessHeartbeat(
            owner_id="dead_worker_456",
            host="old-node",
            pid=99999,
            last_seen=utc_now() - timedelta(minutes=30),
        )
        session.add(stale_hb)
        session.commit()

        # Run janitor cleanup (prunes stale heartbeats > 120s)
        await cm._run_janitor_cleanup(session)

        # dead_worker_456 pruned, test_worker_123 remains
        remaining_dead = session.exec(select(ProcessHeartbeat).where(ProcessHeartbeat.owner_id == "dead_worker_456")).first()
        assert remaining_dead is None
        assert session.exec(select(ProcessHeartbeat).where(ProcessHeartbeat.owner_id == "test_worker_123")).first() is not None


@pytest.mark.asyncio
async def test_cluster_janitor_fails_dead_worker_executions(db_engine):
    """Verify janitor marks executions owned by dead processes as FAILED."""
    cm = ClusterManager(db_engine=db_engine, owner_id="leader_worker")

    with Session(db_engine) as session:
        # Create execution owned by a dead process (not in ProcessHeartbeat table)
        dead_owner = "crashed_worker_node"
        orphaned_log = make_execution_log(
            target_id="sqlserver_prod",
            query="SELECT * FROM abandoned_table",
            status="EXECUTING",
            owner_id=dead_owner,
            started_at=utc_now() - timedelta(minutes=10),
        )
        session.add(orphaned_log)
        session.commit()
        session.refresh(orphaned_log)

        # Run failover cleanup
        await cm._run_janitor_cleanup(session)
        session.refresh(orphaned_log)

        assert orphaned_log.status == "FAILED"
        assert "owner process died" in (orphaned_log.error_message or "")
        assert orphaned_log.finished_at is not None


@pytest.mark.asyncio
async def test_cluster_control_listener_handles_abort(db_engine):
    """Verify background control listener processes pending ABORT commands for this process."""
    my_owner_id = get_owner_id()
    cm = ClusterManager(db_engine=db_engine, owner_id=my_owner_id)

    with Session(db_engine) as session:
        exec_log = make_execution_log(
            target_id="sqlserver_prod",
            query="SELECT * FROM long_running",
            status="EXECUTING",
            owner_id=my_owner_id,
            started_at=utc_now(),
        )
        session.add(exec_log)
        session.commit()
        session.refresh(exec_log)

        # Enqueue an ABORT command
        ctl = ExecutionControl(
            execution_id=exec_log.id,
            command="ABORT",
            created_at=utc_now(),
        )
        session.add(ctl)
        session.commit()
        session.refresh(ctl)

        mock_client = AsyncMock()
        mock_client.abort.return_value = AbortResult(success=True, message="Terminated")

        with patch("core.engine.plugin_registry.PluginRegistry.get_client", return_value=mock_client):
            # Run one cycle of control listener
            await cm._process_pending_controls()
            session.refresh(ctl)

            assert ctl.handled_at is not None
            mock_client.abort.assert_awaited_once()


@pytest.mark.asyncio
async def test_cluster_manager_start_stop_loops(db_engine, monkeypatch):
    """Verify ClusterManager start, heartbeat upsert, loops, and clean shutdown."""
    from core.config import settings
    monkeypatch.setattr(settings, "HEARTBEAT_INTERVAL_SECONDS", 0.01)

    cluster = ClusterManager(owner_id="worker_lifecycle_test")
    cluster.engine = db_engine
    await cluster.start()
    assert cluster._running is True
    assert cluster._heartbeat_task is not None
    assert cluster._janitor_task is not None
    assert cluster._control_listener_task is not None

    import asyncio
    await asyncio.sleep(0.03)

    # Verify heartbeat recorded in DB
    with Session(db_engine) as session:
        hb = session.exec(select(ProcessHeartbeat).where(ProcessHeartbeat.owner_id == "worker_lifecycle_test")).first()
        assert hb is not None
        assert hb.host == cluster.hostname

    # Calling record_heartbeat updates existing heartbeat
    cluster._record_heartbeat()

    # Calling start() again when running returns early
    await cluster.start()

    # Stop cluster
    await cluster.stop()
    assert cluster._running is False
    assert cluster._heartbeat_task is None

    # Heartbeat deleted after stop
    with Session(db_engine) as session:
        hb_after = session.exec(select(ProcessHeartbeat).where(ProcessHeartbeat.owner_id == "worker_lifecycle_test")).first()
        assert hb_after is None


def test_try_acquire_lock_rollback_on_error(db_session: Session):
    """try_acquire_lock rolls back and returns False on DB error."""
    with patch.object(db_session, "commit", side_effect=Exception("DB write failure")):
        assert try_acquire_lock(db_session, "fail_lock", "owner_fail", ttl_seconds=10.0) is False
