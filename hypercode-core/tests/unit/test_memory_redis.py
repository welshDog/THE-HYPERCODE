
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.memory_service import MemoryService
from app.schemas.memory import MemoryCreate
from datetime import datetime, timezone

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    mock.lpush = AsyncMock()
    mock.ltrim = AsyncMock()
    mock.expire = AsyncMock()
    return mock

@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.memory.create = AsyncMock()
    mock.memory.find_unique = AsyncMock()
    mock.memory.update = AsyncMock()
    mock.memory.delete = AsyncMock()
    return mock

@pytest.fixture
def memory_service(mock_redis, mock_db):
    # Create a mock settings object
    mock_settings_obj = MagicMock()
    mock_settings_obj.HYPERCODE_MEMORY_KEY = None
    mock_settings_obj.HYPERCODE_REDIS_URL = "redis://localhost"

    # Mock LLMFactory
    mock_llm_provider = AsyncMock()
    mock_llm_provider.get_embedding.return_value = [0.1, 0.2, 0.3]
    
    mock_llm_factory = MagicMock()
    mock_llm_factory.get_default_provider.return_value = mock_llm_provider

    with patch("app.services.memory_service.redis.from_url", return_value=mock_redis), \
         patch("app.services.memory_service.db", mock_db), \
         patch("app.services.memory_service.settings", mock_settings_obj), \
         patch("app.services.memory_service.LLMFactory", mock_llm_factory):
        
        service = MemoryService()
        service.redis = mock_redis # Inject mock
        yield service

@pytest.mark.asyncio
async def test_create_memory_caching(memory_service, mock_redis, mock_db):
    # Setup
    data = MemoryCreate(
        content="Test memory",
        type="short-term",
        userId="user-1",
        sessionId="session-1"
    )
    
    mock_memory = MagicMock()
    mock_memory.id = "mem-1"
    mock_memory.content = "Test memory"
    mock_memory.json.return_value = '{"id": "mem-1", "content": "Test memory"}'
    
    mock_db.memory.create.return_value = mock_memory
    
    # Execute
    result = await memory_service.create_memory(data)
    
    # Verify DB Call
    mock_db.memory.create.assert_called_once()
    
    # Verify Redis Cache Set
    mock_redis.set.assert_called()
    call_args = mock_redis.set.call_args
    assert call_args[0][0] == "memory:mem-1"
    
    # Verify Session List Update
    mock_redis.lpush.assert_called_with("session:session-1:memories", "mem-1")

@pytest.mark.asyncio
async def test_get_memory_cache_hit(memory_service, mock_redis, mock_db):
    # Setup Cache Hit - needs to match Pydantic model structure
    cached_data = {
        "id": "mem-1",
        "content": "Cached Content",
        "type": "short-term",
        "userId": "user-1",
        "sessionId": "session-1",
        "keywords": [],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }
    import json
    mock_redis.get.return_value = json.dumps(cached_data)
    
    # Execute
    result = await memory_service.get_memory("mem-1")
    
    # Verify
    assert result is not None
    assert result.content == "Cached Content"
    mock_db.memory.find_unique.assert_not_called()

@pytest.mark.asyncio
async def test_get_memory_cache_miss(memory_service, mock_redis, mock_db):
    # Setup Cache Miss
    mock_redis.get.return_value = None
    
    mock_memory = MagicMock()
    mock_memory.id = "mem-1"
    mock_memory.content = "DB Content"
    mock_memory.json.return_value = '{"id": "mem-1", "content": "DB Content"}'
    mock_db.memory.find_unique.return_value = mock_memory
    
    # Execute
    result = await memory_service.get_memory("mem-1")
    
    # Verify
    assert result.content == "DB Content"
    mock_db.memory.find_unique.assert_called_once()
    # Should populate cache
    mock_redis.set.assert_called()
    call_args = mock_redis.set.call_args
    assert call_args[0][0] == "memory:mem-1"

@pytest.mark.asyncio
async def test_delete_memory_clears_cache(memory_service, mock_redis, mock_db):
    mock_db.memory.delete.return_value = None
    
    await memory_service.delete_memory("mem-1")
    
    mock_redis.delete.assert_called_with("memory:mem-1")
    mock_db.memory.delete.assert_called_once()
