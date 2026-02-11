import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.orchestrator import Orchestrator, MissionState, MissionRequest
from app.schemas.agent import AgentMetadata, AgentStatus

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    # Mock hgetall to return a valid mission dict
    mock.hgetall.return_value = {
        "id": "mission-123",
        "title": "Test Mission",
        "state": MissionState.QUEUED.value,
        "priority": "1",
        "agent_id": "",
        "payload": "{}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    mock.keys.return_value = ["mission:123"]
    mock.get.return_value = None # No circuit breaker open
    return mock

@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.mission.create = AsyncMock()
    mock.auditlog.create = AsyncMock()
    mock.mission.update = AsyncMock()
    mock.agent.find_many = AsyncMock(return_value=[])
    return mock

@pytest.fixture
def mock_agent_registry():
    mock = AsyncMock()
    mock.list_agents = AsyncMock()
    mock.get_load = AsyncMock(return_value=0.0)
    return mock

@pytest.fixture
def mock_event_bus():
    mock = AsyncMock()
    mock.publish_stream = AsyncMock()
    return mock

@pytest.fixture
def orchestrator(mock_redis, mock_db, mock_agent_registry, mock_event_bus):
    with patch("app.services.orchestrator.redis.from_url", return_value=mock_redis), \
         patch("app.services.orchestrator.db", mock_db), \
         patch("app.services.orchestrator.agent_registry", mock_agent_registry), \
         patch("app.services.orchestrator.event_bus", mock_event_bus), \
         patch("app.services.orchestrator.settings") as mock_settings:
        
        mock_settings.HYPERCODE_REDIS_URL = "redis://localhost"
        orch = Orchestrator()
        orch.redis = mock_redis
        yield orch

@pytest.mark.asyncio
async def test_submit_mission(orchestrator, mock_redis, mock_db, mock_event_bus):
    req = MissionRequest(title="Test Mission", priority=1, payload={})
    
    result = await orchestrator.submit(req)
    
    assert result.title == "Test Mission"
    assert result.state == MissionState.QUEUED
    
    # Verify Redis interactions
    mock_redis.ping.assert_called()
    assert mock_redis.hset.called
    
    # Verify DB interactions
    mock_db.mission.create.assert_called_once()
    mock_db.auditlog.create.assert_called_once()
    
    # Verify Event Bus
    mock_event_bus.publish_stream.assert_called_once()

@pytest.mark.asyncio
async def test_assign_next_no_missions(orchestrator, mock_redis):
    mock_redis.keys.return_value = []
    result = await orchestrator.assign_next()
    assert result is None

@pytest.mark.asyncio
async def test_assign_next_success(orchestrator, mock_redis, mock_agent_registry, mock_db, mock_event_bus):
    # Setup mission in Redis
    mid = "mission-123"
    mission_data = {
        "id": mid,
        "title": "Test Mission",
        "state": MissionState.QUEUED.value,
        "priority": "1",
        "agent_id": "",
        "payload": json.dumps({"requirements": {"capabilities": ["python"]}}),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    mock_redis.keys.return_value = [f"mission:{mid}"]
    mock_redis.hgetall.side_effect = [
        mission_data, # For loop
        {**mission_data, "state": MissionState.ASSIGNED.value, "agent_id": "agent-1"} # For return
    ]
    
    # Setup Agent
    agent = AgentMetadata(
        id="agent-1",
        name="Agent 1",
        role="coder",
        capabilities=["python"],
        status=AgentStatus.ACTIVE,
        version="1.0.0",
        endpoint="http://agent:8000"
    )
    mock_agent_registry.list_agents.return_value = [agent]
    
    result = await orchestrator.assign_next()
    
    assert result is not None
    assert result.state == MissionState.ASSIGNED
    assert result.agent_id == "agent-1"
    
    # Verify DB update
    mock_db.mission.update.assert_called_once()
    mock_db.auditlog.create.assert_called_once()
    
    # Verify Event
    mock_event_bus.publish_stream.assert_called_once()

@pytest.mark.asyncio
async def test_assign_next_no_matching_agent(orchestrator, mock_redis, mock_agent_registry):
    # Setup mission requiring "rust"
    mid = "mission-123"
    mission_data = {
        "id": mid,
        "state": MissionState.QUEUED.value,
        "payload": json.dumps({"requirements": {"capabilities": ["rust"]}}),
    }
    mock_redis.keys.return_value = [f"mission:{mid}"]
    mock_redis.hgetall.return_value = mission_data
    
    # Setup Agent with only "python"
    agent = AgentMetadata(
        id="agent-1",
        name="Agent 1",
        role="coder",
        capabilities=["python"],
        status=AgentStatus.ACTIVE,
        version="1.0.0",
        endpoint="http://agent:8000"
    )
    mock_agent_registry.list_agents.return_value = [agent]
    
    # Should fallback if implemented or return None
    # Looking at code: if no scored agents, it tries fallback_agents from registry again?
    # Wait, the code says:
    # if not scored:
    #     fallback_agents = await agent_registry.list_agents()
    #     if not fallback_agents: return None
    #     agent_id = fallback_agents[0].id
    # So it falls back to ANY agent if no capability match? That seems like a logic "feature" or bug.
    # Let's verify it falls back to agent-1
    
    mock_redis.hgetall.side_effect = [
        mission_data,
        {**mission_data, "state": MissionState.ASSIGNED.value, "agent_id": "agent-1", "title": "Fallback", "priority": "1", "created_at": datetime.now().isoformat(), "updated_at": datetime.now().isoformat()}
    ]

    result = await orchestrator.assign_next()
    
    assert result is not None
    assert result.agent_id == "agent-1" # Fallback happened

@pytest.mark.asyncio
async def test_ensure_redis_fallback(orchestrator, mock_redis):
    orchestrator._redis_initialized = False
    mock_redis.ping.side_effect = Exception("Connection failed")
    
    # We expect it to log warning and try FakeRedis
    # Since we can't easily mock import inside method without more patching,
    # we just check that it handles the exception gracefully
    
    with patch("fakeredis.aioredis.FakeRedis") as mock_fake:
        await orchestrator._ensure_redis()
        mock_fake.assert_called_once()
        assert orchestrator._redis_initialized is True
