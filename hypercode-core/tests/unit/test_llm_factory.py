
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.llm.factory import LLMFactory
from app.services.llm.ollama import OllamaProvider
from app.services.llm.openai import OpenAIProvider
from app.services.llm_service import LLMService

def test_factory_default_ollama():
    with patch("os.getenv") as mock_env:
        mock_env.return_value = "ollama"
        LLMFactory._instance = None # Reset singleton
        provider = LLMFactory.get_provider()
        assert isinstance(provider, OllamaProvider)

def test_factory_openai():
    with patch("os.getenv") as mock_env:
        def getenv(key, default=None):
            if key == "LLM_PROVIDER": return "openai"
            if key == "OPENAI_API_KEY": return "sk-test"
            return default
        mock_env.side_effect = getenv
        
        LLMFactory._instance = None
        provider = LLMFactory.get_provider()
        assert isinstance(provider, OpenAIProvider)

@pytest.mark.asyncio
async def test_llm_service_delegation():
    # Mock the provider
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = "Generated text"
    
    # Patch factory to return mock
    with patch("app.services.llm_service.LLMFactory.get_provider", return_value=mock_provider):
        service = LLMService()
        service.enabled = True
        
        # Test generate
        result = await service.generate("test prompt")
        assert result == "Generated text"
        mock_provider.generate.assert_called_once_with("test prompt")
        
        # Test health
        await service.health_check()
        mock_provider.health_check.assert_called_once()

@pytest.mark.asyncio
async def test_ollama_provider_generate():
    provider = OllamaProvider("http://localhost:11434", "llama2")
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Ollama response"}
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        
        result = await provider.generate("hello")
        assert result == "Ollama response"

@pytest.mark.asyncio
async def test_openai_provider_generate():
    provider = OpenAIProvider("sk-key")
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "GPT response"}}]
        }
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp
        
        result = await provider.generate("hello")
        assert result == "GPT response"
