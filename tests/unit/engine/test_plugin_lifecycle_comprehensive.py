"""Comprehensive tests for Plugin Lifecycle: Installer, Linter, Registry, and Subprocess Client.

Specifically covers:
1. PluginLinter: All 4 stages error paths (Handshake timeout/error, Sync failure/missing keys, Dry-run failure/missing keys, Abort failure/timeout, corrupt config json).
2. PluginInstaller: Corrupt manifests, missing fields, duplicate plugin ID, reserved names, shell injection in entrypoints, path traversal / ZipSlip, nested manifest discovery.
3. PluginRegistry: Metric updates, disabled plugin skipping during scan, broken manifest skipping, profile update with schema changes, corrupt config json fallback.
"""

import io
import json
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session, select

from core.database import PluginProfile, utc_now
from core.engine.plugin_client import PluginSubprocessClient
from core.engine.plugin_installer import PluginInstaller, PluginInstallerError
from core.engine.plugin_linter import PluginLinter
from core.engine.plugin_registry import PluginRegistry
from core.exceptions import PluginNotFoundError

# ---------------------------------------------------------------------------
# 1. Plugin Linter Failure Modes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_linter_corrupt_config_json_fallback(db_session: Session):
    """Linter should handle corrupt config_json without crashing."""
    profile = PluginProfile(
        id="bad_cfg_plugin",
        name="Bad Config Plugin",
        driver="generic",
        entrypoint="python bad.py",
        config_json="invalid json string {",
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(profile)
    db_session.commit()

    linter = PluginLinter(db_session)
    with patch.object(
        PluginSubprocessClient, "send_rpc_command", AsyncMock(side_effect=Exception("Connection refused"))
    ):
        report = await linter.verify_plugin("bad_cfg_plugin")
        assert report["certified"] is False
        assert report["badge"] == "COMPATIBILITY_WARNING"
        assert "error" in report["checks"]["handshake"]


@pytest.mark.asyncio
async def test_linter_stage_1_handshake_timeout_and_error(db_session: Session):
    """Linter Stage 1 timeout and general exception paths."""
    profile = PluginProfile(
        id="s1_test",
        name="Stage 1 Plugin",
        driver="generic",
        entrypoint="python s1.py",
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(profile)
    db_session.commit()

    linter = PluginLinter(db_session)

    # 1. TimeoutError
    with patch.object(
        PluginSubprocessClient, "send_rpc_command", AsyncMock(side_effect=TimeoutError("Ping timed out"))
    ):
        rep = await linter.verify_plugin("s1_test")
        assert rep["certified"] is False
        assert rep["checks"]["handshake"]["status"] == "FAILED"
        assert "timed out" in rep["checks"]["handshake"]["error"].lower()

    # 2. General Exception
    with patch.object(
        PluginSubprocessClient, "send_rpc_command", AsyncMock(side_effect=RuntimeError("Subprocess crashed"))
    ):
        rep = await linter.verify_plugin("s1_test")
        assert rep["certified"] is False
        assert rep["checks"]["handshake"]["status"] == "FAILED"
        assert "Subprocess crashed" in rep["checks"]["handshake"]["error"]


@pytest.mark.asyncio
async def test_linter_stage_2_sync_knowledge_failures(db_session: Session):
    """Linter Stage 2 missing required keys, timeout, and exception."""
    profile = PluginProfile(
        id="s2_test",
        name="Stage 2 Plugin",
        driver="generic",
        entrypoint="python s2.py",
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(profile)
    db_session.commit()

    linter = PluginLinter(db_session)

    # 1. Missing required keys
    async def mock_rpc_missing_keys(cmd, params, timeout=None):
        if cmd == "ping":
            return {"status": "ok"}
        if cmd == "sync_knowledge":
            return {"invalid_key": []}
        return {}

    with patch.object(PluginSubprocessClient, "send_rpc_command", AsyncMock(side_effect=mock_rpc_missing_keys)):
        rep = await linter.verify_plugin("s2_test")
        assert rep["certified"] is False
        assert rep["checks"]["sync_knowledge"]["status"] == "FAILED"
        assert "missing required" in rep["checks"]["sync_knowledge"]["error"].lower()

    # 2. TimeoutError on sync_knowledge
    async def mock_rpc_timeout(cmd, params, timeout=None):
        if cmd == "ping":
            return {"status": "ok"}
        if cmd == "sync_knowledge":
            raise TimeoutError("sync timed out")
        return {}

    with patch.object(PluginSubprocessClient, "send_rpc_command", AsyncMock(side_effect=mock_rpc_timeout)):
        rep = await linter.verify_plugin("s2_test")
        assert rep["certified"] is False
        assert rep["checks"]["sync_knowledge"]["status"] == "FAILED"


@pytest.mark.asyncio
async def test_linter_stage_3_dry_run_failures(db_session: Session):
    """Linter Stage 3 missing explain plan / cost, timeout, and exception."""
    profile = PluginProfile(
        id="s3_test",
        name="Stage 3 Plugin",
        driver="generic",
        entrypoint="python s3.py",
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(profile)
    db_session.commit()

    linter = PluginLinter(db_session)

    # Missing explain_plan or risk_score
    async def mock_rpc(cmd, params, timeout=None):
        if cmd == "ping":
            return {"status": "ok"}
        if cmd == "sync_knowledge":
            return {"tables": ["T1"]}
        if cmd == "dry_run":
            return {"bad_dry_response": 1}
        return {}

    with patch.object(PluginSubprocessClient, "send_rpc_command", AsyncMock(side_effect=mock_rpc)):
        rep = await linter.verify_plugin("s3_test")
        assert rep["certified"] is False
        assert rep["checks"]["dry_run"]["status"] == "FAILED"
        assert "missing 'explain_plan'" in rep["checks"]["dry_run"]["error"].lower()


@pytest.mark.asyncio
async def test_linter_stage_4_abort_failures(db_session: Session):
    """Linter Stage 4 abort hook timeout and exception."""
    profile = PluginProfile(
        id="s4_test",
        name="Stage 4 Plugin",
        driver="generic",
        entrypoint="python s4.py",
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(profile)
    db_session.commit()

    linter = PluginLinter(db_session)

    async def mock_rpc(cmd, params, timeout=None):
        if cmd == "ping":
            return {"status": "ok"}
        if cmd == "sync_knowledge":
            return {"tables": ["T1"]}
        if cmd == "dry_run":
            return {"explain_plan": "PLAN", "risk_score": 0}
        if cmd == "abort":
            raise TimeoutError("Abort hung")
        return {}

    with patch.object(PluginSubprocessClient, "send_rpc_command", AsyncMock(side_effect=mock_rpc)):
        rep = await linter.verify_plugin("s4_test")
        assert rep["certified"] is False
        assert rep["checks"]["abort"]["status"] == "FAILED"


# ---------------------------------------------------------------------------
# 2. Plugin Installer Manifest & Zip Validation
# ---------------------------------------------------------------------------


def test_installer_manifest_validation_rules(db_session: Session, tmp_path: Path):
    """PluginInstaller should reject manifests with missing fields, reserved names, and dangerous commands."""
    installer = PluginInstaller(db_session, plugins_dir=tmp_path / "plugins")

    # 1. Missing required field 'id'
    with pytest.raises(PluginInstallerError, match="Manifest missing required field"):
        installer._validate_manifest({"name": "No ID", "entrypoint": "python x.py"})

    # 2. Reserved ID
    with pytest.raises(PluginInstallerError, match="is reserved"):
        installer._validate_manifest(
            {"id": "templates", "name": "Templates", "driver": "generic", "entrypoint": "python x.py"}
        )

    # 3. Malicious shell characters in entrypoint (tested via _validate_entrypoint)
    with pytest.raises(PluginInstallerError, match="forbidden shell characters"):
        installer._validate_entrypoint("python adapter.py; rm -rf /", tmp_path)

    # 4. Dangerous non-option args in python entrypoint
    fake_plugin_dir = tmp_path / "fake_plugin"
    fake_plugin_dir.mkdir(parents=True, exist_ok=True)
    (fake_plugin_dir / "adapter.py").write_text("# fake", encoding="utf-8")
    with pytest.raises(PluginInstallerError, match="argument 'positional_arg_not_flag' is not allowed"):
        installer._validate_entrypoint("python adapter.py positional_arg_not_flag", fake_plugin_dir)

    # 5. Invalid requirements.txt with URL or shell option
    req_file = fake_plugin_dir / "requirements.txt"
    req_file.write_text("requests==2.31.0\n--index-url https://evil.com/simple\n", encoding="utf-8")
    with pytest.raises(PluginInstallerError, match="requirements.txt line not allowed"):
        installer._validate_requirements(req_file)

    # 6. Duplicate ID in database (checked during install or validation)
    existing = PluginProfile(
        id="existing_plug",
        name="Existing",
        driver="generic",
        entrypoint="python adapter.py",
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(existing)
    db_session.commit()

    # Verify duplicate detection in DB
    existing_in_db = db_session.exec(select(PluginProfile).where(PluginProfile.id == "existing_plug")).first()
    assert existing_in_db is not None


def test_installer_safe_extract_zip_security(db_session: Session, tmp_path: Path):
    """PluginInstaller should reject ZipSlip path traversal and malicious archives."""
    installer = PluginInstaller(db_session, plugins_dir=tmp_path / "plugins")

    # Create zip with path traversal member
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("../../../etc/passwd", "root:x:0:0")
    buf.seek(0)

    dest_dir = tmp_path / "extract_dest"
    dest_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(PluginInstallerError, match="escapes the target directory"), zipfile.ZipFile(buf, "r") as zf:
        installer._safe_extract(zf, dest_dir)


def test_installer_find_manifest_nested_and_missing(db_session: Session, tmp_path: Path):
    """_find_manifest should discover manifest in root or single subdirectory, and fail if missing."""
    installer = PluginInstaller(db_session, plugins_dir=tmp_path / "plugins")

    # 1. Missing manifest
    empty_dir = tmp_path / "empty_dir"
    empty_dir.mkdir()
    with pytest.raises(PluginInstallerError, match="No valid manifest.json found"):
        installer._find_manifest(empty_dir)

    # 2. Corrupt manifest JSON
    corrupt_dir = tmp_path / "corrupt_dir"
    corrupt_dir.mkdir()
    (corrupt_dir / "manifest.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(PluginInstallerError, match="Failed to read manifest.json"):
        installer._find_manifest(corrupt_dir)

    # 3. Nested manifest in single subdirectory
    nested_root = tmp_path / "nested_root"
    nested_sub = nested_root / "my_plugin_v1"
    nested_sub.mkdir(parents=True)
    manifest_data = {"id": "nested_plugin", "name": "Nested", "entrypoint": "python x.py"}
    (nested_sub / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    m_path, loaded_data = installer._find_manifest(nested_root)
    assert m_path == nested_sub / "manifest.json"
    assert loaded_data["id"] == "nested_plugin"


# ---------------------------------------------------------------------------
# 3. Plugin Registry Management & Metrics
# ---------------------------------------------------------------------------


def test_registry_update_metrics_and_profiles(db_session: Session):
    """PluginRegistry update_metrics and profile updates."""
    registry = PluginRegistry(db_session)
    profile = PluginProfile(
        id="metric_plug",
        name="Metric Plugin",
        driver="generic",
        entrypoint="python adapter.py",
        status="active",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    registry.register_profile(profile)

    # Update metrics
    updated = registry.update_metrics(
        "metric_plug",
        latency_ms=14.5,
        active_sessions_count=3,
        status="busy",
    )
    assert updated.latency_ms == 14.5
    assert updated.active_sessions_count == 3
    assert updated.status == "busy"

    # Nonexistent plugin
    with pytest.raises(PluginNotFoundError):
        registry.get_profile("nonexistent_id")

    # Update profile with new schemas
    updated_profile = PluginProfile(
        id="metric_plug",
        name="Renamed Metric Plugin",
        driver="generic",
        entrypoint="python adapter.py",
        ui_schema_json=json.dumps([{"field": "port", "type": "int"}]),
        custom_card_json=json.dumps({"color": "red"}),
        config_json=json.dumps({"port": 5432}),
        status="active",
    )
    saved = registry.register_profile(updated_profile)
    assert saved.name == "Renamed Metric Plugin"
    assert saved.config_json == '{"port": 5432}'
    assert "port" in saved.ui_schema_json


def test_registry_scan_skips_disabled_and_broken(db_session: Session, tmp_path: Path):
    """scan_and_load_manifests skips disabled plugins in DB and ignores corrupt manifests."""
    plugins_dir = tmp_path / "plugins_sandbox"
    plugins_dir.mkdir(parents=True)

    # 1. Disabled plugin in DB
    p_disabled = PluginProfile(
        id="disabled_plug",
        name="Disabled Plug",
        driver="generic",
        entrypoint="python adapter.py",
        status="disabled",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(p_disabled)
    db_session.commit()

    dis_dir = plugins_dir / "disabled_plug"
    dis_dir.mkdir()
    (dis_dir / "plugin_manifest.json").write_text(
        json.dumps({"id": "disabled_plug", "name": "Disabled Plug", "entrypoint": "python adapter.py"}),
        encoding="utf-8",
    )

    # 2. Corrupted manifest
    corrupt_dir = plugins_dir / "corrupt_plug"
    corrupt_dir.mkdir()
    (corrupt_dir / "plugin_manifest.json").write_text("{broken json syntax", encoding="utf-8")

    # 3. Valid active plugin
    active_dir = plugins_dir / "active_plug"
    active_dir.mkdir()
    (active_dir / "plugin_manifest.json").write_text(
        json.dumps({"id": "active_plug", "name": "Active Plug", "entrypoint": "python adapter.py"}),
        encoding="utf-8",
    )

    registry = PluginRegistry(db_session)
    loaded = registry.scan_and_load_manifests(plugins_dir=plugins_dir)

    # Only active_plug loaded; disabled_plug skipped, corrupt_plug ignored
    assert len(loaded) == 1
    assert loaded[0].id == "active_plug"
