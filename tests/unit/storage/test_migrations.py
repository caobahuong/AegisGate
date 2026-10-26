"""Unit tests for Alembic migrations and init_db behavior."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from core.database import init_db


@pytest.fixture
def temp_db_path(tmp_path: Path):
    return tmp_path / "test_migration.db"


def test_init_db_fresh_database(temp_db_path: Path):
    """Verify init_db initializes a fresh database from scratch up to head revision."""
    db_url = f"sqlite:///{temp_db_path}"
    test_engine = create_engine(db_url)

    init_db(target_engine=test_engine)

    inspector = inspect(test_engine)
    tables = set(inspector.get_table_names())

    # Check baseline and Phase 4 tables
    expected_tables = {
        "alembic_version",
        "plugin_profiles",
        "knowledge_chunks",
        "governance_rules",
        "execution_logs",
        "system_settings",
        "event_outbox",
        "process_heartbeat",
        "execution_control",
        "distributed_lock",
    }
    for expected in expected_tables:
        assert expected in tables, f"Expected table '{expected}' not found in created tables: {tables}"

    # Verify columns in execution_logs
    columns = {col["name"] for col in inspector.get_columns("execution_logs")}
    assert "owner_id" in columns
    assert "started_at" in columns


def test_init_db_existing_legacy_database(temp_db_path: Path):
    """Verify init_db detects an existing pre-alembic DB, stamps it to 001, and upgrades to 002."""
    db_url = f"sqlite:///{temp_db_path}"
    test_engine = create_engine(db_url)

    # 1. Simulate an old database created with SQLModel.metadata.create_all (no alembic_version)
    alembic_ini_path = Path("alembic.ini").resolve()
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # Run upgrade to 001 to simulate legacy phase 1-3 state
    command.upgrade(alembic_cfg, "001")

    # Drop alembic_version table to simulate pre-alembic existing DB
    with test_engine.connect() as conn:
        conn.execute(text("DROP TABLE alembic_version"))
        conn.commit()

    inspector = inspect(test_engine)
    assert "alembic_version" not in inspector.get_table_names()
    assert "execution_logs" in inspector.get_table_names()

    # 2. Run init_db: it should stamp 001 and upgrade to 002
    init_db(target_engine=test_engine)

    inspector = inspect(test_engine)
    assert "alembic_version" in inspector.get_table_names()
    assert "event_outbox" in inspector.get_table_names()

    with test_engine.connect() as conn:
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        assert rev == "002"


def test_migration_downgrade_and_upgrade(temp_db_path: Path):
    """Verify revision 002 can be downgraded to 001 and upgraded back cleanly."""
    db_url = f"sqlite:///{temp_db_path}"
    test_engine = create_engine(db_url)
    init_db(target_engine=test_engine)

    alembic_ini_path = Path("alembic.ini").resolve()
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    with test_engine.connect() as conn:
        alembic_cfg.attributes["connection"] = conn
        # Downgrade to 001
        command.downgrade(alembic_cfg, "001")

        inspector = inspect(test_engine)
        assert "event_outbox" not in inspector.get_table_names()

        # Upgrade back to head
        command.upgrade(alembic_cfg, "head")

        inspector = inspect(test_engine)
        assert "event_outbox" in inspector.get_table_names()
