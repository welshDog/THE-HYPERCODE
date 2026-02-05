import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture(autouse=True)
async def set_local_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    yield


@pytest.mark.asyncio
async def test_report_endpoint_success(async_client: AsyncClient):
    payload = {"agent_id": "agent_test", "overall_project_health": {"composite_score": 80}}
    res = await async_client.post(
        "/orchestrator/mission/HYPERCODE_HEALTH_CHECK_001/report",
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert data.get("ok") is True
    assert "path" in data


@pytest.mark.asyncio
async def test_report_endpoint_error(monkeypatch, async_client: AsyncClient):
    from app.services.orchestrator import orchestrator

    async def fake_submit(mission_id: str, agent_id: str, report: dict):
        return {"ok": False, "error": "boom"}

    monkeypatch.setattr(orchestrator, "submit_report", fake_submit)
    res = await async_client.post(
        "/orchestrator/mission/HYPERCODE_HEALTH_CHECK_001/report",
        json={"agent_id": "x"},
    )
    assert res.status_code == 500
    assert res.json()["detail"] == "boom"


@pytest.mark.asyncio
async def test_report_endpoint_invalid_json(async_client: AsyncClient):
    res = await async_client.post(
        "/orchestrator/mission/HYPERCODE_HEALTH_CHECK_001/report",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert res.status_code in (400, 422)
