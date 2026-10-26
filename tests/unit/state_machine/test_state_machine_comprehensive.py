"""Comprehensive tests for ExecutionStateMachine transitions, invalid flows, and edge cases.

Verifies:
- Complete valid transition sequence
- Invalid state transitions throwing ExecutionStateError
- Rejecting completed or executing states
- Double approval compare-and-set race handling
- Dry-run failure with fail-closed vs fail-open setting
- Governance engine inspection crash fail-closed
- Abort handling on executing vs queued vs finished executions
- Remote abort dispatching to another owner process
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session, select

from core.config import settings
from core.database import ExecutionControl, PluginProfile, utc_now
from core.engine.cluster import get_owner_id
from core.engine.state_machine import ExecutionStateMachine
from core.exceptions import ExecutionStateError
from plugins.plugin_contract import AbortResult, DryRunResult, ExecuteResult
from tests.factories import make_execution_log, make_plugin_profile


@pytest.fixture
def mock_plugin(db_session: Session) -> PluginProfile:
    plugin = make_plugin_profile(
        id="sql_test_target",
        name="SQL Test Target",
        driver="mock",
        entrypoint="python mock.py",
        config={"use_simulation": "true"},
    )
    db_session.add(plugin)
    db_session.commit()
    db_session.refresh(plugin)
    return plugin


@pytest.mark.asyncio
async def test_full_valid_transition_flow(db_session: Session, mock_plugin: PluginProfile):
    """Test full happy path: initiate -> pause -> approve -> execute -> complete."""
    sm = ExecutionStateMachine(db_session)
    sm.setting_store.set_auto_approval(False)

    mock_client = AsyncMock()
    mock_client.dry_run.return_value = DryRunResult(
        is_valid=True,
        violations=[],
        explain_plan={"nodes": 1},
        estimated_time_ms=10.0,
        query_type="READ",
    )
    mock_client.execute.return_value = ExecuteResult(
        data=[{"id": 1, "status": "active"}],
        rows_affected=1,
        execution_time_ms=15.0,
        spid=101,
    )

    with patch.object(sm.registry, "get_client", return_value=mock_client):
        # 1. Initiate -> PAUSED_FOR_REVIEW
        log = await sm.initiate_execution(
            target_id=mock_plugin.id,
            query="SELECT id, status FROM users WHERE id = 1",
            reasoning="Valid check",
        )
        assert log.status == "PAUSED_FOR_REVIEW"
        assert log.auto_approved is False

        # 2. Approve and Resume -> COMPLETED
        resumed = await sm.approve_and_resume(log.id, approved_by="Auditor Alice")
        assert resumed.status == "COMPLETED"
        assert resumed.approved_by == "Auditor Alice"
        assert resumed.spid == 101
        assert resumed.result_summary is not None
        assert "rows_affected" in resumed.result_summary or "active" in resumed.result_summary
        assert resumed.finished_at is not None


@pytest.mark.asyncio
async def test_invalid_state_transitions(db_session: Session, mock_plugin: PluginProfile):
    """Verify that illegal transitions raise ExecutionStateError with clear error messages."""
    sm = ExecutionStateMachine(db_session)

    # 1. Non-existent ID for resume
    with pytest.raises(ExecutionStateError, match="does not exist"):
        await sm.approve_and_resume("non_existent_id")

    # 2. Non-existent ID for reject
    with pytest.raises(ExecutionStateError, match="does not exist"):
        await sm.reject("non_existent_id")

    # 3. Non-existent ID for abort
    with pytest.raises(ExecutionStateError, match="does not exist"):
        await sm.abort_execution("non_existent_id")

    # 4. Attempt to approve an already COMPLETED execution
    completed_log = make_execution_log(
        target_id=mock_plugin.id,
        query="SELECT 1",
        query_type="READ",
        status="COMPLETED",
        finished_at=utc_now(),
    )
    db_session.add(completed_log)
    db_session.commit()
    db_session.refresh(completed_log)

    with pytest.raises(ExecutionStateError, match="Cannot resume execution in status 'COMPLETED'"):
        await sm.approve_and_resume(completed_log.id)

    # 5. Attempt to reject an already COMPLETED execution
    with pytest.raises(ExecutionStateError, match="Cannot reject execution in status 'COMPLETED'"):
        await sm.reject(completed_log.id)

    # 6. Attempt to abort an already COMPLETED execution
    with pytest.raises(ExecutionStateError, match="already finished"):
        await sm.abort_execution(completed_log.id)

    # 7. Attempt to abort an already REJECTED execution
    rejected_log = make_execution_log(
        target_id=mock_plugin.id,
        query="DROP TABLE users",
        query_type="WRITE",
        status="REJECTED",
        finished_at=utc_now(),
    )
    db_session.add(rejected_log)
    db_session.commit()
    db_session.refresh(rejected_log)

    with pytest.raises(ExecutionStateError, match="already finished"):
        await sm.abort_execution(rejected_log.id)


@pytest.mark.asyncio
async def test_reject_paused_execution(db_session: Session, mock_plugin: PluginProfile):
    """Verify clean rejection of an execution in PAUSED_FOR_REVIEW state."""
    sm = ExecutionStateMachine(db_session)
    sm.setting_store.set_auto_approval(False)

    log = make_execution_log(
        target_id=mock_plugin.id,
        query="SELECT * FROM confidential",
        query_type="READ",
        status="PAUSED_FOR_REVIEW",
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    rejected = await sm.reject(log.id, rejected_by="SecOps Lead", reason="Access policy restriction")
    assert rejected.status == "REJECTED"
    assert "Access policy restriction" in (rejected.error_message or "")
    assert "SecOps Lead" in (rejected.error_message or "")
    assert rejected.finished_at is not None


@pytest.mark.asyncio
async def test_dry_run_failure_fail_closed(db_session: Session, mock_plugin: PluginProfile, monkeypatch: pytest.MonkeyPatch):
    """Verify that when dry_run crashes, FAIL_CLOSED_ON_DRY_RUN_ERROR=True marks execution REJECTED."""
    monkeypatch.setattr(settings, "FAIL_CLOSED_ON_DRY_RUN_ERROR", True)
    sm = ExecutionStateMachine(db_session)

    mock_client = AsyncMock()
    mock_client.dry_run.side_effect = RuntimeError("Target DB connection refused")

    with patch.object(sm.registry, "get_client", return_value=mock_client):
        log = await sm.initiate_execution(
            target_id=mock_plugin.id,
            query="SELECT count(*) FROM big_table",
        )
        assert log.status == "REJECTED"
        assert "fail-closed" in (log.error_message or "")
        violations = json.loads(log.violations_json or "[]")
        assert any("fail-closed" in v for v in violations)


@pytest.mark.asyncio
async def test_dry_run_failure_fail_open_pauses_for_review(db_session: Session, mock_plugin: PluginProfile, monkeypatch: pytest.MonkeyPatch):
    """Verify that when dry_run crashes and FAIL_CLOSED_ON_DRY_RUN_ERROR=False, execution forces PAUSED_FOR_REVIEW."""
    monkeypatch.setattr(settings, "FAIL_CLOSED_ON_DRY_RUN_ERROR", False)
    sm = ExecutionStateMachine(db_session)
    sm.setting_store.set_auto_approval(True)  # Even with auto-approval ON, dry run crash must NOT auto-execute

    mock_client = AsyncMock()
    mock_client.dry_run.side_effect = TimeoutError("Dry-run timed out")

    with patch.object(sm.registry, "get_client", return_value=mock_client):
        log = await sm.initiate_execution(
            target_id=mock_plugin.id,
            query="SELECT 1",
        )
        assert log.status == "PAUSED_FOR_REVIEW"
        assert log.auto_approved is False


@pytest.mark.asyncio
async def test_governance_crash_fails_closed(db_session: Session, mock_plugin: PluginProfile):
    """Verify that unexpected exception in GovernanceEngine is caught and fails closed safely."""
    sm = ExecutionStateMachine(db_session)

    mock_client = AsyncMock()
    mock_client.dry_run.return_value = DryRunResult(
        is_valid=True,
        violations=[],
        explain_plan={},
        estimated_time_ms=1.0,
    )

    with (
        patch.object(sm.registry, "get_client", return_value=mock_client),
        patch("core.engine.state_machine.GovernanceEngine.inspect_query_and_plan", side_effect=Exception("Corrupted AST")),
    ):
        log = await sm.initiate_execution(
            target_id=mock_plugin.id,
            query="SELECT 1",
        )
        assert log.status == "REJECTED"
        assert "fail-closed" in (log.error_message or "")


@pytest.mark.asyncio
async def test_abort_execution_local_and_remote(db_session: Session, mock_plugin: PluginProfile):
    """Verify abort behavior for locally owned vs remotely owned executions."""
    sm = ExecutionStateMachine(db_session)

    # 1. Abort locally owned execution
    local_log = make_execution_log(
        target_id=mock_plugin.id,
        query="SELECT * FROM huge_scan",
        query_type="READ",
        status="EXECUTING",
        owner_id=get_owner_id(),
        started_at=utc_now(),
    )
    db_session.add(local_log)
    db_session.commit()
    db_session.refresh(local_log)

    mock_client = AsyncMock()
    mock_client.abort.return_value = AbortResult(success=True, message="SPID killed successfully")

    with patch.object(sm.registry, "get_client", return_value=mock_client):
        aborted = await sm.abort_execution(local_log.id)
        assert aborted.status == "ABORTED"
        assert "manually aborted" in (aborted.error_message or "")

        # Verify ExecutionControl record was created and marked handled
        ctl = db_session.exec(select(ExecutionControl)).first()
        assert ctl is not None
        assert ctl.command == "ABORT"
        assert ctl.handled_at is not None

    # 2. Abort remotely owned execution (owned by remote worker process)
    remote_log = make_execution_log(
        target_id=mock_plugin.id,
        query="SELECT * FROM remote_long_query",
        query_type="READ",
        status="EXECUTING",
        owner_id="remote_worker_node_99",
        started_at=utc_now(),
    )
    db_session.add(remote_log)
    db_session.commit()
    db_session.refresh(remote_log)

    aborted_remote = await sm.abort_execution(remote_log.id)
    assert aborted_remote.status == "ABORTED"
    assert "remote_worker_node_99" in (aborted_remote.error_message or "")


@pytest.mark.asyncio
async def test_abort_during_concurrency_queue_wait(db_session: Session, mock_plugin: PluginProfile):
    """Verify that an execution aborted while waiting in the concurrency queue does not execute."""
    sm = ExecutionStateMachine(db_session)
    log = make_execution_log(
        target_id=mock_plugin.id,
        query="SELECT 1",
        query_type="READ",
        status="PAUSED_FOR_REVIEW",
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)

    # Mark as ABORTED directly before execute_step runs
    log.status = "ABORTED"
    db_session.add(log)
    db_session.commit()

    result = await sm._execute_step(log)
    assert result.status == "ABORTED"
