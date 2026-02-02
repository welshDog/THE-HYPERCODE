
import secrets
import redis.asyncio as redis
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.core.config import get_settings

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
        
    async def generate_key(self, label: str = "default") -> str:
        """Generate a new API key and store it."""
        # Generate a secure random key
        key = f"hk_{secrets.token_urlsafe(32)}"
        
        metadata = ApiKeyMetadata(
            key=key,
            created_at=datetime.utcnow().isoformat(),
            label=label
        )
        
        async with self.redis.pipeline() as pipe:
            # Add to active set
            await pipe.sadd(self.active_keys_set, key)
            # Store metadata
            await pipe.set(f"api_key:{key}:meta", metadata.model_dump_json())
            await pipe.execute()
            
        return key

    async def revoke_key(self, key: str):
        """Revoke an API key."""
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

    async def is_valid(self, key: str) -> bool:
        """Check if a key is valid."""
        # 1. Check Redis Set (Fastest)
        is_active = await self.redis.sismember(self.active_keys_set, key)
        if is_active:
            return True
            
        # 2. Fallback to Env Var (Migration/Bootstrap)
        if settings.API_KEY and key == settings.API_KEY:
            return True
            
        return False

    async def list_keys(self) -> List[ApiKeyMetadata]:
        """List all active keys."""
        keys = await self.redis.smembers(self.active_keys_set)
        results = []
        for key in keys:
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            data = await self.redis.get(f"api_key:{key}:meta")
            if data:
                results.append(ApiKeyMetadata.model_validate_json(data))
        return results

key_manager = KeyManager()
