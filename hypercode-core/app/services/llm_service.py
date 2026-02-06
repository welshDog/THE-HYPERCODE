"""
LLM Service - Unified interface for AI providers
Supports: Ollama (local), OpenAI (cloud)
Uses httpx for async IO to avoid blocking the event loop.
"""
import os
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LLMService:
    """Unified LLM service supporting multiple providers"""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "ollama")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://llama:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "tinyllama")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.enabled = os.getenv("ENABLE_AI_FEATURES", "true").lower() == "true"
        
    async def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """
        Generate text using configured LLM provider asynchronously
        """
        if not self.enabled:
            logger.warning("AI features are disabled")
            return None
            
        try:
            if self.provider == "ollama":
                return await self._generate_ollama(prompt, **kwargs)
            elif self.provider == "openai":
                return await self._generate_openai(prompt, **kwargs)
            else:
                logger.error(f"Unknown LLM provider: {self.provider}")
                return None
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None
    
    async def _generate_ollama(self, prompt: str, **kwargs) -> str:
        """Generate using local Ollama via httpx"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        **kwargs
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama - is the container running?")
            raise
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    async def _generate_openai(self, prompt: str, **kwargs) -> str:
        """Generate using OpenAI API (future implementation)"""
        raise NotImplementedError("OpenAI provider not yet implemented")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if LLM service is healthy"""
        if not self.enabled:
            return {"status": "disabled", "provider": None}
            
        if self.provider == "ollama":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.ollama_url}/api/tags", timeout=5.0)
                    response.raise_for_status()
                    models = response.json().get("models", [])
                    return {
                        "status": "healthy",
                        "provider": "ollama",
                        "url": self.ollama_url,
                        "model": self.ollama_model,
                        "available_models": len(models)
                    }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "provider": "ollama",
                    "error": str(e)
                }
        
        return {"status": "unknown", "provider": self.provider}

# Global instance
llm_service = LLMService()
