import structlog
import redis.asyncio as redis
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import numpy as np
from app.core.db import db
from app.core.config import get_settings
from app.services.llm_service import LLMFactory
import os, base64, json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from prometheus_client import Histogram
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemorySearch

try:
    from prisma.models import Memory
    from prisma import Json
except Exception:
    from pydantic import BaseModel
    class Memory(BaseModel):
        id: str
        content: str
        type: str
        userId: Optional[str] = None
        sessionId: Optional[str] = None
        metadata: Optional[Dict[str, Any]] = None
        keywords: List[str] = []
        embedding: Optional[Any] = None
        missionId: Optional[str] = None
        createdAt: datetime
        updatedAt: datetime
        expiresAt: Optional[datetime] = None
        
        class Config:
            extra = "ignore"

    class Json(dict):
        def __init__(self, value):
            super().__init__(value if isinstance(value, dict) else {})

logger = structlog.get_logger()
settings = get_settings()

MEMORY_SERVICE_LATENCY_SECONDS = Histogram(
    "memory_service_latency_seconds",
    "Latency of MemoryService operations",
    ("operation",),
    buckets=(0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0)
)

class MemoryService:
    def __init__(self):
        # Redis connection for caching and short-term memory
        self.redis = redis.from_url(
            settings.HYPERCODE_REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        self.cache_ttl = 300 # 5 minutes

    @staticmethod
    def _get_aes() -> AESGCM | None:
        key_b64 = settings.HYPERCODE_MEMORY_KEY
        if not key_b64:
            return None
        try:
            key = base64.b64decode(key_b64)
            if len(key) not in (16,24,32):
                return None
            return AESGCM(key)
        except Exception:  # pragma: no cover
            return None

    @staticmethod
    def _enc(plain: str) -> dict | str:
        aes = MemoryService._get_aes()
        if not aes:
            return plain
        nonce = os.urandom(12)
        ct = aes.encrypt(nonce, plain.encode('utf-8'), None)
        return {"enc": True, "n": base64.b64encode(nonce).decode('ascii'), "c": base64.b64encode(ct).decode('ascii')}

    @staticmethod
    def _dec(stored: any) -> str:
        if isinstance(stored, str):
            return stored
        try:
            if isinstance(stored, dict) and stored.get("enc"):
                aes = MemoryService._get_aes()
                if not aes:
                    return ""
                n = base64.b64decode(stored["n"]) 
                c = base64.b64decode(stored["c"]) 
                pt = aes.decrypt(n, c, None)
                return pt.decode('utf-8')
        except Exception:  # pragma: no cover
            return ""
        return str(stored)

    async def _cache_set(self, key: str, value: Any, ttl: int = 300):
        try:
            # Serialize
            if hasattr(value, "model_dump_json"):
                 data = value.model_dump_json()
            elif hasattr(value, "json"): # Prisma models often have json()
                 data = value.json()
            else:
                 data = json.dumps(value, default=str)
            await self.redis.set(key, data, ex=ttl)
        except Exception as e:  # pragma: no cover
            logger.warning("redis_cache_set_failed", error=str(e))

    async def _cache_get(self, key: str) -> Optional[dict]:
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception:  # pragma: no cover
            return None

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using the default LLM provider"""
        try:
            provider = LLMFactory.get_default_provider()
            return await provider.get_embedding(text)
        except Exception as e:  # pragma: no cover
            logger.error("embedding_generation_failed", error=str(e))
            return []

    async def create_memory(self, data: MemoryCreate) -> Memory:
        import time
        t0 = time.perf_counter()
        logger.info("creating_memory", type=data.type, user_id=data.userId)
        
        # Generate embedding if content exists
        embedding = []
        if data.content:
            embedding = await self.generate_embedding(data.content)

        # 1. Create in DB (Long-term)
        create_data = {
            "content": MemoryService._enc(data.content),
            "type": data.type,
            "userId": data.userId,
            "sessionId": data.sessionId,
            "keywords": data.keywords or [],
            "missionId": data.missionId,
            "expiresAt": data.expiresAt,
            "embedding": Json(embedding) if embedding else None
        }
        
        if data.metadata:
            create_data["metadata"] = Json(data.metadata)
            
        memory = await db.memory.create(data=create_data)
        
        # Decrypt for response and cache
        try:
            memory.content = MemoryService._dec(memory.content)
        except Exception:
            pass

        # 2. Cache in Redis (Short-term / Fast Access)
        await self._cache_set(f"memory:{memory.id}", memory, self.cache_ttl)
        
        # 3. Add to Session List (if applicable)
        if data.sessionId:
            try:
                # Store recent memory IDs for session context
                await self.redis.lpush(f"session:{data.sessionId}:memories", memory.id)
                await self.redis.ltrim(f"session:{data.sessionId}:memories", 0, 99) # Keep last 100
                await self.redis.expire(f"session:{data.sessionId}:memories", 86400) # 24h TTL
            except Exception:
                pass

        MEMORY_SERVICE_LATENCY_SECONDS.labels("create").observe(time.perf_counter() - t0)
        return memory

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2:
            return 0.0
        try:
            a = np.array(v1)
            b = np.array(v2)
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
        except Exception:
            return 0.0

    async def search_similar(self, query: str, limit: int = 5, threshold: float = 0.7, filters: Dict[str, Any] = None) -> List[Memory]:
        """Search for memories similar to the query string using vector similarity"""
        query_embedding = await self.generate_embedding(query)
        if not query_embedding:
            return []

        # Fetch candidates from DB (Naïve approach: fetch all matching filters)
        # TODO: Migrate to pgvector or Redis Vector Search for production scale
        where = filters or {}
            
        memories = await db.memory.find_many(where=where)
        
        results = []
        for m in memories:
            if not m.embedding:
                continue
            
            # Decrypt content if needed
            try:
                m.content = MemoryService._dec(m.content)
            except:
                pass

            # Parse embedding if it's stored as JSON string or dict
            emb = m.embedding
            if isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except:
                    continue
            
            # If embedding is a list, calculate score
            if isinstance(emb, list):
                score = MemoryService.cosine_similarity(query_embedding, emb)
                if score >= threshold:
                    # Attach score to metadata for client use
                    if not m.metadata:
                        m.metadata = {}
                    if isinstance(m.metadata, dict):
                        m.metadata["score"] = score
                    results.append((score, m))
        
        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in results[:limit]]

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        import time
        t0 = time.perf_counter()
        
        # 1. Try Cache
        cached = await self._cache_get(f"memory:{memory_id}")
        if cached:
            MEMORY_SERVICE_LATENCY_SECONDS.labels("get_cache_hit").observe(time.perf_counter() - t0)
            # Reconstruct model - minimal effort for now
            # Note: This returns a dict disguised as model or we need to parse it
            # For simplicity, we assume caller handles dict or we parse if strictly typed
            # Prisma models have parse_obj usually
            try:
                return Memory.parse_obj(cached)
            except:
                pass # Fallback to DB if parsing fails

        # 2. DB Fallback
        m = await db.memory.find_unique(where={"id": memory_id})
        MEMORY_SERVICE_LATENCY_SECONDS.labels("get_db").observe(time.perf_counter() - t0)
        
        if m:
            try:
                m.content = MemoryService._dec(m.content)
            except Exception:
                pass
            # Update Cache
            await self._cache_set(f"memory:{memory_id}", m, self.cache_ttl)
            
        return m

    async def update_memory(self, memory_id: str, data: MemoryUpdate) -> Optional[Memory]:
        import time
        t0 = time.perf_counter()
        logger.info("updating_memory", memory_id=memory_id)
        
        update_data = {}
        if data.content is not None:
            update_data["content"] = MemoryService._enc(data.content)
        if data.metadata is not None:
            update_data["metadata"] = Json(data.metadata)
        if data.keywords is not None:
            update_data["keywords"] = data.keywords
        if data.expiresAt is not None:
            update_data["expiresAt"] = data.expiresAt
            
        if not update_data:
            return await self.get_memory(memory_id)

        try:
            memory = await db.memory.update(
                where={"id": memory_id},
                data=update_data
            )
            MEMORY_SERVICE_LATENCY_SECONDS.labels("update").observe(time.perf_counter() - t0)
            try:
                memory.content = MemoryService._dec(memory.content)
            except Exception:
                pass
                
            # Invalidate/Update Cache
            await self._cache_set(f"memory:{memory_id}", memory, self.cache_ttl)
            
            return memory
        except Exception as e:
            logger.error("update_memory_failed", error=str(e))
            MEMORY_SERVICE_LATENCY_SECONDS.labels("update").observe(time.perf_counter() - t0)
            return None

    async def delete_memory(self, memory_id: str) -> bool:
        import time
        t0 = time.perf_counter()
        logger.info("deleting_memory", memory_id=memory_id)
        try:
            await db.memory.delete(where={"id": memory_id})
            await self.redis.delete(f"memory:{memory_id}")
            MEMORY_SERVICE_LATENCY_SECONDS.labels("delete").observe(time.perf_counter() - t0)
            return True
        except Exception:
            MEMORY_SERVICE_LATENCY_SECONDS.labels("delete").observe(time.perf_counter() - t0)
            return False

    async def search_memories(self, params: MemorySearch) -> List[Memory]:
        import time
        t0 = time.perf_counter()
        
        # Prepare filters
        where_clause = {}
        if params.type:
            where_clause["type"] = params.type
        if params.userId:
            where_clause["userId"] = params.userId
        if params.sessionId:
            where_clause["sessionId"] = params.sessionId

        # Use vector search if query is present
        if params.query:
             try:
                 # Attempt vector search
                 return await self.search_similar(
                     query=params.query, 
                     limit=params.limit, 
                     filters=where_clause
                 )
             except Exception as e:
                 logger.warning("vector_search_failed", error=str(e))
                 # Fallback to keyword search below
                 where_clause["OR"] = [
                    {"keywords": {"has": params.query}} 
                 ]

        memories = await db.memory.find_many(
            where=where_clause,
            take=params.limit,
            skip=params.offset,
            order={"createdAt": "desc"}
        )
        
        # Decrypt results
        for m in memories:
            try:
                m.content = MemoryService._dec(m.content)
            except Exception:
                pass
                
        MEMORY_SERVICE_LATENCY_SECONDS.labels("search").observe(time.perf_counter() - t0)
        return memories

    async def cleanup_expired_memories(self) -> int:
        import time
        t0 = time.perf_counter()
        now = datetime.now(timezone.utc)
        
        # Find IDs to expire from cache
        expired = await db.memory.find_many(
            where={"expiresAt": {"lt": now}},
            select={"id": True}
        )
        
        result = await db.memory.delete_many(
            where={"expiresAt": {"lt": now}}
        )
        
        # Cleanup Cache
        if expired:
            pipeline = self.redis.pipeline()
            for m in expired:
                pipeline.delete(f"memory:{m.id}")
            await pipeline.execute()
            
        logger.info("cleanup_expired_memories", count=result)
        MEMORY_SERVICE_LATENCY_SECONDS.labels("cleanup").observe(time.perf_counter() - t0)
        return result

# Global Instance
memory_service = MemoryService()
