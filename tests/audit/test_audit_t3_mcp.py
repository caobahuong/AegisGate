"""Audit Track T3: MCP Server End-to-End Audit.

Examines:
1. FastMCP tool registrations and signatures (get_catalog, get_knowledge, submit_execution, check_execution_status)
2. Unbound mode vs bound target mode
3. Resilience when backend REST API is offline
4. Error payload structure on FAILED status (Defect D-007)
5. Status polling via check_execution_status
"""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlmodel import Session

from core.database import ExecutionLog, utc_now
from core.gateway import mcp_server
from tests.factories import make_execution_log

pytestmark = [pytest.mark.audit, pytest.mark.e2e]


def test_mcp_get_catalog_unbound_error():
    """Verify get_catalog requires target_id when server is not bound to a plugin."""
    with patch.object(mcp_server, "DEFAULT_TARGET_ID", None):
        res_json = mcp_server.get_catalog(target_id=None)
        res = json.loads(res_json)
        assert "error" in res
        assert "target_id must be provided" in res["error"]


def test_mcp_get_knowledge_unbound_error():
    """Verify get_knowledge requires target_id when server is not bound to a plugin."""
    with patch.object(mcp_server, "DEFAULT_TARGET_ID", None):
        res_json = mcp_server.get_knowledge(target_id=None)
        res = json.loads(res_json)
        assert "error" in res
        assert "target_id must be provided" in res["error"]


@pytest.mark.asyncio
async def test_mcp_submit_execution_api_down():
    """Verify submit_execution returns user-friendly guidance when FastAPI is offline."""
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        res_json = await mcp_server.submit_execution(
            query="SELECT 1",
            target_id="sqlserver_prod",
            reasoning="Testing API offline",
        )
        res = json.loads(res_json)
        assert "error" in res
        assert "AegisGate API is not reachable" in res["error"]


@pytest.mark.asyncio
async def test_mcp_submit_execution_failed_status_omits_error_message():
    """Demonstrate Defect D-007: submit_execution omits error_message on FAILED status."""
    fake_resp = httpx.Response(
        status_code=200,
        json={
            "id": "exec_failed_001",
            "target_id": "sqlserver_prod",
            "query": "SELECT 1",
            "query_type": "READ",
            "status": "FAILED",
            "error_message": "Worker crashed unexpectedly with SIGKILL",
        },
        request=httpx.Request("POST", "http://127.0.0.1:8000/api/monitor/executions"),
    )

    with patch("httpx.AsyncClient.post", return_value=fake_resp):
        res_json = await mcp_server.submit_execution(
            query="SELECT 1",
            target_id="sqlserver_prod",
            reasoning="Testing FAILED status",
        )
        res = json.loads(res_json)

        assert res["status"] == "FAILED"
        # DEFECT D-007: mcp_server:206 only checks REJECTED, TIMEOUT, ABORTED, so error_message is dropped!
        assert "error_message" not in res, "Expected defect behavior: error_message is omitted on FAILED status"


def test_mcp_check_execution_status(db_session: Session):
    """Verify check_execution_status retrieves status and results from log store."""
    # 1. Non-existent ID returns error
    res_json = mcp_server.check_execution_status("non_existent_exec_999")
    res = json.loads(res_json)
    assert "error" in res
    assert "was not found" in res["error"]

    # 2. Existing completed log returns parsed result
    log = ExecutionLog(
        id="mcp_test_exec_01",
        target_id="sqlserver_prod",
        query="SELECT 1;",
        query_type="READ",
        status="COMPLETED",
        reasoning="MCP status test",
        created_at=utc_now(),
        result_summary=json.dumps({"rows": [{"num": 1}]}),
    )
    db_session.add(log)
    db_session.commit()

    with patch.object(mcp_server, "engine", db_session.bind):
        res_json = mcp_server.check_execution_status("mcp_test_exec_01")
        res = json.loads(res_json)
        assert res["execution_id"] == "mcp_test_exec_01"
        assert res["status"] == "COMPLETED"
        assert res["result"] == {"rows": [{"num": 1}]}
