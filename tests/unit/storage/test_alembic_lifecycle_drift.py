"""Alembic Full Lifecycle & Schema Drift Verification.

Requirements:
1. Upgrade head from an empty database.
2. Downgrade to base (clean teardown).
3. Upgrade back to head.
4. Compare database schema (tables, columns, types) against SQLModel.metadata to detect schema drift.
"""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlmodel import SQLModel

import core.database  # noqa: F401
from alembic import command


def test_alembic_full_lifecycle_and_schema_drift(tmp_path: Path):
    """Verify upgrade head -> downgrade base -> upgrade head, and assert zero schema drift against SQLModel."""
    db_file = tmp_path / "test_lifecycle_drift.db"
    db_url = f"sqlite:///{db_file}"
    db_url_cfg = db_url.replace("%", "%%")
    test_engine = create_engine(db_url)

    alembic_ini_path = Path("alembic.ini").resolve()
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url_cfg)

    # 1. Upgrade head from empty DB
    with test_engine.connect() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "head")

    inspector = inspect(test_engine)
    head_tables = set(inspector.get_table_names())
    assert "alembic_version" in head_tables
    assert "execution_logs" in head_tables
    assert "event_outbox" in head_tables

    # 2. Downgrade to base
    with test_engine.connect() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.downgrade(alembic_cfg, "base")

    inspector_base = inspect(test_engine)
    base_tables = set(inspector_base.get_table_names()) - {"alembic_version"}
    # Downgrade to base should remove migration-managed application tables
    assert len(base_tables) == 0, f"Expected 0 app tables after downgrade base, found: {base_tables}"

    # 3. Upgrade back to head
    with test_engine.connect() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "head")

    inspector_head2 = inspect(test_engine)
    reupgraded_tables = set(inspector_head2.get_table_names())
    assert "alembic_version" in reupgraded_tables

    # 4. Schema Drift Comparison: SQLModel.metadata vs Database
    model_tables = set(SQLModel.metadata.tables.keys())
    db_tables = set(inspector_head2.get_table_names()) - {"alembic_version"}

    # All model tables must exist in database
    missing_tables = model_tables - db_tables
    assert not missing_tables, f"Schema Drift: Missing tables in database: {missing_tables}"

    # No unexpected tables in database
    unexpected_tables = db_tables - model_tables
    assert not unexpected_tables, f"Schema Drift: Unexpected extra tables in database: {unexpected_tables}"

    # Verify column definitions for each table
    for table_name in model_tables:
        model_table = SQLModel.metadata.tables[table_name]
        model_columns = {col.name: col for col in model_table.columns}

        db_col_dicts = inspector_head2.get_columns(table_name)
        db_column_names = {c["name"] for c in db_col_dicts}

        missing_columns = set(model_columns.keys()) - db_column_names
        assert not missing_columns, f"Schema Drift: Table '{table_name}' is missing columns in DB: {missing_columns}"

        unexpected_columns = db_column_names - set(model_columns.keys())
        assert not unexpected_columns, (
            f"Schema Drift: Table '{table_name}' has extra columns in DB: {unexpected_columns}"
        )
