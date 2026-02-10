import time
import logging
import redis.asyncio as redis
from fastapi import HTTPException, status
from app.core.config import get_settings
from prometheus_client import Counter

logger = logging.getLogger(__name__)
settings = get_settings()

RATE_LIMIT_CHECKS = Counter(
    "rate_limit_checks_total",
    "Rate limit checks performed",
    ["scope", "status"]
)
RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "Rate limit hits (blocked requests)",
    ["scope"]
)
REDIS_ERRORS = Counter(
    "redis_errors_total",
    "Redis errors",
    []
)

# Lua script for atomic fixed window
# Returns 1 if allowed, 0 if blocked
FIXED_WINDOW_SCRIPT = """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[2])
end
if current > tonumber(ARGV[1]) then
    return 0
end
return 1
"""

class RateLimiter:
    def __init__(self):
        self._redis = None
        self._script = None
        self._fallback_counters = {}
        try:
            self._redis = redis.from_url(
                settings.HYPERCODE_REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            self._script = self._redis.register_script(FIXED_WINDOW_SCRIPT)
        except Exception as e:
            logger.error(f"Failed to initialize Redis for rate limiting: {e}")
            self._redis = None

    async def check(self, key: str, limit: int, window: int) -> bool:
        """
        Check if request is allowed.
        Returns True if allowed, False if limit exceeded.
        """
        scope = "voice" # Simplify for now, or extract from key
        if "voice" in key:
            scope = "voice"
        else:
            scope = "general"

        if self._redis:
            try:
                # Use Lua script for atomicity
                result = await self._script(keys=[key], args=[limit, window])
                allowed = bool(result)
                RATE_LIMIT_CHECKS.labels(scope=scope, status="allowed" if allowed else "blocked").inc()
                if not allowed:
                    RATE_LIMIT_HITS.labels(scope=scope).inc()
                return allowed
            except Exception as e:
                logger.error(f"Redis rate limit error: {e}")
                REDIS_ERRORS.inc()
                # Fallback to in-memory on redis failure
                return self._check_fallback(key, limit, window, scope)
        else:
            return self._check_fallback(key, limit, window, scope)

    def _check_fallback(self, key: str, limit: int, window: int, scope: str = "general") -> bool:
        now = int(time.time())
        # Simple fixed window based on time bucket
        bucket = now // window
        full_key = f"{key}:{bucket}"
        
        count = self._fallback_counters.get(full_key, 0)
        if count >= limit:
            RATE_LIMIT_CHECKS.labels(scope=scope, status="blocked").inc()
            RATE_LIMIT_HITS.labels(scope=scope).inc()
            return False
        
        self._fallback_counters[full_key] = count + 1
        RATE_LIMIT_CHECKS.labels(scope=scope, status="allowed").inc()
        
        # Cleanup old counters occasionally (simple optimization)
        if len(self._fallback_counters) > 10000:
            self._fallback_counters.clear()
            
        return True

# Singleton
rate_limiter = RateLimiter()

async def check_rate_limit(user_id: str, limit_per_minute: int = settings.RATE_LIMIT_MAX_REQUESTS) -> None:
    """
    Check rate limit for a user.
    Raises HTTPException(429) if exceeded.
    """
    # Use settings window (default 60s)
    window = settings.RATE_LIMIT_WINDOW_SECONDS
    
    # Key should be specific to the rate limit scope
    key = f"ratelimit:voice:{user_id}"
    
    allowed = await rate_limiter.check(key, limit_per_minute, window)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for voice operations"
        )
