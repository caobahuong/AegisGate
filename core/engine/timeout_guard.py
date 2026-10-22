"""Timeout Guard Module for strictly enforcing execution limits (15s / 30s).

Adheres strictly to python_clean_code.md:
- No hardcoded values (reads from config.py)
- Full async/await discipline using asyncio.wait_for
- Custom ExecutionTimeoutError raised on threshold breach
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from core.config import settings
from core.exceptions import ExecutionTimeoutError

T = TypeVar("T")


class TimeoutGuard:
    """Calculates query timeouts and executes coroutines with strict time limits."""

    @staticmethod
    def get_timeout_for_query(query_type: str, custom_limit: float | None = None) -> float:
        """Resolve maximum allowed execution duration based on query type or rule."""
        if custom_limit is not None and custom_limit > 0:
            return custom_limit

        if query_type.upper() == "WRITE":
            return settings.WRITE_TIMEOUT_SECONDS
        return settings.READ_TIMEOUT_SECONDS

    @staticmethod
    async def run_with_timeout(
        coro: Awaitable[T],
        timeout_seconds: float,
        on_timeout_abort: Callable[[], Awaitable[Any]] | None = None,
    ) -> T:
        """Execute a coroutine within strict timeout.
        
        If timeout is exceeded, invokes the on_timeout_abort hook to kill the session
        on the target system, then raises ExecutionTimeoutError.
        """
        try:
            return await asyncio.wait_for(coro, timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            if on_timeout_abort:
                try:
                    await on_timeout_abort()
                except Exception:
                    pass
            raise ExecutionTimeoutError(
                f"Execution exceeded maximum allowed timeout of {timeout_seconds:.1f} seconds."
            ) from exc

