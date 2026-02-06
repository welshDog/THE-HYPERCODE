import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.middleware.rate_limit import RateLimiter, check_rate_limit
from fastapi import HTTPException

@pytest.mark.asyncio
async def test_rate_limiter_redis_allowed():
    limiter = RateLimiter()
    limiter._redis = AsyncMock()
    limiter._script = AsyncMock(return_value=1) # Lua returns 1 for allowed

    allowed = await limiter.check("test_key", 10, 60)
    assert allowed is True
    limiter._script.assert_called_once()

@pytest.mark.asyncio
async def test_rate_limiter_redis_blocked():
    limiter = RateLimiter()
    limiter._redis = AsyncMock()
    limiter._script = AsyncMock(return_value=0) # Lua returns 0 for blocked

    allowed = await limiter.check("test_key", 10, 60)
    assert allowed is False

@pytest.mark.asyncio
async def test_rate_limiter_fallback():
    limiter = RateLimiter()
    limiter._redis = None # Simulate no redis

    # Should use in-memory fallback
    # Limit 2
    key = "test_fallback"
    assert await limiter.check(key, 2, 60) is True
    assert await limiter.check(key, 2, 60) is True
    assert await limiter.check(key, 2, 60) is False

@pytest.mark.asyncio
async def test_check_rate_limit_dependency():
    # Patch the singleton rate_limiter
    with patch("app.middleware.rate_limit.rate_limiter.check", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = True
        await check_rate_limit("user1")
        mock_check.assert_called_once()

        mock_check.return_value = False
        with pytest.raises(HTTPException) as exc:
            await check_rate_limit("user1")
        assert exc.value.status_code == 429
