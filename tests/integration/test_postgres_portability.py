"""Opt-in PostgreSQL portability and migration integration test.

Only runs when AEGISGATE_TEST_PG_URL is explicitly configured by the user.
Creates an isolated transient database aegisgate_test_<random> and drops it after testing.
"""

import os
import uuid

import pytest
from sqlalchemy import create_engine, text
from sqlmodel import Session, select

from core.database import ExecutionLog, init_db, utc_now

PG_TEST_URL = os.environ.get("AEGISGATE_TEST_PG_URL")


@pytest.mark.skipif(not PG_TEST_URL, reason="AEGISGATE_TEST_PG_URL not configured. Skipping Postgres test.")
def test_postgres_schema_and_crud() -> None:
    """Test schema initialization and basic operations on PostgreSQL."""
    assert PG_TEST_URL is not None
    admin_engine = create_engine(PG_TEST_URL, isolation_level="AUTOCOMMIT")

    random_suffix = uuid.uuid4().hex[:8]
    test_db_name = f"aegisgate_test_{random_suffix}"

    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {test_db_name}"))

    # Build connection string for the transient database
    base_url = PG_TEST_URL.rsplit("/", 1)[0]
    db_url = f"{base_url}/{test_db_name}"
    target_engine = create_engine(db_url)

    try:
        init_db(target_engine)

        with Session(target_engine) as session:
            log = ExecutionLog(
                id="exec_pg_test_1",
                target_id="sqlserver_prod",
                query="SELECT 1;",
                query_type="READ",
                status="COMPLETED",
                created_at=utc_now(),
            )
            session.add(log)
            session.commit()

            fetched = session.exec(select(ExecutionLog).where(ExecutionLog.id == "exec_pg_test_1")).first()
            assert fetched is not None
            assert fetched.query == "SELECT 1;"

    finally:
        target_engine.dispose()
        with admin_engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name} WITH (FORCE)"))
        admin_engine.dispose()
