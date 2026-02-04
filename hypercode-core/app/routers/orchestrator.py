from fastapi import APIRouter, HTTPException, Security
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

@router.get("/{mission_id}", response_model=MissionStatus, dependencies=[Security(get_current_user, scopes=["mission:read"])])
async def get_status(mission_id: str):
    res = await orchestrator.get(mission_id)
    if not res:
        raise HTTPException(status_code=404, detail="not found")
    return res
