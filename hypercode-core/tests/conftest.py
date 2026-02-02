
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from app.services.agent_registry import agent_registry
from app.core.config import get_settings
import fakeredis.aioredis

# Override Redis in AgentRegistry with FakeRedis
@pytest_asyncio.fixture(autouse=True)
async def mock_redis(monkeypatch):
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

@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
