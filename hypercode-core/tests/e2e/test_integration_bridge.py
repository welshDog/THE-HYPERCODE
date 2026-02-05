import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.auth import get_current_user


async def _mock_user():
    return {"sub": "e2e", "scopes": ["mission:write", "mission:read", "mission:assign"]}

app.dependency_overrides[get_current_user] = _mock_user

client = TestClient(app)


def test_agent_registration_e2e():
    payload = {
        "name": "integration-agent",
        "role": "worker",
        "version": "1.0.0",
        "capabilities": ["integration"],
        "topics": ["agent.events"],
        "health_url": "http://integration-agent:9000/health",
        "dedup_key": "integration-agent"
    }
    r1 = client.post("/agents/register", json=payload)
    assert r1.status_code == 200
    r2 = client.post("/agents/register", json=payload)
    assert r2.status_code == 200


def test_mission_submission_e2e():
    req = {
        "title": "Integration Mission",
        "priority": 80,
        "payload": {
            "requirements": {"capabilities": ["frontend", "backend"]},
            "plan_id": "plan-123"
        }
    }
    r = client.post("/orchestrator/mission", json=req)
    assert r.status_code == 200
    mid = r.json()["id"]
    assert mid
    # Transition to executing and completed
    r2 = client.post(f"/orchestrator/{mid}/start")
    assert r2.status_code == 200
    r3 = client.post(f"/orchestrator/{mid}/complete")
    assert r3.status_code == 200


def test_telemetry_aggregation_e2e():
    # Verify metrics endpoints respond
    r = client.get("/metrics/performance")
    assert r.status_code == 200
    r = client.get("/metrics/errors")
    assert r.status_code == 200
