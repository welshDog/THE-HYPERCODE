import asyncio
import pytest
from app.services.agent_registry import agent_registry

@pytest.mark.asyncio
async def test_sse_handles_cancelled_error(monkeypatch, async_client):
    class FakePubSub:
        async def subscribe(self, channel):
            return None

        async def unsubscribe(self, channel):
            return None

        async def get_message(self, ignore_subscribe_messages=False, timeout=None):
            raise asyncio.CancelledError()

    def fake_pubsub():
        return FakePubSub()

    monkeypatch.setattr(agent_registry.redis, "pubsub", fake_pubsub)
    async with async_client.stream("GET", "/agents/stream") as resp:
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("text/event-stream")


@pytest.mark.asyncio
async def test_sse_pubsub_failure_does_not_500(monkeypatch, async_client):
    class FakePubSub:
        async def subscribe(self, channel):
            raise RuntimeError("subscribe failed")

        async def unsubscribe(self, channel):
            return None

        async def get_message(self, ignore_subscribe_messages=False, timeout=None):
            return None

    def fake_pubsub():
        return FakePubSub()

    monkeypatch.setattr(agent_registry.redis, "pubsub", fake_pubsub)
    async with async_client.stream("GET", "/agents/watch") as resp:
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("text/event-stream")
