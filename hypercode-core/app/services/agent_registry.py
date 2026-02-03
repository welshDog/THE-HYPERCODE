import json
import logging
import asyncio
from typing import List, Optional
import time
import redis.asyncio as redis
from prometheus_client import Counter, Histogram
from app.core.config import get_settings
from app.schemas.agent import AgentMetadata, AgentStatus, AgentRegistrationRequest
from app.core.db import db
from datetime import datetime
import uuid

settings = get_settings()
logger = logging.getLogger(__name__)

# Prometheus metrics
REGISTER_COUNT = Counter(
    "agent_registry_register_total",
    "Agent registry registration attempts",
    ["result"],
)
REGISTER_LATENCY = Histogram(
    "agent_registry_register_latency_seconds",
    "Agent registry registration latency (seconds)",
    buckets=(0.1, 0.5, 1.0, 2.0),
)
HEARTBEAT_COUNT = Counter(
    "agent_registry_heartbeat_total",
    "Agent heartbeat updates",
)
ERROR_COUNT = Counter(
    "agent_registry_errors_total",
    "Agent registry errors",
    ["operation"],
)

class AgentRegistry:
    def __init__(self):
        self.redis = redis.from_url(settings.HYPERCODE_REDIS_URL)
        self.ttl = 60  # Agent expiration time in seconds
        self.pubsub_channel = "agents:watch"

    async def register_agent(self, request: AgentRegistrationRequest) -> AgentMetadata:
        """
        Register a new agent or update existing one using idempotency.
        Priority: dedup_key (unique), otherwise fallback to role-based idempotency.
        """
        start = time.monotonic()
        try:
            # 1. Check if agent exists using dedup_key, else by role
            existing_agent = None
            if request.dedup_key:
                existing_agent = await db.agent.find_first(where={"dedupKey": request.dedup_key})
            if not existing_agent:
                existing_agent = await db.agent.find_first(where={"role": request.role})

            if existing_agent:
                # Update existing (role and id immutable)
                agent_id = existing_agent.id
                if existing_agent.version != request.version:
                    logger.info(
                        f"Updating agent {request.role} from {existing_agent.version} to {request.version}"
                    )

                updated_agent = await db.agent.update(
                    where={"id": agent_id},
                    data={
                        "name": request.name,
                        "version": request.version,
                        "capabilities": request.capabilities,
                        "topics": request.topics,
                        "healthUrl": request.health_url,
                        "status": AgentStatus.ACTIVE.value,
                        "lastHeartbeat": datetime.utcnow(),
                        # Preserve role and dedupKey
                    },
                )
                agent_data = AgentMetadata.model_validate(updated_agent)
                REGISTER_COUNT.labels(result="update").inc()
            else:
                # Create new
                agent_id = str(uuid.uuid4())
                new_agent = await db.agent.create(
                    data={
                        "id": agent_id,
                        "name": request.name,
                        "role": request.role,
                        "version": request.version,
                        "capabilities": request.capabilities,
                        "topics": request.topics,
                        "healthUrl": request.health_url,
                        "status": AgentStatus.ACTIVE.value,
                        "lastHeartbeat": datetime.utcnow(),
                        "dedupKey": request.dedup_key or str(uuid.uuid4()),
                    }
                )
                agent_data = AgentMetadata.model_validate(new_agent)
                REGISTER_COUNT.labels(result="create").inc()

            # 2. Update Redis Cache & Notify
            await self._update_cache(agent_data)
            await self._publish_event("registered", agent_data)

            logger.info(f"Registered agent: {agent_data.name} ({agent_data.id})")
            return agent_data
        except Exception as e:
            ERROR_COUNT.labels(operation="register").inc()
            logger.error(f"Register agent failed: {e}")
            raise
        finally:
            REGISTER_LATENCY.observe(time.monotonic() - start)

    async def update_heartbeat(self, agent_id: str, status: AgentStatus, load: float = 0.0) -> bool:
        """Update agent heartbeat in DB and Cache."""
        start = time.monotonic()
        try:
            # Update DB
            agent = await db.agent.update(
                where={"id": agent_id},
                data={
                    "status": status.value,
                    "lastHeartbeat": datetime.utcnow()
                }
            )
            if not agent:
                return False
                
            # Update Cache
            agent_data = AgentMetadata.model_validate(agent)
            await self._update_cache(agent_data)
            HEARTBEAT_COUNT.inc()
            return True
        except Exception as e:
            logger.error(f"Heartbeat failed for {agent_id}: {e}")
            ERROR_COUNT.labels(operation="heartbeat").inc()
            return False
        finally:
            # Reuse register latency histogram for simplicity; separate if needed
            REGISTER_LATENCY.observe(time.monotonic() - start)

    async def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        """Get agent metadata from Cache or DB."""
        # Try Cache first
        cache_key = f"agent:{agent_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return AgentMetadata.model_validate_json(cached)
        
        # Fallback to DB
        agent = await db.agent.find_unique(where={"id": agent_id})
        if agent:
            agent_data = AgentMetadata.model_validate(agent)
            await self._update_cache(agent_data)
            return agent_data
        return None

    async def list_agents(self) -> List[AgentMetadata]:
        """List all active agents from DB."""
        agents = await db.agent.find_many(
            where={"status": {"not": AgentStatus.OFFLINE.value}}
        )
        return [AgentMetadata.model_validate(a) for a in agents]

    async def deregister_agent(self, agent_id: str):
        """Mark agent as offline and remove from cache."""
        await db.agent.update(
            where={"id": agent_id},
            data={"status": AgentStatus.OFFLINE.value}
        )
        
        await self.redis.delete(f"agent:{agent_id}")
        await self._publish_event("deregistered", {"id": agent_id})
        logger.info(f"Deregistered agent: {agent_id}")

    async def _update_cache(self, agent: AgentMetadata):
        key = f"agent:{agent.id}"
        await self.redis.set(key, agent.model_dump_json(), ex=self.ttl)

    async def _publish_event(self, event_type: str, data: any):
        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data.model_dump() if hasattr(data, "model_dump") else data
        }
        await self.redis.publish(self.pubsub_channel, json.dumps(payload))

agent_registry = AgentRegistry()
