"""Server-Sent Events (SSE) Broadcaster for real-time Dashboard state streaming.

Adheres to typescript_clean_code.md & python_clean_code.md:
- Full lifecycle management (allows client cleanup to prevent memory leaks)
- Asynchronous non-blocking message distribution
- Type annotations 100%
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

logger = logging.getLogger(__name__)


class SSEBroadcaster:
    """PubSub event hub for broadcasting execution state changes to UI clients."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> AsyncGenerator[str, None]:
        """Subscribe a new client to the SSE event stream."""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers.add(queue)
            logger.debug("New SSE client subscribed. Total clients: %d", len(self._subscribers))

        try:
            # Yield initial connection heartbeat
            init_packet = json.dumps({"event": "connected", "data": {"message": "AegisGate SSE Connected"}})
            yield f"data: {init_packet}\n\n"

            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            async with self._lock:
                self._subscribers.discard(queue)
                logger.debug("SSE client disconnected. Total clients: %d", len(self._subscribers))

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        """Broadcast an event payload to all currently active SSE subscribers."""
        message = json.dumps({"event": event_type, "data": payload})
        async with self._lock:
            subscribers_snapshot = list(self._subscribers)

        for queue in subscribers_snapshot:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("Client queue full, dropping SSE message")


# Global singleton instance
sse_broadcaster = SSEBroadcaster()
