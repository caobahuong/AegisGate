"""Comprehensive unit tests for Plugin Auto-Installer & Venv Service (Idea 2)."""

import io
import json
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from core.database import PluginProfile, get_session
from core.engine.plugin_installer import PluginInstaller, PluginInstallerError
from core.main import app


@pytest.fixture(name="installer_db_session")
def fixture_installer_db_session(tmp_path: Path):
    """Isolated test database session for installer tests."""
    test_db = tmp_path / "test_installer.db"
    engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _create_mock_plugin_zip(plugin_id: str = "custom_redis_plugin", has_manifest: bool = True) -> bytes:
    """Helper to generate a valid in-memory zip archive."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        if has_manifest:
            manifest_content = {
                "id": plugin_id,
                "name": "Custom Redis Connector",
                "driver": "redis-py",
                "entrypoint": "python adapter.py",
                "dry_run_command": "EXPLAIN {query}",
                "abort_command": "CLIENT KILL {spid}",
                "config": {"host": "127.0.0.1", "port": 6379},
                "ui_schema": [
                    {"key": "host", "label": "Host", "type": "text", "default": "127.0.0.1", "required": True}
                ],
                "custom_card": {"title": "Redis Keyspace"},
            }
            zf.writestr("manifest.json", json.dumps(manifest_content))

        adapter_code = """
import sys, json

for line in sys.stdin:
    req = json.loads(line)
    mid = req.get("id")
    method = req.get("method")
    if method == "ping":
        res = {"status": "pong"}
    elif method == "sync_knowledge":
        res = {"schemas": ["keyspace"], "tables": [{"name": "cache_keys"}]}
    elif method == "dry_run":
        res = {"explain_plan": {"type": "KeyLookup"}, "risk_score": 0}
    elif method == "abort":
        res = True
    else:
        res = {}
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": res}) + "\\n")
    sys.stdout.flush()
"""
        zf.writestr("adapter.py", adapter_code)
        zf.writestr("requirements.txt", "# mock requirements\n")
        zf.writestr("README.md", "# Custom Redis Plugin\n")

    return buffer.getvalue()


@pytest.mark.asyncio
async def test_installer_install_from_zip_success(installer_db_session: Session):
    """Verify successfully installing an external plugin from ZIP bytes."""
    installer = PluginInstaller(installer_db_session)
    zip_bytes = _create_mock_plugin_zip("custom_redis_plugin")

    profile = await installer.install_from_zip(zip_bytes)
    assert profile.id == "custom_redis_plugin"
    assert profile.name == "Custom Redis Connector"
    assert profile.driver == "redis-py"
    assert profile.status == "active"

    # Verify directory created on filesystem
    installed_dir = installer.plugins_dir / "custom_redis_plugin"
    assert installed_dir.exists()
    assert (installed_dir / "manifest.json").exists()
    assert (installed_dir / "adapter.py").exists()

    # Verify persisted in DB
    db_profile = installer_db_session.exec(
        select(PluginProfile).where(PluginProfile.id == "custom_redis_plugin")
    ).first()
    assert db_profile is not None
    assert db_profile.name == "Custom Redis Connector"


@pytest.mark.asyncio
async def test_installer_missing_manifest_error(installer_db_session: Session):
    """Verify error raised when zip has no manifest.json."""
    installer = PluginInstaller(installer_db_session)
    zip_bytes = _create_mock_plugin_zip("broken_plugin", has_manifest=False)

    with pytest.raises(PluginInstallerError) as exc:
        await installer.install_from_zip(zip_bytes)
    assert "No valid manifest.json found" in str(exc.value)


@pytest.mark.asyncio
async def test_installer_corrupt_zip_error(installer_db_session: Session):
    """Verify error raised when file content is not a valid zip."""
    installer = PluginInstaller(installer_db_session)
    with pytest.raises(PluginInstallerError) as exc:
        await installer.install_from_zip(b"THIS_IS_NOT_A_ZIP_CONTENT")
    assert "not a valid ZIP archive" in str(exc.value)


def test_api_install_plugin_zip_endpoint(installer_db_session: Session):
    """Verify POST /api/plugins/install-zip endpoint with multipart file upload."""
    def override_get_session():
        yield installer_db_session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    try:
        zip_bytes = _create_mock_plugin_zip("api_zip_target")
        files = {
            "file": ("api_zip_target.zip", zip_bytes, "application/zip")
        }
        resp = client.post("/api/plugins/install-zip", files=files)
        assert resp.status_code == 201
        data = resp.json()

        assert data["id"] == "api_zip_target"
        assert data["name"] == "Custom Redis Connector"
        assert data["driver"] == "redis-py"
        assert data["status"] == "active"
    finally:
        app.dependency_overrides.clear()

