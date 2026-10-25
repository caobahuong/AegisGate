"""Comprehensive unit tests for Plugin Certification Linter Engine (Idea 5)."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select
from core.database import PluginProfile, get_session
from core.engine.plugin_linter import PluginLinter
from core.main import app


@pytest.fixture(name="db_session")
def fixture_db_session(tmp_path: Path):
    """Isolated test database session."""
    test_db = tmp_path / "test_linter.db"
    engine = create_engine(f"sqlite:///{test_db}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Seed sqlserver_prod plugin
        profile = PluginProfile(
            id="sqlserver_prod",
            name="SQL Server Enterprise",
            driver="pyodbc/mssql",
            entrypoint="python plugins/sqlserver_plugin/adapter.py",
            config_json=json.dumps({"server": "localhost", "use_simulation": "true"}),
            status="active",
        )
        session.add(profile)
        session.commit()
        yield session


@pytest.mark.asyncio
async def test_plugin_linter_verify_sqlserver(db_session: Session):
    """Verify that sqlserver_prod passes all 4 stages of sanity check."""
    linter = PluginLinter(db_session)
    report = await linter.verify_plugin("sqlserver_prod")

    assert report["plugin_id"] == "sqlserver_prod"
    assert report["certified"] is True
    assert report["badge"] == "CERTIFIED_READY"
    assert "checks" in report

    checks = report["checks"]
    assert "handshake" in checks
    assert checks["handshake"]["status"] == "PASSED"
    assert "sync_knowledge" in checks
    assert checks["sync_knowledge"]["status"] == "PASSED"
    assert "dry_run" in checks
    assert checks["dry_run"]["status"] == "PASSED"
    assert "abort" in checks
    assert checks["abort"]["status"] == "PASSED"

    # Verify database persistence
    profile = db_session.exec(select(PluginProfile).where(PluginProfile.id == "sqlserver_prod")).first()
    assert profile is not None
    assert profile.is_certified is True
    assert profile.certification_report_json is not None
    saved_report = json.loads(profile.certification_report_json)
    assert saved_report["badge"] == "CERTIFIED_READY"


@pytest.mark.asyncio
async def test_plugin_linter_verify_nonexistent(db_session: Session):
    """Verify ValueError when attempting to verify unknown plugin."""
    linter = PluginLinter(db_session)
    with pytest.raises(ValueError) as exc:
        await linter.verify_plugin("unknown_target_xyz")
    assert "not found" in str(exc.value)


def test_plugin_linter_endpoint(db_session: Session):
    """Verify POST /api/plugins/{id}/verify REST API endpoint."""
    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    try:
        resp = client.post("/api/plugins/sqlserver_prod/verify")
        assert resp.status_code == 200
        data = resp.json()

        assert data["plugin_id"] == "sqlserver_prod"
        assert data["certified"] is True
        assert data["badge"] == "CERTIFIED_READY"
        assert data["checks"]["handshake"]["status"] == "PASSED"
        assert data["checks"]["sync_knowledge"]["status"] == "PASSED"
    finally:
        app.dependency_overrides.clear()

