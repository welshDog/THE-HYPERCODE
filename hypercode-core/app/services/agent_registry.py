
import json
import logging
from typing import List, Optional
import redis.asyncio as redis
from app.core.config import get_settings
from app.schemas.agent import AgentMetadata, AgentStatus
from datetime import datetime

settings = get_settings()
logger = logging.getLogger(__name__)

class AgentRegistry:
    def __init__(self):
        self.redis = redis.from_url(settings.HYPERCODE_REDIS_URL)
        self.ttl = 60  # Agent expiration time in seconds (heartbeat interval * 2)

    async def register_agent(self, agent: AgentMetadata) -> AgentMetadata:
        """Register a new agent or update existing one."""
        key = f"agent:{agent.id}"
        data = agent.model_dump_json()
        
        async with self.redis.pipeline() as pipe:
            await pipe.set(key, data)
            await pipe.expire(key, self.ttl)
            await pipe.sadd("agents:all", agent.id)
            await pipe.execute()
        
        logger.info(f"Registered agent: {agent.name} ({agent.id})")
        return agent

    async def update_heartbeat(self, agent_id: str, status: AgentStatus, load: float = 0.0):
        """Update agent heartbeat and extend TTL."""
        key = f"agent:{agent_id}"
        agent_data = await self.redis.get(key)
        
        if not agent_data:
            logger.warning(f"Heartbeat for unknown agent: {agent_id}")
            return False

        agent = AgentMetadata.model_validate_json(agent_data)
        agent.status = status
        agent.last_heartbeat = datetime.utcnow()
        # We could store load separately if needed

        async with self.redis.pipeline() as pipe:
            await pipe.set(key, agent.model_dump_json())
            await pipe.expire(key, self.ttl)
            await pipe.execute()
        
        return True

    async def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        """Get agent metadata by ID."""
        data = await self.redis.get(f"agent:{agent_id}")
        if data:
            return AgentMetadata.model_validate_json(data)
        return None

    async def list_agents(self) -> List[AgentMetadata]:
        """List all active agents."""
        agent_ids = await self.redis.smembers("agents:all")
        agents = []
        
        for agent_id in agent_ids:
            # decode bytes if necessary (redis-py returns bytes usually, but check decode_responses)
            if isinstance(agent_id, bytes):
                agent_id = agent_id.decode('utf-8')
                
            agent = await self.get_agent(agent_id)
            if agent:
                agents.append(agent)
            else:
                # Cleanup expired agent from set
                await self.redis.srem("agents:all", agent_id)
        
        return agents

    async def deregister_agent(self, agent_id: str):
        """Remove agent from registry."""
        await self.redis.delete(f"agent:{agent_id}")
        await self.redis.srem("agents:all", agent_id)
        logger.info(f"Deregistered agent: {agent_id}")

agent_registry = AgentRegistry()
