import pytest
import pytest_asyncio
import asyncio
import fakeredis.aioredis
from app.services.event_bus import event_bus
from app.schemas.message import MessageEnvelope

@pytest_asyncio.fixture(autouse=True)
async def patch_redis():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    event_bus.redis = fake
    yield fake
    if hasattr(fake, "aclose"):
        await fake.aclose()
    else:
        await fake.close()

@pytest.mark.asyncio
async def test_publish_subscribe_envelope_roundtrip():
    channel = "system.events"
    env = MessageEnvelope(sender_id="a", message_type="system_event", payload={"x": 1})
    async def collect():
        gen = event_bus.subscribe(channel, role="general")
        async for m in gen:
            return m
    t = asyncio.create_task(collect())
    await asyncio.sleep(0.05)
    ok = await event_bus.publish(channel, env, role="general")
    assert ok is True
    got = await asyncio.wait_for(t, timeout=1.0)
    assert isinstance(got, MessageEnvelope)
    assert got.payload["x"] == 1
