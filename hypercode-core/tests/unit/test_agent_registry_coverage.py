import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone
from app.services.agent_registry import AgentRegistry, AgentStatus
from app.schemas.agent import AgentRegistrationRequest, AgentMetadata

@pytest.fixture
def mock_db():
    with patch("app.services.agent_registry.db") as mock:
        mock.agent = MagicMock()
        # Setup async mocks for DB operations
        mock.agent.find_first = AsyncMock()
        mock.agent.create = AsyncMock()
        mock.agent.update = AsyncMock()
        mock.agent.find_unique = AsyncMock()
        mock.agent.find_many = AsyncMock()
        yield mock

@pytest.fixture
def mock_redis():
    with patch("redis.asyncio.from_url") as mock_from_url:
        redis_instance = AsyncMock()
        mock_from_url.return_value = redis_instance
        yield redis_instance

@pytest.fixture
def registry(mock_db, mock_redis):
    return AgentRegistry()

@pytest.mark.asyncio
async def test_register_agent_new(registry, mock_db, mock_redis):
    # Setup
    request = AgentRegistrationRequest(
        name="New Agent",
        role="worker",
        version="1.0.0",
        capabilities=["code"],
        topics=["python"],
        health_url="http://health",
        dedup_key="key-123"
    )
    
    mock_db.agent.find_first.return_value = None # No existing agent
    
    # Mock create return
    new_agent_mock = MagicMock()
    new_agent_mock.id = "uuid-1"
    new_agent_mock.name = request.name
    new_agent_mock.role = request.role
    new_agent_mock.version = request.version
    new_agent_mock.capabilities = request.capabilities
    new_agent_mock.topics = request.topics
    new_agent_mock.health_url = request.health_url
    new_agent_mock.status = AgentStatus.ACTIVE.value
    new_agent_mock.dedup_key = request.dedup_key
    new_agent_mock.last_heartbeat = datetime.now(timezone.utc)
    new_agent_mock.created_at = datetime.now(timezone.utc)
    
    mock_db.agent.create.return_value = new_agent_mock
    
    # Execute
    agent_data, created = await registry.register_agent(request)
    
    # Assert
    assert created is False # Logic says return agent_data, False if newly created? Wait.
    # Lines 155: return agent_data, False (Wait, line 155 is inside 'else' of existing_agent check?)
    # Line 130 is 'else' (Create new).
    # Line 155 is AFTER the if/else block.
    # Wait, looking at the code:
    # if existing_agent: ... return agent_data, True (line 101) OR agent_data = ... AGENT_UPDATED... (line 129)
    # else: ... AGENT_REGISTERED... (line 148)
    # Then outside: return agent_data, False (line 155).
    # So if created new, it returns False.
    # If updated existing (line 129), it falls through to line 155 and returns False?
    # Logic seems:
    # If exact match (line 98): return agent_data, True.
    # If updated (line 115): falls through to 155 -> False.
    # If created (line 133): falls through to 155 -> False.
    # So 'True' means "Identical existing agent found, no changes". 'False' means "Created or Updated".
    
    assert created is False
    assert agent_data.id == "uuid-1"
    mock_db.agent.create.assert_called_once()
    mock_redis.set.assert_called()
    mock_redis.publish.assert_called()

@pytest.mark.asyncio
async def test_register_agent_update(registry, mock_db):
    request = AgentRegistrationRequest(
        name="Updated Agent",
        role="worker",
        version="1.0.0", # Request version
        dedup_key="key-123"
    )
    
    # Existing agent
    existing = MagicMock()
    existing.id = "uuid-1"
    existing.role = "worker"
    existing.version = "1.0.0"
    existing.dedup_key = "key-123"
    existing.name = "Old Name" # Different name trigger update
    
    mock_db.agent.find_first.return_value = existing
    
    updated_mock = MagicMock()
    updated_mock.id = "uuid-1"
    updated_mock.version = "1.0.1" # Patch incremented
    updated_mock.name = "Updated Agent"
    updated_mock.role = "worker"
    updated_mock.capabilities = []
    updated_mock.topics = []
    updated_mock.health_url = None
    updated_mock.status = "active"
    updated_mock.last_heartbeat = datetime.now(timezone.utc)
    updated_mock.created_at = datetime.now(timezone.utc)
    
    mock_db.agent.update.return_value = updated_mock
    
    agent_data, unchanged = await registry.register_agent(request)
    
    assert unchanged is False
    assert agent_data.version == "1.0.1"
    mock_db.agent.update.assert_called_once()

@pytest.mark.asyncio
async def test_register_agent_immutable_role_error(registry, mock_db):
    request = AgentRegistrationRequest(name="Test", role="new-role", version="1.0.0", dedup_key="key-1")
    
    existing = MagicMock()
    existing.role = "old-role"
    mock_db.agent.find_first.return_value = existing
    
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await registry.register_agent(request)
    
    assert exc.value.status_code == 422
    assert exc.value.detail["error"] == "immutable_field"

@pytest.mark.asyncio
async def test_get_agent_cache_hit(registry, mock_redis, mock_db):
    mock_redis.get.return_value = '{"id": "uuid-1", "name": "Cached", "role": "worker", "status": "active", "version": "1.0.0"}'
    
    agent = await registry.get_agent("uuid-1")
    assert agent.name == "Cached"
    mock_db.agent.find_unique.assert_not_called()

@pytest.mark.asyncio
async def test_get_agent_db_hit(registry, mock_redis, mock_db):
    mock_redis.get.return_value = None
    
    db_agent = MagicMock()
    db_agent.id = "uuid-1"
    db_agent.name = "DB Agent"
    db_agent.role = "worker"
    db_agent.version = "1.0.0"
    db_agent.capabilities = []
    db_agent.topics = []
    db_agent.health_url = None
    db_agent.status = "active"
    db_agent.last_heartbeat = datetime.now(timezone.utc)
    db_agent.created_at = datetime.now(timezone.utc)

    mock_db.agent.find_unique.return_value = db_agent
    
    agent = await registry.get_agent("uuid-1")
    assert agent.name == "DB Agent"
    mock_redis.set.assert_called()

@pytest.mark.asyncio
async def test_deregister_agent(registry, mock_db, mock_redis):
    await registry.deregister_agent("uuid-1")
    
    mock_db.agent.update.assert_called_once()
    mock_redis.delete.assert_called_with("agent:uuid-1")
    mock_redis.publish.assert_called()

@pytest.mark.asyncio
async def test_check_timeouts(registry, mock_db, mock_redis):
    # Setup agents: one active but old heartbeat, one active and fresh
    old_agent = MagicMock()
    old_agent.id = "old"
    old_agent.status = AgentStatus.ACTIVE.value
    # 61 seconds ago (ttl is 60)
    old_agent.lastHeartbeat = datetime.now(timezone.utc).replace(year=2020)
    
    fresh_agent = MagicMock()
    fresh_agent.id = "fresh"
    fresh_agent.status = AgentStatus.ACTIVE.value
    fresh_agent.lastHeartbeat = datetime.now(timezone.utc)
    
    mock_db.agent.find_many.return_value = [old_agent, fresh_agent]
    
    await registry.check_timeouts()
    
    # Should update old agent
    mock_db.agent.update.assert_called_once()
    call_args = mock_db.agent.update.call_args[1]
    assert call_args["where"]["id"] == "old"
    assert call_args["data"]["status"] == AgentStatus.OFFLINE.value
    
    mock_redis.delete.assert_called_with("agent:old")
