
import pytest
from fastapi import FastAPI, Security
from fastapi.testclient import TestClient
from app.core.auth import get_current_user
from unittest.mock import AsyncMock, patch

# Create a dummy app for testing auth
test_app = FastAPI()

@test_app.get("/protected", dependencies=[Security(get_current_user, scopes=["agent:read"])])
async def protected_endpoint():
    return {"status": "ok"}

client = TestClient(test_app)

@pytest.mark.asyncio
async def test_auth_missing_credentials():
    with patch("app.core.auth.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.API_KEY = "master-key"
        
        response = client.get("/protected")
        assert response.status_code == 401
        assert response.json()["detail"] == "Not authenticated"

@pytest.mark.asyncio
async def test_auth_valid_api_key():
    with patch("app.core.auth.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.API_KEY = "master-key"
        
        # Mock key_manager.is_valid
        # Note: We patch where it is used or the instance itself
        with patch("app.core.auth.key_manager.is_valid", new_callable=AsyncMock) as mock_is_valid:
            mock_is_valid.return_value = True
            
            response = client.get("/protected", headers={"X-API-Key": "valid-key"})
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_auth_invalid_api_key():
    with patch("app.core.auth.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "production"
        mock_settings.API_KEY = "master-key"
        
        with patch("app.core.auth.key_manager.is_valid", new_callable=AsyncMock) as mock_is_valid:
            mock_is_valid.return_value = False
            
            response = client.get("/protected", headers={"X-API-Key": "invalid-key"})
            assert response.status_code == 403
            assert response.json()["detail"] == "Invalid API Key"
