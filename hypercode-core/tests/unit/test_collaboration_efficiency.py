import asyncio
from fastapi.testclient import TestClient
from main import app

def test_agents_collaboration_register_list_heartbeat():
    client = TestClient(app)
    a1 = {
        "name": "Crew Worker 1",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["compute"],
        "topics": ["agent.events"],
        "health_url": "http://localhost:5002/health",
        "dedup_key": "00000000-0000-0000-0000-00000000W1",
    }
    a2 = {
        "name": "Crew Worker 2",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["compute"],
        "topics": ["agent.events"],
        "health_url": "http://localhost:5003/health",
        "dedup_key": "00000000-0000-0000-0000-00000000W2",
    }
    r1 = client.post("/agents/register", json=a1)
    r2 = client.post("/agents/register", json=a2)
    assert r1.status_code == 200
    assert r2.status_code == 200
    lst = client.get("/agents/")
    assert lst.status_code == 200
    arr = lst.json()
    assert isinstance(arr, list)
    assert len(arr) >= 2
    agent_id = arr[0]["id"]
    hb = client.post("/agents/heartbeat", json={"agent_id": agent_id, "status": "busy", "load": 0.7})
    assert hb.status_code == 200
    chk = client.get(f"/agents/{agent_id}")
    assert chk.status_code == 200
    data = chk.json()
    assert data["status"] == "busy"
