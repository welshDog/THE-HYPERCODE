from fastapi import APIRouter, HTTPException, Security, Body
from app.core.auth import get_current_user
from app.services.orchestrator import orchestrator
import asyncio
from datetime import datetime, timezone
import random

router = APIRouter()

_SIM_TASK: asyncio.Task | None = None
_SIM_CFG: dict = {"running": False, "mission_id": None, "agent_id": None, "interval": 30.0}


async def _simulate_loop(mission_id: str, agent_id: str, interval_sec: float):
    while _SIM_CFG.get("running", False):
        payload = {
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "cpu": round(random.uniform(0.05, 0.95), 3),
                "mem": round(random.uniform(0.05, 0.95), 3),
                "latency_ms": int(random.uniform(5, 200)),
                "status": "ok",
            },
        }
        try:
            await orchestrator.submit_report(mission_id, agent_id, payload)
        except Exception:
            pass
        await asyncio.sleep(max(float(interval_sec), 1.0))


@router.get("/status", dependencies=[Security(get_current_user, scopes=["mission:read"])])
async def status():
    return {"running": bool(_SIM_CFG.get("running")), "config": _SIM_CFG}


@router.post("/start", dependencies=[Security(get_current_user, scopes=["mission:write"])])
async def start(payload: dict = Body(None)):
    mission_id = (payload or {}).get("mission_id") or "HYPERCODE_HEALTH_CHECK_SIM"
    agent_id = (payload or {}).get("agent_id") or "sim-agent-1"
    interval = float((payload or {}).get("interval_sec") or 30.0)
    if _SIM_CFG.get("running"):
        return {"status": "already_running", "config": _SIM_CFG}
    _SIM_CFG["running"] = True
    _SIM_CFG["mission_id"] = mission_id
    _SIM_CFG["agent_id"] = agent_id
    _SIM_CFG["interval"] = interval
    global _SIM_TASK
    _SIM_TASK = asyncio.create_task(_simulate_loop(mission_id, agent_id, interval))
    return {"status": "started", "config": _SIM_CFG}


@router.post("/stop", dependencies=[Security(get_current_user, scopes=["mission:write"])])
async def stop():
    if not _SIM_CFG.get("running"):
        return {"status": "not_running"}
    _SIM_CFG["running"] = False
    try:
        if _SIM_TASK:
            _SIM_TASK.cancel()
    except Exception:
        pass
    return {"status": "stopped", "config": _SIM_CFG}

