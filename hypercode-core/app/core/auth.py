
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer, SecurityScopes
from jose import jwt, JWTError
from app.services.key_manager import key_manager
from app.core.config import get_settings
from typing import Optional

settings = get_settings()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        if not settings.API_KEY:
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

async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    api_key: Optional[str] = Security(api_key_header)
):
    if settings.ENVIRONMENT == "local" and not token and not api_key:
        return {"sub": "dev-user", "scopes": ["mission:write", "mission:read", "mission:assign", "agent:register", "agent:heartbeat", "agent:read"]}

    # Support API Key as a fallback for M2M (Agents)
    if not token and api_key:
        is_valid = await key_manager.is_valid(api_key)
        if is_valid:
            # Grant agent scopes
            agent_scopes = ["agent:register", "agent:heartbeat", "agent:read"]
            
            for scope in security_scopes.scopes:
                if scope not in agent_scopes:
                     raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Not enough permissions",
                        headers={"WWW-Authenticate": "ApiKey"},
                    )
            return {"sub": "agent-service", "scopes": agent_scopes}
        else:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API Key"
            )

    if not token:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except (JWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token_scopes = payload.get("scopes", [])
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
