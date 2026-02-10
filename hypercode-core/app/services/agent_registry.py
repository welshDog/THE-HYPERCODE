import json
import logging
import asyncio
from typing import List, Optional
import time
import redis.asyncio as redis
from prometheus_client import Counter, Histogram, Summary, Gauge
from os import getenv
from app.core.config import get_settings
from app.schemas.agent import AgentMetadata, AgentStatus, AgentRegistrationRequest
from app.core.db import db
from datetime import datetime, timezone
import uuid

settings = get_settings()
logger = logging.getLogger(__name__)

# Prometheus metrics
_env = settings.ENVIRONMENT
_ver = getenv("SERVICE_VERSION", "2.0.0")
AGENT_REGISTERED = Counter(
    "agent_registered_total",
    "Agent registered",
    ["env", "version"],
)
AGENT_UPDATED = Counter(
    "agent_updated_total",
    "Agent updated",
    ["env", "version"],
)
AGENT_STREAM_CLIENTS = Gauge(
    "agent_stream_clients_total",
    "Agent stream clients connected",
    ["env", "version"],
)
REGISTER_LATENCY = Histogram(
    "agent_registry_register_latency_seconds",
    "Agent registry registration latency (seconds)",
    buckets=(0.1, 0.5, 1.0, 2.0),
)
ERROR_COUNT = Counter(
    "agent_registry_errors_total",
    "Agent registry errors",
    ["operation", "env", "version"],
)
HEARTBEAT_COUNT = Counter(
    "agent_heartbeat_total",
    "Agent heartbeat updates",
    ["env", "version"],
)
STREAM_LATENCY_MS = Histogram(
    "agent_stream_latency_ms",
    "Agent SSE stream latency (milliseconds)",
    buckets=(50, 100, 200, 500, 1000, 2000),
    labelnames=("method", "status", "env", "version"),
)

class AgentRegistry:
    def __init__(self):
        self.redis = redis.from_url(
            settings.HYPERCODE_REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        self.ttl = 60  # Agent expiration time in seconds
        self.pubsub_channel = "agents:watch"
        self._env = _env
        self._ver = _ver

    async def register_agent(self, request: AgentRegistrationRequest):
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
            else:
                existing_agent = await db.agent.find_first(where={"role": request.role})

            if existing_agent:
                # Prevent immutable role change
                req_role = (request.role or "").strip().lower()
                cur_role = (getattr(existing_agent, "role", "") or "").strip().lower()
                if req_role != cur_role:
                    from fastapi import HTTPException
                    raise HTTPException(status_code=422, detail={
                        "error": "immutable_field",
                        "message": "dedup_key and role are immutable after creation"
                    })
                same = (
                    existing_agent.name == request.name and
                    existing_agent.role == request.role and
                    existing_agent.version == request.version and
                    existing_agent.capabilities == request.capabilities and
                    existing_agent.topics == request.topics and
                    existing_agent.healthUrl == request.health_url
                )
                if same:
                    REGISTER_LATENCY.observe(time.monotonic() - start)
                    agent_data = AgentMetadata.model_validate(existing_agent)
                    return agent_data, True
                agent_id = existing_agent.id
                parts = (existing_agent.version or "0.1.0").split(".")
                try:
                    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                except Exception:
                    major, minor, patch = 0, 1, 0
                if request.dedup_key:
                    minor += 1
                    patch = 0
                else:
                    patch += 1
                new_version = f"{major}.{minor}.{patch}"

                updated_agent = await db.agent.update(
                    where={"id": agent_id},
                    data={
                        "name": request.name,
                        "version": new_version,
                        "capabilities": request.capabilities,
                        "topics": request.topics,
                        "healthUrl": request.health_url,
                        "status": AgentStatus.ACTIVE.value,
                        "lastHeartbeat": datetime.now(timezone.utc),
                        # Preserve role and dedupKey
                    },
                )
                agent_data = AgentMetadata.model_validate(updated_agent)
                AGENT_UPDATED.labels(_env, _ver).inc()
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
                        "lastHeartbeat": datetime.now(timezone.utc),
                        "dedupKey": request.dedup_key or str(uuid.uuid4()),
                    }
                )
                agent_data = AgentMetadata.model_validate(new_agent)
                AGENT_REGISTERED.labels(_env, _ver).inc()

            # 2. Update Redis Cache & Notify
            await self._update_cache(agent_data)
            await self._publish_event("registered", agent_data)

            logger.info(f"Registered agent: {agent_data.name} ({agent_data.id})")
            return agent_data, False
        except Exception as e:
            ERROR_COUNT.labels("register", _env, _ver).inc()
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
                    "lastHeartbeat": datetime.now(timezone.utc)
                }
            )
            if not agent:
                return False
                
            # Update Cache
            agent_data = AgentMetadata.model_validate(agent)
            await self._update_cache(agent_data)
            try:
                await self.redis.set(f"agent:load:{agent_id}", str(load), ex=self.ttl)
            except Exception:
                pass
            HEARTBEAT_COUNT.labels(self._env, self._ver).inc()
            return True
        except Exception as e:
            logger.error(f"Heartbeat failed for {agent_id}: {e}")
            ERROR_COUNT.labels("heartbeat", self._env, self._ver).inc()
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
        start = time.monotonic()
        try:
            await db.agent.update(
                where={"id": agent_id},
                data={"status": AgentStatus.OFFLINE.value}
            )
            
            await self.redis.delete(f"agent:{agent_id}")
            await self._publish_event("deregistered", {"id": agent_id})
            logger.info(f"Deregistered agent: {agent_id}")
        except Exception as e:
            logger.error(f"Deregister agent failed: {e}")
            ERROR_COUNT.labels("deregister", self._env, self._ver).inc()
        finally:
            # Reuse register latency histogram for simplicity; separate if needed
            REGISTER_LATENCY.observe(time.monotonic() - start)

    async def _update_cache(self, agent: AgentMetadata):
        key = f"agent:{agent.id}"
        if self.ttl and self.ttl > 0:
            await self.redis.set(key, agent.model_dump_json(), ex=self.ttl)
        else:
            await self.redis.set(key, agent.model_dump_json())

    async def get_load(self, agent_id: str) -> float:
        try:
            val = await self.redis.get(f"agent:load:{agent_id}")
            if not val:
                return 0.0
            if isinstance(val, bytes):
                val = val.decode()
            return float(val)
        except Exception:
            return 0.0

    async def _publish_event(self, event_type: str, data: any):
        payload = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data.model_dump(mode="json") if hasattr(data, "model_dump") else data
        }
        await self.redis.publish(self.pubsub_channel, json.dumps(payload))

    async def check_timeouts(self):
        now = datetime.now(timezone.utc)
        agents = await db.agent.find_many()
        for a in agents:
            try:
                last = getattr(a, "lastHeartbeat", now)
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                status = getattr(a, "status", AgentStatus.OFFLINE.value)
                if status != AgentStatus.OFFLINE.value:
                    if (now - last).total_seconds() > self.ttl:
                        await db.agent.update(
                            where={"id": a.id},
                            data={"status": AgentStatus.OFFLINE.value}
                        )
                        await self.redis.delete(f"agent:{a.id}")
                        await self._publish_event("timeout", {"id": a.id})
            except Exception:
                ERROR_COUNT.labels("timeout_check", self._env, self._ver).inc()

agent_registry = AgentRegistry()
