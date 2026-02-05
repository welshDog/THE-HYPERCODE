import pytest
from fastapi.testclient import TestClient
from main import app


def test_duplicate_payload_returns_200():
    client = TestClient(app)
    payload = {
        "name": "Agent A",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["c1"],
        "topics": ["agent.events"],
        "health_url": "http://localhost:5001/health",
        "dedup_key": "00000000-0000-0000-0000-0000000000AA",
    }
    r1 = client.post("/agents/register", json=payload)
    assert r1.status_code == 200
    r2 = client.post("/agents/register", json=payload)
    assert r2.status_code == 200


def test_immutable_role_change_rejected_422():
    client = TestClient(app)
    base = {
        "name": "Agent B",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["c1"],
        "topics": ["agent.events"],
        "health_url": "http://localhost:5002/health",
        "dedup_key": "00000000-0000-0000-0000-0000000000BB",
    }
    r1 = client.post("/agents/register", json=base)
    assert r1.status_code == 200
    bad = dict(base)
    bad["role"] = "architect"
    r2 = client.post("/agents/register", json=bad)
    assert r2.status_code == 422


def test_version_minor_bumps_and_patch_resets_on_dedup_re_register():
    client = TestClient(app)
    data = {
        "name": "Agent C",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["c1"],
        "topics": ["agent.events"],
        "health_url": "http://localhost:5003/health",
        "dedup_key": "00000000-0000-0000-0000-0000000000CC",
    }
    r1 = client.post("/agents/register", json=data)
    assert r1.status_code == 200
    agent_id = r1.json()["id"]
    upd = dict(data)
    upd["name"] = "Agent C Updated"
    r2 = client.post("/agents/register", json=upd)
    assert r2.status_code == 200
    after = client.get(f"/agents/{agent_id}")
    assert after.status_code == 200
    v = after.json()["version"]
    # Expect minor++ and patch=0 when same dedup_key re-registers
    assert v.endswith(".0")
    assert v.startswith("0.2")
