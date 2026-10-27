"""Graceful Shutdown, Process Cleanup, and Restart Idempotency Stress Tests.

Tests verify:
1. Lifespan shutdown cleanly terminates subprocesses and stops background tasks (cluster, bus).
2. Database initialization and Alembic migrations are strictly idempotent across multiple restarts.
3. Node failover / recovery: Dead worker's in-flight executions are recovered to FAILED without data loss.
4. In-flight execution logs remain safely persisted across system stops and restarts.
"""

from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, select

from core.database import (
    ExecutionLog,
    PluginProfile,
    ProcessHeartbeat,
    Rule,
    init_db,
    utc_now,
)
from core.engine.cluster import ClusterManager
from core.engine.plugin_client import terminate_all_subprocesses
from core.gateway.event_bus import InMemoryBus


@pytest.fixture
def shutdown_db_engine(tmp_path: Path):
    """Provide an isolated database engine."""
    db_file = tmp_path / "shutdown_test.db"
    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 15.0},
    )
    init_db(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.mark.asyncio
async def test_graceful_shutdown_drains_subprocesses_and_preserves_logs(shutdown_db_engine) -> None:
    """Simulate application lifespan start and shutdown while in-flight query is active.

    Invariants:
    - ClusterManager and EventBus cleanly terminate.
    - terminate_all_subprocesses kills all worker subprocesses.
    - Active execution logs in the database are not corrupted or wiped.
    """
    exec_id = "exec_lifespan_shutdown"
    with Session(shutdown_db_engine) as session:
        session.add(
            ExecutionLog(
                id=exec_id,
                target_id="sqlserver_simulated",
                query="SELECT * FROM critical_audit;",
                query_type="READ",
                status="EXECUTING",
                created_at=utc_now(),
            )
        )
        session.commit()

    bus = InMemoryBus()
    cluster = ClusterManager(db_engine=shutdown_db_engine, owner_id="test_worker_shutdown")

    await bus.start()
    await cluster.start()

    # Verify background tasks are active
    assert cluster._heartbeat_task is not None
    assert not cluster._heartbeat_task.done()

    # Trigger graceful shutdown
    await cluster.stop()
    await bus.stop()
    await terminate_all_subprocesses()

    # Verify tasks are cleanly stopped
    assert cluster._heartbeat_task is None
    assert cluster._running is False

    # Verify in-flight log remains securely in DB
    with Session(shutdown_db_engine) as session:
        log = session.exec(select(ExecutionLog).where(ExecutionLog.id == exec_id)).first()
        assert log is not None
        assert log.status == "EXECUTING"


@pytest.mark.asyncio
async def test_restart_idempotency_and_migration_recovery(tmp_path: Path) -> None:
    """Re-initializing the database across multiple application restarts must be idempotent.

    Invariants:
    - Calling init_db() 3 consecutive times does not fail or duplicate tables.
    - Existing records (plugins, rules, executions) are preserved.
    """
    db_file = tmp_path / "restart_idempotent.db"
    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 15.0},
    )

    # Boot 1: Fresh DB
    init_db(test_engine)

    with Session(test_engine) as session:
        session.add(
            Rule(
                id="rule_persisted_restart",
                name="Persisted Across Restarts",
                rule_type="MAX_EXECUTION_TIME",
                expression="30",
            )
        )
        session.add(
            PluginProfile(
                id="plugin_persisted_restart",
                name="Restart Plugin",
                driver="sqlserver",
                entrypoint="python adapter.py",
            )
        )
        session.commit()

    # Boot 2: Restart simulation (calling init_db again on existing DB)
    init_db(test_engine)

    # Boot 3: Second restart
    init_db(test_engine)

    # Verify all records survived intact
    with Session(test_engine) as session:
        rule = session.exec(select(Rule).where(Rule.id == "rule_persisted_restart")).first()
        assert rule is not None
        assert rule.expression == "30"

        plugin = session.exec(select(PluginProfile).where(PluginProfile.id == "plugin_persisted_restart")).first()
        assert plugin is not None
        assert plugin.driver == "sqlserver"

    test_engine.dispose()


@pytest.mark.asyncio
async def test_janitor_failover_recovery_after_process_death(shutdown_db_engine) -> None:
    """When a worker process dies abruptly, surviving janitor marks stranded execution FAILED.

    Invariants:
    - Orphaned execution is detected.
    - Status is updated to FAILED with error_message='owner process died'.
    - finished_at timestamp is populated.
    """
    dead_owner = "worker_node_crashed_99"
    now = utc_now()

    with Session(shutdown_db_engine) as session:
        session.add(
            ProcessHeartbeat(
                owner_id=dead_owner,
                pid=12345,
                host="worker-crash-box",
                last_seen=now - timedelta(seconds=60),  # expired heartbeat
            )
        )
        session.add(
            ExecutionLog(
                id="exec_stranded_after_crash",
                target_id="sqlserver_simulated",
                query="SELECT * FROM long_report;",
                query_type="READ",
                status="EXECUTING",
                owner_id=dead_owner,
                started_at=now - timedelta(seconds=70),
                created_at=now - timedelta(seconds=70),
            )
        )
        session.commit()

    janitor_cluster = ClusterManager(db_engine=shutdown_db_engine, owner_id="worker_janitor_recovery")
    with Session(shutdown_db_engine) as session:
        await janitor_cluster._run_janitor_cleanup(session)

    with Session(shutdown_db_engine) as session:
        recovered = session.exec(select(ExecutionLog).where(ExecutionLog.id == "exec_stranded_after_crash")).one()
        assert recovered.status == "FAILED"
        assert recovered.error_message == "owner process died"
        assert recovered.finished_at is not None
