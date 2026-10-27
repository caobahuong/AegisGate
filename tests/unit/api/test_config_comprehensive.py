"""Comprehensive tests for Settings: environment loading, type validation, and safe defaults.

Specifically tests:
1. Safe default values (DEBUG=False, AUTO_APPROVAL_DEFAULT=False, FAIL_CLOSED=True, localhost binding).
2. Type coercion & validation errors when environment variables have invalid types.
3. Fallback when env file is missing.
4. Environment variable overrides for system and network settings.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from core.config import Settings


def test_settings_safe_defaults():
    """Verify default settings are secure and fail-safe."""
    cfg = Settings(_env_file=None)

    # Security: auto-approval disabled by default
    assert cfg.AUTO_APPROVAL_DEFAULT is False, "Auto approval must be disabled by default"

    # Security: fail-closed on dry-run error
    assert cfg.FAIL_CLOSED_ON_DRY_RUN_ERROR is True, "Fail-closed must be enabled by default"

    # Security: debug mode disabled
    assert cfg.DEBUG is False, "Debug mode must be disabled by default"

    # Security: localhost binding
    assert cfg.API_HOST == "127.0.0.1", "API must bind to localhost by default"

    # Data preservation: archive before prune
    assert cfg.ARCHIVE_BEFORE_DELETE is True, "Archival before deletion must be enabled by default"


def test_settings_env_overrides(monkeypatch: pytest.MonkeyPatch):
    """Verify environment variables properly override settings."""
    monkeypatch.setenv("API_PORT", "9050")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("AUTO_APPROVAL_DEFAULT", "true")
    monkeypatch.setenv("EVENT_BUS", "db")
    monkeypatch.setenv("READ_TIMEOUT_SECONDS", "25.5")

    cfg = Settings(_env_file=None)
    assert cfg.API_PORT == 9050
    assert cfg.DEBUG is True
    assert cfg.AUTO_APPROVAL_DEFAULT is True
    assert cfg.EVENT_BUS == "db"
    assert cfg.READ_TIMEOUT_SECONDS == 25.5


def test_settings_invalid_type_rejection(monkeypatch: pytest.MonkeyPatch):
    """Verify Pydantic raises ValidationError when env vars have invalid types."""
    # 1. Non-integer port
    monkeypatch.setenv("API_PORT", "not_a_valid_port")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)

    # 2. Non-numeric timeout
    monkeypatch.undo()
    monkeypatch.setenv("READ_TIMEOUT_SECONDS", "unparseable_float")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)

    # 3. Non-boolean flag
    monkeypatch.undo()
    monkeypatch.setenv("FAIL_CLOSED_ON_DRY_RUN_ERROR", "invalid_bool_string")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_missing_env_file(tmp_path: Path):
    """Settings instantiates cleanly with defaults even if .env file does not exist."""
    nonexistent = tmp_path / "nonexistent.env"
    cfg = Settings(_env_file=str(nonexistent))
    assert cfg.APP_NAME == "AegisGate Core"
    assert cfg.API_PORT == 8000
