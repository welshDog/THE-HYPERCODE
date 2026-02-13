import pytest
import json
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from app.services.orchestrator import Orchestrator, MissionState, MissionRequest

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    # Mock hgetall to return a valid mission dict
    mission_data = {
        "id": "mission-123",
        "title": "Test Mission",
        "state": MissionState.QUEUED.value,
        "priority": "1",
        "agent_id": "",
        "payload": "{}",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    mock.hgetall.return_value = mission_data
    mock.keys.return_value = ["mission:123"]
    return mock

@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.auditlog.find_many = AsyncMock()
    mock.auditlog.create = AsyncMock()
    return mock

@pytest.fixture
def orchestrator(mock_redis, mock_db):
    with patch("app.services.orchestrator.redis.from_url", return_value=mock_redis), \
         patch("app.services.orchestrator.db", mock_db):
        
        orch = Orchestrator()
        orch.redis = mock_redis
        yield orch

@pytest.mark.asyncio
async def test_list_missions(orchestrator, mock_redis):
    # Setup multiple missions
    mock_redis.keys.return_value = ["mission:1", "mission:2"]
    
    m1 = {
        "id": "mission:1",
        "title": "Mission 1",
        "state": MissionState.QUEUED.value,
        "priority": "1",
        "agent_id": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    m2 = {
        "id": "mission:2",
        "title": "Mission 2",
        "state": MissionState.EXECUTING.value,
        "priority": "2",
        "agent_id": "agent-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Mock hgetall to return different values based on key
    async def side_effect(key):
        if key == "mission:1": return m1
        if key == "mission:2": return m2
        return None
        
    mock_redis.hgetall.side_effect = side_effect
    
    missions = await orchestrator.list(limit=10)
    
    assert len(missions) == 2
    assert missions[0].id == "mission:1" or missions[0].id == "mission:2"
    assert missions[0].state in [MissionState.QUEUED, MissionState.EXECUTING]

@pytest.mark.asyncio
async def test_list_missions_with_error(orchestrator, mock_redis):
    mock_redis.keys.return_value = ["mission:1"]
    # hgetall raises exception
    mock_redis.hgetall.side_effect = Exception("Redis error")
    
    missions = await orchestrator.list()
    assert len(missions) == 0

@pytest.mark.asyncio
async def test_audit_retry_logic(orchestrator, mock_db):
    # Mock find_many to fail twice then succeed
    mock_db.auditlog.find_many.side_effect = [
        Exception("DB Error 1"),
        Exception("DB Error 2"),
        [AsyncMock(id="audit-1", transition="create")] # Success
    ]
    
    logs = await orchestrator.audit("mission-123")
    
    assert len(logs) == 1
    assert logs[0]["id"] == "audit-1"
    assert mock_db.auditlog.find_many.call_count == 3

@pytest.mark.asyncio
async def test_audit_failure(orchestrator, mock_db):
    # Mock find_many to fail 3 times
    mock_db.auditlog.find_many.side_effect = Exception("DB Error")
    
    logs = await orchestrator.audit("mission-123")
    
    assert len(logs) == 0
    assert mock_db.auditlog.find_many.call_count == 3

@pytest.mark.asyncio
async def test_approve_mission(orchestrator, mock_redis, mock_db):
    mission_id = "mission-123"
    
    # Initial state
    initial_data = {
        "id": mission_id,
        "title": "Test Mission",
        "state": MissionState.QUEUED.value,
        "priority": "1",
        "agent_id": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    
    mock_redis.hgetall.return_value = initial_data
    
    result = await orchestrator.approve(mission_id)
    
    assert result is not None
    assert result.id == mission_id
    
    # Verify Redis update
    mock_redis.hset.assert_called_once()
    call_args = mock_redis.hset.call_args
    assert call_args[1]['mapping']['approved'] == "1"
    
    # Verify Audit log
    mock_db.auditlog.create.assert_called_once()
    assert mock_db.auditlog.create.call_args[0][0]["transition"] == "approve"

@pytest.mark.asyncio
async def test_approve_mission_not_found(orchestrator, mock_redis):
    mock_redis.hgetall.return_value = None
    result = await orchestrator.approve("mission-404")
    assert result is None

