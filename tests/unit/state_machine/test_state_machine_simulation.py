"""Unit tests for SQL Server simulated adapter execution, dry run, and abort methods."""

from plugins.plugin_contract import (
    AbortParams,
    DryRunParams,
    ExecuteParams,
    SyncKnowledgeParams,
)
from plugins.sqlserver_plugin.adapter import SqlServerAdapter


class TestSqlServerAdapterDirect:
    """Test SqlServerAdapter simulated in-memory methods directly."""

    def test_sync_knowledge_partitions(self):
        """Verify simulated schema partitions and tables."""
        adapter = SqlServerAdapter()
        res = adapter.sync_knowledge(SyncKnowledgeParams())

        assert res.target_id == "sqlserver_prod"
        assert len(res.partitions) == 3

        part_keys = [p.partition_key for p in res.partitions]
        assert "Sales" in part_keys
        assert "Audit" in part_keys
        assert "Production" in part_keys

        # Check table schemas
        sales_part = next(p for p in res.partitions if p.partition_key == "Sales")
        tbl_names = [t.name for t in sales_part.tables]
        assert "Orders" in tbl_names
        assert "OrderDetails" in tbl_names

    def test_dry_run_safe_query(self):
        """Verify dry run on safe query."""
        adapter = SqlServerAdapter()
        res = adapter.dry_run(
            DryRunParams(
                query="SELECT OrderID, Amount FROM Orders WHERE OrderID = 101",
                rules=[],
            )
        )
        assert res.is_valid is True
        assert len(res.violations) == 0
        assert res.query_type == "READ"
        assert res.explain_plan is not None

    def test_dry_run_rule_violation_join(self):
        """Verify dry run flags forbidden join violations."""
        adapter = SqlServerAdapter()
        rules = [
            {
                "id": "rule_no_join_orders_audit",
                "rule_type": "FORBID_JOIN",
                "expression": "Orders,AuditLogs",
            }
        ]
        res = adapter.dry_run(
            DryRunParams(
                query="SELECT * FROM Orders o JOIN AuditLogs a ON o.OrderID = a.OrderID",
                rules=rules,
            )
        )
        assert res.is_valid is False
        assert len(res.violations) == 1
        assert "rule_no_join_orders_audit" in res.violations[0]

    def test_dry_run_rule_violation_table_scan(self):
        """Verify dry run flags table scan violations."""
        adapter = SqlServerAdapter()
        rules = [
            {
                "id": "rule_no_scan",
                "rule_type": "FORBID_TABLE_SCAN",
                "expression": "Orders",
            }
        ]
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
        """Verify simulated execution and abort results."""
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
