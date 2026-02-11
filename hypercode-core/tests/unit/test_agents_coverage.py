import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from app.schemas.agent import AgentMetadata, AgentStatus

@pytest.fixture
def mock_agent_registry():
    with patch("app.routers.agents.agent_registry") as mock:
        yield mock

@pytest.mark.asyncio
async def test_deregister_agent(async_client, mock_agent_registry):
    mock_agent_registry.deregister_agent = AsyncMock()
    
    response = await async_client.delete("/agents/test-agent-id")
    assert response.status_code == 200
    assert response.json() == {"status": "deregistered"}
    mock_agent_registry.deregister_agent.assert_called_with("test-agent-id")

@pytest.mark.asyncio
async def test_heartbeat_not_found(async_client, mock_agent_registry):
    mock_agent_registry.update_heartbeat = AsyncMock(return_value=False)
    
    payload = {
        "agent_id": "unknown-id",
        "status": "active",
        "load": 0.1
    }
    response = await async_client.post("/agents/heartbeat", json=payload)
    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found"

@pytest.mark.asyncio
async def test_get_agents_list(async_client, mock_agent_registry):
    agent = AgentMetadata(
        id="agent-1",
        name="Agent 1",
        role="worker",
        status=AgentStatus.ACTIVE,
        version="1.0",
        endpoint="http://local"
    )
    mock_agent_registry.list_agents = AsyncMock(return_value=[agent])
    
    response = await async_client.get("/agents/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "agent-1"

@pytest.mark.asyncio
async def test_register_agent_success(async_client, mock_agent_registry):
    req_payload = {
        "name": "New Agent",
        "role": "worker",
        "version": "1.0",
        "capabilities": [],
        "topics": [],
        "health_url": "http://health",
        "dedup_key": "dedup"
    }
    
    agent = AgentMetadata(
        id="new-agent-id",
        name="New Agent",
        role="worker",
        status=AgentStatus.ACTIVE,
        version="1.0",
        endpoint="http://health"
    )
    
    mock_agent_registry.register_agent = AsyncMock(return_value=(agent, False))
    
    response = await async_client.post("/agents/register", json=req_payload)
    assert response.status_code == 200
    assert response.json()["id"] == "new-agent-id"

@pytest.mark.asyncio
async def test_watch_agents_endpoint(async_client, mock_agent_registry):
    # Mock redis pubsub for sse_event_generator
    mock_pubsub = AsyncMock()
    mock_agent_registry.redis.pubsub.return_value = mock_pubsub
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    
    # This is tricky to test with TestClient stream because sse_event_generator is infinite loop
    # unless one_shot=True.
    # But sse_event_generator is inside the router implementation, imported from services?
    # No, it's defined in routers/agents.py
    
    # We rely on one_shot=True to break loop
    response = await async_client.get("/agents/watch?one_shot=true")
    assert response.status_code == 200
    # Content type depends on sse_starlette, usually text/event-stream
    assert "text/event-stream" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_get_agent_details(async_client, mock_agent_registry):
    agent = AgentMetadata(
        id="agent-detail-1",
        name="Agent Detail",
        role="worker",
        status=AgentStatus.ACTIVE,
        version="1.0",
        endpoint="http://local"
    )
    mock_agent_registry.get_agent = AsyncMock(return_value=agent)
    
    response = await async_client.get("/agents/agent-detail-1")
    assert response.status_code == 200
    assert response.json()["name"] == "Agent Detail"

@pytest.mark.asyncio
async def test_get_agent_details_not_found(async_client, mock_agent_registry):
    mock_agent_registry.get_agent = AsyncMock(return_value=None)
    
    response = await async_client.get("/agents/unknown-agent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found"

@pytest.mark.asyncio
async def test_send_task_not_connected(async_client):
    # Ensure CONNECTED_AGENTS is empty or doesn't have the agent
    with patch("app.routers.agents.CONNECTED_AGENTS", {}):
        response = await async_client.post("/agents/test-agent/send", json={"task": "do_it"})
        assert response.status_code == 404
        assert response.json()["detail"] == "Agent not connected"

@pytest.mark.asyncio
async def test_send_task_success(async_client):
    mock_ws = AsyncMock()
    mock_ws.send_text = AsyncMock()
    
    with patch("app.routers.agents.CONNECTED_AGENTS", {"test-agent": mock_ws}):
        response = await async_client.post("/agents/test-agent/send", json={"task": "do_it"})
        assert response.status_code == 202
        mock_ws.send_text.assert_called_once()
