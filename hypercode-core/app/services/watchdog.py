import asyncio
import logging
from datetime import datetime, timezone, timedelta
from app.core.db import db
from enum import Enum

logger = logging.getLogger(__name__)

class AgentState(str, Enum):
    PROVISIONING = "PROVISIONING"
    WARMING = "WARMING"
    READY = "READY"
    BUSY = "BUSY"
    HIBERNATING = "HIBERNATING"
    DRAINING = "DRAINING"
    UNHEALTHY = "UNHEALTHY"

class WatchdogService:
    def __init__(self):
        self.interval = 10  # Run every 10 seconds
        self.heartbeat_threshold = 30  # 30 seconds
        self.restart_threshold = 60  # 60 seconds (Unhealthy > 60s -> Restart)

    async def start(self):
        """
        Starts the background monitoring loop.
        """
        logger.info("Starting Watchdog Service...")
        while True:
            try:
                await self.monitor_agents()
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
            await asyncio.sleep(self.interval)

    async def monitor_agents(self):
        """
        Checks all agents in active states for heartbeat freshness.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Fetch all agents that are supposedly alive
        # Prisma doesn't support 'OR' well in find_many depending on version, 
        # but we can filter for status != 'offline' if we use that, 
        # or just fetch all and filter in python for now for robustness.
        # Ideally: where={"state": {"in": ["READY", "BUSY", "PROVISIONING", "WARMING"]}}
        
        # Let's fetch all and filter to be safe and compatible with our simplified Prisma usage
        agents = await db.agent.find_many()
        
        for agent in agents:
            if not agent.lastHeartbeat:
                continue
                
            # Skip if offline or hibernating
            if agent.state in [AgentState.HIBERNATING.value, AgentState.DRAINING.value, "offline"]:
                continue

            last_beat = agent.lastHeartbeat
            if last_beat.tzinfo is None:
                last_beat = last_beat.replace(tzinfo=timezone.utc)
                
            delta = (now - last_beat).total_seconds()
            
            # Logic 1: Mark UNHEALTHY if heartbeat missing > 30s
            if delta > self.heartbeat_threshold and agent.state != AgentState.UNHEALTHY.value:
                logger.warning(f"Agent {agent.name} ({agent.id}) heartbeat missing for {delta}s. Marking UNHEALTHY.")
                await self._transition_state(agent, AgentState.UNHEALTHY, "Watchdog: Heartbeat timeout")

            # Logic 2: Trigger Restart if UNHEALTHY > 60s
            # Note: In a real system, we'd check how long it's been UNHEALTHY. 
            # Here we check if delta > restart_threshold (meaning it hasn't recovered in 60s total)
            if delta > self.restart_threshold:
                logger.error(f"Agent {agent.name} ({agent.id}) unresponsive for {delta}s. Triggering RECOVERY.")
                await self._trigger_recovery(agent)

    async def _transition_state(self, agent, new_state: AgentState, reason: str):
        """
        Updates agent state and logs the transition.
        """
        try:
            # Update Agent
            await db.agent.update(
                where={"id": agent.id},
                data={"state": new_state.value}
            )
            
            # Create Audit Log
            await db.auditlog.create(data={
                "missionId": "system-watchdog",
                "transition": "health_check",
                "previousState": agent.state,
                "newState": new_state.value,
                "actor": "watchdog",
                # "reason": reason # Schema doesn't have reason yet, added in description but not schema.
                # We'll rely on 'transition' or just implicit context for now to match schema.
            })
        except Exception as e:
            logger.error(f"Failed to transition agent {agent.id}: {e}")

    async def _trigger_recovery(self, agent):
        """
        Simulates a restart/recovery action.
        In V2, this would call the Docker Spawner or Orchestrator.
        """
        # 1. Increment restart count
        new_count = (agent.restartCount or 0) + 1
        
        # 2. Reset state to PROVISIONING (Simulate restart)
        await db.agent.update(
            where={"id": agent.id},
            data={
                "state": AgentState.PROVISIONING.value,
                "restartCount": new_count,
                "lastHeartbeat": datetime.now(timezone.utc) # Reset heartbeat to give it time to boot
            }
        )
        
        logger.info(f"RECOVERY INITIATED for {agent.name}. Restart Count: {new_count}")
        
        # Log recovery
        await db.auditlog.create(data={
            "missionId": "system-watchdog",
            "transition": "auto_recovery",
            "previousState": agent.state,
            "newState": AgentState.PROVISIONING.value,
            "actor": "watchdog"
        })

watchdog_service = WatchdogService()
