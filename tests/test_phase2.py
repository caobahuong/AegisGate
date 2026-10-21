"""Unit tests for Phase 2: Execution Engine, State Machine, Timeout Guards, REST API Gateway.

Tests GovernanceEngine, TimeoutGuard, ExecutionStateMachine, and REST Endpoints.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from core.database import PluginProfile, Rule, get_session
from core.engine.governance import GovernanceEngine
from core.engine.state_machine import ExecutionStateMachine
from core.engine.timeout_guard import TimeoutGuard
from core.exceptions import ExecutionTimeoutError
from core.main import app
from plugins.plugin_contract import DryRunResult, ExecuteResult, AbortResult


@pytest.fixture(name="db_session")
def fixture_db_session(tmp_path: Path):
    """Isolated test database session."""
    test_db = tmp_path / "test_phase2.db"
    engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


class TestGovernanceEngine:
    """Test governance rule enforcement."""

    def test_forbid_join_detection(self):
        rule = Rule(
            id="rule_no_join_orders_logs",
            name="No Join",
            rule_type="FORBID_JOIN",
            expression="Orders,AuditLogs",
            description="Joining orders and audit logs is too heavy",
            is_active=True,
        )

        # Query that violates rule
        bad_query = "SELECT o.Id, a.Action FROM Orders o INNER JOIN AuditLogs a ON o.Id = a.OrderId"
        violations = GovernanceEngine.inspect_query_and_plan(bad_query, [rule], {})
        assert len(violations) == 1
        assert "rule_no_join_orders_logs" in violations[0]

        # Safe query
        safe_query = "SELECT Id, CustomerName FROM Orders WHERE Status = 'Active'"
        safe_violations = GovernanceEngine.inspect_query_and_plan(safe_query, [rule], {})
        assert len(safe_violations) == 0

    def test_table_scan_detection(self):
        rule = Rule(
            id="rule_no_scan",
            name="No Table Scan",
            rule_type="FORBID_TABLE_SCAN",
            expression="",
            description="Prevent full table scans",
            is_active=True,
        )

        plan_with_scan = {"PhysicalOp": "Table Scan", "EstimateRows": 1000000}
        violations = GovernanceEngine.inspect_query_and_plan(
            "SELECT * FROM Users", [rule], plan_with_scan
        )
        assert len(violations) >= 1

    def test_query_type_determination(self):
        assert GovernanceEngine.determine_query_type("SELECT * FROM Customers") == "READ"
        assert GovernanceEngine.determine_query_type("INSERT INTO Orders (Id) VALUES (1)") == "WRITE"
        assert GovernanceEngine.determine_query_type("UPDATE Orders SET Status = 'Done'") == "WRITE"
        assert GovernanceEngine.determine_query_type("DELETE FROM Orders WHERE Id = 1") == "WRITE"


class TestTimeoutGuard:
    """Test timeout guards and abort triggers."""

    def test_timeout_calculation(self):
        assert TimeoutGuard.get_timeout_for_query("READ") == 15.0
        assert TimeoutGuard.get_timeout_for_query("WRITE") == 30.0
        assert TimeoutGuard.get_timeout_for_query("READ", custom_limit=5.0) == 5.0

    @pytest.mark.asyncio
    async def test_run_with_timeout_success(self):
        async def quick_coro():
            await asyncio.sleep(0.01)
            return "SUCCESS"

        result = await TimeoutGuard.run_with_timeout(quick_coro(), timeout_seconds=1.0)
        assert result == "SUCCESS"

    @pytest.mark.asyncio
    async def test_run_with_timeout_trigger_abort_hook(self):
        abort_called = False

        async def slow_coro():
            await asyncio.sleep(0.5)
            return "DONE"

        async def abort_hook():
            nonlocal abort_called
            abort_called = True

        with pytest.raises(ExecutionTimeoutError):
            await TimeoutGuard.run_with_timeout(
                slow_coro(),
                timeout_seconds=0.05,
                on_timeout_abort=abort_hook,
            )

        assert abort_called is True


class TestExecutionStateMachine:
    """Test State Machine transitions."""

    @pytest.mark.asyncio
    async def test_state_machine_pause_and_resume_flow(self, db_session: Session):
        # Register a mock plugin profile
        plugin = PluginProfile(
            id="test_db_plugin",
            name="Test DB Plugin",
            driver="mock",
            entrypoint="python mock.py",
        )
        db_session.add(plugin)
        db_session.commit()

        sm = ExecutionStateMachine(db_session)

        # Mock plugin client responses
        mock_dry_run = DryRunResult(
            is_valid=True,
            violations=[],
            explain_plan={"nodes": 1},
            estimated_time_ms=5.0,
            query_type="READ",
        )
        mock_execute = ExecuteResult(
            data=[{"id": 1, "name": "Item"}],
            rows_affected=1,
            execution_time_ms=12.0,
            spid=42,
        )

        with patch.object(sm.registry, "get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.dry_run.return_value = mock_dry_run
            mock_client.execute.return_value = mock_execute
            mock_get_client.return_value = mock_client

            # Auto mode is OFF by default -> should pause
            log = await sm.initiate_execution(
                target_id="test_db_plugin",
                query="SELECT * FROM Items WHERE Id = 1",
                reasoning="Fetch item",
            )
            assert log.status == "PAUSED_FOR_REVIEW"
            assert log.auto_approved is False

            # Approve and resume
            resumed_log = await sm.approve_and_resume(log.id, approved_by="SecOps Admin")
            assert resumed_log.status == "COMPLETED"
            assert resumed_log.spid == 42
            assert resumed_log.approved_by == "SecOps Admin"

    @pytest.mark.asyncio
    async def test_state_machine_auto_approval_mode(self, db_session: Session):
        plugin = PluginProfile(
            id="test_auto_plugin",
            name="Test Auto",
            driver="mock",
            entrypoint="python mock.py",
        )
        db_session.add(plugin)
        db_session.commit()

        sm = ExecutionStateMachine(db_session)
        sm.setting_store.set_auto_approval(True)

        mock_dry_run = DryRunResult(
            is_valid=True,
            violations=[],
            explain_plan={"nodes": 1},
            estimated_time_ms=5.0,
            query_type="READ",
        )
        mock_execute = ExecuteResult(
            data=[{"result": 1}],
            rows_affected=1,
            execution_time_ms=8.0,
        )

        with patch.object(sm.registry, "get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.dry_run.return_value = mock_dry_run
            mock_client.execute.return_value = mock_execute
            mock_get_client.return_value = mock_client

            log = await sm.initiate_execution(
                target_id="test_auto_plugin",
                query="SELECT 1",
            )
            # With auto approval, goes straight to COMPLETED
            assert log.status == "COMPLETED"
            assert log.auto_approved is True


class TestRestApiGateway:
    """Test FastAPI REST endpoints."""

    @pytest.fixture(autouse=True)
    def override_db(self, db_session: Session):
        def _get_test_session():
            yield db_session

        app.dependency_overrides[get_session] = _get_test_session
        yield
        app.dependency_overrides.clear()

    def test_health_check(self):
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_plugin_endpoints(self, db_session: Session):
        client = TestClient(app)

        # Register plugin via POST
        reg_payload = {
            "id": "mssql_gateway",
            "name": "MSSQL Gateway",
            "driver": "pyodbc",
            "entrypoint": "python adapter.py",
            "dry_run_command": "SET SHOWPLAN_XML ON",
            "abort_command": "KILL {spid}",
            "config": {"host": "localhost", "database": "Finance"},
        }
        res = client.post("/api/plugins", json=reg_payload)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] == "mssql_gateway"

        # List plugins
        res = client.get("/api/plugins")
        assert res.status_code == 200
        plugins = res.json()
        assert any(p["id"] == "mssql_gateway" for p in plugins)

    def test_rules_endpoints(self, db_session: Session):
        client = TestClient(app)

        rule_payload = {
            "id": "rule_test_api",
            "name": "API Rule Test",
            "target_id": "mssql_gateway",
            "rule_type": "FORBID_JOIN",
            "expression": "Customers,Transactions",
            "description": "Cross join forbidden",
            "severity": "CRITICAL",
            "is_active": True,
        }
        res = client.post("/api/rules", json=rule_payload)
        assert res.status_code == 201
        assert res.json()["id"] == "rule_test_api"

        # List rules
        res = client.get("/api/rules")
        assert res.status_code == 200
        assert len(res.json()) >= 1

        # Delete rule
        res = client.delete("/api/rules/rule_test_api")
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_auto_mode_setting_endpoints(self):
        client = TestClient(app)

        # Get initial
        res = client.get("/api/settings/auto-mode")
        assert res.status_code == 200

        # Set to True
        res = client.post("/api/settings/auto-mode", json={"enabled": True})
        assert res.status_code == 200
        assert res.json()["auto_approval_enabled"] is True

        # Set back to False
        res = client.post("/api/settings/auto-mode", json={"enabled": False})
        assert res.status_code == 200
        assert res.json()["auto_approval_enabled"] is False

