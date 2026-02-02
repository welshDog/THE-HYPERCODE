
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.services.key_manager import key_manager

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        # Check if auth is disabled (dev mode fallback handled in key_manager or here?)
        # Actually, key_manager fallback logic handles the env var check.
        # But if NO key is provided at all, and env var is set, we should fail.
        # If env var is NOT set, we allow open access (Dev).
        from app.core.config import get_settings
        settings = get_settings()
        if not settings.API_KEY:
             # Open mode (Dev)
             return True
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API Key"
        )

    is_valid = await key_manager.is_valid(api_key)
    
    if is_valid:
        return True
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API Key"
    )
