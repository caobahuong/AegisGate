"""Unit tests for ExecutionStateMachine lifecycle transitions and approval modes."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session

from core.database import PluginProfile
from core.engine.state_machine import ExecutionStateMachine
from plugins.plugin_contract import DryRunResult, ExecuteResult


@pytest.mark.asyncio
async def test_state_machine_pause_and_resume_flow(db_session: Session):
    """Verify pause-for-review when auto approval is OFF, then resume to completion."""
    plugin = PluginProfile(
        id="test_db_plugin",
        name="Test DB Plugin",
        driver="mock",
        entrypoint="python mock.py",
    )
    db_session.add(plugin)
    db_session.commit()

    sm = ExecutionStateMachine(db_session)

    mock_dry_run = DryRunResult(
        is_valid=True,
        violations=[],
        explain_plan={"nodes": 1},
        estimated_time_ms=5.0,
        query_type="READ",
    )
    mock_execute = ExecuteResult(
        data=[{"id": 1, "name": "Item"}],
        rows_affected=1,
        execution_time_ms=12.0,
        spid=42,
    )

    with patch.object(sm.registry, "get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.dry_run.return_value = mock_dry_run
        mock_client.execute.return_value = mock_execute
        mock_get_client.return_value = mock_client

        # Auto mode is OFF by default -> should pause
        log = await sm.initiate_execution(
            target_id="test_db_plugin",
            query="SELECT * FROM Items WHERE Id = 1",
            reasoning="Fetch item",
        )
        assert log.status == "PAUSED_FOR_REVIEW"
        assert log.auto_approved is False

        # Approve and resume
        resumed_log = await sm.approve_and_resume(log.id, approved_by="SecOps Admin")
        assert resumed_log.status == "COMPLETED"
        assert resumed_log.spid == 42
        assert resumed_log.approved_by == "SecOps Admin"


@pytest.mark.asyncio
async def test_state_machine_auto_approval_mode(db_session: Session):
    """Verify automatic execution through to COMPLETED when auto approval is ON."""
    plugin = PluginProfile(
        id="test_auto_plugin",
        name="Test Auto",
        driver="mock",
        entrypoint="python mock.py",
    )
    db_session.add(plugin)
    db_session.commit()

    sm = ExecutionStateMachine(db_session)
    sm.setting_store.set_auto_approval(True)

    mock_dry_run = DryRunResult(
        is_valid=True,
        violations=[],
        explain_plan={"nodes": 1},
        estimated_time_ms=5.0,
        query_type="READ",
    )
    mock_execute = ExecuteResult(
        data=[{"result": 1}],
        rows_affected=1,
        execution_time_ms=8.0,
    )

    with patch.object(sm.registry, "get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.dry_run.return_value = mock_dry_run
        mock_client.execute.return_value = mock_execute
        mock_get_client.return_value = mock_client

        log = await sm.initiate_execution(
            target_id="test_auto_plugin",
            query="SELECT 1",
        )
        assert log.status == "COMPLETED"
        assert log.auto_approved is True
