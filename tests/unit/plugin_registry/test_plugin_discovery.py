"""Unit tests for plugin manifest discovery and catalog ingestion."""

from sqlmodel import Session

from core.engine.plugin_registry import PluginRegistry


def test_manifest_discovery_and_catalog_ingest(db_session: Session):
    """Verify discovery of manifests in plugins/ directory and ingestion into database."""
    registry = PluginRegistry(session=db_session)
    loaded = registry.scan_and_load_manifests()
    assert len(loaded) >= 1

    sql_plugin = next((p for p in loaded if p.id == "sqlserver_prod"), None)
    assert sql_plugin is not None
    assert sql_plugin.driver == "pyodbc/mssql"
    assert sql_plugin.dry_run_command == "SET SHOWPLAN_XML ON"
