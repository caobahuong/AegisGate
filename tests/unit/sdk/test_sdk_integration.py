"""Integration tests between AegisGate Core Gateway and Plugins built with aegisgate_sdk.

Specifically tests:
1. Registering an SDK-based plugin (using plugins/templates/starter/adapter.py).
2. Verifying the plugin through the 4-stage linter via gateway REST endpoint.
3. Syncing the plugin catalog via gateway REST endpoint into KnowledgeStore.
4. Submitting a real query execution lifecycle (DRY_RUN -> GOVERNANCE -> EXECUTION -> COMPLETED)
   handled by the real SDK PluginServer subprocess over JSON-RPC stdio.
5. Aborting an execution.
"""

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from core.config import settings
from core.database import PluginProfile, utc_now


@pytest.fixture(autouse=True)
def isolate_knowledge_docs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Ensure test doc files are written into tmp_path sandbox."""
    docs_sandbox = tmp_path / "knowledge_docs"
    docs_sandbox.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "KNOWLEDGE_DOCS_DIR", docs_sandbox)
    return docs_sandbox


@pytest.fixture
def starter_plugin_registered(api_client: TestClient, db_session: Session) -> str:
    """Register the SDK starter plugin into the database."""
    starter_dir = settings.BASE_DIR / "plugins" / "templates" / "starter"
    adapter_path = starter_dir / "adapter.py"
    assert adapter_path.exists(), f"Starter adapter missing at {adapter_path}"

    plugin_id = "sdk_starter_test"
    entrypoint = f'"{sys.executable}" "{adapter_path}"'

    profile = PluginProfile(
        id=plugin_id,
        name="SDK Starter Test Plugin",
        driver="starter_driver",
        entrypoint=entrypoint,
        dry_run_command="EXPLAIN",
        abort_command="KILL {spid}",
        config_json=json.dumps({"database": "test_db", "use_simulation": True}),
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(profile)
    db_session.commit()
    return plugin_id


def test_sdk_plugin_linter_and_sync_integration(api_client: TestClient, starter_plugin_registered: str):
    """Test 4-stage automated linter and schema sync on real SDK PluginServer subprocess."""
    plugin_id = starter_plugin_registered

    # 1. 4-Stage Linter certification
    res_verify = api_client.post(f"/api/plugins/{plugin_id}/verify")
    assert res_verify.status_code == 200
    report = res_verify.json()
    assert report["plugin_id"] == plugin_id
    assert report["certified"] is True
    assert report["badge"] == "CERTIFIED_READY"
    assert report["checks"]["handshake"]["status"] == "PASSED"
    assert report["checks"]["sync_knowledge"]["status"] == "PASSED"
    assert report["checks"]["dry_run"]["status"] == "PASSED"
    assert report["checks"]["abort"]["status"] == "PASSED"

    # 2. Sync catalog into KnowledgeStore
    res_sync = api_client.post(f"/api/plugins/{plugin_id}/sync")
    assert res_sync.status_code == 200
    synced = res_sync.json()
    assert len(synced) >= 1
    # Verify tables extracted by the SDK plugin
    catalog = synced[0].get("catalog", [])
    tables = catalog.get("tables", []) if isinstance(catalog, dict) else catalog
    table_names = [t.get("name") for t in tables if isinstance(t, dict)]
    assert "users" in table_names


def test_sdk_plugin_execution_lifecycle_integration(api_client: TestClient, starter_plugin_registered: str):
    """Test end-to-end execution lifecycle with real SDK PluginServer subprocess."""
    plugin_id = starter_plugin_registered

    # Enable auto approval so query runs to completion
    api_client.post("/api/settings/auto-mode", json={"enabled": True})

    # Submit query for execution
    query_payload = {
        "target_id": plugin_id,
        "query": "SELECT id, email FROM users WHERE id = 1;",
        "reasoning": "Integration test query execution via SDK plugin",
    }
    res_exec = api_client.post("/api/monitor/executions?wait=true", json=query_payload)
    assert res_exec.status_code == 201
    data = res_exec.json()

    assert data["target_id"] == plugin_id
    assert data["status"] == "COMPLETED"
    assert data["auto_approved"] is True
    assert data["explain_plan"] is not None
    assert data["result_summary"] is not None
    assert data["execution_time_ms"] is not None

    # Reset auto approval
    api_client.post("/api/settings/auto-mode", json={"enabled": False})
