"""Unit tests for cross-process execution control and abort routing."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session, select

from core.database import ExecutionControl, ExecutionLog, PluginProfile, utc_now
from core.engine.cluster import ClusterManager, get_owner_id
from core.engine.state_machine import ExecutionStateMachine
from plugins.plugin_contract import AbortResult


@pytest.mark.asyncio
async def test_local_abort_records_control_and_calls_client(db_session: Session) -> None:
    """A locally owned execution abort calls the local plugin client and stamps handled_at."""
    profile = PluginProfile(
        id="mock_target",
        name="Mock Plugin",
        driver="sqlserver",
        entrypoint="mock --serve",
    )
    db_session.add(profile)

    exec_id = "exec_local_01"
    owner_id = get_owner_id()
    log = ExecutionLog(
        id=exec_id,
        target_id="mock_target",
        query="WAITFOR DELAY '00:00:10';",
        query_type="READ",
        status="EXECUTING",
        owner_id=owner_id,
        started_at=utc_now(),
        created_at=utc_now(),
    )
    db_session.add(log)
    db_session.commit()

    sm = ExecutionStateMachine(db_session)
    mock_client = AsyncMock()
    mock_client.abort.return_value = AbortResult(success=True, message="SPID killed")

    with patch.object(sm.registry, "get_client", return_value=mock_client):
        res = await sm.abort_execution(exec_id)

    assert res.status == "ABORTED"
    mock_client.abort.assert_called_once()

    # Check ExecutionControl row was created and stamped
    ctl = db_session.exec(select(ExecutionControl).where(ExecutionControl.execution_id == exec_id)).first()
    assert ctl is not None
    assert ctl.command == "ABORT"
    assert ctl.handled_at is not None


@pytest.mark.asyncio
async def test_cross_process_abort_dispatched_and_handled(db_session: Session) -> None:
    """An execution owned by worker_remote is aborted by another process, then handled by worker_remote."""
    profile = PluginProfile(
        id="mock_target_2",
        name="Mock Plugin 2",
        driver="sqlserver",
        entrypoint="mock --serve",
    )
    db_session.add(profile)

    exec_id = "exec_remote_01"
    remote_owner = "worker_remote_99"
    log = ExecutionLog(
        id=exec_id,
        target_id="mock_target_2",
        query="WAITFOR DELAY '00:00:15';",
        query_type="READ",
        status="EXECUTING",
        owner_id=remote_owner,
        started_at=utc_now(),
        created_at=utc_now(),
    )
    db_session.add(log)
    db_session.commit()

    # sm simulates Process B (current process != remote_owner)
    sm = ExecutionStateMachine(db_session)

    # Abort with a quick timeout on remote wait so test does not hang
    with patch("asyncio.sleep", new_callable=AsyncMock):
        res = await sm.abort_execution(exec_id)

    assert res.status == "ABORTED"

    # ExecutionControl row should be pending
    ctl = db_session.exec(select(ExecutionControl).where(ExecutionControl.execution_id == exec_id)).first()
    assert ctl is not None
    assert ctl.command == "ABORT"

    # Now simulate remote process's cluster manager picking up the control command
    remote_cm = ClusterManager(db_engine=db_session.bind, owner_id=remote_owner)
    mock_remote_client = AsyncMock()
    mock_remote_client.abort.return_value = AbortResult(success=True, message="Remote kill OK")

    with patch("core.engine.plugin_registry.PluginRegistry.get_client", return_value=mock_remote_client):
        await remote_cm._process_pending_controls()

    # Verify remote client was invoked
    mock_remote_client.abort.assert_called_once()

    # Verify control row is now handled
    db_session.refresh(ctl)
    assert ctl.handled_at is not None
