"""Unit tests for JSON-RPC plugin contract models and data schemas."""

from plugins.plugin_contract import (
    ColumnSchema,
    DryRunResult,
    JsonRpcRequest,
    JsonRpcResponse,
    PartitionSchema,
    SyncKnowledgeResult,
    TableSchema,
)


def test_plugin_contract_models():
    """Verify serialization and validation of plugin JSON-RPC models."""
    req = JsonRpcRequest(
        method="dry_run",
        params={"query": "SELECT 1", "rules": []},
        id="req_1",
    )
    assert req.method == "dry_run"

    dry_run_res = DryRunResult(
        is_valid=True,
        violations=[],
        explain_plan={"nodes": 3},
        estimated_time_ms=15.0,
        query_type="READ",
    )
    resp = JsonRpcResponse(result=dry_run_res.model_dump(), id="req_1")
    assert resp.result["is_valid"] is True

    col = ColumnSchema(name="OrderID", data_type="INT", is_primary_key=True)
    tbl = TableSchema(name="Orders", columns=[col])
    part = PartitionSchema(partition_key="Sales", title="Sales", tables=[tbl])
    sync_res = SyncKnowledgeResult(
        partitions=[part],
        target_id="sqlserver_plugin",
        timestamp="2026-10-21T00:00:00Z",
    )
    assert len(sync_res.partitions[0].tables[0].columns) == 1
