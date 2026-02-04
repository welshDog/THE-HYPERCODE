import asyncio
import time
import pytest
from unittest.mock import patch
from app.services.event_bus import event_bus

@pytest.mark.asyncio
async def test_schedule_retry_exponential_backoff_and_jitter(monkeypatch):
    try:
        from fakeredis.aioredis import FakeRedis
        event_bus.redis = FakeRedis()
    except Exception:
        pytest.skip("fakeredis not available")

    mid = "mission-backoff-1"
    with patch("random.uniform", return_value=0.5):
        ok, delay1 = await event_bus.schedule_retry(mid, 1, base=2.0, factor=2.0, jitter=0.5, max_delay=300.0)
        assert ok
        assert 2.0 <= delay1 <= 2.5

    with patch("random.uniform", return_value=0.5):
        ok, delay2 = await event_bus.schedule_retry(mid, 2, base=2.0, factor=2.0, jitter=0.5, max_delay=300.0)
        assert ok
        assert 4.0 <= delay2 <= 4.5

    now = time.time() + 1000
    due = await event_bus.dequeue_due_retries(now)
    assert mid in due

@pytest.mark.asyncio
async def test_max_retries_prevents_scheduling(monkeypatch):
    try:
        from fakeredis.aioredis import FakeRedis
        event_bus.redis = FakeRedis()
    except Exception:
        pytest.skip("fakeredis not available")

    mid = "mission-backoff-2"
    ok, delay = await event_bus.schedule_retry(mid, 6, base=2.0, factor=2.0, jitter=0.5, max_delay=300.0, max_retries=5)
    assert not ok
    assert delay == 0.0
    due = await event_bus.dequeue_due_retries(time.time() + 1000)
    assert mid not in due
