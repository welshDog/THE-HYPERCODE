import asyncio
import types
from fastapi.testclient import TestClient
from main import app
from app.services.agent_registry import agent_registry


def test_sse_handles_cancelled_error(monkeypatch):
    class FakePubSub:
        async def subscribe(self, channel):
            return None

        async def unsubscribe(self, channel):
            return None

        async def listen(self):
            raise asyncio.CancelledError()

    def fake_pubsub():
        return FakePubSub()

    monkeypatch.setattr(agent_registry.redis, "pubsub", fake_pubsub)
    client = TestClient(app)
    resp = client.get("/agents/stream")
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("text/event-stream")


def test_sse_pubsub_failure_does_not_500(monkeypatch):
    class FakePubSub:
        async def subscribe(self, channel):
            raise RuntimeError("subscribe failed")

        async def unsubscribe(self, channel):
            return None

        async def listen(self):
            async def gen():
                if False:
                    yield None
            return gen()

    def fake_pubsub():
        return FakePubSub()

    monkeypatch.setattr(agent_registry.redis, "pubsub", fake_pubsub)
    client = TestClient(app)
    resp = client.get("/agents/watch")
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("text/event-stream")
