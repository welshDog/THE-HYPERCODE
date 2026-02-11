import pytest
from fastapi import HTTPException, status
from fastapi.security import SecurityScopes
from unittest.mock import AsyncMock, Mock, patch
from app.core.auth import verify_api_key, get_current_user

# Mock Settings
@pytest.fixture
def mock_settings():
    with patch("app.core.auth.settings") as mock:
        mock.API_KEY = "test-secret-key"
        mock.ENVIRONMENT = "production"
        mock.JWT_PUBLIC_KEY = "test-public-key"
        yield mock

# Mock Key Manager
@pytest.fixture
def mock_key_manager():
    with patch("app.core.auth.key_manager") as mock:
        yield mock

# Tests for verify_api_key

@pytest.mark.asyncio
async def test_verify_api_key_valid(mock_settings, mock_key_manager):
    mock_key_manager.is_valid = AsyncMock(return_value=True)
    result = await verify_api_key(api_key="valid-key")
    assert result is True
    mock_key_manager.is_valid.assert_called_with("valid-key")

@pytest.mark.asyncio
async def test_verify_api_key_invalid(mock_settings, mock_key_manager):
    mock_key_manager.is_valid = AsyncMock(return_value=False)
    with pytest.raises(HTTPException) as exc:
        await verify_api_key(api_key="invalid-key")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Invalid API Key"

@pytest.mark.asyncio
async def test_verify_api_key_missing_key_provided_none(mock_settings):
    # When api_key is None, it should raise 403 because API_KEY is set in settings
    with pytest.raises(HTTPException) as exc:
        await verify_api_key(api_key=None)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc.value.detail == "Missing API Key"

@pytest.mark.asyncio
async def test_verify_api_key_missing_settings_key_prod(mock_settings):
    # If API_KEY is NOT set in settings, and env is production -> 500 Error
    mock_settings.API_KEY = None
    mock_settings.ENVIRONMENT = "production"
    
    with pytest.raises(HTTPException) as exc:
        await verify_api_key(api_key=None)
    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc.value.detail == "Server misconfiguration: API_KEY not set"

@pytest.mark.asyncio
async def test_verify_api_key_missing_settings_key_local(mock_settings):
    # If API_KEY is NOT set in settings, and env is local -> Allow (return True)
    mock_settings.API_KEY = None
    mock_settings.ENVIRONMENT = "local"
    
    result = await verify_api_key(api_key=None)
    assert result is True

# Tests for get_current_user

@pytest.mark.asyncio
async def test_get_current_user_no_token():
    security_scopes = SecurityScopes()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(security_scopes, token=None)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == "Not authenticated"

@pytest.mark.asyncio
async def test_get_current_user_valid_token_no_scopes(mock_settings):
    security_scopes = SecurityScopes()
    token = "valid.jwt.token"
    
    with patch("app.core.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = {"sub": "user123", "scopes": []}
        
        payload = await get_current_user(security_scopes, token)
        assert payload["sub"] == "user123"
        mock_decode.assert_called_once_with(token, "test-public-key", algorithms=["RS256"])

@pytest.mark.asyncio
async def test_get_current_user_valid_token_with_scopes(mock_settings):
    security_scopes = SecurityScopes(scopes=["mission:read"])
    token = "valid.jwt.token"
    
    with patch("app.core.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = {"sub": "user123", "scopes": ["mission:read", "mission:write"]}
        
        payload = await get_current_user(security_scopes, token)
        assert payload["sub"] == "user123"

@pytest.mark.asyncio
async def test_get_current_user_missing_scopes(mock_settings):
    security_scopes = SecurityScopes(scopes=["mission:admin"])
    token = "valid.jwt.token"
    
    with patch("app.core.auth.jwt.decode") as mock_decode:
        mock_decode.return_value = {"sub": "user123", "scopes": ["mission:read"]}
        
        with pytest.raises(HTTPException) as exc:
            await get_current_user(security_scopes, token)
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.value.detail == "Not enough permissions"

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(mock_settings):
    security_scopes = SecurityScopes()
    token = "invalid.token"
    
    with patch("app.core.auth.jwt.decode") as mock_decode:
        mock_decode.side_effect = Exception("Invalid token")
        
        with pytest.raises(HTTPException) as exc:
            await get_current_user(security_scopes, token)
        assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc.value.detail == "Could not validate credentials"

@pytest.mark.asyncio
async def test_get_current_user_missing_public_key_prod(mock_settings):
    mock_settings.JWT_PUBLIC_KEY = None
    mock_settings.ENVIRONMENT = "production"
    security_scopes = SecurityScopes()
    token = "some.token"
    
    with pytest.raises(HTTPException) as exc:
        await get_current_user(security_scopes, token)
    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc.value.detail == "Server configuration error: JWT_PUBLIC_KEY missing"

@pytest.mark.asyncio
async def test_get_current_user_missing_public_key_local(mock_settings):
    mock_settings.JWT_PUBLIC_KEY = None
    mock_settings.ENVIRONMENT = "local"
    security_scopes = SecurityScopes()
    token = "some.token"
    
    with pytest.raises(HTTPException) as exc:
        await get_current_user(security_scopes, token)
    # Even in local, it currently raises 500 "JWT Public Key not configured" based on the code logic
    assert exc.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert exc.value.detail == "JWT Public Key not configured"
