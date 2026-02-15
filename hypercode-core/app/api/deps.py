from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.security import verify_token
from app.core.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
settings = get_settings()

class SecurityScopes:
    CREW_READ = "crew:read"
    CREW_WRITE = "crew:write"
    TOOL_EXEC = "tool:exec"
    ADMIN = "admin"

def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

def require_scopes(scopes: List[str]):
    def _checker(token_payload: dict = Depends(get_current_user)):
        token_scopes = token_payload.get("scopes", [])
        if "admin" in token_scopes:
            return token_payload
            
        for scope in scopes:
            if scope not in token_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Not enough permissions. Required: {scope}",
                )
        return token_payload
    return _checker
