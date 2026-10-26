"""Comprehensive tests for AegisGate MCP Server tools and CLI behavior."""

import json
import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlmodel import Session, SQLModel, create_engine

from core.config import settings
from core.database import ExecutionLog, KnowledgeChunk, Rule, utc_now
from core.gateway import mcp_server
from core.storage.knowledge_store import KnowledgeStore


@pytest.fixture(name="mcp_test_engine")
def fixture_mcp_test_engine(tmp_path):
    """Isolated sqlite engine for MCP tests."""
    db_file = tmp_path / "test_mcp.db"
    test_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(test_engine)
    with patch.object(mcp_server, "engine", test_engine), patch.object(settings, "KNOWLEDGE_DOCS_DIR", tmp_path / "docs"):
        yield test_engine


def test_get_catalog_no_target_id():
    """get_catalog should return error when target_id is omitted and no default bound."""
    with patch.object(mcp_server, "DEFAULT_TARGET_ID", None):
        res = json.loads(mcp_server.get_catalog())
        assert "error" in res
        assert "target_id must be provided" in res["error"]


def test_get_catalog_empty_and_populated(mcp_test_engine):
    """get_catalog handles empty partitions and partition filtering."""
    with Session(mcp_test_engine) as session:
        # 1. Empty catalog
        empty_res = json.loads(mcp_server.get_catalog(target_id="test_target"))
        assert empty_res["target_id"] == "test_target"
        assert empty_res["partitions"] == []
        assert "No catalog partitions found" in empty_res["message"]

        # 2. Populate chunks
        chunk1 = KnowledgeChunk(
            id="c_sales",
            target_id="test_target",
            partition_key="Sales",
            title="Sales Partition",
            catalog_json=json.dumps({"tables": ["Orders"]}),
            updated_at=utc_now(),
        )
        chunk2 = KnowledgeChunk(
            id="c_hr",
            target_id="test_target",
            partition_key="HR",
            title="HR Partition",
            catalog_json=json.dumps({"tables": ["Employees"]}),
            updated_at=utc_now(),
        )
        session.add(chunk1)
        session.add(chunk2)
        session.commit()

    # Query all
    all_res = json.loads(mcp_server.get_catalog(target_id="test_target"))
    assert len(all_res) == 2
    assert {c["partition_key"] for c in all_res} == {"Sales", "HR"}

    # Query with partition_key filter (case-insensitive)
    filtered = json.loads(mcp_server.get_catalog(target_id="test_target", partition_key="sales"))
    assert len(filtered) == 1
    assert filtered[0]["partition_key"] == "Sales"
    assert filtered[0]["catalog"] == {"tables": ["Orders"]}


def test_get_knowledge_comprehensive(mcp_test_engine, tmp_path):
    """get_knowledge retrieves hydrated chunks and active rules."""
    # Without target
    with patch.object(mcp_server, "DEFAULT_TARGET_ID", None):
        res = json.loads(mcp_server.get_knowledge())
        assert "target_id must be provided" in res["error"]

    with Session(mcp_test_engine) as session:
        k_store = KnowledgeStore(session, docs_dir=tmp_path / "docs")
        chunk = KnowledgeChunk(
            id="c_fin",
            target_id="test_target",
            partition_key="Finance",
            title="Finance Ledger",
            catalog_json="{}",
            updated_at=utc_now(),
        )
        k_store.save_chunk(
            chunk,
            doc_content="Financial records and invoices.",
            skills_content="Run SELECT against Invoices with index.",
        )
        rule_active = Rule(
            id="rule_1",
            target_id="test_target",
            name="Block Drop Table",
            rule_type="regex_deny",
            expression=r"(?i)\bDROP\s+TABLE\b",
            description="Prevent dropping tables",
            severity="BLOCK",
            is_active=True,
            created_at=utc_now(),
        )
        rule_inactive = Rule(
            id="rule_2",
            target_id="test_target",
            name="Inactive Rule",
            rule_type="regex_deny",
            expression=r"FOO",
            description="Inactive",
            severity="WARN",
            is_active=False,
            created_at=utc_now(),
        )
        session.add(rule_active)
        session.add(rule_inactive)
        session.commit()

    res = json.loads(mcp_server.get_knowledge(target_id="test_target"))
    assert res["target_id"] == "test_target"
    assert len(res["knowledge_chunks"]) == 1
    assert res["knowledge_chunks"][0]["partition_key"] == "Finance"
    assert "Financial records" in res["knowledge_chunks"][0]["documentation"]
    assert "Run SELECT" in res["knowledge_chunks"][0]["skills"]

    # Filter with matching partition_key
    res_filtered = json.loads(mcp_server.get_knowledge(target_id="test_target", partition_key="finance"))
    assert len(res_filtered["knowledge_chunks"]) == 1

    # Filter with non-matching partition_key
    res_none = json.loads(mcp_server.get_knowledge(target_id="test_target", partition_key="nonexistent"))
    assert len(res_none["knowledge_chunks"]) == 0

    # Active rules only
    assert len(res["active_rules"]) == 1
    assert res["active_rules"][0]["id"] == "rule_1"
    assert res["active_rules"][0]["name"] == "Block Drop Table"


def test_check_execution_status_cases(mcp_test_engine):
    """check_execution_status handles missing, completed, json/text results, and errors."""
    # 1. Missing execution
    notFound = json.loads(mcp_server.check_execution_status("missing_exec_id"))
    assert "error" in notFound
    assert "not found" in notFound["error"]

    with Session(mcp_test_engine) as session:
        # 2. Execution with valid json result_summary and execution_time_ms
        log1 = ExecutionLog(
            id="exec_succ_json",
            target_id="target_1",
            status="COMPLETED",
            query="SELECT 1",
            query_type="READ",
            auto_approved=True,
            execution_time_ms=12.4,
            result_summary=json.dumps({"rows": 1, "data": [{"id": 1}]}),
            created_at=utc_now(),
            finished_at=utc_now(),
        )
        # 3. Execution with non-json result_summary and error_message
        log2 = ExecutionLog(
            id="exec_succ_text",
            target_id="target_1",
            status="REJECTED",
            query="DELETE FROM x",
            query_type="WRITE",
            auto_approved=False,
            result_summary="Raw unformatted text output",
            error_message="Policy violation: delete not allowed",
            created_at=utc_now(),
            finished_at=utc_now(),
        )
        session.add(log1)
        session.add(log2)
        session.commit()

    res1 = json.loads(mcp_server.check_execution_status("exec_succ_json"))
    assert res1["execution_id"] == "exec_succ_json"
    assert res1["status"] == "COMPLETED"
    assert res1["execution_time_ms"] == 12.4
    assert isinstance(res1["result"], dict)
    assert res1["result"]["rows"] == 1

    res2 = json.loads(mcp_server.check_execution_status("exec_succ_text"))
    assert res2["execution_id"] == "exec_succ_text"
    assert res2["status"] == "REJECTED"
    assert res2["result"] == "Raw unformatted text output"
    assert res2["error_message"] == "Policy violation: delete not allowed"


@pytest.mark.asyncio
async def test_submit_execution_timeout_and_text_error():
    """submit_execution handles httpx.TimeoutException and non-json http error responses."""
    # 1. TimeoutException
    with patch.object(httpx.AsyncClient, "post", AsyncMock(side_effect=httpx.TimeoutException("timed out"))):
        out_timeout = json.loads(await mcp_server.submit_execution("SELECT 1", target_id="target_1"))
        assert "error" in out_timeout
        assert "timed out" in out_timeout["error"]

    # 2. HTTP 500 with non-json body
    req = httpx.Request("POST", "http://x/api/monitor/executions")
    non_json_resp = httpx.Response(500, text="Internal Server Crash Dump", request=req)
    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=non_json_resp)):
        out_500 = json.loads(await mcp_server.submit_execution("SELECT 1", target_id="target_1"))
        assert "error" in out_500
        assert "Internal Server Crash Dump" in out_500["error"]
        assert "500" in out_500["error"]


@pytest.mark.asyncio
async def test_submit_execution_various_statuses():
    """submit_execution correctly maps explain_plan, auto_approved, timeout and aborted statuses."""
    req = httpx.Request("POST", "http://x/api/monitor/executions")

    body_paused = {
        "id": "e_paused",
        "target_id": "target_1",
        "query": "UPDATE items SET price = 10",
        "query_type": "WRITE",
        "status": "PAUSED_FOR_REVIEW",
        "auto_approved": False,
        "explain_plan": {"cost": 42.0},
    }
    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=httpx.Response(201, json=body_paused, request=req))):
        out = json.loads(await mcp_server.submit_execution("UPDATE items SET price = 10", target_id="target_1"))
        assert out["status"] == "PAUSED_FOR_REVIEW"
        assert out["auto_approved"] is False
        assert out["explain_plan"] == {"cost": 42.0}

    body_abort = {
        "id": "e_abort",
        "target_id": "target_1",
        "query": "SELECT * FROM huge",
        "query_type": "READ",
        "status": "ABORTED",
        "auto_approved": False,
        "error_message": "Execution was aborted by operator",
    }
    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=httpx.Response(201, json=body_abort, request=req))):
        out = json.loads(await mcp_server.submit_execution("SELECT * FROM huge", target_id="target_1"))
        assert out["status"] == "ABORTED"
        assert out["error_message"] == "Execution was aborted by operator"
