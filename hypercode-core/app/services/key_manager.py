
import secrets
import redis.asyncio as redis
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from app.core.config import get_settings
from prometheus_client import Histogram

settings = get_settings()

class ApiKeyMetadata(BaseModel):
    key: str
    created_at: str
    revoked: bool = False
    label: Optional[str] = None

class KeyManager:
    def __init__(self):
        self.redis = redis.from_url(settings.HYPERCODE_REDIS_URL)
        self.active_keys_set = "api_keys:active"
        self._latency = Histogram(
            "key_manager_latency_seconds",
            "Latency of key manager operations",
            ("operation",),
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5)
        )
        
    async def generate_key(self, label: str = "default") -> str:
        """Generate a new API key and store it."""
        import time
        t0 = time.perf_counter()
        # Generate a secure random key
        key = f"hk_{secrets.token_urlsafe(32)}"
        
        metadata = ApiKeyMetadata(
            key=key,
            created_at=datetime.now(timezone.utc).isoformat(),
            label=label
        )
        
        async with self.redis.pipeline() as pipe:
            # Add to active set
            await pipe.sadd(self.active_keys_set, key)
            # Store metadata
            await pipe.set(f"api_key:{key}:meta", metadata.model_dump_json())
            await pipe.execute()
            
        self._latency.labels("generate").observe(time.perf_counter() - t0)
        return key

    async def revoke_key(self, key: str):
        """Revoke an API key."""
        import time
        t0 = time.perf_counter()
        async with self.redis.pipeline() as pipe:
            await pipe.srem(self.active_keys_set, key)
            # Mark as revoked in metadata (optional, for audit)
            meta_key = f"api_key:{key}:meta"
            data = await self.redis.get(meta_key)
            if data:
                meta = ApiKeyMetadata.model_validate_json(data)
                meta.revoked = True
                await pipe.set(meta_key, meta.model_dump_json())
            await pipe.execute()
        self._latency.labels("revoke").observe(time.perf_counter() - t0)

    async def is_valid(self, key: str) -> bool:
        """Check if a key is valid."""
        import time
        t0 = time.perf_counter()
        # 1. Check Redis Set (Fastest)
        is_active = await self.redis.sismember(self.active_keys_set, key)
        if is_active:
            self._latency.labels("is_valid").observe(time.perf_counter() - t0)
            return True
            
        # 2. Fallback to Env Var (Migration/Bootstrap)
        import os
        s = get_settings()
        env_key = os.getenv("API_KEY") or s.API_KEY
        if env_key and key == env_key:
            self._latency.labels("is_valid").observe(time.perf_counter() - t0)
            return True
            
        self._latency.labels("is_valid").observe(time.perf_counter() - t0)
        return False

    async def list_keys(self) -> List[ApiKeyMetadata]:
        """List all active keys."""
        import time
        t0 = time.perf_counter()
        keys = await self.redis.smembers(self.active_keys_set)
        results = []
        for key in keys:
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            data = await self.redis.get(f"api_key:{key}:meta")
            if data:
                results.append(ApiKeyMetadata.model_validate_json(data))
        self._latency.labels("list").observe(time.perf_counter() - t0)
        return results

key_manager = KeyManager()
