import pytest
import os
from unittest.mock import patch, MagicMock
import httpx
from app.services.llm_service import LLMService
from app.services.llm.factory import LLMFactory

@pytest.fixture(autouse=True)
def reset_llm_factory():
    """Reset LLMFactory singleton to ensure isolation between tests"""
    LLMFactory._instance = None
    yield
    LLMFactory._instance = None

# Mock environment variables
@pytest.fixture
def mock_env_ollama():
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "ollama",
        "OLLAMA_URL": "http://mock-ollama:11434",
        "OLLAMA_MODEL": "mock-model",
        "ENABLE_AI_FEATURES": "true"
    }):
        yield

@pytest.fixture
def mock_env_openai():
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-mock",
        "ENABLE_AI_FEATURES": "true"
    }):
        yield

@pytest.fixture
def mock_env_disabled():
    with patch.dict(os.environ, {"ENABLE_AI_FEATURES": "false"}):
        yield

from app.services.llm.ollama import OllamaProvider

@pytest.mark.asyncio
async def test_llm_service_init_defaults():
    # Test default initialization
    with patch.dict(os.environ, {}, clear=True):
        service = LLMService()
        assert isinstance(service.provider, OllamaProvider)
        assert service.provider.base_url == "http://llama:11434"
        assert service.enabled is True

@pytest.mark.asyncio
async def test_llm_service_init_custom(mock_env_ollama):
    service = LLMService()
    assert isinstance(service.provider, OllamaProvider)
    assert service.provider.base_url == "http://mock-ollama:11434"
    assert service.provider.model == "mock-model"

@pytest.mark.asyncio
async def test_generate_disabled(mock_env_disabled):
    service = LLMService()
    result = await service.generate("test prompt")
    assert result is None

@pytest.mark.asyncio
async def test_generate_ollama_success(mock_env_ollama):
    service = LLMService()
    mock_response = {"response": "Mocked LLM response"}
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_response,
            raise_for_status=lambda: None
        )
        
        result = await service.generate("Hello")
        assert result == "Mocked LLM response"
        
        # Verify call arguments
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://mock-ollama:11434/api/generate"
        assert kwargs["json"]["prompt"] == "Hello"
        assert kwargs["json"]["model"] == "mock-model"

@pytest.mark.asyncio
async def test_generate_ollama_connection_error(mock_env_ollama):
    service = LLMService()
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        # generate() catches exceptions and returns None
        result = await service.generate("Hello")
        assert result is None

@pytest.mark.asyncio
async def test_generate_openai_not_implemented(mock_env_openai):
    service = LLMService()
    # Should catch NotImplementedError and return None
    result = await service.generate("Hello")
    assert result is None

@pytest.mark.asyncio
async def test_generate_unknown_provider():
    with patch.dict(os.environ, {"LLM_PROVIDER": "unknown", "ENABLE_AI_FEATURES": "true"}):
        service = LLMService()
        result = await service.generate("Hello")
        assert result is None

@pytest.mark.asyncio
async def test_health_check_healthy(mock_env_ollama):
    service = LLMService()
    mock_tags_response = {"models": [{"name": "tinyllama"}, {"name": "mistral"}]}
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_tags_response,
            raise_for_status=lambda: None
        )
        
        status = await service.health_check()
        assert status["status"] == "healthy"
        assert status["provider"] == "ollama"
        assert status["available_models"] == 2

@pytest.mark.asyncio
async def test_health_check_unhealthy(mock_env_ollama):
    service = LLMService()
    
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Down")):
        status = await service.health_check()
        assert status["status"] == "unhealthy"
        assert "error" in status

@pytest.mark.asyncio
async def test_health_check_disabled(mock_env_disabled):
    service = LLMService()
    status = await service.health_check()
    assert status["status"] == "disabled"
