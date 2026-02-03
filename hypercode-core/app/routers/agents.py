from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse
from app.services.agent_registry import agent_registry
from app.schemas.agent import AgentMetadata, AgentRegistrationRequest, AgentHeartbeat
from app.core.auth import verify_api_key
import logging
import asyncio
import json

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=list[AgentMetadata])
async def get_agents():
    return await agent_registry.list_agents()

@router.get("/{agent_id}", response_model=AgentMetadata)
async def get_agent(agent_id: str):
    agent = await agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("/register", response_model=AgentMetadata)
async def register_agent(request: AgentRegistrationRequest):
    return await agent_registry.register_agent(request)

@router.post("/heartbeat")
async def heartbeat(heartbeat: AgentHeartbeat):
    success = await agent_registry.update_heartbeat(
        heartbeat.agent_id, 
        heartbeat.status, 
        heartbeat.load
    )
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"status": "ok"}

@router.delete("/{agent_id}")
async def deregister_agent(agent_id: str):
    await agent_registry.deregister_agent(agent_id)
    return {"status": "deregistered"}

@router.get("/watch")
async def watch_agents():
    """Server-Sent Events stream for agent registry changes."""
    async def event_generator():
        pubsub = agent_registry.redis.pubsub()
        await pubsub.subscribe(agent_registry.pubsub_channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield message["data"].decode("utf-8")
        except asyncio.CancelledError:
            await pubsub.unsubscribe(agent_registry.pubsub_channel)
            
    return EventSourceResponse(event_generator())

@router.get("/stream")
async def stream_agents():
    """Alternate SSE endpoint emitting agent lifecycle events."""
    async def event_generator():
        pubsub = agent_registry.redis.pubsub()
        await pubsub.subscribe(agent_registry.pubsub_channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield message["data"].decode("utf-8")
        except asyncio.CancelledError:
            await pubsub.unsubscribe(agent_registry.pubsub_channel)
    return EventSourceResponse(event_generator())
