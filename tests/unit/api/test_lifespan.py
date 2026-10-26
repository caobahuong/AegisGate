"""Unit tests for FastAPI lifespan startup and shutdown context manager."""

from unittest.mock import AsyncMock, patch

import pytest
from sqlmodel import Session

from core.database import init_db
from core.main import app, lifespan


@pytest.mark.asyncio
async def test_app_lifespan_startup_and_shutdown(db_engine, monkeypatch):
    """Verify lifespan context manager executes startup and shutdown sequences."""
    with patch("core.main.init_db") as mock_init_db, \
         patch("core.main.cluster_manager.start", AsyncMock()) as mock_cluster_start, \
         patch("core.main.cluster_manager.stop", AsyncMock()) as mock_cluster_stop, \
         patch("core.main.terminate_all_subprocesses", AsyncMock(return_value=0)) as mock_terminate, \
         patch("core.main.get_event_bus") as mock_get_bus:

        mock_bus = AsyncMock()
        mock_get_bus.return_value = mock_bus

        async with lifespan(app):
            mock_init_db.assert_called_once()
            mock_bus.start.assert_called_once()
            mock_cluster_start.assert_called_once()

        mock_cluster_stop.assert_called_once()
        mock_bus.stop.assert_called_once()
        mock_terminate.assert_called_once()
