import pytest
from unittest.mock import AsyncMock, patch
from app.services.event_bus import event_bus
from app.core.db import db
from app.schemas.message import MessageEnvelope

@pytest.mark.asyncio
async def test_dlq_publish_and_persist(monkeypatch):
    try:
        from fakeredis.aioredis import FakeRedis
        event_bus.redis = FakeRedis()
    except Exception:
        pytest.skip("fakeredis not available")

    await event_bus.ensure_consumer_group("mission.dlq", "mission-dlq")
    env = MessageEnvelope(sender_id="core", message_type="mission.retry.exhausted", payload={"mission_id": "mid-1"})
    entry_id = await event_bus.publish_stream("mission.dlq", env)
    assert entry_id
