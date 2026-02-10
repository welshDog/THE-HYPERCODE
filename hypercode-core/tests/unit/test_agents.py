
import pytest
from app.schemas.agent import AgentStatus
from fastapi.testclient import TestClient
from main import app

@pytest.mark.asyncio
async def test_register_agent(async_client):
    payload = {
        "name": "Test Agent",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["compute"],
        "topics": ["agent.events"],
        "health_url": "http://localhost:5000/health",
        "dedup_key": "00000000-0000-0000-0000-00000000TA"
    }
    response = await async_client.post("/agents/register", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == payload["name"]
    assert "id" in data
    return data["id"]

@pytest.mark.asyncio
async def test_get_agents(async_client):
    # Register an agent first
    await test_register_agent(async_client)
    
    response = await async_client.get("/agents/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

@pytest.mark.asyncio
async def test_heartbeat(async_client):
    # Register
    agent_id = await test_register_agent(async_client)
    
    # Send heartbeat
    payload = {
        "agent_id": agent_id,
        "status": "busy",
        "load": 0.5
    }
    response = await async_client.post("/agents/heartbeat", json=payload)
    assert response.status_code == 200
    
    # Verify status update
    response = await async_client.get(f"/agents/{agent_id}")
    data = response.json()
    assert data["status"] == "busy"

@pytest.mark.asyncio
async def test_sse_stream_endpoint_sync(async_client):
    async with async_client.stream("GET", "/agents/watch?one_shot=true") as resp:
        assert resp.status_code == 200
        assert resp.headers.get("content-type", "").startswith("text/event-stream")
