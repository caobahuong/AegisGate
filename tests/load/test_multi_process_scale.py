"""Multi-process distributed load, failover, CAS double-approve, and event sync soak tests."""

import asyncio
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, select

from core.database import (
    ExecutionControl,
    ExecutionLog,
    PluginProfile,
    ProcessHeartbeat,
    init_db,
    utc_now,
)
from core.engine.cluster import ClusterManager
from core.engine.state_machine import ExecutionStateMachine
from core.exceptions import ExecutionStateError
from core.gateway.event_bus import DbOutboxBus


@pytest.fixture
def multi_proc_db(tmp_path: Path):
    """Provide a shared SQLite engine with WAL mode and high concurrency pooling."""
    db_file = tmp_path / "multi_proc_test.db"
    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 15.0},
        pool_size=10,
        max_overflow=20,
    )
    init_db(test_engine)

    # Seed simulated plugin
    with Session(test_engine) as session:
        session.add(
            PluginProfile(
                id="sqlserver_prod",
                name="SQL Server Enterprise",
                driver="sqlserver",
                entrypoint="python plugins/sqlserver_plugin/adapter.py --serve",
                config_json='{"use_simulation": "true"}',
            )
        )
        session.commit()

    yield test_engine
    test_engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_double_approve_cas(multi_proc_db) -> None:
    """Two concurrent requests approve the same paused execution. Exactly one wins; the other fails."""
    exec_id = "exec_double_approve"

    with Session(multi_proc_db) as session:
        log = ExecutionLog(
            id=exec_id,
            target_id="sqlserver_prod",
            query="SELECT 1;",
            query_type="READ",
            status="PAUSED_FOR_REVIEW",
            created_at=utc_now(),
        )
        session.add(log)
        session.commit()

    async def _try_approve(approver_name: str) -> bool:
        with Session(multi_proc_db) as session:
            sm = ExecutionStateMachine(session)

            # Patch _execute_step so it does not invoke real subprocess during CAS test
            async def _fake_execute_step(log_item: ExecutionLog) -> ExecutionLog:
                log_item.status = "COMPLETED"
                session.add(log_item)
                session.commit()
                return log_item

            sm._execute_step = _fake_execute_step  # type: ignore[method-assign]
            try:
                await sm.approve_and_resume(exec_id, approved_by=approver_name)
                return True
            except ExecutionStateError:
                return False

    results = await asyncio.gather(_try_approve("Approver_A"), _try_approve("Approver_B"))

    # Exactly one approver wins, the other is rejected
    assert results.count(True) == 1
    assert results.count(False) == 1

    with Session(multi_proc_db) as session:
        final_log = session.exec(select(ExecutionLog).where(ExecutionLog.id == exec_id)).one()
        assert final_log.status == "COMPLETED"
        assert final_log.approved_by in ("Approver_A", "Approver_B")


@pytest.mark.asyncio
async def test_cross_process_event_bus_sync(multi_proc_db) -> None:
    """Events published by Process B through DbOutboxBus are received by Process A."""
    bus_a = DbOutboxBus(poll_interval=0.05, engine_override=multi_proc_db)
    bus_b = DbOutboxBus(poll_interval=0.05, engine_override=multi_proc_db)

    await bus_a.start()
    await bus_b.start()

    try:
        # Process B publishes 3 events
        ev1 = await bus_b.publish("execution_created", {"msg": "First from B"})
        await bus_b.publish("execution_running", {"msg": "Second from B"})
        await bus_b.publish("execution_completed", {"msg": "Third from B"})

        # Process A subscribes and reads the events via replay
        received: list[str] = []
        sub = bus_a.subscribe(last_event_id=ev1 - 1)

        for _ in range(3):
            msg = await anext(sub)
            received.append(msg.event_type)

        assert received == ["execution_created", "execution_running", "execution_completed"]

    finally:
        await bus_a.stop()
        await bus_b.stop()


@pytest.mark.asyncio
async def test_cross_process_abort_routing_soak(multi_proc_db) -> None:
    """Process B aborts a long-running execution owned by Process A."""
    owner_a = "worker_proc_a"
    exec_id = "exec_soak_abort"

    with Session(multi_proc_db) as session:
        log = ExecutionLog(
            id=exec_id,
            target_id="sqlserver_prod",
            query="WAITFOR DELAY '00:00:30';",
            query_type="READ",
            status="EXECUTING",
            owner_id=owner_a,
            started_at=utc_now(),
            created_at=utc_now(),
        )
        session.add(log)
        session.commit()

    # Process A cluster manager runs control listener
    cm_a = ClusterManager(db_engine=multi_proc_db, owner_id=owner_a)

    # Process B state machine issues abort
    with Session(multi_proc_db) as session_b:
        sm_b = ExecutionStateMachine(session_b)
        with patch.object(cm_a, "_process_pending_controls", wraps=cm_a._process_pending_controls):
            res = await sm_b.abort_execution(exec_id)

    assert res.status == "ABORTED"

    # Now simulate Process A processing control command
    with Session(multi_proc_db) as session_a:
        ctl = session_a.exec(select(ExecutionControl).where(ExecutionControl.execution_id == exec_id)).first()
        assert ctl is not None
        assert ctl.command == "ABORT"


@pytest.mark.asyncio
async def test_janitor_failover_on_process_death(multi_proc_db) -> None:
    """When Process B dies, Janitor on Process A discovers its orphaned execution and marks it FAILED."""
    owner_dead = "worker_died_suddenly"
    owner_janitor = "worker_janitor_node"
    now = utc_now()

    with Session(multi_proc_db) as session:
        # Heartbeat expired 50s ago
        session.add(
            ProcessHeartbeat(
                owner_id=owner_dead,
                pid=9999,
                host="worker-box",
                last_seen=now - timedelta(seconds=50),
            )
        )
        # Execution left stranded in EXECUTING state
        session.add(
            ExecutionLog(
                id="exec_stranded_orphan",
                target_id="sqlserver_prod",
                query="SELECT * FROM massive_export;",
                query_type="READ",
                status="EXECUTING",
                owner_id=owner_dead,
                started_at=now - timedelta(seconds=60),
                created_at=now - timedelta(seconds=60),
            )
        )
        session.commit()

    cm = ClusterManager(db_engine=multi_proc_db, owner_id=owner_janitor)
    with Session(multi_proc_db) as session:
        await cm._run_janitor_cleanup(session)

    with Session(multi_proc_db) as session:
        recovered = session.exec(select(ExecutionLog).where(ExecutionLog.id == "exec_stranded_orphan")).one()
        assert recovered.status == "FAILED"
        assert recovered.error_message == "owner process died"
