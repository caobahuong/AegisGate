"""Prepare isolated benchmark database with test plugins and rules."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import contextlib

from sqlmodel import Session, create_engine

from core.database import PluginProfile, init_db

db_file = BASE_DIR / "data" / "perf_test.db"

if db_file.exists():
    with contextlib.suppress(OSError):
        db_file.unlink()

engine = create_engine(f"sqlite:///{db_file}")
init_db(engine)

with Session(engine) as session:
    existing = session.get(PluginProfile, "sqlserver_prod")
    if not existing:
        session.add(
            PluginProfile(
                id="sqlserver_prod",
                name="SQL Server Prod Simulated",
                driver="sqlserver",
                entrypoint="python plugins/sqlserver_plugin/adapter.py --serve",
                config_json='{"use_simulation": "true"}',
            )
        )
        session.commit()

engine.dispose()
print("Initialized perf_test.db successfully at", db_file)
