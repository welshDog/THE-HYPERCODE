import pytest
import asyncio
pytestmark = pytest.mark.experimental

from app.services.execution_service import ExecutionService
from app.schemas.execution import ExecutionRequest, Language


class FakeProcess:
    def __init__(self):
        self.returncode = 0
        self._stdout = b"CLI"
        self._stderr = b""
    async def communicate(self):
        await asyncio.sleep(0)
        return self._stdout, self._stderr


@pytest.mark.asyncio
async def test_cli_includes_target_flag(monkeypatch):
    captured = {"args": None}

    async def fake_create_subprocess_exec(cmd, *args, stdout=None, stderr=None, env=None):
        captured["args"] = (cmd, *args)
        return FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    req = ExecutionRequest(code='print "OK"', language=Language.HYPERCODE, timeout=5, env_vars=None, target="python")
    result = await ExecutionService.execute_code(req)
    assert result.status == "success"
    assert result.stdout == "CLI"
    assert captured["args"] is not None
    cmd, *args = captured["args"]
    assert cmd == "python"
    assert "-t" in args
    assert "python" in args
