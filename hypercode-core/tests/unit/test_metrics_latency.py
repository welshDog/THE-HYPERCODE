import pytest
from fastapi.testclient import TestClient
from main import app
from app.routers.agents import sse_event_generator
from app.services.agent_registry import agent_registry


class _Msg:
    def __init__(self, payload):
        self.payload = payload
    def as_event(self):
        return {"type": "message", "data": self.payload}


class FakePubSub:
    def __init__(self, messages):
        self.messages = messages
    async def subscribe(self, channel):
        return None
    async def unsubscribe(self, channel):
        return None
    async def get_message(self, ignore_subscribe_messages=False, timeout=None):
        if not self.messages:
            return None
        m = self.messages.pop(0)
        return m.as_event()


@pytest.mark.asyncio
async def test_stream_latency_metric_observed(monkeypatch):
    msgs = [_Msg(b"ping"), _Msg(b"pong"), _Msg(b"x")] 
    def fake_pubsub():
        return FakePubSub(list(msgs))
    monkeypatch.setattr(agent_registry.redis, "pubsub", fake_pubsub)
    gen = sse_event_generator()
    await gen.__anext__()
    await gen.__anext__()
    await gen.__anext__()

    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "agent_stream_latency_ms" in text
    assert "agent_stream_latency_ms_sum" in text
    assert "agent_stream_latency_ms_count" in text
