import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture(autouse=True)
async def set_local_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    yield


@pytest.mark.asyncio
async def test_mission_flow_and_report(async_client: AsyncClient):
    create = await async_client.post(
        "/orchestrator/mission",
        json={"title": "Demo", "priority": 10, "payload": {"requirements": {"capabilities": ["backend"]}}},
    )
    assert create.status_code == 200
    mission_id = create.json()["id"]

    await async_client.post("/orchestrator/assign")
    await async_client.post(f"/orchestrator/{mission_id}/start")
    await async_client.post(f"/orchestrator/{mission_id}/verify")
    await async_client.post(f"/orchestrator/{mission_id}/complete")

    rep = await async_client.post(
        f"/orchestrator/mission/{mission_id}/report",
        json={"agent_id": "agent_test", "overall_project_health": {"composite_score": 70}},
    )
    assert rep.status_code == 200

    audit = await async_client.get(f"/orchestrator/{mission_id}/audit")
    assert audit.status_code == 200
    rows = audit.json()
    assert isinstance(rows, list)
    assert any(r.get("transition") == "report" for r in rows)
