
import pytest
from fastapi.testclient import TestClient
from main import app
from app.core.auth import get_current_user
from app.services.event_bus import event_bus
from unittest.mock import AsyncMock, patch
import json

# Override dependency
async def mock_get_current_user():
    return {"sub": "test-user", "scopes": ["mission:write", "mission:read", "mission:assign"]}

app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)

@pytest.mark.asyncio
async def test_mission_full_lifecycle():
    # Mock EventBus
    with patch.object(event_bus, "publish_stream", new_callable=AsyncMock) as mock_publish:
        mock_publish.return_value = "1-0" # Mock entry ID

        # 1. Submit
        req = {"title": "Lifecycle Mission", "priority": 80, "payload": {"foo": "bar"}}
        r = client.post("/orchestrator/mission", json=req)
        assert r.status_code == 200
        mid = r.json()["id"]
        assert r.json()["state"] == "queued"
        
        # Verify Create Event
        assert mock_publish.call_count == 1
        args, _ = mock_publish.call_args
        assert args[0] == "mission.events"
        assert args[1].message_type == "mission.created"

        # 2. Assign (need an agent first)
        # Register agent
        agent_data = {
            "name": "Test Agent",
            "role": "worker",
            "capabilities": ["foo"],
            "topics": [],
            "health_url": "http://localhost",
            "dedup_key": "unique-lifecycle-key"
        }
        client.post("/agents/register", json=agent_data)
        
        # Assign
        r = client.post("/orchestrator/assign")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == mid
        assert data["state"] == "assigned"
        
        # Verify Assign Event
        assert mock_publish.call_count == 2
        args, _ = mock_publish.call_args
        assert args[1].message_type == "mission.assigned"

        # 3. Start
        r = client.post(f"/orchestrator/{mid}/start")
        assert r.status_code == 200
        assert r.json()["state"] == "executing"
        
        # Verify Start Event
        assert mock_publish.call_count == 3
        args, _ = mock_publish.call_args
        assert args[1].message_type == "mission.executing"
        
        # 4. Complete
        r = client.post(f"/orchestrator/{mid}/complete")
        assert r.status_code == 200
        assert r.json()["state"] == "completed"

        # Verify Complete Event
        assert mock_publish.call_count == 4
        args, _ = mock_publish.call_args
        assert args[1].message_type == "mission.completed"

        # 5. Verify Persistence (Access DB directly via fallback or property if available)
        # Since we use the in-memory fallback in tests (if no real DB), we can check db.mission._items
        from app.core.db import db
        # Wait for async writes if any (though they are awaited in orchestrator)
        
        # In the test environment, we expect _InMemoryDB to be used if Prisma fails or is mocked
        if hasattr(db, "mission") and hasattr(db.mission, "_items"):
            item = db.mission._items.get(mid)
            if item:
                assert item["status"] == "completed"
            
            # Check Audit Logs
            if hasattr(db, "auditlog") and hasattr(db.auditlog, "_items"):
                logs = list(db.auditlog._items.values())
                mission_logs = [l for l in logs if l["missionId"] == mid]
                # We expect at least 4 logs: create, assign, executing, completed
                assert len(mission_logs) >= 4
                
                transitions = [l["transition"] for l in mission_logs]
                assert "create" in transitions
                assert "assign" in transitions
                assert "update" in transitions 
