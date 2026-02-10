import asyncio
import json
import time
import pytest
from app.routers.agents import sse_event_generator
from app.services.agent_registry import agent_registry


class _Msg:
    def __init__(self, payload):
        self.payload = payload

    def as_event(self):
        return {"type": "message", "data": self.payload}


class FakePubSub:
    def __init__(self, messages, fail_first=False):
        self.messages = messages
        self.fail_first = fail_first
        self._subscribed = False

    async def subscribe(self, channel):
        if self.fail_first and not self._subscribed:
            self._subscribed = True
            raise RuntimeError("subscribe failed")
        self._subscribed = True

    async def unsubscribe(self, channel):
        return None

    async def get_message(self, ignore_subscribe_messages=False, timeout=None):
        if not self.messages:
            return None
        m = self.messages.pop(0)
        return m.as_event()


@pytest.mark.asyncio
async def test_sse_emits_valid_messages(monkeypatch):
    payloads = [
        _Msg(json.dumps({"event": "registered", "data": {"id": "a1"}}).encode()),
        _Msg(json.dumps({"event": "updated", "data": {"id": "a1"}}).encode()),
    ]

    def fake_pubsub():
        return FakePubSub(list(payloads))

    monkeypatch.setattr(agent_registry.redis, "pubsub", fake_pubsub)
    gen = sse_event_generator()
    out1 = await gen.__anext__()
    out2 = await gen.__anext__()
    assert "registered" in out1 or "updated" in out1
    assert "registered" in out2 or "updated" in out2


@pytest.mark.asyncio
async def test_sse_handles_malformed_data(monkeypatch):
    bad = _Msg(b"\xff\xfe\xfd")
    good = _Msg(json.dumps({"event": "registered", "data": {"id": "x"}}).encode())

    class MalPubSub(FakePubSub):
        async def get_message(self, ignore_subscribe_messages=False, timeout=None):
            if not self.messages:
                return None
            m = self.messages.pop(0)
            if m == bad:
                raise Exception("Bad encoding")
            return m.as_event()

    def fake_pubsub():
        return MalPubSub([bad, good])

    monkeypatch.setattr(agent_registry.redis, "pubsub", fake_pubsub)
    gen = sse_event_generator()
    v = await gen.__anext__()
    assert "registered" in v


@pytest.mark.asyncio
async def test_sse_high_frequency(monkeypatch):
    msgs = [
        _Msg(json.dumps({"i": i}).encode()) for i in range(50)
    ]
    def fake_pubsub():
        return FakePubSub(list(msgs))
    monkeypatch.setattr(agent_registry.redis, "pubsub", fake_pubsub)
    gen = sse_event_generator()
    count = 0
    async for _ in gen:
        count += 1
        if count >= 10:
            break
    assert count >= 10


@pytest.mark.asyncio
async def test_sse_connection_recovers(monkeypatch):
    msgs = [_Msg(b"ok")]
    def fake_pubsub():
        return FakePubSub(list(msgs), fail_first=True)
    monkeypatch.setattr(agent_registry.redis, "pubsub", fake_pubsub)
    gen = sse_event_generator()
    v = await gen.__anext__()
    assert v == "ok"

if __name__ == "__main__":
    import sys, pytest
    sys.exit(pytest.main([__file__]))
