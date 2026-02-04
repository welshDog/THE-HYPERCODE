import pytest
from datetime import datetime, timedelta
from app.services.memory_service import MemoryService
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemorySearch

@pytest.mark.asyncio
async def test_memory_crud_and_search():
    create = MemoryCreate(
        content="Hello world",
        type="short-term",
        userId="u1",
        sessionId="s1",
        metadata={"a": 1},
        keywords=["hello", "greeting"],
        missionId="m1",
        expiresAt=None,
    )
    m = await MemoryService.create_memory(create)
    assert m.id
    got = await MemoryService.get_memory(m.id)
    assert got.id == m.id
    upd = MemoryUpdate(content="Hello universe", keywords=["hello", "universe"])
    u = await MemoryService.update_memory(m.id, upd)
    assert u.content == "Hello universe"
    res = await MemoryService.search_memories(MemorySearch(query="universe", limit=10))
    assert isinstance(res, list)
    assert len(res) >= 1
    ok = await MemoryService.delete_memory(m.id)
    assert ok is True
    none = await MemoryService.get_memory(m.id)
    assert none is None

@pytest.mark.asyncio
async def test_memory_cleanup_expired():
    expire_time = datetime.utcnow() + timedelta(seconds=0.1)
    m = await MemoryService.create_memory(MemoryCreate(
        content="To expire",
        type="short-term",
        userId="u2",
        sessionId="s2",
        keywords=["expire"],
        missionId=None,
        expiresAt=expire_time
    ))
    assert m.id
    import asyncio
    await asyncio.sleep(0.2)
    count = await MemoryService.cleanup_expired_memories()
    assert count >= 1
