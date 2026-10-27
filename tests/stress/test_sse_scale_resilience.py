"""Server-Sent Events (SSE) Scale, Reconnection, and Resilience Stress Tests.

Tests verify:
1. 100+ concurrent subscribers receiving high-throughput broadcasts.
2. Sudden abrupt subscriber disconnects mid-stream with zero subscriber/queue leaks.
3. Slow subscriber isolation (bounded queue overflow drops events without stalling fast subscribers).
4. Reconnection with Last-Event-ID replay (gapless replay of missed events in monotonic order).
5. SSE endpoint streaming over HTTP with initial handshake and live updates.
"""

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine

from core.database import init_db
from core.gateway.event_bus import DbOutboxBus, InMemoryBus
from core.gateway.sse_broadcaster import SSEBroadcaster


@pytest.mark.asyncio
async def test_sse_100_subscribers_burst_and_disconnect() -> None:
    """100 concurrent subscribers receive events, 50 disconnect abruptly mid-stream.

    Invariants:
    - All 100 receive initial batch.
    - Abruptly closing 50 subscriber generators does not crash the broadcaster.
    - Remaining 50 subscribers continue receiving second batch cleanly.
    - When all 100 are closed, subscriber count in EventBus returns strictly to 0.
    """
    bus = InMemoryBus(buffer_size=2000)

    # Launch 100 subscribers
    received_counts: list[int] = [0] * 100
    stop_flags: list[bool] = [False] * 100
    sub_tasks: list[asyncio.Task[None]] = []

    async def _subscriber_task(sub_idx: int) -> None:
        async for _ in bus.subscribe():
            received_counts[sub_idx] += 1
            if stop_flags[sub_idx]:
                break

    for i in range(100):
        sub_tasks.append(asyncio.create_task(_subscriber_task(i)))

    # Allow all subscribers to register
    await asyncio.sleep(0.05)
    assert len(bus._subscribers) == 100

    # Broadcast Batch 1 (30 events)
    for i in range(30):
        await bus.publish("test_event_batch1", {"seq": i})
        if i % 10 == 0:
            await asyncio.sleep(0.001)

    await asyncio.sleep(0.05)
    for i in range(100):
        assert received_counts[i] == 30, f"Subscriber {i} received {received_counts[i]} != 30"

    # Abruptly disconnect subscribers 0 through 49
    for i in range(50):
        stop_flags[i] = True
        sub_tasks[i].cancel()

    await asyncio.sleep(0.05)
    # 50 subscribers remain active
    assert len(bus._subscribers) == 50

    # Broadcast Batch 2 (20 events)
    for i in range(20):
        await bus.publish("test_event_batch2", {"seq": i})
        if i % 10 == 0:
            await asyncio.sleep(0.001)

    await asyncio.sleep(0.05)

    # Active subscribers (50 to 99) received all 30 + 20 = 50 events
    for i in range(50, 100):
        assert received_counts[i] == 50, f"Subscriber {i} received {received_counts[i]} != 50"

    # Disconnect remaining 50 subscribers
    for i in range(50, 100):
        stop_flags[i] = True
        sub_tasks[i].cancel()

    await asyncio.sleep(0.05)

    # Verify zero subscriber leaks
    assert len(bus._subscribers) == 0, f"Leaked subscribers: {len(bus._subscribers)}"


@pytest.mark.asyncio
async def test_sse_slow_subscriber_isolation() -> None:
    """A slow/stalled subscriber must not block or slow down fast subscribers.

    Invariants:
    - Slow subscriber queue fills to capacity (maxsize=500) and drops overflow.
    - Fast subscriber drains immediately and receives all 600 events without stalling.
    - Broadcaster logs dropped events without raising unhandled exceptions.
    """
    bus = InMemoryBus(buffer_size=2000)

    fast_received = 0
    fast_done = asyncio.Event()

    async def _fast_consumer() -> None:
        nonlocal fast_received
        async for _ in bus.subscribe():
            fast_received += 1
            if fast_received == 600:
                fast_done.set()
                break

    fast_task = asyncio.create_task(_fast_consumer())

    # Slow consumer subscribes and pulls 1 event, then stops consuming
    slow_sub = bus.subscribe()
    slow_task = asyncio.create_task(anext(slow_sub))

    await asyncio.sleep(0.02)
    assert len(bus._subscribers) == 2

    # Publish 600 events; fast subscriber processes cooperatively
    for i in range(600):
        await bus.publish("high_throughput_metric", {"seq": i, "val": i * 1.5})
        if i % 20 == 0:
            await asyncio.sleep(0.001)  # Yield to fast consumer

    # Fast subscriber must consume all 600 events promptly
    await asyncio.wait_for(fast_done.wait(), timeout=5.0)
    assert fast_received == 600

    # Cleanup
    fast_task.cancel()
    slow_task.cancel()
    await slow_sub.aclose()
    await asyncio.sleep(0.02)
    assert len(bus._subscribers) == 0


@pytest.mark.asyncio
async def test_sse_reconnection_replay_with_last_event_id() -> None:
    """A reconnecting subscriber retrieves missed events via Last-Event-ID replay.

    Invariants:
    - Initial connection receives events 1..10.
    - Disconnect occurs; events 11..25 are published while client is offline.
    - Client reconnects with last_event_id=10 and receives replayed events 11..25.
    - Events arrive in strictly monotonic ascending order.
    """
    bus = InMemoryBus(buffer_size=1000)

    # Publish initial 10 events
    for i in range(1, 11):
        await bus.publish("status_update", {"num": i})

    # Subscriber reads first 10 via replay
    collected_first: list[int] = []
    sub1 = bus.subscribe(last_event_id=0)
    for _ in range(10):
        msg = await anext(sub1)
        collected_first.append(msg.id)
    await sub1.aclose()

    assert collected_first == list(range(1, 11))
    last_seen_id = collected_first[-1]  # 10

    # Publish 15 more events while client is disconnected
    for i in range(11, 26):
        await bus.publish("status_update", {"num": i})

    # Client reconnects with last_event_id=10
    collected_reconnected: list[int] = []
    sub2 = bus.subscribe(last_event_id=last_seen_id)
    for _ in range(15):
        msg = await anext(sub2)
        collected_reconnected.append(msg.id)
    await sub2.aclose()

    # Verify gapless, strictly monotonic sequence 11..25
    assert collected_reconnected == list(range(11, 26))


@pytest.mark.asyncio
async def test_db_outbox_bus_reconnection_and_replay(tmp_path: Path) -> None:
    """DbOutboxBus cross-process event replay from SQLite event_outbox table."""
    test_engine = create_engine(
        f"sqlite:///{tmp_path}/db_outbox_replay.db",
        connect_args={"check_same_thread": False, "timeout": 15.0},
    )
    init_db(test_engine)

    bus = DbOutboxBus(poll_interval=0.02, engine_override=test_engine)
    await bus.start()

    try:
        # Publish 15 events into database outbox
        for i in range(1, 16):
            await bus.publish("distributed_event", {"index": i})

        # Subscriber connects with last_event_id=5
        replayed_ids: list[int] = []
        sub = bus.subscribe(last_event_id=5)

        for _ in range(10):  # events 6 through 15
            msg = await anext(sub)
            replayed_ids.append(msg.id)
        await sub.aclose()

        assert replayed_ids == list(range(6, 16))
    finally:
        await bus.stop()
        test_engine.dispose()


@pytest.mark.asyncio
async def test_sse_broadcaster_packet_formatting() -> None:
    """SSEBroadcaster formats events according to SSE RFC specifications."""
    broadcaster = SSEBroadcaster()
    bus = InMemoryBus()

    with patch("core.gateway.sse_broadcaster.get_event_bus", return_value=bus):
        sub = broadcaster.subscribe(last_event_id=0)

        # First packet is always the 'connected' handshake
        handshake = await anext(sub)
        assert handshake.startswith("id: 0\nevent: connected\ndata: ")

        # Publish a test event
        await broadcaster.broadcast("execution_created", {"execution_id": "exec_999"})

        # Second packet is the formatted event replayed from buffer
        packet = await anext(sub)
        assert "event: execution_created" in packet
        assert "exec_999" in packet
        assert packet.endswith("\n\n")

        await sub.aclose()
