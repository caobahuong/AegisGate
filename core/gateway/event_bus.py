"""Event Bus Abstraction for Single-Process and Multi-Process AegisGate Deployments.

Provides decoupled event publication and subscription:
- InMemoryBus: Fast in-memory distribution with ring-buffer replay.
- DbOutboxBus: Multi-process coordination backed by `event_outbox` with monotonic IDs.
- Guaranteed SSE reconnection with Last-Event-ID replay.
"""

import abc
import asyncio
import contextlib
import json
import logging
from collections import deque
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlmodel import Session, col, select

from core.config import settings
from core.database import EventOutbox, engine

logger = logging.getLogger("AegisGate.EventBus")


@dataclass
class EventMessage:
    """Standardized event packet broadcast over the event bus."""

    id: int
    event_type: str
    data: dict[str, Any]
    created_at: datetime

    def to_sse_packet(self) -> str:
        """Serialize into valid Server-Sent Events (SSE) protocol chunk with ID."""
        payload = json.dumps({"event": self.event_type, "data": self.data})
        return f"id: {self.id}\nevent: {self.event_type}\ndata: {payload}\n\n"


class EventBus(abc.ABC):
    """Abstract Event Bus interface."""

    @abc.abstractmethod
    async def publish(self, event_type: str, data: dict[str, Any]) -> int:
        """Publish an event and return its monotonic event ID."""
        pass

    @abc.abstractmethod
    def subscribe(self, last_event_id: int | None = None) -> AsyncGenerator[EventMessage, None]:
        """Subscribe to live events, optionally replaying history from last_event_id."""
        raise NotImplementedError

    async def start(self) -> None:
        """Start any background tailing workers."""
        return None

    async def stop(self) -> None:
        """Stop background workers and cleanup resources."""
        return None


class InMemoryBus(EventBus):
    """In-memory event bus with ring buffer for replay on reconnect."""

    def __init__(self, buffer_size: int = 2000) -> None:
        self._counter: int = 0
        self._history: deque[EventMessage] = deque(maxlen=buffer_size)
        self._subscribers: set[asyncio.Queue[EventMessage]] = set()
        self._lock = asyncio.Lock()

    async def publish(self, event_type: str, data: dict[str, Any]) -> int:
        async with self._lock:
            self._counter += 1
            event_id = self._counter
            msg = EventMessage(
                id=event_id,
                event_type=event_type,
                data=data,
                created_at=datetime.now(UTC),
            )
            self._history.append(msg)
            subscribers_snapshot = list(self._subscribers)

        for queue in subscribers_snapshot:
            try:
                queue.put_nowait(msg)
            except asyncio.QueueFull:
                logger.warning("Subscriber queue full; dropping event %d", event_id)

        return event_id

    async def subscribe(self, last_event_id: int | None = None) -> AsyncGenerator[EventMessage, None]:
        queue: asyncio.Queue[EventMessage] = asyncio.Queue(maxsize=500)
        async with self._lock:
            # Gather replay events if requested
            replay_events: list[EventMessage] = []
            if last_event_id is not None:
                replay_events = [msg for msg in self._history if msg.id > last_event_id]

            self._subscribers.add(queue)

        try:
            # Yield historical replayed events first
            for replay_msg in replay_events:
                yield replay_msg

            while True:
                msg = await queue.get()
                yield msg
        except asyncio.CancelledError:
            pass
        finally:
            async with self._lock:
                self._subscribers.discard(queue)


class DbOutboxBus(EventBus):
    """Database-backed outbox bus enabling cross-process event synchronization."""

    def __init__(self, poll_interval: float | None = None, engine_override: Any = None) -> None:
        self.poll_interval = poll_interval or settings.OUTBOX_POLL_INTERVAL_SECONDS
        self._engine = engine_override or engine
        self._subscribers: set[asyncio.Queue[EventMessage]] = set()
        self._lock = asyncio.Lock()
        self._tail_task: asyncio.Task[None] | None = None
        self._running = False
        self._last_tail_id: int = 0

    async def start(self) -> None:
        if self._running:
            return
        self._running = True

        # Initialize last_tail_id to latest existing event to avoid flooding past history on boot
        with Session(self._engine) as session:
            latest = session.exec(select(EventOutbox).order_by(col(EventOutbox.id).desc()).limit(1)).first()
            if latest and latest.id is not None:
                self._last_tail_id = latest.id

        self._tail_task = asyncio.create_task(self._tail_outbox())
        logger.info("DbOutboxBus started tailing event_outbox from id=%d", self._last_tail_id)

    async def stop(self) -> None:
        self._running = False
        if self._tail_task:
            self._tail_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._tail_task
            self._tail_task = None
        logger.info("DbOutboxBus stopped")

    async def publish(self, event_type: str, data: dict[str, Any]) -> int:
        now = datetime.now(UTC)
        payload_str = json.dumps(data)

        # Write to database outbox table
        with Session(self._engine) as session:
            outbox_entry = EventOutbox(
                event_type=event_type,
                payload_json=payload_str,
                created_at=now,
            )
            session.add(outbox_entry)
            session.commit()
            session.refresh(outbox_entry)
            event_id = outbox_entry.id
            assert event_id is not None

        # Discard payload for notification
        msg = EventMessage(
            id=event_id,
            event_type=event_type,
            data=data,
            created_at=now,
        )

        # Promptly dispatch to local subscribers without waiting for tailer poll
        async with self._lock:
            if event_id > self._last_tail_id:
                self._last_tail_id = event_id
            subscribers_snapshot = list(self._subscribers)

        for queue in subscribers_snapshot:
            try:
                queue.put_nowait(msg)
            except asyncio.QueueFull:
                logger.warning("Local subscriber queue full; dropping event %d", event_id)

        return event_id

    async def _tail_outbox(self) -> None:
        """Poll the event_outbox table for new events produced by other processes."""
        while self._running:
            try:
                await asyncio.sleep(self.poll_interval)
                with Session(self._engine) as session:
                    stmt = (
                        select(EventOutbox)
                        .where(col(EventOutbox.id) > self._last_tail_id)
                        .order_by(col(EventOutbox.id).asc())
                        .limit(200)
                    )
                    new_events = session.exec(stmt).all()

                if new_events:
                    async with self._lock:
                        subscribers_snapshot = list(self._subscribers)

                    for item in new_events:
                        assert item.id is not None
                        if item.id <= self._last_tail_id:
                            continue
                        self._last_tail_id = item.id

                        try:
                            parsed_data = json.loads(item.payload_json)
                        except Exception:
                            parsed_data = {}

                        msg = EventMessage(
                            id=item.id,
                            event_type=item.event_type,
                            data=parsed_data,
                            created_at=item.created_at,
                        )

                        for queue in subscribers_snapshot:
                            with contextlib.suppress(asyncio.QueueFull):
                                queue.put_nowait(msg)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("Error while tailing event_outbox: %s", exc)

    async def subscribe(self, last_event_id: int | None = None) -> AsyncGenerator[EventMessage, None]:
        queue: asyncio.Queue[EventMessage] = asyncio.Queue(maxsize=500)

        # 1. Fetch replay events from database if last_event_id specified
        replay_events: list[EventMessage] = []
        if last_event_id is not None:
            with Session(self._engine) as session:
                stmt = (
                    select(EventOutbox)
                    .where(col(EventOutbox.id) > last_event_id)
                    .order_by(col(EventOutbox.id).asc())
                    .limit(500)
                )
                replayed = session.exec(stmt).all()
                for item in replayed:
                    assert item.id is not None
                    try:
                        p_data = json.loads(item.payload_json)
                    except Exception:
                        p_data = {}
                    replay_events.append(
                        EventMessage(
                            id=item.id,
                            event_type=item.event_type,
                            data=p_data,
                            created_at=item.created_at,
                        )
                    )

        async with self._lock:
            self._subscribers.add(queue)

        try:
            # Yield historical replayed events first
            seen_ids: set[int] = set()
            for r_msg in replay_events:
                seen_ids.add(r_msg.id)
                yield r_msg

            while True:
                msg = await queue.get()
                if msg.id not in seen_ids:
                    seen_ids.add(msg.id)
                    yield msg
        except asyncio.CancelledError:
            pass
        finally:
            async with self._lock:
                self._subscribers.discard(queue)


# Singleton factory
_event_bus_instance: EventBus | None = None


def get_event_bus() -> EventBus:
    """Return configured EventBus singleton instance."""
    global _event_bus_instance
    if _event_bus_instance is None:
        if settings.EVENT_BUS.lower() == "db":
            logger.info("Initializing DbOutboxBus for multi-process distributed events")
            _event_bus_instance = DbOutboxBus()
        else:
            logger.info("Initializing InMemoryBus for single-process events")
            _event_bus_instance = InMemoryBus()
    return _event_bus_instance
