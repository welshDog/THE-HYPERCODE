from fastapi.testclient import TestClient
from main import app
import pytest

pytestmark = pytest.mark.experimental

def test_agent_register_role_change_422():
    client = TestClient(app)
    base = {
        "name": "Crew A",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["c"],
        "topics": ["agent.events"],
        "health_url": "http://localhost:5001/health",
        "dedup_key": "00000000-0000-0000-0000-00000000RC",
    }
    r1 = client.post("/agents/register", json=base)
    assert r1.status_code == 200
    bad = dict(base)
    bad["role"] = "manager"
    r2 = client.post("/agents/register", json=bad)
    assert r2.status_code == 422

def test_execution_error_status():
    client = TestClient(app)
    payload = {"code": "python -c 'raise SystemExit(1)'", "language": "shell", "timeout": 5}
    r = client.post("/execution/execute", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
