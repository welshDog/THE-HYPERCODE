
import pytest
from app.schemas.agent import AgentStatus
from fastapi.testclient import TestClient
from main import app

@pytest.mark.asyncio
async def test_register_agent(async_client):
    payload = {
        "name": "Test Agent",
        "description": "A unit test agent",
        "version": "0.1.0",
        "endpoint": "http://localhost:5000",
        "tags": ["test", "unit"]
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

def test_websocket_connection_sync(async_client):
    # We need to use TestClient for WebSockets if AsyncClient doesn't support it in this version
    # Mixed async/sync test: we register via sync client or mock the registry
    
    client = TestClient(app)
    
    # 1. Register (Sync)
    payload = {
        "name": "WS Agent",
        "description": "WS Test",
        "version": "0.1.0",
        "endpoint": "http://localhost:5000",
        "tags": ["ws"]
    }
    reg_response = client.post("/agents/register", json=payload)
    assert reg_response.status_code == 200
    agent_id = reg_response.json()["id"]
    
    # 2. Connect via WebSocket
    with client.websocket_connect(f"/agents/{agent_id}/channel") as websocket:
        # 3. Send Ping
        websocket.send_text("ping")
        
        # 4. Expect Pong
        response = websocket.receive_text()
        assert response == "pong"
