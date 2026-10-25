"""Global pytest configuration and fixtures for AegisGate test suite.

Provides:
- Isolated SQLite database engine and session fixtures (db_engine, db_session)
- FastAPI TestClient fixture with dependency override (api_client)
- Isolated PLUGINS_DIR sandbox fixture (tmp_plugins_dir)
- Automated persistent worker process cleanup (worker_cleanup)
- Simulated plugin profile fixture (sim_plugin_profile)
- Pollution guard hook (pytest_sessionfinish) ensuring git cleanliness
"""

import contextlib
import shutil
import subprocess
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from core.config import settings
from core.database import PluginProfile, get_session
from core.engine.plugin_client import terminate_all_subprocesses
from core.main import app
from tests.factories import make_plugin_profile


@pytest.fixture
def db_engine(tmp_path: Path):
    """Provide an isolated SQLite database engine for testing."""
    db_file = tmp_path / "aegisgate_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Provide a clean, isolated database session."""
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient wired to the isolated test database."""

    def override_get_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def tmp_plugins_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide an isolated plugins directory pre-populated with bundled plugins."""
    plugins_sandbox = tmp_path / "plugins"
    plugins_sandbox.mkdir(parents=True, exist_ok=True)

    real_plugins = settings.BASE_DIR / "plugins"
    for name in ["sqlserver_plugin", "mongodb_plugin", "templates"]:
        src = real_plugins / name
        if src.exists() and src.is_dir():
            shutil.copytree(src, plugins_sandbox / name, dirs_exist_ok=True)

    monkeypatch.setattr(settings, "PLUGINS_DIR", plugins_sandbox)
    return plugins_sandbox


@pytest.fixture(autouse=True)
async def worker_cleanup() -> AsyncGenerator[None, None]:
    """Ensure persistent worker subprocesses are cleanly terminated after each test."""
    yield
    with contextlib.suppress(Exception):
        await terminate_all_subprocesses()


@pytest.fixture
def sim_plugin_profile(db_session: Session) -> PluginProfile:
    """Create and persist a default simulated SQL Server plugin profile."""
    profile = make_plugin_profile(
        id="sqlserver_prod",
        name="SQL Server Enterprise",
        driver="sqlserver",
        entrypoint="python plugins/sqlserver_plugin/adapter.py --serve",
        config={"use_simulation": "true"},
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)
    return profile


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Pollution Guard: verify the test run did not modify or leave untracked files in git."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(settings.BASE_DIR),
        )
        if res.returncode == 0 and res.stdout.strip():
            # Ignore cache paths that might legitimately exist
            dirty_lines = [
                line
                for line in res.stdout.strip().splitlines()
                if not any(
                    cache_dir in line for cache_dir in [".pytest_cache", ".ruff_cache", ".mypy_cache", ".coverage"]
                )
            ]
            if dirty_lines:
                print("\n\n" + "=" * 70)
                print("[POLLUTION GUARD ERROR] Test suite left git working tree dirty:")
                for line in dirty_lines:
                    print(f"  {line}")
                print("=" * 70 + "\n")
                session.exitstatus = 1
    except Exception as exc:
        print(f"[POLLUTION GUARD WARNING] Could not verify git status: {exc}")
