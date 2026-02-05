from fastapi import APIRouter, HTTPException, Security, Body
from app.schemas.mission import MissionRequest, MissionStatus
from app.services.orchestrator import orchestrator
from app.core.auth import get_current_user

router = APIRouter()

@router.post("/mission", response_model=MissionStatus, dependencies=[Security(get_current_user, scopes=["mission:write"])])
async def submit_mission(req: MissionRequest):
    return await orchestrator.submit(req)

@router.post("/assign", response_model=MissionStatus, dependencies=[Security(get_current_user, scopes=["mission:assign"])])
async def assign_next():
    res = await orchestrator.assign_next()
    if not res:
        raise HTTPException(status_code=204, detail="")
    return res

@router.post("/{mission_id}/start", response_model=MissionStatus, dependencies=[Security(get_current_user, scopes=["mission:write"])])
async def start(mission_id: str):
    res = await orchestrator.start(mission_id)
    if not res:
        raise HTTPException(status_code=404, detail="not found")
    return res

@router.post("/mission/{mission_id}/report", dependencies=[Security(get_current_user, scopes=["mission:write"])])
async def submit_health_report(mission_id: str, payload: dict = Body(...)):
    agent_id = str(payload.get("agent_id") or "agent")
    res = await orchestrator.submit_report(mission_id, agent_id, payload)
    if not res.get("ok"):
        raise HTTPException(status_code=500, detail=res.get("error") or "submit failed")
    return res

@router.post("/{mission_id}/verify", response_model=MissionStatus, dependencies=[Security(get_current_user, scopes=["mission:write"])])
async def verify(mission_id: str):
    res = await orchestrator.verify(mission_id)
    if not res:
        raise HTTPException(status_code=404, detail="not found")
    return res

@router.post("/{mission_id}/complete", response_model=MissionStatus, dependencies=[Security(get_current_user, scopes=["mission:write"])])
async def complete(mission_id: str):
    res = await orchestrator.complete(mission_id)
    if not res:
        raise HTTPException(status_code=404, detail="not found")
    return res

@router.post("/{mission_id}/fail", response_model=MissionStatus, dependencies=[Security(get_current_user, scopes=["mission:write"])])
async def fail(mission_id: str):
    res = await orchestrator.fail(mission_id)
    if not res:
        raise HTTPException(status_code=404, detail="not found")
    return res

@router.get("/list", dependencies=[Security(get_current_user, scopes=["mission:read"])])
async def list_missions(limit: int = 10):
    items = await orchestrator.list(limit=limit)
    return items

@router.get("/{mission_id}/audit", dependencies=[Security(get_current_user, scopes=["mission:read"])])
async def get_audit(mission_id: str):
    rows = await orchestrator.audit(mission_id)
    if rows is None:
        raise HTTPException(status_code=404, detail="not found")
    return rows

@router.post("/{mission_id}/approve", response_model=MissionStatus, dependencies=[Security(get_current_user, scopes=["mission:write"])])
async def approve(mission_id: str):
    res = await orchestrator.approve(mission_id)
    if not res:
        raise HTTPException(status_code=404, detail="not found")
    return res

@router.get("/by-id/{mission_id}", response_model=MissionStatus, dependencies=[Security(get_current_user, scopes=["mission:read"])])
async def get_status(mission_id: str):
    res = await orchestrator.get(mission_id)
    if not res:
        raise HTTPException(status_code=404, detail="not found")
    return res

@router.get("/{mission_id}", response_model=MissionStatus, dependencies=[Security(get_current_user, scopes=["mission:read"])])
async def get_status_alias(mission_id: str):
    res = await orchestrator.get(mission_id)
    if not res:
        raise HTTPException(status_code=404, detail="not found")
    return res
