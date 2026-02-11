
import httpx
import logging
from typing import Optional, Dict, Any, List
from .base import LLMProvider

logger = logging.getLogger(__name__)

class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
        
    async def generate(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        **kwargs
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                response.raise_for_status()
                models = response.json().get("models", [])
                return {
                    "status": "healthy",
                    "provider": "ollama",
                    "url": self.base_url,
                    "model": self.model,
                    "available_models": len(models)
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "ollama",
                "error": str(e)
            }

    async def get_embedding(self, text: str) -> List[float]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json().get("embedding", [])
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            return []
