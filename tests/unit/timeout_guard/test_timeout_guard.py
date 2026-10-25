"""Unit tests for TimeoutGuard execution and abort triggers."""

import asyncio

import pytest

from core.engine.timeout_guard import ExecutionTimeoutError, TimeoutGuard


def test_timeout_calculation():
    """Verify default and custom timeout calculations based on query type."""
    assert TimeoutGuard.get_timeout_for_query("READ") == 15.0
    assert TimeoutGuard.get_timeout_for_query("WRITE") == 30.0
    assert TimeoutGuard.get_timeout_for_query("READ", custom_limit=5.0) == 5.0


@pytest.mark.asyncio
async def test_run_with_timeout_success():
    """Verify successful execution within timeout limits."""

    async def quick_coro():
        await asyncio.sleep(0.01)
        return "SUCCESS"

    result = await TimeoutGuard.run_with_timeout(quick_coro(), timeout_seconds=1.0)
    assert result == "SUCCESS"


@pytest.mark.asyncio
async def test_run_with_timeout_trigger_abort_hook():
    """Verify ExecutionTimeoutError raised and abort hook invoked on timeout."""
    abort_called = False

    async def slow_coro():
        await asyncio.sleep(0.5)
        return "DONE"

    async def abort_hook():
        nonlocal abort_called
        abort_called = True

    with pytest.raises(ExecutionTimeoutError):
        await TimeoutGuard.run_with_timeout(
            slow_coro(),
            timeout_seconds=0.05,
            on_timeout_abort=abort_hook,
        )

    assert abort_called is True
