import pytest
import time
from unittest.mock import AsyncMock, patch
from app.services.event_bus import event_bus
from app.services.orchestrator import orchestrator
from app.schemas.mission import MissionState
from app.core.db import db

@pytest.mark.asyncio
async def test_retry_flow_schedules_and_requeues(monkeypatch):
    try:
        from fakeredis.aioredis import FakeRedis
        event_bus.redis = FakeRedis()
        orchestrator.redis = event_bus.redis
    except Exception:
        pytest.skip("fakeredis not available")

    mid = "mission-int-1"
    key = await orchestrator._key(mid)
    await orchestrator.redis.hset(key, mapping={
        "id": mid,
        "title": "Integration Mission",
        "state": MissionState.FAILED.value,
        "priority": 50,
        "agent_id": "agent-x",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    })

    await event_bus.redis.set(f"mission:{mid}:retries", "1")
    ok, delay = await event_bus.schedule_retry(mid, 1, base=1.0, factor=2.0, jitter=0.0, max_delay=10.0, max_retries=5)
    assert ok

    due = await event_bus.dequeue_due_retries(time.time() + 1000)
    assert mid in due

    await event_bus.clear_retry(mid)
    await event_bus.redis.hset(key, mapping={
        "state": MissionState.QUEUED.value,
        "agent_id": "",
        "updated_at": "2024-01-01T00:00:01",
    })

    v = await orchestrator.redis.hgetall(key)
    assert v[b"state"].decode() == MissionState.QUEUED.value
