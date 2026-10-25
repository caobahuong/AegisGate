"""Unit tests for Dynamic Plugin UI, Manifest Schemas, and Plugin Edit Endpoints."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from core.database import PluginProfile, get_session
from core.engine.plugin_registry import PluginRegistry
from core.main import app


@pytest.fixture(name="db_session")
def fixture_db_session(tmp_path: Path):
    """Isolated test database session."""
    test_db = tmp_path / "test_dynamic_ui.db"
    engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_get_plugin_schema_endpoint(db_session: Session):
    """Test GET /api/plugins/{plugin_id}/schema returns ui_schema and current_config."""
    ui_schema = [
        {"key": "server", "label": "Host", "type": "text", "default": "localhost", "required": True},
        {"key": "port", "label": "Port", "type": "number", "default": 1433, "required": True},
    ]
    custom_card = {
        "type": "sqlserver_spid",
        "title": "Active SPID & Pool",
        "columns": ["SPID", "Status"],
    }
    profile = PluginProfile(
        id="sqlserver_test",
        name="SQL Server Test",
        driver="pyodbc/mssql",
        entrypoint="python plugins/sqlserver_plugin/adapter.py",
        config_json=json.dumps({"server": "10.0.0.1", "port": 1433}),
        ui_schema_json=json.dumps(ui_schema),
        custom_card_json=json.dumps(custom_card),
    )
    db_session.add(profile)
    db_session.commit()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    # 1. Fetch valid plugin schema
    res = client.get("/api/plugins/sqlserver_test/schema")
    assert res.status_code == 200
    data = res.json()
    assert data["plugin_id"] == "sqlserver_test"
    assert len(data["ui_schema"]) == 2
    assert data["ui_schema"][0]["key"] == "server"
    assert data["current_config"]["server"] == "10.0.0.1"
    assert data["custom_card"]["type"] == "sqlserver_spid"

    # 2. Fetch non-existent plugin schema
    res_404 = client.get("/api/plugins/non_existent/schema")
    assert res_404.status_code == 404

    app.dependency_overrides.clear()


def test_put_plugin_config_endpoint(db_session: Session):
    """Test PUT /api/plugins/{plugin_id} updates config_json and returns updated profile."""
    profile = PluginProfile(
        id="sqlserver_test2",
        name="SQL Server Test 2",
        driver="pyodbc/mssql",
        entrypoint="python plugins/sqlserver_plugin/adapter.py",
        config_json=json.dumps({"server": "localhost", "database": "OldDB"}),
        ui_schema_json=json.dumps([{"key": "database", "label": "DB", "type": "text"}]),
    )
    db_session.add(profile)
    db_session.commit()

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)

    # 1. Update configuration
    updated_payload = {
        "name": "SQL Server Enterprise Production",
        "config": {
            "server": "192.168.1.50",
            "port": 1433,
            "database": "ProductionDB_V2",
            "username": "sa_admin",
        },
    }
    res = client.put("/api/plugins/sqlserver_test2", json=updated_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "SQL Server Enterprise Production"
    assert data["config"]["server"] == "192.168.1.50"
    assert data["config"]["database"] == "ProductionDB_V2"

    # Verify persisted in database
    db_session.refresh(profile)
    persisted = json.loads(profile.config_json)
    assert persisted["database"] == "ProductionDB_V2"
    assert persisted["server"] == "192.168.1.50"

    # 2. Update non-existent plugin returns 404
    res_404 = client.put("/api/plugins/unknown_plugin", json={"config": {"test": 123}})
    assert res_404.status_code == 404

    app.dependency_overrides.clear()


def test_manifest_scanning_with_dynamic_ui_and_multiple_plugins(db_session: Session):
    """Test scan_and_load_manifests loads ui_schema and custom_card for SQL Server and MongoDB."""
    registry = PluginRegistry(db_session)
    loaded = registry.scan_and_load_manifests()

    plugin_ids = [p.id for p in loaded]
    assert "sqlserver_prod" in plugin_ids
    assert "mongodb_prod" in plugin_ids

    # Verify SQL Server profile
    sql_prof = registry.get_profile("sqlserver_prod")
    sql_schema = json.loads(sql_prof.ui_schema_json)
    assert len(sql_schema) >= 5
    assert any(f["key"] == "server" for f in sql_schema)
    assert any(f["key"] == "password" for f in sql_schema)
    sql_card = json.loads(sql_prof.custom_card_json)
    assert sql_card.get("type") == "sqlserver_spid"

    # Verify MongoDB profile
    mongo_prof = registry.get_profile("mongodb_prod")
    mongo_schema = json.loads(mongo_prof.ui_schema_json)
    assert len(mongo_schema) >= 3
    assert any(f["key"] == "connection_uri" for f in mongo_schema)
    mongo_card = json.loads(mongo_prof.custom_card_json)
    assert mongo_card.get("type") == "mongodb_opid"


def test_plugin_uninstall_soft_disable_and_hard_delete(db_session: Session):
    """Test DELETE /api/plugins/{plugin_id} with soft disable and hard delete modes."""
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    # 1. Setup active test plugin
    profile = PluginProfile(
        id="uninstall_target_test",
        name="Target To Delete",
        driver="pyodbc/mssql",
        entrypoint="python plugins/sqlserver_plugin/adapter.py",
        config_json=json.dumps({"server": "localhost", "database": "TempDB"}),
        status="active",
    )
    db_session.add(profile)
    db_session.commit()

    # 2. Test Soft Delete (Default: status="disabled")
    del_res = client.delete("/api/plugins/uninstall_target_test")
    assert del_res.status_code == 200
    res_data = del_res.json()
    assert res_data["success"] is True
    assert res_data["mode"] == "soft_disabled"
    assert res_data["plugin_id"] == "uninstall_target_test"

    # Verify status in DB is disabled
    db_session.refresh(profile)
    assert profile.status == "disabled"

    # Verify list_plugins excludes disabled plugins by default
    list_res = client.get("/api/plugins")
    assert list_res.status_code == 200
    active_ids = [p["id"] for p in list_res.json()]
    assert "uninstall_target_test" not in active_ids

    # Verify include_disabled=True includes it
    list_all_res = client.get("/api/plugins?include_disabled=true")
    assert "uninstall_target_test" in [p["id"] for p in list_all_res.json()]

    # 3. Test Hard Delete (hard_delete=true)
    hard_del_res = client.delete("/api/plugins/uninstall_target_test?hard_delete=true")
    assert hard_del_res.status_code == 200
    assert hard_del_res.json()["mode"] == "hard_delete"

    # Verify profile completely removed from DB
    from sqlmodel import select

    check = db_session.exec(select(PluginProfile).where(PluginProfile.id == "uninstall_target_test")).first()
    assert check is None

    # 4. Deleting non-existent plugin returns 404
    del_404 = client.delete("/api/plugins/non_existent_plugin")
    assert del_404.status_code == 404

    app.dependency_overrides.clear()


def test_mcp_config_endpoints(db_session: Session):
    """Test GET /api/mcp/config and GET /api/plugins/{plugin_id}/mcp-config."""
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    # 1. Setup test plugin
    profile = PluginProfile(
        id="mcp_test_target",
        name="MCP Test Target",
        driver="pyodbc/mssql",
        entrypoint="python plugins/sqlserver_plugin/adapter.py",
        config_json=json.dumps({"server": "localhost", "database": "MCPDB"}),
        status="active",
    )
    db_session.add(profile)
    db_session.commit()

    # 2. Test global MCP config
    global_res = client.get("/api/mcp/config")
    assert global_res.status_code == 200
    global_data = global_res.json()
    assert "mcpServers" in global_data
    assert "aegisgate" in global_data["mcpServers"]
    assert "aegisgate-mcp_test_target" in global_data["mcpServers"]
    assert global_data["mcpServers"]["aegisgate"]["command"] == "python"

    # 3. Test plugin-specific MCP config
    plugin_res = client.get("/api/plugins/mcp_test_target/mcp-config")
    assert plugin_res.status_code == 200
    plugin_data = plugin_res.json()
    assert plugin_data["plugin_id"] == "mcp_test_target"
    assert "aegisgate-mcp_test_target" in plugin_data["mcpServers"]
    target_server = plugin_data["mcpServers"]["aegisgate-mcp_test_target"]
    assert target_server["command"] == "python"
    assert target_server["args"] == ["-m", "core.gateway.mcp_server", "--plugin", "mcp_test_target"]
    assert "AEGISGATE_API_URL" in target_server["env"]

    # 4. Non-existent plugin returns 404
    not_found_res = client.get("/api/plugins/non_existent/mcp-config")
    assert not_found_res.status_code == 404

    app.dependency_overrides.clear()


def test_rules_and_skills_target_scoping(db_session: Session):
    """Test target scoping for rules and skills filtering."""
    app.dependency_overrides[get_session] = lambda: db_session
    client = TestClient(app)

    # 1. Create a Global Rule (target_id=None)
    global_rule_payload = {
        "id": "rule_global_test",
        "name": "Global Block Cross Join",
        "target_id": None,
        "rule_type": "FORBID_JOIN",
        "expression": "Orders,AuditLogs",
        "description": "Applies across all database engines",
        "severity": "CRITICAL",
        "is_active": True,
    }
    res_g = client.post("/api/rules", json=global_rule_payload)
    assert res_g.status_code == 201

    # 2. Create a Target-Scoped Rule (target_id="sqlserver_prod")
    sql_rule_payload = {
        "id": "rule_sqlserver_test",
        "name": "SQL Server Max Time Limit",
        "target_id": "sqlserver_prod",
        "rule_type": "MAX_EXECUTION_TIME",
        "expression": "10",
        "description": "Applies specifically to SQL Server Production",
        "severity": "HIGH",
        "is_active": True,
    }
    res_sql = client.post("/api/rules", json=sql_rule_payload)
    assert res_sql.status_code == 201

    # 3. Filter by target_id="global"
    res_filtered_global = client.get("/api/rules?target_id=global")
    assert res_filtered_global.status_code == 200
    global_ids = [r["id"] for r in res_filtered_global.json()]
    assert "rule_global_test" in global_ids
    assert "rule_sqlserver_test" not in global_ids

    # 4. Filter by target_id="sqlserver_prod" with exact=true
    res_exact_sql = client.get("/api/rules?target_id=sqlserver_prod&exact=true")
    assert res_exact_sql.status_code == 200
    exact_sql_ids = [r["id"] for r in res_exact_sql.json()]
    assert "rule_sqlserver_test" in exact_sql_ids
    assert "rule_global_test" not in exact_sql_ids

    # 5. Test GET /api/skills
    skills_res = client.get("/api/skills")
    assert skills_res.status_code == 200
    assert isinstance(skills_res.json(), list)

    # 6. Test PUT /api/rules/{rule_id} to reassign target_id (Plugin scoping & Global)
    # Reassign rule_global_test to mongodb_prod
    update_res = client.put(
        "/api/rules/rule_global_test",
        json={"name": "Updated Mongo Rule", "target_id": "mongodb_prod", "severity": "CRITICAL"},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["name"] == "Updated Mongo Rule"
    assert updated_data["target_id"] == "mongodb_prod"
    assert updated_data["severity"] == "CRITICAL"

    # Reassign rule_sqlserver_test to Global scope (target_id=None / "")
    update_to_global_res = client.put(
        "/api/rules/rule_sqlserver_test",
        json={"target_id": ""},
    )
    assert update_to_global_res.status_code == 200
    assert update_to_global_res.json()["target_id"] is None

    app.dependency_overrides.clear()
