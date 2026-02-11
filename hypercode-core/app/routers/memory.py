from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryResponse, MemorySearch
from app.services.memory_service import memory_service

router = APIRouter()

@router.post("/", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(memory: MemoryCreate):
    return await memory_service.create_memory(memory)

@router.get("/search", response_model=List[MemoryResponse])
async def search_memories(
    query: str = Query(None, description="Search query for content or keywords"),
    type: str = Query(None, description="Filter by memory type"),
    userId: str = Query(None, description="Filter by user ID"),
    sessionId: str = Query(None, description="Filter by session ID"),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    search_params = MemorySearch(
        query=query,
        type=type,
        userId=userId,
        sessionId=sessionId,
        limit=limit,
        offset=offset
    )
    return await memory_service.search_memories(search_params)

@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: str):
    memory = await memory_service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory

@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(memory_id: str, memory_update: MemoryUpdate):
    memory = await memory_service.update_memory(memory_id, memory_update)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory

@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: str):
    success = await memory_service.delete_memory(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return

@router.post("/cleanup", status_code=status.HTTP_200_OK)
async def cleanup_memories():
    count = await memory_service.cleanup_expired_memories()
    return {"message": f"Cleaned up {count} expired memories", "count": count}
