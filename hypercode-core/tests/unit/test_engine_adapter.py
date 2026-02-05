import sys
import types
import pytest
from fastapi.testclient import TestClient
from main import app

pytestmark = pytest.mark.experimental

def test_adapter_api_path(monkeypatch):
    m = types.ModuleType("hypercode_engine")
    class Res:
        stdout = "OK"
        stderr = ""
        exit_code = 0
    def run_code(src: str, target: str | None = None):
        return Res()
    m.run_code = run_code
    monkeypatch.setitem(sys.modules, "hypercode_engine", m)
    client = TestClient(app)
    resp = client.post("/execution/execute-hc", json={"source": "print \"Hi\""})
    assert resp.status_code == 200
    body = resp.json()
    assert body["stdout"] == "OK"
    assert body["status"] == "success"

def test_adapter_cli_path():
    client = TestClient(app)
    resp = client.post("/execution/execute-hc", json={"source": "print \"CLI\""})
    assert resp.status_code == 200
    body = resp.json()
    assert body["stdout"] == "CLI"
