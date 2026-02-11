
import httpx
import logging
from typing import Optional, Dict, Any, List
from .base import LLMProvider

logger = logging.getLogger(__name__)

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        
    async def generate(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                **kwargs
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            async with httpx.AsyncClient() as client:
                # Simple model list check
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers,
                    timeout=5.0
                )
                response.raise_for_status()
                return {
                    "status": "healthy",
                    "provider": "openai",
                    "model": self.model
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "openai",
                "error": str(e)
            }

    async def get_embedding(self, text: str) -> List[float]:
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            # Use text-embedding-3-small or fallback to text-embedding-ada-002
            # For now hardcode small model for efficiency
            payload = {
                "model": "text-embedding-3-small",
                "input": text
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            return []
