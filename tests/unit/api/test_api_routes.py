"""Unit tests for FastAPI REST API endpoints."""

from fastapi.testclient import TestClient


def test_health_check(api_client: TestClient):
    """Verify /health endpoint returns healthy status."""
    resp = api_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_plugin_endpoints(api_client: TestClient):
    """Verify registering and listing plugins via REST API."""
    reg_payload = {
        "id": "mssql_gateway",
        "name": "MSSQL Gateway",
        "driver": "pyodbc",
        "entrypoint": "python adapter.py",
        "dry_run_command": "SET SHOWPLAN_XML ON",
        "abort_command": "KILL {spid}",
        "config": {"host": "localhost", "database": "Finance"},
    }
    res = api_client.post("/api/plugins", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] == "mssql_gateway"

    # List plugins
    res = api_client.get("/api/plugins")
    assert res.status_code == 200
    plugins = res.json()
    assert any(p["id"] == "mssql_gateway" for p in plugins)


def test_rules_endpoints(api_client: TestClient):
    """Verify creating, listing, and deleting governance rules via REST API."""
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
    res = api_client.post("/api/rules", json=rule_payload)
    assert res.status_code == 201
    assert res.json()["id"] == "rule_test_api"

    # List rules
    res = api_client.get("/api/rules")
    assert res.status_code == 200
    assert len(res.json()) >= 1

    # Delete rule
    res = api_client.delete("/api/rules/rule_test_api")
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_auto_mode_setting_endpoints(api_client: TestClient):
    """Verify getting and setting auto-mode setting via REST API."""
    res = api_client.get("/api/settings/auto-mode")
    assert res.status_code == 200

    # Set to True
    res = api_client.post("/api/settings/auto-mode", json={"enabled": True})
    assert res.status_code == 200
    assert res.json()["auto_approval_enabled"] is True

    # Set back to False
    res = api_client.post("/api/settings/auto-mode", json={"enabled": False})
    assert res.status_code == 200
    assert res.json()["auto_approval_enabled"] is False
