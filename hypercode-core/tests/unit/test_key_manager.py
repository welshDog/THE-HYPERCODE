import pytest
import pytest_asyncio
import os
from app.services.key_manager import key_manager
import fakeredis.aioredis

@pytest_asyncio.fixture(autouse=True)
async def patch_redis(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    key_manager.redis = fake
    yield fake
    if hasattr(fake, "aclose"):
        await fake.aclose()
    else:
        await fake.close()

@pytest.mark.asyncio
async def test_generate_list_validate_revoke(monkeypatch):
    k = await key_manager.generate_key(label="test")
    assert k.startswith("hk_")
    lst = await key_manager.list_keys()
    assert any(i.key == k for i in lst)
    valid = await key_manager.is_valid(k)
    assert valid is True
    await key_manager.revoke_key(k)
    valid2 = await key_manager.is_valid(k)
    assert valid2 is False

@pytest.mark.asyncio
async def test_api_key_fallback(monkeypatch):
    monkeypatch.setenv("API_KEY", "static_key")
    from app.core.config import get_settings
    s = get_settings()
    s.API_KEY = "static_key"
    ok = await key_manager.is_valid("static_key")
    assert ok is True
