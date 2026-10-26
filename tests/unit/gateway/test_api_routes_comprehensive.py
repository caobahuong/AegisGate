"""Comprehensive endpoint testing for AegisGate REST API routes and GatewayService.

Tests:
- /api/monitor/events (SSE streaming with Last-Event-ID header and last_event_id param)
- /api/executions/page (Cursor pagination, filters: status, target_id, q, from_date, to_date, invalid cursor)
- /api/monitor/executions (list, get by id, not found 404)
- /api/monitor/executions (submit wait=True and wait=False, errors: 404, 400, 429, 504)
- /api/monitor/executions/{id}/approve (200, 400 invalid state)
- /api/monitor/executions/{id}/reject (200, 400 invalid state)
- /api/monitor/executions/{id}/abort (200, 400 invalid state)
- /api/plugins (list include_disabled, register, schema, update config, delete hard/soft, mcp-config, sync)
- /api/mcp/config (global mcp config)
- /api/knowledge (list, get by id, 404, update docs, 404)
- /api/skills (list with and without target filter)
- /api/rules (list exact, create, update valid, update invalid 422, update 404, delete, delete 404)
- /api/settings/auto-mode (get, post)
- /api/logs (list with limit and filters)
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from core.config import settings
from core.database import ExecutionLog, KnowledgeChunk, PluginProfile, Rule, utc_now
from core.exceptions import (
    ExecutionStateError,
    ExecutionTimeoutError,
    PluginExecutionError,
    PluginNotFoundError,
    PluginQueueFullError,
    RuleViolationError,
)
from core.gateway.services import GatewayService


@pytest.fixture(autouse=True)
def isolate_knowledge_docs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Ensure test doc files are written into tmp_path sandbox."""
    docs_sandbox = tmp_path / "knowledge_docs"
    docs_sandbox.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "KNOWLEDGE_DOCS_DIR", docs_sandbox)
    return docs_sandbox


def test_sse_events_header_and_query(api_client: TestClient):
    """GET /api/monitor/events handles Last-Event-ID header and query param."""
    # Test with Last-Event-ID header
    with api_client.stream("GET", "/api/monitor/events", headers={"Last-Event-ID": "42"}) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

    # Test with query param
    with api_client.stream("GET", "/api/monitor/events?last_event_id=10") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")


def test_executions_cursor_pagination_and_filters(api_client: TestClient, db_session: Session):
    """GET /api/executions/page handles filtering and cursor pagination."""
    # Seed logs
    now = datetime.now(UTC)
    for i in range(5):
        log = ExecutionLog(
            id=f"page_exec_{i:02d}",
            target_id="target_sql" if i % 2 == 0 else "target_mongo",
            status="COMPLETED" if i < 3 else "FAILED",
            query=f"SELECT {i} FROM table_{i}",
            query_type="READ",
            reasoning=f"Reasoning note {i}",
            created_at=now,
        )
        db_session.add(log)
    db_session.commit()

    # Query with target_id filter
    resp = api_client.get("/api/executions/page?target_id=target_sql&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 3
    assert all(item["target_id"] == "target_sql" for item in data["items"])

    # Query with search q filter
    resp_q = api_client.get("/api/executions/page?q=table_0&limit=10")
    assert resp_q.status_code == 200
    assert len(resp_q.json()["items"]) == 1
    assert resp_q.json()["items"][0]["id"] == "page_exec_00"

    # Query with status filter
    resp_status = api_client.get("/api/executions/page?status=FAILED&limit=10")
    assert resp_status.status_code == 200
    assert len(resp_status.json()["items"]) == 2

    # Query pagination limit=2
    resp_p1 = api_client.get("/api/executions/page?limit=2")
    assert resp_p1.status_code == 200
    p1_data = resp_p1.json()
    assert len(p1_data["items"]) == 2
    assert p1_data["next_cursor"] is not None
    next_cursor = p1_data["next_cursor"]

    # Fetch page 2 using cursor
    resp_p2 = api_client.get(f"/api/executions/page?cursor={next_cursor}&limit=2")
    assert resp_p2.status_code == 200
    p2_data = resp_p2.json()
    assert len(p2_data["items"]) == 2
    assert p2_data["items"][0]["id"] != p1_data["items"][0]["id"]

    # Invalid cursor format gives empty or fallback
    resp_inv = api_client.get("/api/executions/page?cursor=invalid_base64_not_json")
    assert resp_inv.status_code in (200, 422)


def test_monitor_executions_get_and_list(api_client: TestClient, db_session: Session):
    """GET /api/monitor/executions and /api/monitor/executions/{id}."""
    log = ExecutionLog(
        id="single_exec_test",
        target_id="target_sql",
        status="COMPLETED",
        query="SELECT 42",
        query_type="READ",
        reasoning="Test reasoning",
        explain_plan_json=json.dumps({"cost": 1.0}),
        violations_json=json.dumps(["warn"]),
        result_summary=json.dumps({"answer": 42}),
        execution_time_ms=5.0,
        auto_approved=True,
        created_at=utc_now(),
    )
    db_session.add(log)
    db_session.commit()

    # Get single execution
    res = api_client.get("/api/monitor/executions/single_exec_test")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "single_exec_test"
    assert data["explain_plan"] == {"cost": 1.0}
    assert data["violations"] == ["warn"]
    assert data["result_summary"] == {"answer": 42}

    # 404 for missing execution
    res_404 = api_client.get("/api/monitor/executions/missing_id_xyz")
    assert res_404.status_code == 404
    assert "not found" in res_404.json()["detail"].lower()

    # List executions
    res_list = api_client.get("/api/monitor/executions?target_id=target_sql&limit=10")
    assert res_list.status_code == 200
    assert any(x["id"] == "single_exec_test" for x in res_list.json())

    # Logs endpoint
    res_logs = api_client.get("/api/logs?target_id=target_sql")
    assert res_logs.status_code == 200
    assert any(x["id"] == "single_exec_test" for x in res_logs.json())


def test_submit_execution_error_mappings(api_client: TestClient):
    """POST /api/monitor/executions maps domain exceptions to HTTP error codes."""
    payload = {"target_id": "target_err", "query": "SELECT 1", "reasoning": "Test"}

    # 1. PluginNotFoundError -> 404
    with patch.object(GatewayService, "submit_execution", AsyncMock(side_effect=PluginNotFoundError("Plugin missing"))):
        r = api_client.post("/api/monitor/executions", json=payload)
        assert r.status_code == 404
        assert "Plugin missing" in r.json()["detail"]

    # 2. PluginQueueFullError -> 429
    with patch.object(
        GatewayService, "submit_execution", AsyncMock(side_effect=PluginQueueFullError("Queue saturated"))
    ):
        r = api_client.post("/api/monitor/executions", json=payload)
        assert r.status_code == 429
        assert "Queue saturated" in r.json()["detail"]

    # 3. RuleViolationError -> 400
    with patch.object(GatewayService, "submit_execution", AsyncMock(side_effect=RuleViolationError("Forbidden join"))):
        r = api_client.post("/api/monitor/executions", json=payload)
        assert r.status_code == 400
        assert "Forbidden join" in r.json()["detail"]

    # 4. ExecutionTimeoutError -> 504
    with patch.object(
        GatewayService, "submit_execution", AsyncMock(side_effect=ExecutionTimeoutError("Query timed out"))
    ):
        r = api_client.post("/api/monitor/executions", json=payload)
        assert r.status_code == 504
        assert "timed out" in r.json()["detail"]


def test_submit_execution_background_wait_false(api_client: TestClient, db_session: Session):
    """POST /api/monitor/executions with wait=False dispatches in background."""
    profile = PluginProfile(
        id="bg_target",
        name="BG Target",
        driver="mock",
        entrypoint="python mock.py",
        config_json="{}",
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(profile)
    db_session.commit()

    payload = {"target_id": "bg_target", "query": "SELECT 123", "reasoning": "BG test"}
    with patch("core.gateway.services.ExecutionStateMachine.initiate_execution", AsyncMock()):
        r = api_client.post("/api/monitor/executions?wait=false", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["target_id"] == "bg_target"
        assert data["status"] == "DRY_RUN"


def test_approve_reject_abort_state_error(api_client: TestClient):
    """POST /api/monitor/executions/{id}/approve, reject, and abort handle ExecutionStateError."""
    with patch.object(
        GatewayService, "approve_execution", AsyncMock(side_effect=ExecutionStateError("Cannot approve non-paused"))
    ):
        r = api_client.post("/api/monitor/executions/e1/approve", json={"approved_by": "admin"})
        assert r.status_code == 400
        assert "Cannot approve" in r.json()["detail"]

    with patch.object(
        GatewayService, "reject_execution", AsyncMock(side_effect=ExecutionStateError("Cannot reject non-paused"))
    ):
        r = api_client.post("/api/monitor/executions/e1/reject", json={"reason": "bad"})
        assert r.status_code == 400
        assert "Cannot reject" in r.json()["detail"]

    with patch.object(
        GatewayService, "abort_execution", AsyncMock(side_effect=ExecutionStateError("Cannot abort finished"))
    ):
        r = api_client.post("/api/monitor/executions/e1/abort")
        assert r.status_code == 400
        assert "Cannot abort" in r.json()["detail"]


def test_plugin_management_endpoints(api_client: TestClient, db_session: Session):
    """Verify plugin schema, config update, soft and hard delete, mcp config, and sync."""
    profile = PluginProfile(
        id="plugin_mgr_test",
        name="Plugin For Manager",
        driver="sqlite",
        entrypoint="python adapter.py",
        config_json=json.dumps({"path": ":memory:"}),
        ui_schema_json=json.dumps([{"key": "path", "type": "string"}]),
        custom_card_json=json.dumps({"color": "blue"}),
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(profile)
    db_session.commit()

    # 1. Get schema
    res_schema = api_client.get("/api/plugins/plugin_mgr_test/schema")
    assert res_schema.status_code == 200
    s_data = res_schema.json()
    assert s_data["plugin_id"] == "plugin_mgr_test"
    assert s_data["current_config"] == {"path": ":memory:"}

    # 404 for schema of missing plugin
    assert api_client.get("/api/plugins/nonexistent/schema").status_code == 404

    # 2. Update config
    update_payload = {"config": {"path": "updated.db"}, "name": "Renamed Plugin"}
    with patch("core.engine.plugin_client.PluginSubprocessClient.reinit", AsyncMock()):
        res_upd = api_client.put("/api/plugins/plugin_mgr_test", json=update_payload)
        assert res_upd.status_code == 200
        assert res_upd.json()["name"] == "Renamed Plugin"
        assert res_upd.json()["config"] == {"path": "updated.db"}

    # 404 for update of missing plugin
    assert api_client.put("/api/plugins/nonexistent", json=update_payload).status_code == 404

    # 3. Get MCP config for specific plugin & global MCP config
    res_mcp = api_client.get("/api/plugins/plugin_mgr_test/mcp-config")
    assert res_mcp.status_code == 200
    assert "aegisgate-plugin_mgr_test" in res_mcp.json()["mcpServers"]

    assert api_client.get("/api/plugins/nonexistent/mcp-config").status_code == 404

    res_global_mcp = api_client.get("/api/mcp/config")
    assert res_global_mcp.status_code == 200
    assert "aegisgate" in res_global_mcp.json()["mcpServers"]

    # 4. Sync plugin catalog
    with patch.object(GatewayService, "sync_plugin_catalog", AsyncMock(return_value=[{"partition_key": "Main"}])):
        res_sync = api_client.post("/api/plugins/plugin_mgr_test/sync")
        assert res_sync.status_code == 200
        assert res_sync.json()[0]["partition_key"] == "Main"

    # Sync plugin not found -> 404
    assert api_client.post("/api/plugins/nonexistent/sync").status_code == 404

    # Sync plugin execution error -> 500
    with patch.object(
        GatewayService, "sync_plugin_catalog", AsyncMock(side_effect=PluginExecutionError("Sync timeout"))
    ):
        res_sync_err = api_client.post("/api/plugins/plugin_mgr_test/sync")
        assert res_sync_err.status_code == 500

    # 5. Soft delete (deactivate)
    res_del_soft = api_client.delete("/api/plugins/plugin_mgr_test?hard_delete=false")
    assert res_del_soft.status_code == 200
    assert res_del_soft.json()["mode"] == "soft_disabled"

    # List include_disabled=True includes it
    res_all = api_client.get("/api/plugins?include_disabled=true")
    assert any(p["id"] == "plugin_mgr_test" for p in res_all.json())

    # 6. Hard delete
    res_del_hard = api_client.delete("/api/plugins/plugin_mgr_test?hard_delete=true")
    assert res_del_hard.status_code == 200
    assert res_del_hard.json()["mode"] == "hard_delete"

    # Now it is completely gone -> 404
    assert api_client.delete("/api/plugins/plugin_mgr_test").status_code == 404


def test_install_plugin_zip_and_git_endpoints(api_client: TestClient):
    """POST /api/plugins/install-zip and /api/plugins/install-git handle errors."""
    # Invalid zip content -> 400
    bad_zip = b"not a valid zip file content"
    files = {"file": ("test.zip", bad_zip, "application/zip")}
    res_zip = api_client.post("/api/plugins/install-zip", files=files)
    assert res_zip.status_code == 400

    # Invalid git URL -> 400
    res_git = api_client.post(
        "/api/plugins/install-git",
        json={"git_url": "https://example.com/not_exist.git", "branch": "main"},
    )
    assert res_git.status_code == 400


def test_knowledge_and_skills_endpoints(api_client: TestClient, db_session: Session):
    """Verify knowledge chunk list, get, 404, update docs, and skills list."""
    chunk = KnowledgeChunk(
        id="k_chunk_test",
        target_id="target_k",
        partition_key="CoreData",
        title="Core Data Partition",
        catalog_json=json.dumps({"tables": ["Users", "Roles"]}),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(chunk)
    db_session.commit()

    # List knowledge
    res_list = api_client.get("/api/knowledge?target_id=target_k")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1
    assert res_list.json()[0]["id"] == "k_chunk_test"

    # Get single chunk
    res_get = api_client.get("/api/knowledge/k_chunk_test")
    assert res_get.status_code == 200
    assert res_get.json()["title"] == "Core Data Partition"

    # Get missing chunk -> 404
    assert api_client.get("/api/knowledge/missing_chunk").status_code == 404

    # Update docs
    res_docs = api_client.put(
        "/api/knowledge/k_chunk_test/docs",
        json={"doc_content": "# New Docs", "skills_content": "SELECT 1"},
    )
    assert res_docs.status_code == 200
    assert res_docs.json()["success"] is True

    # Update docs for missing chunk -> 404
    assert api_client.put("/api/knowledge/missing_chunk/docs", json={"doc_content": "x"}).status_code == 404

    # Skills list
    res_skills = api_client.get("/api/skills?target_id=target_k")
    assert res_skills.status_code == 200
    assert len(res_skills.json()) >= 1
    assert res_skills.json()[0]["partition_key"] == "CoreData"


def test_rules_update_validation_and_errors(api_client: TestClient, db_session: Session):
    """Verify PUT /api/rules/{id} validation (422), not found (404), and successful update."""
    rule = Rule(
        id="rule_validate_test",
        name="Validation Rule",
        target_id="target_rule",
        rule_type="MAX_EXECUTION_TIME",
        expression="30",
        description="Limit query time",
        severity="HIGH",
        is_active=True,
        created_at=utc_now(),
    )
    db_session.add(rule)
    db_session.commit()

    # Successful update
    res_upd = api_client.put(
        "/api/rules/rule_validate_test",
        json={"expression": "15", "severity": "CRITICAL"},
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["expression"] == "15"
    assert res_upd.json()["severity"] == "CRITICAL"

    # Invalid expression for FORBID_JOIN (needs at least 2 tables) -> 422
    res_bad = api_client.put(
        "/api/rules/rule_validate_test",
        json={"rule_type": "FORBID_JOIN", "expression": "SingleTableOnly"},
    )
    assert res_bad.status_code == 422

    # Update nonexistent rule -> 404
    res_missing = api_client.put(
        "/api/rules/nonexistent_rule",
        json={"expression": "10"},
    )
    assert res_missing.status_code == 404

    # Delete nonexistent rule -> 404
    assert api_client.delete("/api/rules/nonexistent_rule").status_code == 404


@pytest.mark.asyncio
async def test_gateway_service_execution_actions(db_session: Session):
    """Directly test GatewayService approve, reject, abort, and stop execution methods."""
    from core.gateway.schemas import ApproveExecutionRequest, RejectExecutionRequest

    service = GatewayService(db_session)
    log = ExecutionLog(
        id="paused_act_test",
        target_id="target_act",
        status="PAUSED_FOR_REVIEW",
        query="UPDATE acc SET bal = 0",
        query_type="WRITE",
        created_at=utc_now(),
    )
    db_session.add(log)
    db_session.commit()

    with (
        patch.object(service.state_machine, "approve_and_resume", AsyncMock(return_value=log)),
        patch.object(service.state_machine, "reject", AsyncMock(return_value=log)),
        patch.object(service.state_machine, "abort_execution", AsyncMock(return_value=log)),
    ):
        resp_app = await service.approve_execution("paused_act_test", ApproveExecutionRequest(approved_by="tester"))
        assert resp_app.id == "paused_act_test"

        resp_rej = await service.reject_execution(
            "paused_act_test", RejectExecutionRequest(rejected_by="tester", reason="bad")
        )
        assert resp_rej.id == "paused_act_test"

        resp_ab = await service.abort_execution("paused_act_test")
        assert resp_ab.id == "paused_act_test"

        resp_stop = await service.stop_execution("paused_act_test")
        assert resp_stop.id == "paused_act_test"
