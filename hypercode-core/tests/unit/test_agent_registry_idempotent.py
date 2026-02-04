import pytest
from fastapi.testclient import TestClient
from main import app


def test_sse_stream_endpoint_available():
    client = TestClient(app)
    resp = client.get("/agents/watch?one_shot=true")
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("text/event-stream")


@pytest.mark.asyncio
async def test_idempotent_registration_by_dedup_key(async_client):
    payload1 = {
        "name": "Idem Agent",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["compute"],
        "topics": ["agent.events"],
        "health_url": "http://localhost:5001/health",
        "dedup_key": "00000000-0000-0000-0000-000000000001",
    }
    r1 = await async_client.post("/agents/register", json=payload1)
    assert r1.status_code == 200
    id1 = r1.json()["id"]

    # Re-register with same dedup_key and new version
    payload2 = {**payload1, "version": "0.2.0"}
    r2 = await async_client.post("/agents/register", json=payload2)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["id"] == id1
    assert body2["version"] == "0.2.0"


def test_metrics_exposed():
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "agent_registered_total" in text
    assert "agent_registry_register_latency_seconds" in text
