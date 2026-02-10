
import pytest
import pytest_asyncio
import asyncio
import os
import sys
from httpx import AsyncClient, ASGITransport
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from main import app
from app.services.agent_registry import agent_registry
from app.services.event_bus import event_bus
from app.services.orchestrator import orchestrator
from app.services.key_manager import key_manager
from app.middleware.rate_limit import rate_limiter, FIXED_WINDOW_SCRIPT
from app.core.config import get_settings
import fakeredis.aioredis
import redis.asyncio.connection

# Monkeypatch redis.asyncio.connection.Connection.can_read_destructive to handle FakeReader missing at_eof
# This is needed because fakeredis < 2.22.0 (or incompatible version) returns a reader without at_eof
# which recent redis-py checks.
original_can_read = redis.asyncio.connection.Connection.can_read_destructive

async def patched_can_read(self):
    try:
        return await original_can_read(self)
    except AttributeError as e:
        # If FakeReader object has no attribute 'at_eof', assume it's fine (not at eof)
        if "at_eof" in str(e):
            return False 
        raise

redis.asyncio.connection.Connection.can_read_destructive = patched_can_read

# Override Redis in AgentRegistry with FakeRedis
@pytest_asyncio.fixture(autouse=True)
async def reset_sse_starlette_event():
    # Force reset of sse_starlette's global event loop binding
    try:
        import sse_starlette.sse
        if hasattr(sse_starlette.sse.AppStatus, "should_exit_event"):
             sse_starlette.sse.AppStatus.should_exit_event = None
    except ImportError:
        pass
    yield

@pytest_asyncio.fixture(autouse=True)
async def mock_redis(monkeypatch):
    monkeypatch.setenv("OTLP_EXPORTER_DISABLED", "true")
    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    
    # Patch the redis client in all services
    agent_registry.redis = fake_redis
    event_bus.redis = fake_redis
    orchestrator.redis = fake_redis
    key_manager.redis = fake_redis
    
    # Patch rate limiter
    rate_limiter._redis = fake_redis
    try:
        rate_limiter._script = fake_redis.register_script(FIXED_WINDOW_SCRIPT)
    except Exception:
        # Fallback if script registration fails in mock
        pass
    
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
