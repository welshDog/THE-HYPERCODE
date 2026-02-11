"""
LLM Service - Unified interface for AI providers
Supports: Ollama (local), OpenAI (cloud) via Strategy Pattern
"""
import os
import logging
import time
from typing import Optional, Dict, Any
from app.services.llm.factory import LLMFactory
from prometheus_client import Histogram, Counter

logger = logging.getLogger(__name__)

LLM_REQUEST_LATENCY = Histogram(
    "llm_request_latency_seconds",
    "Latency of LLM requests",
    ("provider", "status"),
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

LLM_REQUEST_TOTAL = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ("provider", "status")
)

class LLMService:
    """Unified LLM service supporting multiple providers"""
    
    def __init__(self):
        self.enabled = os.getenv("ENABLE_AI_FEATURES", "true").lower() == "true"
        self._provider = None
        self._fallback_provider = None
        self._fallback_enabled = os.getenv("ENABLE_LLM_FALLBACK", "true").lower() == "true"
        
    @property
    def provider(self):
        if not self._provider:
            self._provider = LLMFactory.get_default_provider()
        return self._provider
        
    @property
    def fallback_provider(self):
        if not self._fallback_enabled:
            return None
        if not self._fallback_provider:
            current_name = os.getenv("LLM_PROVIDER", "ollama").lower()
            fallback_name = "openai" if current_name == "ollama" else "ollama"
            try:
                self._fallback_provider = LLMFactory.create_provider(fallback_name)
            except Exception:
                logger.warning(f"Could not create fallback provider: {fallback_name}")
                self._fallback_provider = None
        return self._fallback_provider

    async def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """
        Generate text using configured LLM provider asynchronously
        """
        if not self.enabled:
            logger.warning("AI features are disabled")
            return None
            
        t0 = time.perf_counter()
        provider_name = "unknown"
        try:
            # We assume provider has a 'provider' attribute or we infer from class
            # But here we just use the configured name for metrics
            provider_name = os.getenv("LLM_PROVIDER", "ollama")
            
            result = await self.provider.generate(prompt, **kwargs)
            
            latency = time.perf_counter() - t0
            LLM_REQUEST_LATENCY.labels(provider=provider_name, status="success").observe(latency)
            LLM_REQUEST_TOTAL.labels(provider=provider_name, status="success").inc()
            
            return result
        except Exception as e:
            latency = time.perf_counter() - t0
            LLM_REQUEST_LATENCY.labels(provider=provider_name, status="error").observe(latency)
            LLM_REQUEST_TOTAL.labels(provider=provider_name, status="error").inc()
            
            logger.error(f"LLM generation failed with primary provider: {e}")
            
            # Try fallback
            fallback = self.fallback_provider
            if fallback:
                logger.info("Attempting fallback LLM provider")
                t1 = time.perf_counter()
                try:
                    result = await fallback.generate(prompt, **kwargs)
                    
                    latency_fb = time.perf_counter() - t1
                    LLM_REQUEST_LATENCY.labels(provider="fallback", status="success").observe(latency_fb)
                    LLM_REQUEST_TOTAL.labels(provider="fallback", status="success").inc()
                    
                    return result
                except Exception as e2:
                    latency_fb = time.perf_counter() - t1
                    LLM_REQUEST_LATENCY.labels(provider="fallback", status="error").observe(latency_fb)
                    LLM_REQUEST_TOTAL.labels(provider="fallback", status="error").inc()
                    
                    logger.error(f"LLM fallback generation failed: {e2}")
            
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if LLM service is healthy"""
        if not self.enabled:
            return {"status": "disabled", "provider": None}
            
        return await self.provider.health_check()

# Global instance
llm_service = LLMService()
