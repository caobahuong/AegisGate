"""MCP submit_execution must delegate to the API process (so SSE reaches the dashboard)."""

import json
from unittest.mock import AsyncMock, patch

import httpx

from core.gateway import mcp_server

REQ = httpx.Request("POST", "http://x/api/monitor/executions")


def _resp(status: int, body: dict) -> httpx.Response:
    return httpx.Response(status, json=body, request=REQ)


async def test_submit_delegates_to_rest_and_maps_response() -> None:
    body = {
        "id": "exec_1",
        "target_id": "t1",
        "query": "SELECT 1",
        "query_type": "READ",
        "status": "COMPLETED",
        "auto_approved": True,
        "violations": [],
        "explain_plan": {"a": 1},
        "result_summary": {"data": [{"x": 1}], "rows_affected": 1},
        "execution_time_ms": 2.5,
    }
    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=_resp(201, body))) as post:
        out = json.loads(await mcp_server.submit_execution("SELECT 1", target_id="t1", reasoning="r"))
    assert post.call_args.args[0].endswith("/api/monitor/executions")
    assert post.call_args.kwargs["json"] == {"target_id": "t1", "query": "SELECT 1", "reasoning": "r"}
    assert out["execution_id"] == "exec_1" and out["result"]["rows_affected"] == 1
    assert out["status"] == "COMPLETED" and "error" not in out


async def test_rejected_includes_violations_and_message() -> None:
    body = {
        "id": "e2",
        "target_id": "t1",
        "query": "q",
        "query_type": "READ",
        "status": "REJECTED",
        "violations": ["Rule Violation [r]: x"],
        "error_message": "Rule Violation [r]: x",
    }
    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=_resp(201, body))):
        out = json.loads(await mcp_server.submit_execution("q", target_id="t1"))
    assert out["violations"] == ["Rule Violation [r]: x"] and out["error_message"]


async def test_api_down_gives_actionable_error() -> None:
    with patch.object(httpx.AsyncClient, "post", AsyncMock(side_effect=httpx.ConnectError("refused"))):
        out = json.loads(await mcp_server.submit_execution("q", target_id="t1"))
    assert "not reachable" in out["error"] and "uvicorn" in out["error"]


async def test_http_error_detail_is_surfaced() -> None:
    with patch.object(
        httpx.AsyncClient, "post", AsyncMock(return_value=_resp(404, {"detail": "Plugin 'zz' not found"}))
    ):
        out = json.loads(await mcp_server.submit_execution("q", target_id="zz"))
    assert "404" in out["error"] and "zz" in out["error"]


async def test_missing_target_is_rejected_locally() -> None:
    with patch.object(mcp_server, "DEFAULT_TARGET_ID", None):
        out = json.loads(await mcp_server.submit_execution("q"))
    assert "target_id must be provided" in out["error"]
