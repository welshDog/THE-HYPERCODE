import asyncio
import pytest
from fastapi.testclient import TestClient
from main import app
from app.services.agent_registry import agent_registry
from app.schemas.agent import AgentStatus


@pytest.mark.asyncio
async def test_heartbeat_full_lifecycle(async_client):
    payload = {
        "name": "Lifecycle Agent",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": ["c"],
        "topics": ["t"],
        "health_url": "http://localhost",
        "dedup_key": "00000000-0000-0000-0000-00000000LC"
    }
    r = await async_client.post("/agents/register", json=payload)
    assert r.status_code == 200
    agent_id = r.json()["id"]

    hb1 = {"agent_id": agent_id, "status": "busy", "load": 0.2}
    r2 = await async_client.post("/agents/heartbeat", json=hb1)
    assert r2.status_code == 200

    r3 = await async_client.get(f"/agents/{agent_id}")
    assert r3.status_code == 200
    assert r3.json()["status"] == "busy"

    await agent_registry.check_timeouts()
    r4 = await async_client.get(f"/agents/{agent_id}")
    assert r4.status_code == 200
    assert r4.json()["status"] in ["busy", "active"]

    upd = await agent_registry.update_heartbeat(agent_id, AgentStatus.ACTIVE)
    assert upd

    await agent_registry.deregister_agent(agent_id)
    r5 = await async_client.get(f"/agents/{agent_id}")
    assert r5.status_code == 200
    assert r5.json()["status"] == "offline"


@pytest.mark.asyncio
async def test_timeout_marks_offline(async_client, monkeypatch):
    payload = {
        "name": "Timeout Agent",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": [],
        "topics": [],
        "health_url": None,
        "dedup_key": "00000000-0000-0000-0000-00000000TO"
    }
    r = await async_client.post("/agents/register", json=payload)
    assert r.status_code == 200
    agent_id = r.json()["id"]

    agent_registry.ttl = 0
    await agent_registry.check_timeouts()

    r2 = await async_client.get(f"/agents/{agent_id}")
    assert r2.status_code == 200
    assert r2.json()["status"] == "offline"
