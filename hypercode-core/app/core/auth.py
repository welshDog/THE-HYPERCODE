
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer, SecurityScopes
import jwt
from jwt import PyJWTError
from app.services.key_manager import key_manager
from app.core.config import get_settings
from typing import Optional

settings = get_settings()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        # SEC-02: Patch Auth Bypass - Require API Key if configured, or fail safe
        if not settings.API_KEY:
             # If no API Key configured in settings, we must NOT allow access by default in production
             if settings.ENVIRONMENT not in ["local", "test"]:
                 raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                    detail="Server misconfiguration: API_KEY not set"
                 )
             return True # Only allow in local/test if explicitly intended
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

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme)
):
    # SEC-02: Remove backdoor for local dev that bypasses auth completely
    # if settings.ENVIRONMENT == "local" and not token:
    #    return {"sub": "dev-user", "scopes": ["mission:write", "mission:read", "mission:assign"]}

    if not token:
        # Fallback to API Key check for M2M if needed, but for now strict JWT or API Key separate
        # If we want to allow API Key to bypass scopes, we'd handle it here.
        # But instructions say "Add JWT auth... and RBAC".
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = None
    try:
        key = getattr(settings, "JWT_PUBLIC_KEY", None)
        if key:
            payload = jwt.decode(token, key, algorithms=["RS256"])
        else:
            # SEC-02: Patch JWT Bypass - Do not allow unverified claims
            # Fail securely if no key is configured
            if settings.ENVIRONMENT not in ["local", "test"]:
                 raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Server configuration error: JWT_PUBLIC_KEY missing"
                )
            # Only in local/test, and ONLY if strictly necessary (better to warn)
            # Ideally we should still require a key even in local. 
            # For now, we raise error to enforce security.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="JWT Public Key not configured"
            )
    except PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_scopes = payload.get("scopes", [])
    # Handle space-separated scopes string if that's the format
    if isinstance(token_scopes, str):
        token_scopes = token_scopes.split(" ")
        
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
                raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": f"Bearer scope=\"{security_scopes.scope_str}\""},
            )
    return payload
