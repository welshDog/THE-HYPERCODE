# Backend Maintenance Upgrade (Feb 2026)

## 1. FastAPI Upgrade to 0.115.x
We have upgraded FastAPI to the latest stable version (0.115.x).

**Changes:**
- Updated `requirements.txt`:
  - `fastapi>=0.115.0`
  - `uvicorn>=0.30.0`
  - `pydantic>=2.9.0`
  - `python-multipart>=0.0.9`

**Verification:**
- Full test suite passed.
- `python-multipart` explicitly added as it is now an optional dependency in newer FastAPI versions but required for form parsing.

## 2. Redis Rate Limiting Migration
We migrated from in-memory rate limiting to a distributed Redis-backed solution.

**Features:**
- **Atomic Counting**: Uses Lua script (`INCR` + `EXPIRE`) to ensure race-condition-free counting.
- **Graceful Degradation**: Falls back to in-memory counters if Redis is unavailable.
- **Metrics**: Prometheus counters for:
  - `rate_limit_hits_total`
  - `rate_limit_checks_total`
  - `rate_limit_redis_errors_total`
- **Configuration**:
  - `RATE_LIMIT_WINDOW_SECONDS` (default: 60)
  - `RATE_LIMIT_MAX_REQUESTS` (default: 100)

**New Endpoints:**
- `GET /ready`: Verifies Database and Redis connectivity.

## Rollback Plan

### FastAPI Rollback
If critical regressions occur:
1.  Revert `requirements.txt` to previous versions:
    ```text
    fastapi==0.109.0
    uvicorn==0.27.0
    pydantic==2.5.3
    python-multipart==0.0.6
    ```
2.  Run `pip install -r requirements.txt`.
3.  Restart service.

### Rate Limit Rollback
If Redis issues occur:
1.  The system automatically degrades to in-memory fallback, so immediate rollback is likely unnecessary for availability.
2.  To disable Redis rate limiting entirely, unset `HYPERCODE_REDIS_URL` or set `RATE_LIMIT_MAX_REQUESTS` to a high value.
3.  To revert code: Restore `app/middleware/rate_limit.py` from git history.
