import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryResponse

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_memory_service():
    mock = AsyncMock()
    return mock

from datetime import datetime, timezone

def test_create_memory(client, mock_memory_service):
    mock_response = MemoryResponse(
        id="mem-1",
        content="test",
        type="short-term",
        userId="u1",
        sessionId="s1",
        keywords=[],
        metadata={},
        timestamp=123.0,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc)
    )
    mock_memory_service.create_memory.return_value = mock_response
    
    with patch("app.routers.memory.memory_service", mock_memory_service):
        payload = {
            "content": "test",
            "type": "short-term",
            "userId": "u1",
            "sessionId": "s1"
        }
        response = client.post("/memory/", json=payload)
        assert response.status_code == 201
        assert response.json()["id"] == "mem-1"

def test_search_memories(client, mock_memory_service):
    mock_memory_service.search_memories.return_value = []
    
    with patch("app.routers.memory.memory_service", mock_memory_service):
        response = client.get("/memory/search?query=test")
        assert response.status_code == 200
        assert response.json() == []
        
        # Verify params
        call_args = mock_memory_service.search_memories.call_args[0][0]
        assert call_args.query == "test"

def test_get_memory_found(client, mock_memory_service):
    mock_response = MemoryResponse(
        id="mem-1",
        content="test",
        type="short-term",
        userId="u1",
        sessionId="s1",
        keywords=[],
        metadata={},
        timestamp=123.0,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc)
    )
    mock_memory_service.get_memory.return_value = mock_response
    
    with patch("app.routers.memory.memory_service", mock_memory_service):
        response = client.get("/memory/mem-1")
        assert response.status_code == 200
        assert response.json()["id"] == "mem-1"

def test_get_memory_not_found(client, mock_memory_service):
    mock_memory_service.get_memory.return_value = None
    
    with patch("app.routers.memory.memory_service", mock_memory_service):
        response = client.get("/memory/mem-404")
        assert response.status_code == 404

def test_update_memory(client, mock_memory_service):
    mock_response = MemoryResponse(
        id="mem-1",
        content="updated",
        type="short-term",
        userId="u1",
        sessionId="s1",
        keywords=[],
        metadata={},
        timestamp=123.0,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc)
    )
    mock_memory_service.update_memory.return_value = mock_response
    
    with patch("app.routers.memory.memory_service", mock_memory_service):
        payload = {"content": "updated"}
        response = client.put("/memory/mem-1", json=payload)
        assert response.status_code == 200
        assert response.json()["content"] == "updated"

def test_update_memory_not_found(client, mock_memory_service):
    mock_memory_service.update_memory.return_value = None
    
    with patch("app.routers.memory.memory_service", mock_memory_service):
        payload = {"content": "updated"}
        response = client.put("/memory/mem-404", json=payload)
        assert response.status_code == 404

def test_delete_memory(client, mock_memory_service):
    mock_memory_service.delete_memory.return_value = True
    
    with patch("app.routers.memory.memory_service", mock_memory_service):
        response = client.delete("/memory/mem-1")
        assert response.status_code == 204

def test_delete_memory_not_found(client, mock_memory_service):
    mock_memory_service.delete_memory.return_value = False
    
    with patch("app.routers.memory.memory_service", mock_memory_service):
        response = client.delete("/memory/mem-404")
        assert response.status_code == 404

def test_cleanup_memories(client, mock_memory_service):
    mock_memory_service.cleanup_expired_memories.return_value = 5
    
    with patch("app.routers.memory.memory_service", mock_memory_service):
        response = client.post("/memory/cleanup")
        assert response.status_code == 200
        assert response.json()["count"] == 5
