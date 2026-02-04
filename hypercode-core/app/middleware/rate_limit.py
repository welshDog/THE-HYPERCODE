import time
from typing import Optional
import redis.asyncio as redis
from fastapi import HTTPException, status
from app.core.config import get_settings

_settings = get_settings()
try:
    _redis = redis.from_url(_settings.HYPERCODE_REDIS_URL)
except Exception:
    _redis = None
_fallback_counters = {}

async def check_rate_limit(user_id: str, limit_per_minute: int = 100) -> None:
    now = int(time.time())
    bucket = now // 60
    key = f"ratelimit:voice:{user_id}:{bucket}"
    if _redis:
        try:
            cnt = await _redis.incr(key)
            if cnt == 1:
                await _redis.expire(key, 120)
            if cnt > limit_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded for voice operations"
                )
            return
        except Exception:
            pass
    # Fallback in-memory counters for tests/dev
    cnt = _fallback_counters.get(key, 0) + 1
    _fallback_counters[key] = cnt
    if cnt > limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for voice operations"
        )
