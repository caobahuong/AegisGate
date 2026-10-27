"""Unit tests for PluginRegistry."""

import pytest
from sqlmodel import Session

from core.database import PluginProfile
from core.engine.plugin_registry import PluginRegistry
from core.exceptions import PluginNotFoundError


def test_plugin_registry(db_session: Session):
    """Verify PluginRegistry registration, retrieval, and metrics updates."""
    registry = PluginRegistry(session=db_session)

    profile = PluginProfile(
        id="sqlserver_prod",
        name="SQL Server Production",
        driver="pyodbc/mssql",
        entrypoint="python plugins/sqlserver_plugin/adapter.py",
        dry_run_command="SET SHOWPLAN_XML ON",
        abort_command="KILL {spid}",
    )
    registered = registry.register_profile(profile)
    assert registered.id == "sqlserver_prod"

    fetched = registry.get_profile("sqlserver_prod")
    assert fetched.name == "SQL Server Production"

    # Update metrics
    registry.update_metrics("sqlserver_prod", latency_ms=25.0, active_sessions_count=3)
    updated = registry.get_profile("sqlserver_prod")
    assert updated.latency_ms == 25.0
    assert updated.active_sessions_count == 3

    with pytest.raises(PluginNotFoundError):
        registry.get_profile("non_existent_plugin")
