import pytest
import types
import sys
import asyncio

from app.engine.adapter import run_hypercode


class FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload
    def json(self):
        return {"stdout": "API", "stderr": "", "exit_code": 0}


class FakeAsyncClient:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.last_json = None
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        return False
    async def post(self, url: str, json: dict):
        self.last_json = json
        return FakeResponse(json)


@pytest.mark.asyncio
async def test_adapter_forwards_env_and_target(monkeypatch):
    import app.engine.adapter as adapter
    client = FakeAsyncClient()
    monkeypatch.setattr(adapter.httpx, "AsyncClient", lambda timeout=30: client)

    env = {"A": "1", "B": "2"}
    target = "python"
    stdout, stderr, code, _ = await run_hypercode("print \"X\"", timeout=5, env=env, target=target)
    assert code == 0
    assert stdout == "API"
    assert client.last_json is not None
    assert client.last_json.get("env_vars") == env
    assert client.last_json.get("target") == target

