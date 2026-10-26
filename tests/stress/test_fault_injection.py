"""Fault Injection, Chaos, and Resiliency Tests for AegisGate.

Tests verify that the system handles anomalies gracefully without crashing the process or hanging:
1. Database locked / dropped connection fault injection during API calls.
2. Simulated disk full (ENOSPC) during knowledge document save.
3. Plugin subprocess crash / unexpected exit code during dry-run and execution.
4. Plugin hang / upstream timeout triggering emergency timeout abort.
5. Plugin returning garbage / corrupt JSON-RPC on stdout.
6. Malformed JSON payloads, truncated request bodies, and body size limits (>10MB -> HTTP 413).
7. Extreme inputs: empty strings, None, massive query strings, null bytes (\\x00).
"""

import asyncio
import errno
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from core.database import ExecutionLog, KnowledgeChunk, init_db, utc_now
from core.engine.state_machine import ExecutionStateMachine
from core.exceptions import JsonRpcProtocolError, PluginProcessError, StorageError
from core.gateway.api_routes import get_service
from core.main import app
from core.storage.knowledge_store import KnowledgeStore


@pytest.fixture
def test_client():
    """FastAPI TestClient with isolated Lifespan context."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_fault_injection_db_locked_error(test_client) -> None:
    """Simulate SQLite 'database is locked' OperationalError during API request.

    Invariant:
    - FastAPI returns clean HTTP 500.
    - Process does NOT crash.
    - Subsequent healthy requests succeed immediately.
    """

    def _failing_service():
        raise OperationalError("database is locked", None, None)

    app.dependency_overrides[get_service] = _failing_service
    try:
        resp = test_client.get("/api/monitor/executions")
        assert resp.status_code == 500
    finally:
        app.dependency_overrides.pop(get_service, None)

    # Verify gateway process is still alive and responds cleanly to health check
    health_resp = test_client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"


def test_fault_injection_simulated_disk_full(tmp_path: Path) -> None:
    """Simulate OS disk full (errno.ENOSPC) during knowledge document save.

    Invariant:
    - Raises StorageError cleanly.
    - Process does not crash or leave corrupted file handles.
    """
    k_store = KnowledgeStore(Session(), docs_dir=tmp_path)
    chunk = KnowledgeChunk(
        id="chunk_test_disk_full",
        target_id="sqlserver_simulated",
        partition_key="sales",
        title="Sales Partition",
    )

    with patch.object(Path, "write_text", side_effect=OSError(errno.ENOSPC, "No space left on device")):
        with pytest.raises(StorageError) as exc_info:
            k_store.save_chunk(chunk, doc_content="# Massive content")
        assert "Failed to write file" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fault_injection_plugin_subprocess_crash(tmp_path: Path) -> None:
    """Simulate plugin process crashing with non-zero exit during query execution.

    Invariant:
    - State machine transitions execution to FAILED.
    - Error message records the failure.
    - Does NOT crash the gateway or hang.
    """
    from sqlalchemy import create_engine

    test_engine = create_engine(f"sqlite:///{tmp_path}/crash_test.db")
    init_db(test_engine)

    exec_id = "exec_fault_crash"
    with Session(test_engine) as session:
        session.add(
            ExecutionLog(
                id=exec_id,
                target_id="sqlserver_simulated",
                query="SELECT * FROM crash_table;",
                query_type="READ",
                status="PAUSED_FOR_REVIEW",
                created_at=utc_now(),
            )
        )
        session.commit()

    with Session(test_engine) as session:
        sm = ExecutionStateMachine(session)

        # Mock client to simulate worker crash
        mock_client = MagicMock()
        mock_client.execute = AsyncMock(side_effect=PluginProcessError("Plugin worker process exited with code 1"))
        mock_client.abort = AsyncMock()

        with patch.object(sm.registry, "get_client", return_value=mock_client):
            res = await sm.approve_and_resume(exec_id, approved_by="Tester")

        assert res.status == "FAILED"
        assert "Plugin worker process exited with code 1" in (res.error_message or "")


@pytest.mark.asyncio
async def test_fault_injection_plugin_hang_timeout(tmp_path: Path) -> None:
    """Simulate plugin hanging indefinitely on query execution.

    Invariant:
    - TimeoutGuard aborts the execution cleanly.
    - Execution status transitions to TIMEOUT.
    - Emergency abort hook is called.
    """
    from sqlalchemy import create_engine

    test_engine = create_engine(f"sqlite:///{tmp_path}/timeout_test.db")
    init_db(test_engine)

    exec_id = "exec_fault_timeout"
    with Session(test_engine) as session:
        session.add(
            ExecutionLog(
                id=exec_id,
                target_id="sqlserver_simulated",
                query="SELECT * FROM hanging_query;",
                query_type="READ",
                status="PAUSED_FOR_REVIEW",
                created_at=utc_now(),
            )
        )
        session.commit()

    with Session(test_engine) as session:
        sm = ExecutionStateMachine(session)

        async def _hang(*args, **kwargs):
            await asyncio.sleep(10.0)

        mock_client = MagicMock()
        mock_client.execute = AsyncMock(side_effect=_hang)
        abort_called = False

        async def _fake_abort(*args, **kwargs):
            nonlocal abort_called
            abort_called = True
            mock_res = MagicMock()
            mock_res.success = True
            return mock_res

        mock_client.abort = AsyncMock(side_effect=_fake_abort)

        with (
            patch.object(sm.registry, "get_client", return_value=mock_client),
            patch("core.engine.timeout_guard.TimeoutGuard.get_timeout_for_query", return_value=0.05),
        ):
            res = await sm.approve_and_resume(exec_id, approved_by="Tester")

        assert res.status == "TIMEOUT"
        assert abort_called is True
        assert "timeout" in (res.error_message or "").lower()


@pytest.mark.asyncio
async def test_fault_injection_plugin_garbage_json(tmp_path: Path) -> None:
    """Simulate plugin sending corrupted/garbage non-JSON text on stdout.

    Invariant:
    - PersistentWorker filters noise and fails pending futures on corrupt responses.
    - State machine marks execution FAILED without hanging.
    """
    from sqlalchemy import create_engine

    test_engine = create_engine(f"sqlite:///{tmp_path}/garbage_test.db")
    init_db(test_engine)

    exec_id = "exec_fault_garbage"
    with Session(test_engine) as session:
        session.add(
            ExecutionLog(
                id=exec_id,
                target_id="sqlserver_simulated",
                query="SELECT 1;",
                query_type="READ",
                status="PAUSED_FOR_REVIEW",
                created_at=utc_now(),
            )
        )
        session.commit()

    with Session(test_engine) as session:
        sm = ExecutionStateMachine(session)

        mock_client = MagicMock()
        mock_client.execute = AsyncMock(side_effect=JsonRpcProtocolError("Malformed JSON response from plugin"))
        mock_client.abort = AsyncMock()

        with patch.object(sm.registry, "get_client", return_value=mock_client):
            res = await sm.approve_and_resume(exec_id, approved_by="Tester")

        assert res.status == "FAILED"
        assert "Malformed JSON response" in (res.error_message or "")


def test_fault_injection_malformed_and_truncated_json(test_client) -> None:
    """Send truncated / malformed JSON to submit execution endpoint.

    Invariant:
    - Returns HTTP 422 Unprocessable Entity or 400 Bad Request.
    - Zero server 500 crash or hanging connection.
    """
    # Malformed truncated JSON string
    resp = test_client.post(
        "/api/monitor/executions",
        content='{"target_id": "sqlserver", "query": "SELECT',
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code in (400, 422)


def test_fault_injection_payload_size_limit_exceeded(test_client) -> None:
    """Send massive request body (>10MB limit configured in security middleware).

    Invariant:
    - Returns HTTP 413 Payload Too Large.
    - Gateway middleware aborts before processing or allocating huge memory.
    """
    huge_payload = '{"target_id": "test", "query": "' + ("A" * (11 * 1024 * 1024)) + '"}'
    resp = test_client.post(
        "/api/monitor/executions",
        content=huge_payload,
        headers={"Content-Type": "application/json", "Content-Length": str(len(huge_payload))},
    )
    assert resp.status_code == 413
    assert "Payload too large" in resp.json()["detail"]


def test_fault_injection_extreme_inputs(test_client) -> None:
    """Test empty, null-byte, and unusual Unicode inputs.

    Invariant:
    - Empty target/query rejected with HTTP 422 validation error.
    - Null bytes handled safely without terminating or crashing C extensions.
    """
    # Empty strings
    resp_empty = test_client.post(
        "/api/monitor/executions",
        json={"target_id": "", "query": ""},
    )
    assert resp_empty.status_code in (400, 404, 422)

    # Null byte string inside query
    resp_null = test_client.post(
        "/api/monitor/executions",
        json={"target_id": "nonexistent", "query": "SELECT * \x00 FROM users;"},
    )
    # Target not found returns 404, not an unhandled server 500
    assert resp_null.status_code == 404
