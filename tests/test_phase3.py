"""Unit tests for Phase 3: SQL Server Plugin with JSON-RPC over Stdio.

Tests SqlServerAdapter direct methods and end-to-end Subprocess IPC communication.
"""

from pathlib import Path
import pytest
from sqlmodel import Session, SQLModel, create_engine
from core.database import PluginProfile
from core.engine.plugin_client import PluginSubprocessClient
from core.engine.plugin_registry import PluginRegistry
from core.storage.knowledge_store import KnowledgeStore
from plugins.plugin_contract import (
    AbortParams,
    DryRunParams,
    ExecuteParams,
    SyncKnowledgeParams,
)
from plugins.sqlserver_plugin.adapter import SqlServerAdapter


@pytest.fixture(name="db_session")
def fixture_db_session(tmp_path: Path):
    """Isolated database session for integration testing."""
    test_db = tmp_path / "test_phase3.db"
    engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


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


class TestSqlServerSubprocessIPC:
    """End-to-End JSON-RPC Subprocess communication tests."""

    @pytest.mark.asyncio
    async def test_subprocess_sync_knowledge(self):
        client = PluginSubprocessClient(entrypoint_cmd="python plugins/sqlserver_plugin/adapter.py")
        res = await client.sync_knowledge(SyncKnowledgeParams())

        assert res.target_id == "sqlserver_prod"
        assert len(res.partitions) == 3

    @pytest.mark.asyncio
    async def test_subprocess_dry_run(self):
        client = PluginSubprocessClient(entrypoint_cmd="python plugins/sqlserver_plugin/adapter.py")
        res = await client.dry_run(
            DryRunParams(
                query="SELECT OrderID FROM Orders WHERE OrderID = 5",
                rules=[],
            )
        )
        assert res.is_valid is True
        assert res.query_type == "READ"

    @pytest.mark.asyncio
    async def test_subprocess_execute(self):
        client = PluginSubprocessClient(entrypoint_cmd="python plugins/sqlserver_plugin/adapter.py")
        res = await client.execute(
            ExecuteParams(
                execution_id="exec_ipc_01",
                query="SELECT * FROM Orders WHERE OrderID = 1001",
                timeout_seconds=10.0,
            )
        )
        assert res.rows_affected == 3
        assert res.spid is not None

    @pytest.mark.asyncio
    async def test_subprocess_abort(self):
        client = PluginSubprocessClient(entrypoint_cmd="python plugins/sqlserver_plugin/adapter.py")
        res = await client.abort(AbortParams(execution_id="exec_ipc_01"))
        assert res.success is True

    def test_manifest_discovery_and_catalog_ingest(self, db_session: Session, tmp_path: Path):
        registry = PluginRegistry(session=db_session)
        loaded = registry.scan_and_load_manifests()
        assert len(loaded) >= 1

        sql_plugin = next((p for p in loaded if p.id == "sqlserver_prod"), None)
        assert sql_plugin is not None
        assert sql_plugin.driver == "pyodbc/mssql"
        assert sql_plugin.dry_run_command == "SET SHOWPLAN_XML ON"
