"""
Real-Time Mission Control Dashboard API

Provides WebSocket endpoint for streaming live agent status,
mission progress, and system metrics to the frontend.

Phase 1: Real-Time Mission Control Dashboard
Estimated: 3 days | Priority: High
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import asyncio
import json
import time
from datetime import datetime

from app.core.config import get_settings
from app.services.redis_client import get_redis_client

settings = get_settings()
router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Active WebSocket connections
active_connections: List[WebSocket] = []


class DashboardManager:
    """Manages real-time dashboard data aggregation and broadcasting."""
    
    def __init__(self):
        self.redis_client = None
    
    async def connect(self, websocket: WebSocket):
        """Accept and register new WebSocket connection."""
        await websocket.accept()
        active_connections.append(websocket)
        print(f"📡 New dashboard connection. Total: {len(active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove disconnected WebSocket."""
        active_connections.remove(websocket)
        print(f"📡 Dashboard disconnected. Total: {len(active_connections)}")
    
    async def get_agent_status(self) -> List[Dict[str, Any]]:
        """Fetch current status of all agents from Redis."""
        if not self.redis_client:
            self.redis_client = await get_redis_client()
        
        agents = []
        agent_names = [
            "project-strategist",
            "frontend-specialist",
            "backend-specialist",
            "database-architect",
            "qa-engineer",
            "devops-engineer",
            "security-engineer",
            "system-architect"
        ]
        
        for agent_name in agent_names:
            # Fetch agent status from Redis
            status_key = f"agents:status:{agent_name}"
            status_data = await self.redis_client.hgetall(status_key)
            
            if status_data:
                agents.append({
                    "id": agent_name,
                    "name": agent_name.replace("-", " ").title(),
                    "status": status_data.get(b"status", b"idle").decode(),
                    "current_task": status_data.get(b"current_task", b"").decode(),
                    "last_heartbeat": status_data.get(b"last_heartbeat", b"").decode(),
                    "metrics": {
                        "cpu": float(status_data.get(b"cpu", b"0").decode() or 0),
                        "memory": float(status_data.get(b"memory", b"0").decode() or 0),
                        "tasks_completed": int(status_data.get(b"tasks_completed", b"0").decode() or 0)
                    }
                })
            else:
                # Agent not reporting (offline or starting)
                agents.append({
                    "id": agent_name,
                    "name": agent_name.replace("-", " ").title(),
                    "status": "offline",
                    "current_task": "",
                    "last_heartbeat": "",
                    "metrics": {
                        "cpu": 0,
                        "memory": 0,
                        "tasks_completed": 0
                    }
                })
        
        return agents
    
    async def get_active_missions(self) -> List[Dict[str, Any]]:
        """Fetch active missions from Redis."""
        if not self.redis_client:
            self.redis_client = await get_redis_client()
        
        # Get active mission IDs
        mission_ids = await self.redis_client.lrange("missions:active", 0, 9)
        
        missions = []
        for mission_id in mission_ids:
            mission_key = f"missions:{mission_id.decode()}"
            mission_data = await self.redis_client.hgetall(mission_key)
            
            if mission_data:
                missions.append({
                    "id": mission_id.decode(),
                    "type": mission_data.get(b"type", b"unknown").decode(),
                    "description": mission_data.get(b"description", b"").decode(),
                    "status": mission_data.get(b"status", b"pending").decode(),
                    "progress": int(mission_data.get(b"progress", b"0").decode() or 0),
                    "assigned_agents": mission_data.get(b"assigned_agents", b"").decode().split(","),
                    "created_at": mission_data.get(b"created_at", b"").decode()
                })
        
        return missions
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Fetch overall system metrics."""
        if not self.redis_client:
            self.redis_client = await get_redis_client()
        
        metrics_key = "metrics:system"
        metrics_data = await self.redis_client.hgetall(metrics_key)
        
        return {
            "total_agents": 8,
            "active_agents": int(metrics_data.get(b"active_agents", b"0").decode() or 0),
            "total_missions": int(metrics_data.get(b"total_missions", b"0").decode() or 0),
            "completed_missions": int(metrics_data.get(b"completed_missions", b"0").decode() or 0),
            "uptime": metrics_data.get(b"uptime", b"0").decode(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def broadcast_dashboard_data(self):
        """Aggregate and broadcast dashboard data to all connections."""
        agents = await self.get_agent_status()
        missions = await self.get_active_missions()
        system = await self.get_system_metrics()
        
        data = {
            "type": "dashboard_update",
            "agents": agents,
            "missions": missions,
            "system": system,
            "timestamp": time.time()
        }
        
        # Broadcast to all connected clients
        disconnected = []
        for connection in active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                print(f"❌ Failed to send to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            if connection in active_connections:
                active_connections.remove(connection)


manager = DashboardManager()


@router.websocket("/ws")
async def dashboard_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time dashboard updates.
    
    Sends updates every 1 second with:
    - Agent status (idle/active/offline)
    - Active missions and progress
    - System-wide metrics
    
    Example client usage:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/dashboard/ws');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Agents:', data.agents);
        console.log('Missions:', data.missions);
    };
    ```
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Send dashboard data every 1 second
            await manager.broadcast_dashboard_data()
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        manager.disconnect(websocket)


@router.get("/status")
async def get_dashboard_status():
    """
    HTTP endpoint to get current dashboard data (non-streaming).
    
    Useful for initial page load or debugging.
    """
    agents = await manager.get_agent_status()
    missions = await manager.get_active_missions()
    system = await manager.get_system_metrics()
    
    return {
        "agents": agents,
        "missions": missions,
        "system": system,
        "connections": len(active_connections)
    }
