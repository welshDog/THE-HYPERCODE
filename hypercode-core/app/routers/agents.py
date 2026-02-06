from fastapi import APIRouter, HTTPException, Depends, Response, WebSocket, WebSocketDisconnect, status
from sse_starlette.sse import EventSourceResponse
from app.services.agent_registry import agent_registry, AGENT_STREAM_CLIENTS, STREAM_LATENCY_MS, ERROR_COUNT, _env as ENV_LABEL, _ver as VER_LABEL
from app.schemas.agent import AgentMetadata, AgentRegistrationRequest, AgentHeartbeat
from app.core.auth import verify_api_key
import logging
import os
import asyncio
import json
from pathlib import Path

router = APIRouter()
logger = logging.getLogger(__name__)
CONNECTED_AGENTS: dict[str, WebSocket] = {}

async def sse_event_generator(one_shot: bool = False, max_failures: int | None = 3, connect_timeout: float = 5.0, idle_sleep: float = 0.1):
    AGENT_STREAM_CLIENTS.labels(ENV_LABEL, VER_LABEL).inc()
    try:
        failures = 0
        pubsub = agent_registry.redis.pubsub()
        while True:
            try:
                await asyncio.wait_for(pubsub.subscribe(agent_registry.pubsub_channel), timeout=connect_timeout)
                try:
                    # Prefer native async listener if available; fallback to polling
                    if one_shot:
                        await pubsub.unsubscribe(agent_registry.pubsub_channel)
                        break
                    if hasattr(pubsub, "listen"):
                        listener = await pubsub.listen()
                        async for message in listener:
                            if message.get("type") == "message":
                                try:
                                    t0 = asyncio.get_event_loop().time()
                                    payload = message["data"].decode("utf-8")
                                    yield payload
                                    dt = (asyncio.get_event_loop().time() - t0) * 1000.0
                                    STREAM_LATENCY_MS.labels("GET", "200", ENV_LABEL, VER_LABEL).observe(dt)
                                except Exception:
                                    continue
                    else:
                        while True:
                            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                            if message and message.get("type") == "message":
                                try:
                                    t0 = asyncio.get_event_loop().time()
                                    payload = message["data"].decode("utf-8")
                                    yield payload
                                    dt = (asyncio.get_event_loop().time() - t0) * 1000.0
                                    STREAM_LATENCY_MS.labels("GET", "200", ENV_LABEL, VER_LABEL).observe(dt)
                                except Exception:
                                    continue
                            await asyncio.sleep(idle_sleep)
                except asyncio.CancelledError:
                    await pubsub.unsubscribe(agent_registry.pubsub_channel)
                    break
            except Exception:
                ERROR_COUNT.labels("stream", ENV_LABEL, VER_LABEL).inc()
                failures += 1
                if max_failures is not None and failures >= max_failures:
                    break
                await asyncio.sleep(0.1)
    finally:
        AGENT_STREAM_CLIENTS.labels(ENV_LABEL, VER_LABEL).dec()

@router.get("/", response_model=list[AgentMetadata])
async def get_agents():
    return await agent_registry.list_agents()

@router.post("/register", response_model=AgentMetadata)
async def register_agent(request: AgentRegistrationRequest):
    data, no_change = await agent_registry.register_agent(request)
    return data

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
async def watch_agents(one_shot: bool = False):
    """Server-Sent Events stream for agent registry changes."""
    return EventSourceResponse(sse_event_generator(one_shot))

@router.get("/stream")
async def stream_agents(one_shot: bool = False):
    """Alternate SSE endpoint emitting agent lifecycle events."""
    return EventSourceResponse(sse_event_generator(one_shot))

@router.get("/bible")
async def get_agents_bible():
    base = Path(__file__).resolve().parents[4]
    md_path = base / "agents" / "HYPER-AGENT-BIBLE.md"
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="Agents Bible not found")
    content = md_path.read_text(encoding="utf-8")
    return Response(content, media_type="text/plain; charset=utf-8")

@router.websocket("/{agent_id}/channel")
async def agent_channel(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    logger.info(f"Agent {agent_id} connected via WebSocket")
    CONNECTED_AGENTS[agent_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"Agent {agent_id} disconnected")
    finally:
        if CONNECTED_AGENTS.get(agent_id) is websocket:
            CONNECTED_AGENTS.pop(agent_id, None)

@router.get("/{agent_id}", response_model=AgentMetadata)
async def get_agent(agent_id: str):
    agent = await agent_registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.post("/{agent_id}/send")
async def send_task(agent_id: str, payload: dict):
    ws = CONNECTED_AGENTS.get(agent_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Agent not connected")
    try:
        await ws.send_text(json.dumps({"type": "task", "payload": payload}))
        return Response(status_code=status.HTTP_202_ACCEPTED)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send task")
