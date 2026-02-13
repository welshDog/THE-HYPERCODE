import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect
from datetime import datetime, timezone

from main import app
from app.services.agent_registry import AgentRegistry
from app.schemas.agent import AgentMetadata
from app.routers.dashboard import router

# Helper for testing WebSocket with mocked dependencies
@pytest.fixture
def mock_agent_registry():
    mock = AsyncMock()
    mock.list_agents.return_value = []
    mock.get_load.return_value = 0.5
    return mock

@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.mission.find_many.return_value = []
    mock.memory.count.return_value = 100
    return mock

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_dashboard_websocket_flow(client, mock_agent_registry, mock_db):
    # Prepare mock data
    agent_data = AgentMetadata(
        id="agent-1",
        name="Test Agent",
        role="worker",
        version="1.0.0",
        status="active",
        capabilities=["python"],
        updated_at=datetime.now(timezone.utc)
    )
    
    mock_agent_registry.list_agents.return_value = [agent_data]
    
    mission_data = MagicMock()
    mission_data.model_dump.return_value = {
        "id": "mission-1",
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }
    mock_db.mission.find_many.return_value = [mission_data]
    mock_db.memory.count.return_value = 42

    with patch("app.routers.dashboard.agent_registry", mock_agent_registry), \
         patch("app.routers.dashboard.db", mock_db):
        
        with client.websocket_connect("/dashboard/ws") as websocket:
            # Receive the first message
            data = websocket.receive_json()
            
            assert "agents" in data
            assert len(data["agents"]) == 1
            assert data["agents"][0]["id"] == "agent-1"
            assert data["agents"][0]["load"] == 0.5
            
            assert "missions" in data
            assert len(data["missions"]) == 1
            assert data["missions"][0]["id"] == "mission-1"
            
            assert "memory" in data
            assert data["memory"]["total_memories"] == 42
            
            assert data["system_status"] == "operational"

@pytest.mark.asyncio
async def test_dashboard_websocket_partial_failure(client, mock_agent_registry, mock_db):
    # Simulate partial failures in services
    mock_agent_registry.list_agents.side_effect = Exception("Agent Registry Down")
    mock_db.mission.find_many.side_effect = Exception("DB Down")
    
    with patch("app.routers.dashboard.agent_registry", mock_agent_registry), \
         patch("app.routers.dashboard.db", mock_db):
        
        with client.websocket_connect("/dashboard/ws") as websocket:
            data = websocket.receive_json()
            
            # Should still return partial data
            assert data["agents"] == []
            assert data["missions"] == []
            assert "memory" in data
            assert data["system_status"] == "operational"

@pytest.mark.asyncio
async def test_dashboard_websocket_disconnect_handling(client, mock_agent_registry, mock_db):
    with patch("app.routers.dashboard.agent_registry", mock_agent_registry), \
         patch("app.routers.dashboard.db", mock_db):
             
        with client.websocket_connect("/dashboard/ws") as websocket:
            websocket.receive_json()
            websocket.close()
            # No assertion needed, just verifying it doesn't crash the server
