import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from app.routers.simulator import _SIM_CFG

from app.core.auth import get_current_user

@pytest.fixture
def client():
    # Reset config before each test
    _SIM_CFG["running"] = False
    _SIM_CFG["mission_id"] = None
    _SIM_CFG["agent_id"] = None
    _SIM_CFG["interval"] = 30.0
    return TestClient(app)

@pytest.fixture
def mock_auth():
    async def mock_get_current_user():
        return {"id": "test-user", "scopes": ["mission:read", "mission:write"]}
    return mock_get_current_user

@pytest.fixture
def mock_orchestrator():
    mock = AsyncMock()
    mock.submit_report = AsyncMock()
    return mock

def test_simulator_status(client, mock_auth):
    app.dependency_overrides[get_current_user] = mock_auth
    
    # Debug print
    print(f"Overrides: {app.dependency_overrides}")
    
    response = client.get("/simulator/status")
    assert response.status_code == 200
    assert response.json()["running"] is False

def test_simulator_start_stop(client, mock_auth, mock_orchestrator):
    app.dependency_overrides["get_current_user"] = mock_auth
    
    with patch("app.routers.simulator.orchestrator", mock_orchestrator):
        # Start
        payload = {"mission_id": "test-mission", "agent_id": "test-agent", "interval_sec": 0.1}
        response = client.post("/simulator/start", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "started"
        
        # Verify status
        response = client.get("/simulator/status")
        assert response.json()["running"] is True
        
        # Start again (already running)
        response = client.post("/simulator/start", json=payload)
        assert response.json()["status"] == "already_running"
        
        # Stop
        response = client.post("/simulator/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"
        
        # Verify status
        response = client.get("/simulator/status")
        assert response.json()["running"] is False
        
        # Stop again (not running)
        response = client.post("/simulator/stop")
        assert response.json()["status"] == "not_running"

@pytest.mark.asyncio
async def test_simulator_loop(mock_orchestrator):
    from app.routers.simulator import _simulate_loop, _SIM_CFG
    
    _SIM_CFG["running"] = True
    
    # Run the loop for a short time
    # We'll use a side effect on submit_report to stop the loop after one call
    async def stop_loop(*args, **kwargs):
        _SIM_CFG["running"] = False
        
    mock_orchestrator.submit_report.side_effect = stop_loop
    
    with patch("app.routers.simulator.orchestrator", mock_orchestrator):
        # We need to mock asyncio.sleep to avoid waiting
        with patch("asyncio.sleep", AsyncMock()):
             await _simulate_loop("m1", "a1", 0.1)
             
    assert mock_orchestrator.submit_report.called
