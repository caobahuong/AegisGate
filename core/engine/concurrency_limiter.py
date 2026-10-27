"""Per-plugin bounded concurrency limiter and queue management.

Prevents target plugin overload and manages bounded queues with backpressure (HTTP 429).
Adheres strictly to python_clean_code.md:
- Full type hints
- Async context managers
- Domain exception handling
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncGenerator

from sqlmodel import Session

from core.config import settings
from core.database import ExecutionLog, utc_now
from core.engine.cluster import get_owner_id
from core.exceptions import ExecutionTimeoutError, PluginQueueFullError
from core.gateway.sse_broadcaster import sse_broadcaster
from core.storage.log_store import LogStore

logger = logging.getLogger(__name__)


class PluginConcurrencyLimiter:
    """Manages active concurrency slots and bounded queue backlog for a specific plugin target."""

    def __init__(self, target_id: str, max_concurrency: int, max_queue_size: int) -> None:
        self.target_id = target_id
        self.max_concurrency = max_concurrency
        self.max_queue_size = max_queue_size
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._queue_depth = 0
        self._lock = asyncio.Lock()

    @property
    def queue_depth(self) -> int:
        return self._queue_depth

    @contextlib.asynccontextmanager
    async def acquire_slot(
        self,
        session: Session,
        log: ExecutionLog,
        timeout_seconds: float | None = None,
    ) -> AsyncGenerator[None, None]:
        """Acquire an execution concurrency slot.

        If immediate slot is unavailable:
        - If backlog is full, raises PluginQueueFullError (HTTP 429).
        - Otherwise, moves execution to QUEUED state and emits 'execution_queued' event.
        - Waits up to timeout_seconds.
        - Once acquired, restores EXECUTING state.
        """
        effective_timeout = timeout_seconds if timeout_seconds is not None else settings.PLUGIN_QUEUE_TIMEOUT_SECONDS

        async with self._lock:
            if self._queue_depth >= self.max_queue_size:
                logger.warning(
                    "Plugin queue for %s is full (%d >= %d). Rejecting request.",
                    self.target_id,
                    self._queue_depth,
                    self.max_queue_size,
                )
                raise PluginQueueFullError(
                    f"Execution queue backlog for plugin '{self.target_id}' is full (max {self.max_queue_size})."
                )
            self._queue_depth += 1

        slot_acquired = False
        log_store = LogStore(session)

        try:
            # Check if semaphore can be acquired immediately without waiting
            if self._semaphore.locked():
                # Needs to wait in queue: transition to QUEUED
                won = log_store.transition_status(
                    log.id,
                    ("EXECUTING", "DRY_RUN", "PAUSED_FOR_REVIEW"),
                    {"status": "QUEUED"},
                )
                if won:
                    session.refresh(log)
                    await sse_broadcaster.broadcast(
                        "execution_queued",
                        {
                            "execution_id": log.id,
                            "target_id": self.target_id,
                            "status": "QUEUED",
                            "queue_depth": self._queue_depth,
                        },
                    )

            try:
                await asyncio.wait_for(self._semaphore.acquire(), timeout=effective_timeout)
                slot_acquired = True
            except TimeoutError as exc:
                # Timed out waiting in queue
                logger.warning("Execution %s timed out waiting for %s slot", log.id, self.target_id)
                log_store.transition_status(
                    log.id,
                    ("QUEUED", "EXECUTING"),
                    {
                        "status": "TIMEOUT",
                        "error_message": f"Plugin execution queue wait timeout ({effective_timeout}s) exceeded.",
                        "finished_at": utc_now(),
                    },
                )
                session.refresh(log)
                await sse_broadcaster.broadcast(
                    "execution_timeout",
                    {"execution_id": log.id, "error": f"Queue timeout exceeded ({effective_timeout}s)"},
                )
                raise ExecutionTimeoutError(
                    f"Plugin execution queue wait timeout ({effective_timeout}s) exceeded."
                ) from exc

            # Once acquired, transition to EXECUTING
            log_store.transition_status(
                log.id,
                ("QUEUED", "DRY_RUN", "PAUSED_FOR_REVIEW"),
                {
                    "status": "EXECUTING",
                    "owner_id": get_owner_id(),
                    "started_at": utc_now(),
                },
            )
            session.refresh(log)

            yield

        finally:
            async with self._lock:
                self._queue_depth = max(0, self._queue_depth - 1)
            if slot_acquired:
                self._semaphore.release()


class ConcurrencyLimiterRegistry:
    """Registry maintaining per-plugin concurrency limiters."""

    def __init__(self) -> None:
        self._limiters: dict[str, PluginConcurrencyLimiter] = {}
        self._lock = asyncio.Lock()

    async def get_limiter(self, target_id: str) -> PluginConcurrencyLimiter:
        """Get or create the concurrency limiter for a target plugin."""
        async with self._lock:
            if target_id not in self._limiters:
                self._limiters[target_id] = PluginConcurrencyLimiter(
                    target_id=target_id,
                    max_concurrency=settings.PLUGIN_MAX_CONCURRENCY,
                    max_queue_size=settings.PLUGIN_QUEUE_MAXSIZE,
                )
            return self._limiters[target_id]


limiter_registry = ConcurrencyLimiterRegistry()
