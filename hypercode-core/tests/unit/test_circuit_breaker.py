import pytest
from app.services.orchestrator import orchestrator
from app.schemas.mission import MissionState

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(monkeypatch):
    try:
        from fakeredis.aioredis import FakeRedis
        orchestrator.redis = FakeRedis(decode_responses=True)
    except Exception:
        pytest.skip("fakeredis not available")

    mid = "mission-fail-1"
    key = await orchestrator._key(mid)
    await orchestrator.redis.hset(key, mapping={
        "id": mid,
        "title": "Breaker Mission",
        "state": MissionState.ASSIGNED.value,
        "priority": 50,
        "agent_id": "agent-123",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00",
    })

    for _ in range(3):
        await orchestrator.fail(mid)

    val = await orchestrator.redis.get("cb:open:agent-123")
    assert val is not None
