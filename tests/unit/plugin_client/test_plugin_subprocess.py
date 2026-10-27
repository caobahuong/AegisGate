"""Unit tests for JSON-RPC plugin subprocess communication with simulated adapter."""

import pytest

from core.engine.plugin_client import PluginSubprocessClient
from plugins.plugin_contract import AbortParams, DryRunParams, ExecuteParams, SyncKnowledgeParams


@pytest.mark.asyncio
async def test_subprocess_sync_knowledge():
    """Verify sync_knowledge call over subprocess IPC."""
    client = PluginSubprocessClient(entrypoint_cmd="python plugins/sqlserver_plugin/adapter.py")
    res = await client.sync_knowledge(SyncKnowledgeParams())

    assert res.target_id == "sqlserver_prod"
    assert len(res.partitions) == 3


@pytest.mark.asyncio
async def test_subprocess_dry_run():
    """Verify dry_run call over subprocess IPC."""
    client = PluginSubprocessClient(entrypoint_cmd="python plugins/sqlserver_plugin/adapter.py")
    res = await client.dry_run(
        DryRunParams(
            query="SELECT OrderID FROM Orders WHERE OrderID = 5",
            rules=[],
        )
    )
    assert res.is_valid is True
    assert res.query_type == "READ"


@pytest.mark.asyncio
async def test_subprocess_execute():
    """Verify execute call over subprocess IPC."""
    client = PluginSubprocessClient(entrypoint_cmd="python plugins/sqlserver_plugin/adapter.py")
    res = await client.execute(
        ExecuteParams(
            execution_id="exec_ipc_01",
            query="SELECT * FROM Orders WHERE OrderID = 1001",
            timeout_seconds=10.0,
        )
    )
    assert res.rows_affected == 3
    assert res.spid is not None


@pytest.mark.asyncio
async def test_subprocess_abort():
    """Verify abort call over subprocess IPC."""
    client = PluginSubprocessClient(entrypoint_cmd="python plugins/sqlserver_plugin/adapter.py")
    res = await client.abort(AbortParams(execution_id="exec_ipc_01"))
    assert res.success is True
