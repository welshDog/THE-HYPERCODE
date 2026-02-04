import structlog
from typing import List, Optional
from datetime import datetime
from app.core.db import db
from app.core.config import get_settings
import os, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from prometheus_client import Histogram
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemorySearch
try:
    from prisma.models import Memory
    from prisma import Json
except Exception:
    from typing import Any
    Memory = Any
    class Json(dict):
        def __init__(self, value):
            super().__init__(value if isinstance(value, dict) else {})

logger = structlog.get_logger()

MEMORY_SERVICE_LATENCY_SECONDS = Histogram(
    "memory_service_latency_seconds",
    "Latency of MemoryService operations",
    ("operation",),
    buckets=(0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0)
)

class MemoryService:
    @staticmethod
    def _get_aes() -> AESGCM | None:
        key_b64 = get_settings().HYPERCODE_MEMORY_KEY
        if not key_b64:
            return None
        try:
            key = base64.b64decode(key_b64)
            if len(key) not in (16,24,32):
                return None
            return AESGCM(key)
        except Exception:
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
        except Exception:
            return ""
        return str(stored)
    @staticmethod
    async def create_memory(data: MemoryCreate) -> Memory:
        import time
        t0 = time.perf_counter()
        logger.info("creating_memory", type=data.type, user_id=data.userId)
        create_data = {
            "content": MemoryService._enc(data.content),
            "type": data.type,
            "userId": data.userId,
            "sessionId": data.sessionId,
            "keywords": data.keywords or [],
            "missionId": data.missionId,
            "expiresAt": data.expiresAt
        }
        
        if data.metadata:
            create_data["metadata"] = Json(data.metadata)
            
        memory = await db.memory.create(
            data=create_data
        )
        MEMORY_SERVICE_LATENCY_SECONDS.labels("create").observe(time.perf_counter() - t0)
        # Decrypt for response
        try:
            memory.content = MemoryService._dec(memory.content)
        except Exception:
            pass
        return memory

    @staticmethod
    async def get_memory(memory_id: str) -> Optional[Memory]:
        import time
        t0 = time.perf_counter()
        m = await db.memory.find_unique(where={"id": memory_id})
        MEMORY_SERVICE_LATENCY_SECONDS.labels("get").observe(time.perf_counter() - t0)
        if m:
            try:
                m.content = MemoryService._dec(m.content)
            except Exception:
                pass
        return m

    @staticmethod
    async def update_memory(memory_id: str, data: MemoryUpdate) -> Optional[Memory]:
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
            res = await MemoryService.get_memory(memory_id)
            MEMORY_SERVICE_LATENCY_SECONDS.labels("update").observe(time.perf_counter() - t0)
            return res

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
            return memory
        except Exception as e:
            logger.error("update_memory_failed", error=str(e))
            MEMORY_SERVICE_LATENCY_SECONDS.labels("update").observe(time.perf_counter() - t0)
            return None

    @staticmethod
    async def delete_memory(memory_id: str) -> bool:
        import time
        t0 = time.perf_counter()
        logger.info("deleting_memory", memory_id=memory_id)
        try:
            await db.memory.delete(where={"id": memory_id})
            MEMORY_SERVICE_LATENCY_SECONDS.labels("delete").observe(time.perf_counter() - t0)
            return True
        except Exception:
            MEMORY_SERVICE_LATENCY_SECONDS.labels("delete").observe(time.perf_counter() - t0)
            return False

    @staticmethod
    async def search_memories(params: MemorySearch) -> List[Memory]:
        import time
        t0 = time.perf_counter()
        where_clause = {}
        if params.type:
            where_clause["type"] = params.type
        if params.userId:
            where_clause["userId"] = params.userId
        if params.sessionId:
            where_clause["sessionId"] = params.sessionId
        
        # Simple keyword/content search
        if params.query:
            where_clause["OR"] = [
                {"content": {"contains": params.query, "mode": "insensitive"}},
                {"keywords": {"has": params.query}} 
            ]

        memories = await db.memory.find_many(
            where=where_clause,
            take=params.limit,
            skip=params.offset,
            order={"createdAt": "desc"}
        )
        MEMORY_SERVICE_LATENCY_SECONDS.labels("search").observe(time.perf_counter() - t0)
        for m in memories:
            try:
                m.content = MemoryService._dec(m.content)
            except Exception:
                pass
        return memories

    @staticmethod
    async def cleanup_expired_memories() -> int:
        import time
        t0 = time.perf_counter()
        now = datetime.utcnow()
        result = await db.memory.delete_many(
            where={
                "expiresAt": {
                    "lt": now
                }
            }
        )
        logger.info("cleanup_expired_memories", count=result)
        MEMORY_SERVICE_LATENCY_SECONDS.labels("cleanup").observe(time.perf_counter() - t0)
        return result
