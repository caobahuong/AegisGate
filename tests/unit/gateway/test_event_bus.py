"""Unit tests for EventBus (InMemoryBus, DbOutboxBus) and SSE reconnection replay."""

import asyncio

import pytest

from core.gateway.event_bus import DbOutboxBus, InMemoryBus, get_event_bus
from core.gateway.sse_broadcaster import sse_broadcaster


@pytest.mark.asyncio
async def test_in_memory_bus_publish_and_subscribe():
    bus = InMemoryBus(buffer_size=100)

    # 1. Publish before subscriber to test ring-buffer storage
    id1 = await bus.publish("execution_created", {"id": "exec_001"})
    id2 = await bus.publish("execution_completed", {"id": "exec_001", "status": "COMPLETED"})
    assert id1 == 1
    assert id2 == 2

    # 2. Subscribe with last_event_id=1 -> should replay event id 2
    received = []

    async def reader():
        async for msg in bus.subscribe(last_event_id=1):
            received.append(msg)
            if len(received) >= 2:
                break

    read_task = asyncio.create_task(reader())
    await asyncio.sleep(0.05)

    # 3. Publish a new event while subscription is active
    id3 = await bus.publish("execution_paused", {"id": "exec_002"})
    assert id3 == 3

    await asyncio.wait_for(read_task, timeout=2.0)

    assert len(received) == 2
    # First was the replayed event (id 2)
    assert received[0].id == 2
    assert received[0].event_type == "execution_completed"
    # Second was the live event (id 3)
    assert received[1].id == 3
    assert received[1].event_type == "execution_paused"


@pytest.mark.asyncio
async def test_db_outbox_bus_publish_and_replay(db_engine):
    bus = DbOutboxBus(poll_interval=0.05, engine_override=db_engine)
    await bus.start()

    try:
        id1 = await bus.publish("plugin_installed", {"plugin_id": "test_plugin"})
        id2 = await bus.publish("execution_created", {"execution_id": "exec_outbox_1"})
        assert id2 > id1

        # Reconnect with last_event_id=id1
        received = []

        async def reader():
            async for msg in bus.subscribe(last_event_id=id1):
                received.append(msg)
                if len(received) >= 1:
                    break

        await asyncio.wait_for(reader(), timeout=3.0)

        assert len(received) == 1
        assert received[0].id == id2
        assert received[0].event_type == "execution_created"
        assert received[0].data["execution_id"] == "exec_outbox_1"
    finally:
        await bus.stop()


@pytest.mark.asyncio
async def test_sse_broadcaster_frames_and_replay():
    bus = get_event_bus()

    # 1. Test sse_broadcaster adapter yields formatted SSE frames
    gen = sse_broadcaster.subscribe(last_event_id=0)
    init_frame = await anext(gen)
    assert "id: 0" in init_frame
    assert "event: connected" in init_frame

    # 2. Publish an event to the bus and verify next frame format
    await bus.publish("execution_queued", {"id": "exec_test_sse"})
    event_frame = await anext(gen)
    assert "event: execution_queued" in event_frame
    assert "exec_test_sse" in event_frame
    assert "id: " in event_frame
