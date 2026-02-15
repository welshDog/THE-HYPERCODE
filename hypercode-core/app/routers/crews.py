from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas.crew import CrewManifest, CrewAssemblyResponse, CrewStatus
from typing import Dict
import uuid
import logging

# Logger setup
logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["crews"],
    responses={404: {"description": "Not found"}},
)

# In-memory storage for MVP (To be replaced with DB/Redis)
_CREWS: Dict[str, CrewManifest] = {}
_CREW_STATUS: Dict[str, CrewStatus] = {}
_CREW_ENDPOINTS: Dict[str, Dict[str, str]] = {}

async def _spawn_agents(manifest: CrewManifest):
    """
    Background task to simulate agent spawning.
    In real implementation, this would trigger Docker/K8s/Celery tasks.
    """
    logger.info(f"Starting assembly for crew: {manifest.crew_id}")
    _CREW_STATUS[manifest.crew_id] = CrewStatus.ASSEMBLING
    
    try:
        endpoints = {}
        for agent in manifest.agents:
            # Simulate spawning delay/logic
            # In V2, this calls the Factory Spawner
            logger.info(f"Spawning agent: {agent.name} ({agent.role})")
            
            # Mock endpoint generation
            sanitized_name = agent.name.lower().replace(" ", "-")
            endpoints[agent.name] = f"http://{sanitized_name}.{manifest.crew_id}.svc:8000"
            
        _CREW_ENDPOINTS[manifest.crew_id] = endpoints
        _CREW_STATUS[manifest.crew_id] = CrewStatus.READY
        logger.info(f"Crew {manifest.crew_id} assembly complete.")
        
    except Exception as e:
        logger.error(f"Failed to assemble crew {manifest.crew_id}: {e}")
        _CREW_STATUS[manifest.crew_id] = CrewStatus.FAILED

@router.post("/assemble", response_model=CrewAssemblyResponse, status_code=201)
async def assemble_crew(manifest: CrewManifest, background_tasks: BackgroundTasks):
    """
    Assemble a multi-agent crew based on the provided manifest.
    Triggers asynchronous spawning of agents.
    """
    if not manifest.crew_id:
        manifest.crew_id = str(uuid.uuid4())
        
    if manifest.crew_id in _CREWS:
        raise HTTPException(status_code=409, detail="Crew ID already exists")

    _CREWS[manifest.crew_id] = manifest
    _CREW_STATUS[manifest.crew_id] = CrewStatus.ASSEMBLING
    
    # Trigger background assembly
    background_tasks.add_task(_spawn_agents, manifest)
    
    return CrewAssemblyResponse(
        crew_id=manifest.crew_id,
        status=CrewStatus.ASSEMBLING,
        endpoints={}, # Correct field for response model
        message="Crew assembly initiated."
    )

@router.get("/{crew_id}/status", response_model=CrewAssemblyResponse)
async def get_crew_status(crew_id: str):
    """
    Get the current status and endpoints of a crew.
    """
    if crew_id not in _CREWS:
        raise HTTPException(status_code=404, detail="Crew not found")
        
    return CrewAssemblyResponse(
        crew_id=crew_id,
        status=_CREW_STATUS.get(crew_id, CrewStatus.FAILED),
        endpoints=_CREW_ENDPOINTS.get(crew_id, {}),
        message="Status retrieved."
    )
