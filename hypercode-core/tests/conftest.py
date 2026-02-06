
import pytest
import pytest_asyncio
import asyncio
import os
import sys
from httpx import AsyncClient, ASGITransport
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import app
from app.services.agent_registry import agent_registry
from app.core.config import get_settings
import fakeredis.aioredis

# Override Redis in AgentRegistry with FakeRedis
@pytest_asyncio.fixture(autouse=True)
async def mock_redis(monkeypatch):
    monkeypatch.setenv("OTLP_EXPORTER_DISABLED", "true")
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    
    # Patch the redis client in the registry instance
    agent_registry.redis = fake_redis
    
    yield fake_redis
    # await fake_redis.aclose() # fakeredis might not implement aclose in all versions, close() is async in aioredis
    # But warnings say use aclose(). Let's try it.
    if hasattr(fake_redis, 'aclose'):
        await fake_redis.aclose()
    else:
        await fake_redis.close()

@pytest_asyncio.fixture(autouse=True)
async def reset_inmemory_db():
    from app.core.db import db
    if hasattr(db, "agent") and hasattr(db.agent, "_items"):
        db.agent._items.clear()
    yield

@pytest_asyncio.fixture(autouse=True)
async def db_lifespan():
    from app.core.db import db
    connected = False
    if hasattr(db, "connect"):
        try:
            await db.connect()
            connected = True
        except Exception as e:
            print(f"!!! DB CONNECTION FAILED: {e}")
            pass
    yield
    if connected and hasattr(db, "disconnect"):
        await db.disconnect()

@pytest_asyncio.fixture
async def async_client(db_lifespan):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
