
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from app.services.llm import llm_service
from app.services.agent_registry import agent_registry
from app.schemas.agent import AgentMetadata, AgentRegistrationRequest, AgentHeartbeat
from app.core.auth import verify_api_key
import uuid
import logging
import asyncio

# Note: WebSocket routes must be registered differently or carefully with APIRouter prefixes.
# We will ensure the router handles this correctly.
router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    messages: list[dict]
    model: str = "gpt-4o"

@router.get("/", response_model=list[AgentMetadata])
async def get_agents():
    return await agent_registry.list_agents()

@router.get("/{agent_id}", response_model=AgentMetadata)
async def get_agent(agent_id: str):
    agent = await agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("/register", response_model=AgentMetadata, dependencies=[Depends(verify_api_key)])
async def register_agent(request: AgentRegistrationRequest):
    agent_id = str(uuid.uuid4())
    agent = AgentMetadata(
        id=agent_id,
        **request.model_dump()
    )
    return await agent_registry.register_agent(agent)

@router.post("/heartbeat", dependencies=[Depends(verify_api_key)])
async def heartbeat(heartbeat: AgentHeartbeat):
    success = await agent_registry.update_heartbeat(
        heartbeat.agent_id, 
        heartbeat.status, 
        heartbeat.load
    )
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found or expired")
    return {"status": "ok"}

# FIX: WebSocket routes on APIRouter with prefix need careful handling.
# Ideally, we should define this path relative to the router's prefix.
# If router is mounted at "/agents", this becomes "/agents/{agent_id}/channel"
# NOTE: WebSocket auth is complex to handle via headers in browser JS, usually done via query param or initial message.
# For now, we leave it open or check protocol in handshake if needed.
@router.websocket("/{agent_id}/channel")
async def agent_websocket(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    agent = await agent_registry.get_agent(agent_id)
    
    if not agent:
        # WebSocket close codes: 4000-4999 are private/framework specific.
        # 1008 is Policy Violation, which fits "Unauthorized/Not Found" generic.
        await websocket.close(code=1008, reason="Agent not found")
        return
    
    try:
        while True:
            # Simple heartbeat mechanism
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                # Update heartbeat in registry
                await agent_registry.update_heartbeat(agent_id, agent.status)
            else:
                # Handle other messages (e.g., task status updates)
                pass
    except WebSocketDisconnect:
        logger.info(f"Agent {agent_id} disconnected")
        # Optionally mark agent as offline
        # await agent_registry.update_status(agent_id, AgentStatus.OFFLINE)

@router.delete("/{agent_id}", dependencies=[Depends(verify_api_key)])
async def deregister_agent(agent_id: str):
    await agent_registry.deregister_agent(agent_id)
    return {"status": "deregistered"}

@router.post("/chat", dependencies=[Depends(verify_api_key)])
async def chat_with_agent(request: ChatRequest):
    try:
        response = await llm_service.generate_response(
            messages=request.messages,
            model=request.model
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
