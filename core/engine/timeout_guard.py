"""Timeout Guard Module for strictly enforcing execution limits (15s / 30s).

Adheres strictly to python_clean_code.md:
- No hardcoded values (reads from config.py)
- Full async/await discipline using asyncio.wait_for
- Custom ExecutionTimeoutError raised on threshold breach
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from core.config import settings
from core.exceptions import ExecutionTimeoutError

T = TypeVar("T")
logger = logging.getLogger(__name__)


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
        except TimeoutError as exc:
            abort_failure: str | None = None
            if on_timeout_abort:
                try:
                    await on_timeout_abort()
                except Exception as abort_exc:
                    # A failed kill means the query may still be running on the target:
                    # never swallow it silently, surface it in the log and the error.
                    logger.exception("Emergency abort hook failed after timeout")
                    abort_failure = str(abort_exc) or type(abort_exc).__name__
            message = f"Execution exceeded maximum allowed timeout of {timeout_seconds:.1f} seconds."
            if abort_failure:
                message += (
                    f" WARNING: emergency abort FAILED ({abort_failure}); the query may still be running on the target."
                )
            raise ExecutionTimeoutError(message, details={"abort_failed": abort_failure is not None}) from exc
