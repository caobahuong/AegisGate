"""Standalone test suite for Starter Database Plugin."""

import sys
from pathlib import Path

# Add plugin folder and SDK to path
plugin_dir = Path(__file__).resolve().parent.parent
sdk_dir = plugin_dir.parent.parent.parent / "sdk"
sys.path.insert(0, str(plugin_dir))
sys.path.insert(0, str(sdk_dir))

from adapter import StarterDatabasePlugin


def test_starter_plugin_sync_knowledge():
    plugin = StarterDatabasePlugin()
    catalog = plugin.sync_knowledge({"database": "test_db"})
    assert "schemas" in catalog
    assert "tables" in catalog
    assert len(catalog["tables"]) >= 2
    assert catalog["database"] == "test_db"


def test_starter_plugin_dry_run():
    plugin = StarterDatabasePlugin()
    dry_res = plugin.dry_run("SELECT * FROM users WHERE id = 1;", {})
    assert "explain_plan" in dry_res
    assert dry_res["risk_score"] <= 25
    assert "Node Type" in dry_res["explain_plan"]["Plan"]


def test_starter_plugin_execute():
    plugin = StarterDatabasePlugin()
    exec_res = plugin.execute("SELECT id, email FROM users;", {})
    assert exec_res["rows_affected"] == 2
    assert len(exec_res["data"]) == 2
    assert "spid" in exec_res


def test_starter_plugin_abort():
    plugin = StarterDatabasePlugin()
    assert plugin.abort(101, {}) is True


if __name__ == "__main__":
    test_starter_plugin_sync_knowledge()
    test_starter_plugin_dry_run()
    test_starter_plugin_execute()
    test_starter_plugin_abort()
    print("All Starter Plugin tests passed successfully!")
