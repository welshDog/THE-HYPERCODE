from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.agent_registry import agent_registry
from app.core.db import db
import asyncio
import json
import logging
import time
from datetime import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws")
async def dashboard_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 1. Fetch Agents
            try:
                agents = await agent_registry.list_agents()
                
                # 2. Enrich with Load/Metrics
                agent_data = []
                for agent in agents:
                    load = await agent_registry.get_load(agent.id)
                    agent_dict = agent.model_dump()
                    agent_dict["load"] = load
                    # Handle datetime serialization for agents
                    for k, v in agent_dict.items():
                        if isinstance(v, datetime):
                            agent_dict[k] = v.isoformat()
                    agent_data.append(agent_dict)
            except Exception as e:
                logger.error(f"Failed to fetch agents: {e}")
                agent_data = []
            
            # 3. Fetch Missions
            try:
                # Fetch recent missions
                recent_missions = await db.mission.find_many(
                    take=20,
                    order={"updatedAt": "desc"}
                )
                missions_data = []
                for m in recent_missions:
                     m_dict = m.model_dump()
                     # Serialize datetimes
                     if m_dict.get('createdAt'): m_dict['createdAt'] = m_dict['createdAt'].isoformat()
                     if m_dict.get('updatedAt'): m_dict['updatedAt'] = m_dict['updatedAt'].isoformat()
                     missions_data.append(m_dict)
            except Exception as e:
                logger.error(f"Failed to fetch missions: {e}")
                missions_data = []

            # 4. Fetch Memory Stats
            try:
                memory_count = await db.memory.count()
                memory_stats = {
                    "total_memories": memory_count,
                    "last_updated": time.time()
                }
            except Exception as e:
                logger.error(f"Failed to fetch memory stats: {e}")
                memory_stats = {"total_memories": 0}
            
            # 5. Construct Payload
            payload = {
                "timestamp": time.time(),
                "agents": agent_data,
                "missions": missions_data,
                "memory": memory_stats,
                "system_status": "operational" 
            }
            
            await websocket.send_json(payload)
            await asyncio.sleep(1) # 1Hz update rate
            
    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket disconnected")
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass
