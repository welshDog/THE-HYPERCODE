
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.memory_service import MemoryService
from app.schemas.memory import MemoryCreate
import numpy as np
from datetime import datetime, timezone

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set = AsyncMock()
    return mock

@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.memory.find_many = AsyncMock()
    return mock

@pytest.fixture
def memory_service(mock_redis, mock_db):
    mock_settings_obj = MagicMock()
    mock_settings_obj.HYPERCODE_MEMORY_KEY = None
    mock_settings_obj.HYPERCODE_REDIS_URL = "redis://localhost"

    # Mock LLMFactory
    mock_llm_provider = AsyncMock()
    mock_llm_provider.get_embedding.side_effect = lambda text: [1.0, 0.0] if "A" in text else [0.0, 1.0]
    
    mock_llm_factory = MagicMock()
    mock_llm_factory.get_default_provider.return_value = mock_llm_provider

    with patch("app.services.memory_service.redis.from_url", return_value=mock_redis), \
         patch("app.services.memory_service.db", mock_db), \
         patch("app.services.memory_service.settings", mock_settings_obj), \
         patch("app.services.memory_service.LLMFactory", mock_llm_factory):
        
        service = MemoryService()
        service.redis = mock_redis
        yield service

def test_cosine_similarity(memory_service):
    v1 = [1.0, 0.0]
    v2 = [1.0, 0.0]
    assert memory_service.cosine_similarity(v1, v2) > 0.99
    
    v3 = [0.0, 1.0]
    assert memory_service.cosine_similarity(v1, v3) == 0.0
    
    v4 = [0.707, 0.707]
    assert 0.69 < memory_service.cosine_similarity(v1, v4) < 0.72

@pytest.mark.asyncio
async def test_search_similar(memory_service, mock_db):
    # Setup mocks
    mock_mem1 = MagicMock()
    mock_mem1.id = "1"
    mock_mem1.content = "Memory A"
    mock_mem1.embedding = [1.0, 0.0]
    mock_mem1.metadata = {}

    mock_mem2 = MagicMock()
    mock_mem2.id = "2"
    mock_mem2.content = "Memory B"
    mock_mem2.embedding = [0.0, 1.0]
    mock_mem2.metadata = {}

    mock_db.memory.find_many.return_value = [mock_mem1, mock_mem2]

    # Search for "A" (embedding [1.0, 0.0])
    results = await memory_service.search_similar("A", limit=1, threshold=0.5)
    
    assert len(results) == 1
    assert results[0].id == "1"
    assert results[0].metadata["score"] > 0.9

    # Search for "B" (embedding [0.0, 1.0])
    results_b = await memory_service.search_similar("B", limit=1, threshold=0.5)
    assert len(results_b) == 1
    assert results_b[0].id == "2"
