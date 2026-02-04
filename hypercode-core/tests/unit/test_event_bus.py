import pytest
import pytest_asyncio
import asyncio
import fakeredis.aioredis
from app.core.event_bus import event_bus

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
async def test_publish_subscribe_roundtrip():
    channel = "test:events"
    msg = {"hello": "world"}
    async def collect():
        gen = event_bus.subscribe(channel)
        async for m in gen:
            return m
    t = asyncio.create_task(collect())
    await asyncio.sleep(0.05)
    await event_bus.publish(channel, msg)
    got = await asyncio.wait_for(t, timeout=1.0)
    assert got == msg
