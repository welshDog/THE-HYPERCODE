import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.memory_service import MemoryService
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemorySearch

@pytest.fixture
def mock_db_memory():
    with patch("app.services.memory_service.db") as mock_db:
        # Setup mock returns
        mock_memory = MagicMock()
        mock_db.memory = mock_memory
        yield mock_memory

@pytest.mark.asyncio
async def test_memory_crud_and_search(mock_db_memory, mock_redis):
    # Setup
    mock_created = MagicMock()
    mock_created.id = "mem1"
    mock_created.content = "Hello world"
    mock_db_memory.create = AsyncMock(return_value=mock_created)
    
    mock_got = MagicMock()
    mock_got.id = "mem1"
    mock_db_memory.find_unique = AsyncMock(return_value=mock_got)
    
    mock_updated = MagicMock()
    mock_updated.id = "mem1"
    mock_updated.content = "Hello universe"
    mock_db_memory.update = AsyncMock(return_value=mock_updated)
    
    mock_search_res = [MagicMock()]
    mock_db_memory.find_many = AsyncMock(return_value=mock_search_res)
    
    mock_db_memory.delete = AsyncMock(return_value=MagicMock())

    service = MemoryService()
    service.redis = mock_redis # Use fake redis to avoid connection errors
    
    # Mock embedding generation using patch.object to ensure it intercepts calls
    with patch.object(MemoryService, 'generate_embedding', new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [1.0, 0.0]
        
        # Ensure DB search result has embedding for vector search
        mock_search_res[0].embedding = [1.0, 0.0]
        mock_search_res[0].content = "Hello universe"

        # Test Create
        create = MemoryCreate(
            content="Hello world",
            type="short-term",
            userId="u1",
            sessionId="s1",
            metadata={"a": 1},
            keywords=["hello", "greeting"],
            missionId="m1",
            expiresAt=None,
        )
        m = await service.create_memory(create)
        assert m.id == "mem1"
        mock_db_memory.create.assert_called_once()

        # Test Get
        got = await service.get_memory(m.id)
        assert got.id == "mem1"
        mock_db_memory.find_unique.assert_called_with(where={"id": "mem1"})

        # Test Update
        upd = MemoryUpdate(content="Hello universe", keywords=["hello", "universe"])
        u = await service.update_memory(m.id, upd)
        assert u.content == "Hello universe"
        mock_db_memory.update.assert_called_once()

        # Test Search
        res = await service.search_memories(MemorySearch(query="universe", limit=10))
        assert isinstance(res, list)
        assert len(res) >= 1
        mock_db_memory.find_many.assert_called_once()

        # Test Delete
        ok = await service.delete_memory(m.id)
        assert ok is True
        mock_db_memory.delete.assert_called_once()

@pytest.mark.asyncio
async def test_memory_cleanup_expired(mock_db_memory, mock_redis):
    mock_db_memory.delete_many = AsyncMock(return_value=5)
    mock_db_memory.find_many = AsyncMock(return_value=[]) # Mock find_many for the first call

    service = MemoryService()
    service.redis = mock_redis # Use fake redis
    count = await service.cleanup_expired_memories()
    assert count == 5
    mock_db_memory.delete_many.assert_called_once()
