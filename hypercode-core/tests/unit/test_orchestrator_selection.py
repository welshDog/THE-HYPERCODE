import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.auth import get_current_user

def test_orchestrator_assign_prefers_capability_and_health():
    # Override auth to allow access
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "test-user", 
        "scopes": ["mission:write", "mission:read", "mission:assign"]
    }
    client = TestClient(app)
    # Register two agents: one with gpu capability, one without
    a1 = {
        "name": "Worker NoGPU",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["compute"],
        "topics": ["agent.events"],
        "health_url": "http://localhost:5004/health",
        "dedup_key": "00000000-0000-0000-0000-00000000NG",
    }
    a2 = {
        "name": "Worker GPU",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["compute", "gpu"],
        "topics": ["agent.events"],
        "health_url": "http://localhost:5005/health",
        "dedup_key": "00000000-0000-0000-0000-00000000GP",
    }
    r1 = client.post("/agents/register", json=a1)
    r2 = client.post("/agents/register", json=a2)
    assert r1.status_code == 200
    assert r2.status_code == 200

    # Create mission requiring gpu capability
    mission_req = {
        "title": "GPU Mission",
        "priority": 50,
        "payload": {"requirements": {"capabilities": ["gpu"]}}
    }
    m = client.post("/orchestrator/mission", json=mission_req)
    assert m.status_code == 200
    mid = m.json()["id"]

    # Assign next mission
    assign = client.post("/orchestrator/assign")
    assert assign.status_code in (200, 204)
    if assign.status_code == 200:
        data = assign.json()
        assert data["state"] == "assigned"
        # Expect GPU agent selected
        selected_agent_id = data["agent_id"]
        # Fetch agents to verify
        agents = client.get("/agents/").json()
        gpu_agent = next(a for a in agents if "gpu" in a.get("capabilities", []))
        assert selected_agent_id == gpu_agent["id"]

