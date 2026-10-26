"""Concurrency, Race Condition, and Deadlock Stress Tests for AegisGate.

Tests verify:
1. CAS (Compare-and-Set) state machine resilience with 50+ concurrent approvals/rejects/aborts.
2. Mutually exclusive racing between concurrent Approves and Rejects on the same paused execution.
3. CAS abort racing: 50 concurrent abort requests on an in-flight execution (exactly 1 wins).
4. Abort vs Completion race: If abort transitions status to ABORTED, late completion results are discarded.
5. ConcurrencyLimiter backpressure with 100+ requests (slot limits, queue limits, HTTP 429).
6. Concurrent rule and setting updates with SQLite WAL mode (zero "database is locked" errors).
7. High-volume concurrent log writes while background retention pruning executes simultaneously.
"""

import asyncio
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlmodel import Session, select

from core.database import (
    ExecutionLog,
    PluginProfile,
    Rule,
    SystemSetting,
    init_db,
    utc_now,
)
from core.engine.concurrency_limiter import PluginConcurrencyLimiter
from core.engine.state_machine import ExecutionStateMachine
from core.exceptions import ExecutionStateError, PluginQueueFullError
from core.storage.log_store import LogStore
from core.storage.retention import prune_logs
from core.storage.rule_store import RuleStore
from core.storage.setting_store import SettingStore


@pytest.fixture
def stress_db_engine(tmp_path: Path):
    """Provide an isolated SQLite database configured with WAL mode and high concurrency pooling."""
    db_file = tmp_path / "stress_concurrency.db"
    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 20.0},
        pool_size=30,
        max_overflow=50,
        pool_timeout=30.0,
    )

    import sqlite3

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=20000")
            cursor.close()

    init_db(test_engine)

    # Seed mock plugin profile
    with Session(test_engine) as session:
        session.add(
            PluginProfile(
                id="sqlserver_stress",
                name="SQL Server Stress",
                driver="sqlserver",
                entrypoint="python plugins/sqlserver_plugin/adapter.py --serve",
                config_json='{"use_simulation": "true"}',
            )
        )
        session.commit()

    yield test_engine
    test_engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_state_machine_cas_50_approvals(stress_db_engine) -> None:
    """50 concurrent requests attempt to approve the SAME paused execution.

    Invariants:
    - Exactly 1 request wins the CAS transition and executes.
    - Exactly 49 requests fail with ExecutionStateError.
    - Zero 'database is locked' errors.
    - DB record ends up in COMPLETED status with approved_by set to one of the approvers.
    """
    exec_id = "exec_stress_cas_50"

    with Session(stress_db_engine) as session:
        session.add(
            ExecutionLog(
                id=exec_id,
                target_id="sqlserver_stress",
                query="SELECT COUNT(*) FROM Customers;",
                query_type="READ",
                status="PAUSED_FOR_REVIEW",
                created_at=utc_now(),
            )
        )
        session.commit()

    async def _try_approve(approver_id: int) -> tuple[bool, str]:
        with Session(stress_db_engine) as session:
            sm = ExecutionStateMachine(session)

            # Mock _execute_step so no actual subprocess is spawned
            async def _fake_execute_step(log_item: ExecutionLog) -> ExecutionLog:
                await asyncio.sleep(0.01)  # Simulate small async execution window
                log_item.status = "COMPLETED"
                log_item.result_summary = "5000"
                session.add(log_item)
                session.commit()
                return log_item

            sm._execute_step = _fake_execute_step  # type: ignore[method-assign]
            try:
                await sm.approve_and_resume(exec_id, approved_by=f"Approver_{approver_id}")
                return True, f"Approver_{approver_id}"
            except ExecutionStateError:
                return False, f"Approver_{approver_id}"

    # Fire 50 simultaneous approval requests
    tasks = [_try_approve(i) for i in range(50)]
    results = await asyncio.gather(*tasks)

    successes = [r for r in results if r[0] is True]
    failures = [r for r in results if r[0] is False]

    assert len(successes) == 1, f"Expected exactly 1 winner, got {len(successes)}"
    assert len(failures) == 49, f"Expected exactly 49 failures, got {len(failures)}"

    winner_name = successes[0][1]

    # Verify database state
    with Session(stress_db_engine) as session:
        final_log = session.exec(select(ExecutionLog).where(ExecutionLog.id == exec_id)).one()
        assert final_log.status == "COMPLETED"
        assert final_log.approved_by == winner_name
        assert final_log.result_summary == "5000"


@pytest.mark.asyncio
async def test_concurrent_state_machine_cas_racing_approve_vs_reject(stress_db_engine) -> None:
    """50 concurrent requests (25 approve vs 25 reject) race on the SAME paused execution.

    Invariants:
    - Exactly 1 operation succeeds (either 1 Approve or 1 Reject).
    - Exactly 49 operations fail with ExecutionStateError.
    - Zero data corruption; final status is either COMPLETED or REJECTED.
    """
    exec_id = "exec_stress_race_app_rej"

    with Session(stress_db_engine) as session:
        session.add(
            ExecutionLog(
                id=exec_id,
                target_id="sqlserver_stress",
                query="UPDATE Accounts SET balance = balance + 100;",
                query_type="WRITE",
                status="PAUSED_FOR_REVIEW",
                created_at=utc_now(),
            )
        )
        session.commit()

    async def _action(action_type: str, actor_id: int) -> tuple[str, bool]:
        with Session(stress_db_engine) as session:
            sm = ExecutionStateMachine(session)

            async def _fake_execute_step(log_item: ExecutionLog) -> ExecutionLog:
                await asyncio.sleep(0.01)
                log_item.status = "COMPLETED"
                session.add(log_item)
                session.commit()
                return log_item

            sm._execute_step = _fake_execute_step  # type: ignore[method-assign]

            try:
                if action_type == "approve":
                    await sm.approve_and_resume(exec_id, approved_by=f"Actor_{actor_id}")
                else:
                    await sm.reject(exec_id, rejected_by=f"Actor_{actor_id}", reason="Rejected under race")
                return action_type, True
            except ExecutionStateError:
                return action_type, False

    tasks = []
    for i in range(25):
        tasks.append(_action("approve", i))
        tasks.append(_action("reject", i))

    results = await asyncio.gather(*tasks)

    successes = [r for r in results if r[1] is True]
    failures = [r for r in results if r[1] is False]

    assert len(successes) == 1, f"Expected exactly 1 winner, got {len(successes)}"
    assert len(failures) == 49, f"Expected 49 failures, got {len(failures)}"

    winning_action = successes[0][0]
    expected_status = "COMPLETED" if winning_action == "approve" else "REJECTED"

    with Session(stress_db_engine) as session:
        final_log = session.exec(select(ExecutionLog).where(ExecutionLog.id == exec_id)).one()
        assert final_log.status == expected_status


@pytest.mark.asyncio
async def test_concurrent_state_machine_cas_50_aborts(stress_db_engine) -> None:
    """50 concurrent abort requests race to kill the same in-flight EXECUTING query.

    Invariants:
    - Exactly 1 abort operation wins the CAS transition and triggers kill.
    - Exactly 49 abort operations fail with ExecutionStateError (cannot abort already aborted/finished).
    - Status is cleanly ABORTED.
    """
    exec_id = "exec_stress_cas_aborts_50"

    with Session(stress_db_engine) as session:
        session.add(
            ExecutionLog(
                id=exec_id,
                target_id="sqlserver_stress",
                query="WAITFOR DELAY '00:01:00';",
                query_type="READ",
                status="EXECUTING",
                started_at=utc_now(),
                created_at=utc_now(),
            )
        )
        session.commit()

    async def _try_abort(abort_idx: int) -> bool:
        with Session(stress_db_engine) as session:
            sm = ExecutionStateMachine(session)
            with patch.object(sm.registry, "get_client"):
                try:
                    await sm.abort_execution(exec_id)
                    return True
                except ExecutionStateError:
                    return False

    tasks = [_try_abort(i) for i in range(50)]
    results = await asyncio.gather(*tasks)

    assert results.count(True) == 1, f"Expected exactly 1 abort winner, got {results.count(True)}"
    assert results.count(False) == 49

    with Session(stress_db_engine) as session:
        final_log = session.exec(select(ExecutionLog).where(ExecutionLog.id == exec_id)).one()
        assert final_log.status == "ABORTED"
        assert "manually aborted" in (final_log.error_message or "")


@pytest.mark.asyncio
async def test_abort_vs_late_completion_race(stress_db_engine) -> None:
    """If an execution is aborted while executing, a late completion result must be discarded by _finish."""
    exec_id = "exec_abort_vs_completion"

    with Session(stress_db_engine) as session:
        session.add(
            ExecutionLog(
                id=exec_id,
                target_id="sqlserver_stress",
                query="SELECT * FROM massive_table;",
                query_type="READ",
                status="EXECUTING",
                started_at=utc_now(),
                created_at=utc_now(),
            )
        )
        session.commit()

    with Session(stress_db_engine) as session:
        sm = ExecutionStateMachine(session)

        # 1. Abort the execution
        with patch.object(sm.registry, "get_client"):
            await sm.abort_execution(exec_id)

        # 2. Simulate late worker trying to call _finish() with COMPLETED status
        log_item = sm.log_store.get_log(exec_id)
        assert log_item is not None
        assert log_item.status == "ABORTED"

        # Call _finish attempting to mark it COMPLETED
        finished = await sm._finish(
            log_item,
            {"status": "COMPLETED", "result_summary": "late_results"},
            "execution_completed",
            {"status": "COMPLETED"},
        )

        # The late finish must be discarded; status remains ABORTED!
        assert finished.status == "ABORTED"
        assert finished.result_summary != "late_results"


@pytest.mark.asyncio
async def test_concurrency_limiter_contention_100_requests(stress_db_engine) -> None:
    """100 concurrent requests contend for 4 concurrency slots with a queue backlog limit of 30.

    Invariants:
    - At no point does active executing concurrency exceed 4.
    - Requests arriving when backlog >= 30 are rejected with PluginQueueFullError (HTTP 429).
    - All remaining requests complete cleanly.
    - Final queue depth returns to 0 (no leaked slots).
    """
    limiter = PluginConcurrencyLimiter(
        target_id="sqlserver_stress",
        max_concurrency=4,
        max_queue_size=30,
    )

    max_observed_concurrency = 0
    current_concurrency = 0
    lock = asyncio.Lock()
    completed_count = 0
    rejected_count = 0

    async def _worker(req_id: int) -> None:
        nonlocal max_observed_concurrency, current_concurrency, completed_count, rejected_count

        with Session(stress_db_engine) as session:
            log = ExecutionLog(
                id=f"exec_limit_{req_id}",
                target_id="sqlserver_stress",
                query="SELECT 1;",
                query_type="READ",
                status="DRY_RUN",
                created_at=utc_now(),
            )
            session.add(log)
            session.commit()

            try:
                async with limiter.acquire_slot(session, log, timeout_seconds=5.0):
                    async with lock:
                        current_concurrency += 1
                        if current_concurrency > max_observed_concurrency:
                            max_observed_concurrency = current_concurrency

                    await asyncio.sleep(0.02)  # Simulate workload in slot

                    async with lock:
                        current_concurrency -= 1
                    completed_count += 1
            except PluginQueueFullError:
                rejected_count += 1

    # Launch 100 concurrent worker tasks simultaneously
    tasks = [_worker(i) for i in range(100)]
    await asyncio.gather(*tasks)

    assert max_observed_concurrency <= 4, f"Max concurrency exceeded: {max_observed_concurrency} > 4"
    assert completed_count + rejected_count == 100
    assert rejected_count > 0, "Expected backpressure rejections (HTTP 429) when queue filled"
    assert limiter.queue_depth == 0, f"Leaked queue depth: {limiter.queue_depth}"


@pytest.mark.asyncio
async def test_concurrent_rule_and_setting_updates_50(stress_db_engine) -> None:
    """50 concurrent updates to rules and settings in SQLite WAL mode.

    Invariants:
    - Zero 'database is locked' or deadlock errors.
    - All rules and settings are consistently committed.
    """
    # Pre-seed base rules and settings
    with Session(stress_db_engine) as session:
        r_store = RuleStore(session)
        s_store = SettingStore(session)
        for i in range(10):
            r_store.create_rule(
                Rule(
                    id=f"rule_bench_{i}",
                    name=f"Benchmark Rule {i}",
                    rule_type="MAX_EXECUTION_TIME",
                    expression="15",
                )
            )
            s_store.set_setting(f"config_bench_{i}", f"initial_{i}")

    async def _update_rule(index: int) -> None:
        with Session(stress_db_engine) as session:
            r_store = RuleStore(session)
            rule_id = f"rule_bench_{index % 10}"
            r_store.update_rule(rule_id, {"expression": str(20 + index), "is_active": (index % 2 == 0)})

    async def _update_setting(index: int) -> None:
        with Session(stress_db_engine) as session:
            s_store = SettingStore(session)
            s_store.set_setting(f"config_bench_{index % 10}", f"updated_val_{index}")

    tasks = []
    for i in range(25):
        tasks.append(_update_rule(i))
        tasks.append(_update_setting(i))

    # All 50 concurrent updates must complete cleanly without locking errors
    await asyncio.gather(*tasks)

    with Session(stress_db_engine) as session:
        rules = session.exec(select(Rule)).all()
        assert len(rules) >= 10
        settings_entries = session.exec(select(SystemSetting)).all()
        assert len(settings_entries) >= 10


@pytest.mark.asyncio
async def test_concurrent_log_writes_during_active_retention(stress_db_engine) -> None:
    """50 concurrent workers writing logs while background retention pruning executes repeatedly.

    Invariants:
    - Retention pruning executes without locking out writers.
    - Zero database locked errors.
    - Active (non-terminal) logs being written are NEVER pruned or lost.
    """
    now = utc_now()
    # Pre-seed 100 old completed logs (older than 3 days)
    with Session(stress_db_engine) as session:
        for i in range(100):
            session.add(
                ExecutionLog(
                    id=f"old_terminal_{i}",
                    target_id="sqlserver_stress",
                    query="SELECT 1;",
                    query_type="READ",
                    status="COMPLETED",
                    created_at=now - timedelta(days=5),
                    finished_at=now - timedelta(days=5),
                )
            )
        session.commit()

    retention_running = True
    prune_iterations = 0

    async def _retention_loop() -> None:
        nonlocal prune_iterations
        while retention_running:
            with Session(stress_db_engine) as session:
                prune_logs(session, log_retention_days=3, archive_before_delete=False)
            prune_iterations += 1
            await asyncio.sleep(0.01)

    retention_task = asyncio.create_task(_retention_loop())

    async def _write_worker(worker_id: int) -> None:
        with Session(stress_db_engine) as session:
            l_store = LogStore(session)
            log = ExecutionLog(
                id=f"active_log_{worker_id}",
                target_id="sqlserver_stress",
                query=f"SELECT {worker_id};",
                query_type="READ",
                status="EXECUTING",
                created_at=utc_now(),
            )
            l_store.create_log(log)
            await asyncio.sleep(0.005)
            l_store.update_log(log.id, {"status": "COMPLETED", "execution_time_ms": 12.5})

    # Run 50 concurrent writer workers
    writer_tasks = [_write_worker(i) for i in range(50)]
    await asyncio.gather(*writer_tasks)

    retention_running = False
    await retention_task

    assert prune_iterations >= 1

    # Verify that all 50 newly written logs exist and were not accidentally deleted
    with Session(stress_db_engine) as session:
        active_written_logs = session.exec(select(ExecutionLog).where(ExecutionLog.id.startswith("active_log_"))).all()
        assert len(active_written_logs) == 50

        # Verify old logs were pruned
        old_surviving = session.exec(select(ExecutionLog).where(ExecutionLog.id.startswith("old_terminal_"))).all()
        assert len(old_surviving) == 0
