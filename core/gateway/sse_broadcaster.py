"""Server-Sent Events (SSE) Broadcaster Adapter for AegisGate Core.

Adapts the underlying EventBus (InMemoryBus or DbOutboxBus) to provide
backward-compatible broadcasting and SSE subscriptions.
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from core.gateway.event_bus import get_event_bus


class SSEBroadcaster:
    """Thin backward-compatible adapter delegating to the configured EventBus."""

    async def subscribe(self, last_event_id: int | None = None) -> AsyncGenerator[str, None]:
        """Subscribe to SSE stream, yielding standard SSE protocol chunks."""
        bus = get_event_bus()

        # Emit initial connected packet
        init_packet = json.dumps({"event": "connected", "data": {"message": "AegisGate SSE Connected"}})
        yield f"id: 0\nevent: connected\ndata: {init_packet}\n\n"

        async for msg in bus.subscribe(last_event_id=last_event_id):
            yield msg.to_sse_packet()

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> int:
        """Broadcast an event payload via the configured EventBus."""
        bus = get_event_bus()
        return await bus.publish(event_type, payload)


# Global singleton instance
sse_broadcaster = SSEBroadcaster()
