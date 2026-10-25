"""Opt-in integration tests against a REAL SQL Server (read-only statements + own WAITFOR sessions).

Skipped unless AEGISGATE_TEST_MSSQL_SERVER is set, e.g. (PowerShell):

    $env:AEGISGATE_TEST_MSSQL_SERVER = "localhost"
    $env:AEGISGATE_TEST_MSSQL_AUTH   = "windows"      # or "sql" + _USER / _PASSWORD
    python -m pytest tests/test_sqlserver_integration.py -v

Optional: AEGISGATE_TEST_MSSQL_PORT (1433), _DATABASE (master), _TRUST (true).
Nothing here writes data; the only "slow" statement is WAITFOR DELAY in the test's own session.
"""

import asyncio
import json
import os
import time
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from core.config import settings
from core.database import PluginProfile
from core.engine.plugin_client import PluginSubprocessClient, terminate_all_subprocesses
from core.engine.state_machine import ExecutionStateMachine
from core.exceptions import JsonRpcProtocolError
from plugins.plugin_contract import AbortParams, DryRunParams, ExecuteParams, SyncKnowledgeParams

SERVER = os.environ.get("AEGISGATE_TEST_MSSQL_SERVER")
pytestmark = pytest.mark.skipif(not SERVER, reason="set AEGISGATE_TEST_MSSQL_SERVER to run SQL Server integration tests")

ENTRYPOINT = "python plugins/sqlserver_plugin/adapter.py --serve"


def _config(**extra: object) -> dict[str, object]:
    cfg: dict[str, object] = {
        "server": SERVER,
        "port": os.environ.get("AEGISGATE_TEST_MSSQL_PORT", "1433"),
        "database": os.environ.get("AEGISGATE_TEST_MSSQL_DATABASE", "master"),
        "auth_mode": "Windows Authentication" if os.environ.get("AEGISGATE_TEST_MSSQL_AUTH", "windows") == "windows" else "SQL Server Authentication",
        "username": os.environ.get("AEGISGATE_TEST_MSSQL_USER", ""),
        "password": os.environ.get("AEGISGATE_TEST_MSSQL_PASSWORD", ""),
        "trust_server_certificate": os.environ.get("AEGISGATE_TEST_MSSQL_TRUST", "true"),
        "use_simulation": "false",
    }
    cfg.update(extra)
    return cfg


def _running_waitfors() -> int:
    """How many AegisGate sessions are currently inside WAITFOR (checked on a separate connection)."""
    import pyodbc

    from plugins.sqlserver_plugin.adapter import SqlServerAdapter

    adapter = SqlServerAdapter()
    conn = pyodbc.connect(adapter._conn_str(_config(), read_only=False), autocommit=True, timeout=10)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM sys.dm_exec_requests r JOIN sys.dm_exec_sessions s ON s.session_id = r.session_id "
            "WHERE s.program_name = 'AegisGate' AND r.command = 'WAITFOR'"
        )
        return int(cur.fetchone()[0])
    finally:
        conn.close()


async def _wait_until(predicate, seconds: float = 8.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return True
        await asyncio.sleep(0.2)
    return predicate()


@pytest.fixture(name="client")
async def fixture_client():
    client = PluginSubprocessClient(ENTRYPOINT, plugin_id="itest_mssql", config=_config())
    yield client
    await terminate_all_subprocesses()


@pytest.fixture(name="session")
async def fixture_session(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'it.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(
            PluginProfile(
                id="itest_mssql", name="IT", driver="pyodbc/mssql", entrypoint=ENTRYPOINT,
                config_json=json.dumps(_config()), status="active",
            )
        )
        s.commit()
        yield s
    await terminate_all_subprocesses()


async def test_ping_connects_for_real(client: PluginSubprocessClient) -> None:
    res = await client.send_rpc_command("ping", {})
    assert res["mode"] == "sqlserver" and "Microsoft SQL Server" in res["server_version"]


async def test_not_configured_plugin_refuses_to_fake_data() -> None:
    bare = PluginSubprocessClient(ENTRYPOINT, plugin_id="itest_unconfigured")  # no config pushed
    try:
        with pytest.raises(JsonRpcProtocolError, match="not configured"):
            await bare.dry_run(DryRunParams(query="SELECT 1"))
    finally:
        await terminate_all_subprocesses()


async def test_execute_returns_real_rows(client: PluginSubprocessClient) -> None:
    res = await client.execute(
        ExecuteParams(
            execution_id="it_rows",
            query="SELECT TOP 3 name, database_id, create_date FROM sys.databases ORDER BY database_id",
            read_only=True,
        )
    )
    assert [r["name"] for r in res.data][:2] == ["master", "tempdb"]
    assert isinstance(res.data[0]["create_date"], str) and res.spid and res.spid > 0
    assert res.truncated is False


async def test_row_cap_marks_truncated() -> None:
    capped = PluginSubprocessClient(ENTRYPOINT, plugin_id="itest_cap", config=_config(max_rows=2))
    try:
        res = await capped.execute(
            ExecuteParams(execution_id="it_cap", query="SELECT name FROM sys.all_objects", read_only=True)
        )
        assert len(res.data) == 2 and res.truncated is True
    finally:
        await terminate_all_subprocesses()


async def test_dry_run_returns_real_showplan(client: PluginSubprocessClient) -> None:
    res = await client.dry_run(DryRunParams(query="SELECT name FROM sys.databases WHERE database_id = 1"))
    assert res.explain_plan["Source"] == "SET SHOWPLAN_XML ON"
    assert res.explain_plan["QueryPlan"]["RelOp"]  # real operators from the optimizer
    assert res.query_type == "READ" and res.is_valid


async def test_dry_run_never_executes_the_statement(client: PluginSubprocessClient) -> None:
    # If this were executed it would block for 20s; SHOWPLAN only compiles it.
    started = time.monotonic()
    await client.dry_run(DryRunParams(query="WAITFOR DELAY '00:00:20'"))
    assert time.monotonic() - started < 8


async def test_sync_knowledge_reads_catalog(client: PluginSubprocessClient) -> None:
    res = await client.sync_knowledge(SyncKnowledgeParams())
    assert res.target_id and isinstance(res.partitions, list)


async def test_abort_really_cancels_running_query(client: PluginSubprocessClient) -> None:
    running = asyncio.create_task(
        client.execute(ExecuteParams(execution_id="it_abort", query="WAITFOR DELAY '00:00:30'", timeout_seconds=60, read_only=True))
    )
    assert await _wait_until(lambda: _running_waitfors() == 1), "query never started on the server"

    started = time.monotonic()
    abort_res = await client.abort(AbortParams(execution_id="it_abort"))
    assert abort_res.success, abort_res.message

    with pytest.raises(JsonRpcProtocolError, match="aborted"):
        await running
    assert time.monotonic() - started < 10, "execute should return right after abort, not after 30s"
    assert await _wait_until(lambda: _running_waitfors() == 0), "query is still running on SQL Server"


async def test_server_side_timeout_is_enforced(client: PluginSubprocessClient) -> None:
    started = time.monotonic()
    with pytest.raises(JsonRpcProtocolError, match="timeout"):
        await client.execute(ExecuteParams(execution_id="it_to", query="WAITFOR DELAY '00:00:30'", timeout_seconds=1, read_only=True))
    assert time.monotonic() - started < 10
    assert await _wait_until(lambda: _running_waitfors() == 0)


async def test_core_timeout_guard_kills_query_on_server(session: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "READ_TIMEOUT_SECONDS", 3.0)
    sm = ExecutionStateMachine(session)
    sm.setting_store.set_auto_approval(True)
    started = time.monotonic()
    log = await sm.initiate_execution("itest_mssql", "WAITFOR DELAY '00:00:30'")
    assert log.status == "TIMEOUT", (log.status, log.error_message)
    assert time.monotonic() - started < 12
    assert "abort FAILED" not in (log.error_message or "")
    assert await _wait_until(lambda: _running_waitfors() == 0), "timeout did not kill the query"


async def test_manual_stop_keeps_aborted_status(session: Session) -> None:
    sm = ExecutionStateMachine(session)
    sm.setting_store.set_auto_approval(True)
    run = asyncio.create_task(sm.initiate_execution("itest_mssql", "WAITFOR DELAY '00:00:30'", execution_id="it_stop"))
    assert await _wait_until(lambda: _running_waitfors() == 1), "query never started on the server"

    stopped = await ExecutionStateMachine(session).abort_execution("it_stop")
    assert stopped.status == "ABORTED"
    final = await run
    assert final.status == "ABORTED", "the late execute error must not overwrite ABORTED"
    assert await _wait_until(lambda: _running_waitfors() == 0)
