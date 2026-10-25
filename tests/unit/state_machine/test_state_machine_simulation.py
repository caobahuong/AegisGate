"""Unit tests for SQL Server simulated adapter execution, dry run, and abort methods."""

from plugins.plugin_contract import (
    AbortParams,
    DryRunParams,
    ExecuteParams,
    SyncKnowledgeParams,
)
from plugins.sqlserver_plugin.adapter import SqlServerAdapter


class TestSqlServerAdapterDirect:
    """Direct method tests on SqlServerAdapter."""

    def test_sync_knowledge_partitions(self):
        adapter = SqlServerAdapter()
        res = adapter.sync_knowledge(SyncKnowledgeParams())

        assert res.target_id == "sqlserver_prod"
        assert len(res.partitions) == 3

        part_keys = {p.partition_key for p in res.partitions}
        assert "Sales" in part_keys
        assert "Inventory" in part_keys
        assert "Finance" in part_keys

        sales = next(p for p in res.partitions if p.partition_key == "Sales")
        table_names = {t.name for t in sales.tables}
        assert "Orders" in table_names
        assert "OrderItems" in table_names

    def test_dry_run_safe_query(self):
        adapter = SqlServerAdapter()
        res = adapter.dry_run(
            DryRunParams(
                query="SELECT OrderID, TotalAmount FROM Orders WHERE OrderID = 1001",
                rules=[],
            )
        )
        assert res.is_valid is True
        assert len(res.violations) == 0
        assert res.query_type == "READ"
        assert "StatementText" in res.explain_plan

    def test_dry_run_rule_violation_join(self):
        adapter = SqlServerAdapter()
        rules = [
            {
                "rule_type": "FORBID_JOIN",
                "expression": "Orders,AuditLogs",
            }
        ]
        res = adapter.dry_run(
            DryRunParams(
                query="SELECT * FROM Orders o JOIN AuditLogs a ON o.OrderID = a.LogID",
                rules=rules,
            )
        )
        assert res.is_valid is False
        assert len(res.violations) == 1
        assert "ORDERS, AUDITLOGS" in res.violations[0].upper()

    def test_dry_run_rule_violation_table_scan(self):
        adapter = SqlServerAdapter()
        rules = [{"rule_type": "FORBID_TABLE_SCAN", "expression": ""}]
        res = adapter.dry_run(
            DryRunParams(
                query="SELECT * FROM Orders",
                rules=rules,
            )
        )
        assert res.is_valid is False
        assert len(res.violations) == 1
        assert "Table Scan" in res.violations[0]

    def test_execute_and_abort(self):
        adapter = SqlServerAdapter()
        exec_res = adapter.execute(
            ExecuteParams(
                execution_id="exec_test_99",
                query="SELECT * FROM Orders WHERE Status = 'Completed'",
                timeout_seconds=15.0,
            )
        )
        assert exec_res.rows_affected == 3
        assert exec_res.spid is not None
        assert exec_res.execution_time_ms > 0

        # Abort call
        abort_res = adapter.abort(AbortParams(execution_id="exec_test_99"))
        assert abort_res.success is True
