"""Unit tests for cursor-based pagination, server-side search, and result size limits."""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from core.config import settings
from core.database import ExecutionLog, PluginProfile, utc_now
from core.engine.state_machine import ExecutionStateMachine
from plugins.plugin_contract import ExecuteResult


def test_cursor_pagination_forward_traversal(api_client: TestClient, db_session: Session) -> None:
    """Verifies cursor pagination traverses all pages without duplicates or missing items."""
    now = utc_now()
    created_ids: list[str] = []

    # Insert 12 logs in chronological order
    for i in range(12):
        exec_id = f"exec_page_{i:02d}"
        created_ids.append(exec_id)
        log = ExecutionLog(
            id=exec_id,
            target_id="sqlserver_prod",
            query=f"SELECT {i};",
            query_type="READ",
            status="COMPLETED",
            created_at=now + timedelta(seconds=i),
        )
        db_session.add(log)
    db_session.commit()

    # Page 1: limit=5
    res1 = api_client.get("/api/executions/page?limit=5")
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1["items"]) == 5
    assert data1["total_count"] >= 12
    assert data1["next_cursor"] is not None

    page1_ids = [item["id"] for item in data1["items"]]
    # Should be newest first (exec_page_11, 10, 09, 08, 07)
    assert page1_ids[0] == "exec_page_11"

    # Page 2: limit=5
    cursor1 = data1["next_cursor"]
    res2 = api_client.get(f"/api/executions/page?limit=5&cursor={cursor1}")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["items"]) == 5
    assert data2["next_cursor"] is not None

    page2_ids = [item["id"] for item in data2["items"]]
    # No overlap between page 1 and page 2
    assert set(page1_ids).isdisjoint(set(page2_ids))
    assert page2_ids[0] == "exec_page_06"

    # Page 3: limit=5 (remaining 2 items)
    cursor2 = data2["next_cursor"]
    res3 = api_client.get(f"/api/executions/page?limit=5&cursor={cursor2}")
    assert res3.status_code == 200
    data3 = res3.json()
    assert len(data3["items"]) == 2
    assert data3["next_cursor"] is None

    page3_ids = [item["id"] for item in data3["items"]]
    assert set(page2_ids).isdisjoint(set(page3_ids))


def test_server_side_search_and_filters(api_client: TestClient, db_session: Session) -> None:
    """Verifies server-side substring search on query/reasoning and target/status filters."""
    log1 = ExecutionLog(
        id="exec_search_alpha",
        target_id="plugin_alpha",
        query="SELECT * FROM sensitive_customer_tokens;",
        reasoning="Identity provider migration check",
        status="COMPLETED",
        created_at=utc_now(),
    )
    log2 = ExecutionLog(
        id="exec_search_beta",
        target_id="plugin_beta",
        query="UPDATE orders SET status = 'Shipped';",
        reasoning="Daily warehouse dispatch job",
        status="FAILED",
        created_at=utc_now(),
    )
    db_session.add(log1)
    db_session.add(log2)
    db_session.commit()

    # Search by query token
    res_q1 = api_client.get("/api/executions/page?q=sensitive_customer")
    assert res_q1.status_code == 200
    items1 = res_q1.json()["items"]
    assert len(items1) == 1
    assert items1[0]["id"] == "exec_search_alpha"

    # Search by reasoning keyword
    res_q2 = api_client.get("/api/executions/page?q=warehouse")
    assert res_q2.status_code == 200
    items2 = res_q2.json()["items"]
    assert len(items2) == 1
    assert items2[0]["id"] == "exec_search_beta"

    # Filter by status
    res_failed = api_client.get("/api/executions/page?status=FAILED")
    assert res_failed.status_code == 200
    for it in res_failed.json()["items"]:
        assert it["status"] == "FAILED"

    # Filter by target
    res_alpha = api_client.get("/api/executions/page?target_id=plugin_alpha")
    assert res_alpha.status_code == 200
    for it in res_alpha.json()["items"]:
        assert it["target_id"] == "plugin_alpha"


@pytest.mark.asyncio
async def test_result_summary_byte_limit_truncation(db_session: Session) -> None:
    """When a plugin returns a payload larger than RESULT_MAX_BYTES, result_summary is truncated."""
    profile = PluginProfile(
        id="target_big_data",
        name="Big Data Target",
        driver="sqlserver",
        entrypoint="mock --serve",
    )
    db_session.add(profile)

    log = ExecutionLog(
        id="exec_big_payload",
        target_id="target_big_data",
        query="SELECT * FROM massive_log_dump;",
        query_type="READ",
        status="EXECUTING",
        created_at=utc_now(),
    )
    db_session.add(log)
    db_session.commit()

    # Generate oversized data payload (> 50,000 bytes)
    oversized_data = [{"row_index": i, "chunk": "A" * 500} for i in range(150)]

    mock_client = AsyncMock()
    mock_client.execute.return_value = ExecuteResult(
        execution_id="exec_big_payload",
        data=oversized_data,
        rows_affected=150,
        execution_time_ms=12.5,
    )

    sm = ExecutionStateMachine(db_session)
    with patch.object(sm.registry, "get_client", return_value=mock_client):
        res = await sm._execute_step(log)

    assert res.status == "COMPLETED"
    assert res.result_summary is not None

    parsed_summary = json.loads(res.result_summary)
    assert parsed_summary.get("truncated") is True
    assert parsed_summary["original_bytes"] > settings.RESULT_MAX_BYTES
    assert len(res.result_summary.encode("utf-8")) < settings.RESULT_MAX_BYTES
