"""Unit tests for Phase 1: Core Foundation & SQLite Database.

Tests SQLite models, KnowledgeStore, RuleStore, LogStore, Plugin Contract, and Registry.
"""

import json
from pathlib import Path

import pytest
from sqlmodel import Session, SQLModel, create_engine

from core.database import ExecutionLog, KnowledgeChunk, Rule
from core.storage.knowledge_store import KnowledgeStore
from core.storage.log_store import LogStore
from core.storage.rule_store import RuleStore
from core.storage.setting_store import SettingStore


@pytest.fixture(name="db_session")
def fixture_db_session(tmp_path: Path):
    """Create an isolated in-memory or temp SQLite database session for testing."""
    test_db = tmp_path / "test_aegisgate.db"
    engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="docs_dir")
def fixture_docs_dir(tmp_path: Path):
    """Temporary directory for markdown knowledge docs."""
    d = tmp_path / "knowledge_docs"
    d.mkdir(parents=True, exist_ok=True)
    return d


class TestPhase1Foundation:
    """Test suite for Phase 1 Core components."""

    def test_knowledge_store_crud_and_hybrid_markdown(self, db_session: Session, docs_dir: Path):
        store = KnowledgeStore(session=db_session, docs_dir=docs_dir)

        chunk = KnowledgeChunk(
            id="kc_test_sales",
            target_id="sqlserver_test",
            partition_key="Sales",
            title="Sales Partition",
            catalog_json=json.dumps({"tables": ["Orders", "OrderItems"]}),
        )

        saved = store.save_chunk(
            chunk=chunk,
            doc_content="# Sales System Overview\nHandles customer orders.",
            skills_content="# Sales Query Skills\nAlways filter by OrderDate.",
        )
        assert saved.id == "kc_test_sales"

        # Read back chunk
        retrieved = store.get_chunk("kc_test_sales")
        assert retrieved is not None
        assert retrieved["title"] == "Sales Partition"
        assert "customer orders" in retrieved["doc_content"]
        assert "OrderDate" in retrieved["skills_content"]

        # Update doc
        store.update_docs("kc_test_sales", doc_content="# Updated Doc")
        updated = store.get_chunk("kc_test_sales")
        assert updated is not None
        assert updated["doc_content"] == "# Updated Doc"

        # List chunks
        chunks = store.list_chunks("sqlserver_test")
        assert len(chunks) == 1
        assert chunks[0]["id"] == "kc_test_sales"

        # Delete chunk
        assert store.delete_chunk("kc_test_sales") is True
        assert store.get_chunk("kc_test_sales") is None

    def test_knowledge_store_ingest_plugin_catalog(self, db_session: Session, docs_dir: Path):
        store = KnowledgeStore(session=db_session, docs_dir=docs_dir)

        partitions = [
            {
                "partition_key": "Finance",
                "title": "Finance & Invoicing",
                "tables": [{"name": "Invoices", "columns": [{"name": "Id", "data_type": "INT"}]}],
            },
            {
                "partition_key": "Inventory",
                "title": "Warehouse & Stock",
                "tables": [{"name": "StockItems", "columns": [{"name": "Sku", "data_type": "VARCHAR"}]}],
            },
        ]

        chunks = store.ingest_plugin_catalog("sqlserver_prod", partitions)
        assert len(chunks) == 2

        finance_chunk = store.get_chunk("sqlserver_prod_finance")
        assert finance_chunk is not None
        assert finance_chunk["partition_key"] == "Finance"
        assert "Invoices" in str(finance_chunk["catalog"])

    def test_rule_store_crud(self, db_session: Session):
        rule_store = RuleStore(session=db_session)

        rule1 = Rule(
            id="rule_no_cross_join",
            name="Forbid Orders and Logs Join",
            target_id="sqlserver_prod",
            rule_type="FORBID_JOIN",
            expression="Orders,AuditLogs",
            description="Prevent massive cross join",
            severity="CRITICAL",
            is_active=True,
        )
        rule_store.create_rule(rule1)

        # Global rule
        rule_global = Rule(
            id="rule_global_timeout",
            name="Max Timeout Rule",
            target_id=None,
            rule_type="MAX_EXECUTION_TIME",
            expression="30",
            description="Global 30s limit",
            severity="HIGH",
            is_active=True,
        )
        rule_store.create_rule(rule_global)

        # List rules for sqlserver_prod (should return target + global rules)
        rules = rule_store.list_rules("sqlserver_prod", is_active_only=True)
        assert len(rules) == 2
        rule_ids = {r.id for r in rules}
        assert "rule_no_cross_join" in rule_ids
        assert "rule_global_timeout" in rule_ids

        # Update rule
        rule_store.update_rule("rule_no_cross_join", {"severity": "MEDIUM"})
        updated = rule_store.get_rule("rule_no_cross_join")
        assert updated is not None
        assert updated.severity == "MEDIUM"

        # Delete rule
        assert rule_store.delete_rule("rule_no_cross_join") is True
        assert rule_store.get_rule("rule_no_cross_join") is None

    def test_log_store_crud(self, db_session: Session):
        log_store = LogStore(session=db_session)

        log = ExecutionLog(
            id="exec_test_001",
            target_id="sqlserver_prod",
            query="SELECT * FROM Orders WHERE Status = 'Pending'",
            query_type="READ",
            reasoning="AI fetching pending orders for customer review",
            status="DRY_RUN",
        )
        log_store.create_log(log)

        retrieved = log_store.get_log("exec_test_001")
        assert retrieved is not None
        assert retrieved.query_type == "READ"

        # Update status
        log_store.update_log(
            "exec_test_001",
            {
                "status": "COMPLETED",
                "execution_time_ms": 42.5,
                "result_summary": json.dumps({"count": 5}),
            },
        )
        updated = log_store.get_log("exec_test_001")
        assert updated is not None
        assert updated.status == "COMPLETED"
        assert updated.execution_time_ms == 42.5

        # List logs
        all_logs = log_store.list_logs(limit=10, target_id="sqlserver_prod")
        assert len(all_logs) == 1

    def test_setting_store(self, db_session: Session):
        setting_store = SettingStore(session=db_session)
        assert setting_store.is_auto_approval_enabled() is False

        setting_store.set_auto_approval(True)
        assert setting_store.is_auto_approval_enabled() is True

        setting_store.set_auto_approval(False)
        assert setting_store.is_auto_approval_enabled() is False
