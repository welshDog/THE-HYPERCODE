import asyncio
import random
import pytest
from httpx import Timeout

def _backoff_delays(start=0.5, factor=1.5, jitter=0.2, max_delay=10.0, max_attempts=6):
    delay = start
    for _ in range(max_attempts):
        yield max(0.0, delay + random.uniform(-jitter, jitter))
        delay = min(max_delay, delay * factor)

@pytest.mark.asyncio
async def test_sse_stream_connects_with_backoff(async_client):
    connected = False
    for delay in _backoff_delays():
        try:
            async with async_client.stream("GET", "/agents/watch?one_shot=true", timeout=Timeout(2.0)) as resp:
                if resp.status_code == 200:
                    connected = True
                    break
        except Exception:
            await asyncio.sleep(delay)
    assert connected

@pytest.mark.asyncio
async def test_metrics_endpoint_exposes_sse_metrics(async_client):
    payload = {
        "name": "SSE Metrics Agent",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": [],
        "topics": [],
        "health_url": None,
        "dedup_key": "00000000-0000-0000-0000-00000000SM"
    }
    r = await async_client.post("/agents/register", json=payload)
    assert r.status_code == 200
    m = await async_client.get("/metrics")
    assert m.status_code == 200
    text = m.text
    assert "agent_stream_latency_ms" in text
    assert "agent_stream_latency_ms_count" in text
