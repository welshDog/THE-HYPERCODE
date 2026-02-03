import structlog
from typing import List, Optional
from datetime import datetime
from app.core.db import db
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

class MemoryService:
    @staticmethod
    async def create_memory(data: MemoryCreate) -> Memory:
        logger.info("creating_memory", type=data.type, user_id=data.userId)
        
        create_data = {
            "content": data.content,
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
        return memory

    @staticmethod
    async def get_memory(memory_id: str) -> Optional[Memory]:
        return await db.memory.find_unique(where={"id": memory_id})

    @staticmethod
    async def update_memory(memory_id: str, data: MemoryUpdate) -> Optional[Memory]:
        logger.info("updating_memory", memory_id=memory_id)
        
        update_data = {}
        if data.content is not None:
            update_data["content"] = data.content
        if data.metadata is not None:
            update_data["metadata"] = Json(data.metadata)
        if data.keywords is not None:
            update_data["keywords"] = data.keywords
        if data.expiresAt is not None:
            update_data["expiresAt"] = data.expiresAt
            
        if not update_data:
            return await MemoryService.get_memory(memory_id)

        try:
            memory = await db.memory.update(
                where={"id": memory_id},
                data=update_data
            )
            return memory
        except Exception as e:
            logger.error("update_memory_failed", error=str(e))
            return None

    @staticmethod
    async def delete_memory(memory_id: str) -> bool:
        logger.info("deleting_memory", memory_id=memory_id)
        try:
            await db.memory.delete(where={"id": memory_id})
            return True
        except Exception:
            return False

    @staticmethod
    async def search_memories(params: MemorySearch) -> List[Memory]:
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
        return memories

    @staticmethod
    async def cleanup_expired_memories() -> int:
        now = datetime.utcnow()
        result = await db.memory.delete_many(
            where={
                "expiresAt": {
                    "lt": now
                }
            }
        )
        logger.info("cleanup_expired_memories", count=result)
        return result
