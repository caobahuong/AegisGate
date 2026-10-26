"""Comprehensive unit tests for SSE Broadcaster and EventBus edge cases.

Specifically verifies:
1. Client disconnect mid-stream (GeneratorExit and task cancellation) clean cleanup (no subscriber leak).
2. Slow subscriber queue full handling (event dropping without crashing other subscribers).
3. Multiple concurrent subscribers receiving identical broadcasted events.
4. DbOutboxBus tailer polling events inserted directly into DB outbox (simulating multi-process).
5. DbOutboxBus corrupt JSON payload parsing recovery (fallback to {}).
6. EventBus factory selection based on settings (db vs memory).
"""

import asyncio
import contextlib
import json
from unittest.mock import patch

import pytest
from sqlmodel import Session

from core.config import settings
from core.database import EventOutbox, utc_now
from core.gateway.event_bus import (
    DbOutboxBus,
    EventMessage,
    InMemoryBus,
    get_event_bus,
    set_event_bus,
)


@pytest.mark.asyncio
async def test_subscriber_disconnect_no_leak():
    """Verify that when an SSE subscriber disconnects mid-stream, it cleanly unsubscribes."""
    bus = InMemoryBus()
    assert len(bus._subscribers) == 0

    sub_gen = bus.subscribe()
    # Advance generator to register subscriber
    task = asyncio.create_task(sub_gen.__anext__())
    await asyncio.sleep(0.02)
    assert len(bus._subscribers) == 1

    # Simulate client disconnect by canceling consumer task and closing generator
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
        await task
    await sub_gen.aclose()

    # Subscriber queue must be cleaned up
    assert len(bus._subscribers) == 0


@pytest.mark.asyncio
async def test_multiple_concurrent_subscribers():
    """Verify multiple subscribers concurrently receive the exact same sequence of events."""
    bus = InMemoryBus()
    results1: list[EventMessage] = []
    results2: list[EventMessage] = []
    results3: list[EventMessage] = []

    async def consume(collector: list[EventMessage], count: int):
        async for msg in bus.subscribe():
            collector.append(msg)
            if len(collector) >= count:
                break

    t1 = asyncio.create_task(consume(results1, 3))
    t2 = asyncio.create_task(consume(results2, 3))
    t3 = asyncio.create_task(consume(results3, 3))
    await asyncio.sleep(0.02)
    assert len(bus._subscribers) == 3

    await bus.publish("event_a", {"num": 1})
    await bus.publish("event_b", {"num": 2})
    await bus.publish("event_c", {"num": 3})

    await asyncio.wait_for(asyncio.gather(t1, t2, t3), timeout=2.0)

    for res in (results1, results2, results3):
        assert len(res) == 3
        assert [m.event_type for m in res] == ["event_a", "event_b", "event_c"]
        assert [m.data["num"] for m in res] == [1, 2, 3]

    # After consumption completes, all 3 subscribers clean up
    assert len(bus._subscribers) == 0


@pytest.mark.asyncio
async def test_slow_subscriber_queue_full_dropping():
    """Verify that when a subscriber is too slow and queue is full, events are dropped without crashing."""
    bus = InMemoryBus()

    # Create a subscriber with tiny queue size
    tiny_queue: asyncio.Queue[EventMessage] = asyncio.Queue(maxsize=2)
    bus._subscribers.add(tiny_queue)

    # Publish 4 events
    for i in range(4):
        await bus.publish("ping", {"idx": i})

    # First 2 events queued, 3rd and 4th dropped
    assert tiny_queue.qsize() == 2
    msg1 = tiny_queue.get_nowait()
    msg2 = tiny_queue.get_nowait()
    assert msg1.data["idx"] == 0
    assert msg2.data["idx"] == 1

    bus._subscribers.clear()


@pytest.mark.asyncio
async def test_db_outbox_bus_tailer_cross_process(db_engine):
    """Verify DbOutboxBus polls events inserted directly into DB by other processes."""
    bus = DbOutboxBus(poll_interval=0.02, engine_override=db_engine)
    await bus.start()

    try:
        received = []

        async def reader():
            async for msg in bus.subscribe():
                received.append(msg)
                if len(received) >= 2:
                    break

        read_task = asyncio.create_task(reader())
        await asyncio.sleep(0.05)

        # Simulate another process writing directly to event_outbox table
        with Session(db_engine) as session:
            outbox1 = EventOutbox(
                event_type="cross_proc_1",
                payload_json=json.dumps({"worker": "worker_beta", "status": "active"}),
                created_at=utc_now(),
            )
            outbox2 = EventOutbox(
                event_type="cross_proc_2",
                payload_json="invalid json string {",  # Corrupt JSON fallback test
                created_at=utc_now(),
            )
            session.add(outbox1)
            session.add(outbox2)
            session.commit()

        # Wait for tailer loop to pick them up
        await asyncio.wait_for(read_task, timeout=3.0)

        assert len(received) == 2
        assert received[0].event_type == "cross_proc_1"
        assert received[0].data["worker"] == "worker_beta"
        # Corrupt JSON handled gracefully
        assert received[1].event_type == "cross_proc_2"
        assert received[1].data == {}
    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_event_bus_factory_and_sse_packet():
    """Verify get_event_bus() initializes correct bus based on settings."""
    set_event_bus(None)

    # 1. Test memory bus default
    with patch.object(settings, "EVENT_BUS", "memory"):
        bus_mem = get_event_bus()
        assert isinstance(bus_mem, InMemoryBus)

    # 2. Test DB outbox bus selection
    set_event_bus(None)
    with patch.object(settings, "EVENT_BUS", "db"):
        bus_db = get_event_bus()
        assert isinstance(bus_db, DbOutboxBus)

    set_event_bus(None)

    # 3. Test EventMessage.to_sse_packet() formatting
    msg = EventMessage(
        id=123,
        event_type="query_executed",
        data={"rows": 5},
        created_at=utc_now(),
    )
    packet = msg.to_sse_packet()
    assert "id: 123\n" in packet
    assert "event: query_executed\n" in packet
    assert 'data: {"event": "query_executed", "data": {"rows": 5}}\n\n' in packet
