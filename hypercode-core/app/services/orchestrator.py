import structlog
import redis.asyncio as redis
from app.core.config import get_settings
from app.schemas.mission import MissionRequest, MissionStatus, MissionState
from app.services.event_bus import event_bus
from app.services.agent_registry import agent_registry
from app.schemas.agent import AgentMetadata
from app.core.db import db
from app.schemas.message import MessageEnvelope
from prometheus_client import Counter, Histogram
from datetime import datetime, timezone
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import uuid
import json
import asyncio
import os

logger = structlog.get_logger()
settings = get_settings()

MISSION_TRANSITIONS = Counter(
    "mission_transitions_total",
    "Mission state transitions",
    ("from_state", "to_state"),
)
MISSION_STATE_DURATION = Histogram(
    "mission_state_duration_seconds",
    "Mission state duration",
    ("state",),
    buckets=(0.01, 0.1, 0.5, 1.0, 2.0, 5.0)
)
AUDIT_RETRIEVE_LATENCY = Histogram(
    "audit_retrieve_latency_seconds",
    "Latency of audit retrieval",
    ("status",),
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1)
)

class Orchestrator:
    def __init__(self):
        self.redis = redis.from_url(
            settings.HYPERCODE_REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        self._redis_initialized = False

    async def _ensure_redis(self):
        if self._redis_initialized:
            return
        try:
            await self.redis.ping()
            self._redis_initialized = True
        except Exception as e:
            logger.warning(f"Redis not available: {e}, falling back to fakeredis for development/testing")
            try:
                from fakeredis.aioredis import FakeRedis
                self.redis = FakeRedis(decode_responses=True)
                self._redis_initialized = True
            except Exception:
                pass

    async def _key(self, mission_id: str) -> str:
        return f"mission:{mission_id}"

    async def submit(self, req: MissionRequest) -> MissionStatus:
        await self._ensure_redis()
        mid = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "id": mid,
            "title": req.title,
            "state": MissionState.QUEUED.value,
            "priority": req.priority,
            "agent_id": "",
            "payload": json.dumps(req.payload or {}),
            "created_at": now,
            "updated_at": now,
        }
        await self.redis.hset(await self._key(mid), mapping=data)
        
        # Persistence & Audit
        try:
            await db.mission.create({
                "id": mid,
                "title": req.title,
                "status": MissionState.QUEUED.value,
                "userId": "system",
                "payload": req.payload or {},
                "createdAt": datetime.fromisoformat(now),
                "updatedAt": datetime.fromisoformat(now),
            })
            await db.auditlog.create({
                "missionId": mid,
                "transition": "create",
                "previousState": "none",
                "newState": MissionState.QUEUED.value,
                "actor": "system",
                "reason": "Submission",
            })
        except Exception as e:
            logger.error(f"Persistence failed for mission {mid}: {e}")

        # Event Stream
        try:
            await event_bus.publish_stream(
                "mission.events",
                MessageEnvelope(
                    sender_id="orchestrator",
                    message_type="mission.created",
                    payload={"mission_id": mid, "title": req.title}
                )
            )
        except Exception as e:
            logger.error(f"Event publish failed for mission {mid}: {e}")

        MISSION_TRANSITIONS.labels("none", MissionState.QUEUED.value).inc()
        return MissionStatus.model_validate({
            "id": mid,
            "title": req.title,
            "state": MissionState.QUEUED,
            "priority": req.priority,
            "agent_id": None,
            "created_at": datetime.fromisoformat(now),
            "updated_at": datetime.fromisoformat(now),
        })

    async def assign_next(self) -> MissionStatus | None:
        await self._ensure_redis()
        keys = await self.redis.keys("mission:*")
        for k in keys:
            v = await self.redis.hgetall(k)
            if v.get("state", "") != MissionState.QUEUED.value:
                continue
            req_caps: list[str] = []
            try:
                payload_raw = v.get("payload")
                if payload_raw:
                    import json
                    payload = json.loads(payload_raw)
                    req_caps = payload.get("requirements", {}).get("capabilities", [])
            except Exception:
                req_caps = []

            agents = await agent_registry.list_agents()
            if not agents:
                try:
                    raw_agents = await db.agent.find_many()
                    agents = [AgentMetadata.model_validate(a) for a in raw_agents]
                except Exception:
                    return None

            async def score_agent(a):
                # Skip circuit-broken agents
                try:
                    cb = await self.redis.get(f"cb:open:{a.id}")
                    if cb:
                        return -1.0
                except Exception:
                    pass
                # Capability match
                caps = set(a.capabilities or [])
                if any(rc for rc in req_caps) and not set(req_caps).issubset(caps):
                    return -1.0
                # Health based on status and heartbeat recency
                status_weight = {
                    "active": 1.0,
                    "busy": 0.7,
                    "error": 0.3,
                    "offline": 0.0,
                }.get(a.status.value if hasattr(a.status, "value") else str(a.status), 0.5)
                try:
                    last = getattr(a, "lastHeartbeat", None) or getattr(a, "createdAt", None)
                    last_dt = last or datetime.now(timezone.utc)
                    if last_dt.tzinfo is None:
                        last_dt = last_dt.replace(tzinfo=timezone.utc)
                    now_dt = datetime.now(timezone.utc)
                    age = max((now_dt - last_dt).total_seconds(), 0.0)
                    recency = max(0.0, 1.0 - min(age / 60.0, 1.0))
                except Exception:
                    recency = 0.5
                load = await agent_registry.get_load(a.id)
                load_factor = max(0.0, 1.0 - min(load, 1.0))
                return status_weight * 0.5 + recency * 0.3 + load_factor * 0.2

            scored = []
            for a in agents:
                s = await score_agent(a)
                if s >= 0:
                    scored.append((s, a))
            if not scored:
                try:
                    fallback_agents = await agent_registry.list_agents()
                except Exception:
                    fallback_agents = []
                if not fallback_agents:
                    return None
                agent_id = fallback_agents[0].id
                mid = v["id"]
                await self.redis.hset(k, mapping={
                    "state": MissionState.ASSIGNED.value,
                    "agent_id": agent_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                try:
                    await db.mission.update(
                        where={"id": mid},
                        data={"status": MissionState.ASSIGNED.value, "agentId": agent_id}
                    )
                    await db.auditlog.create({
                        "missionId": mid,
                        "transition": "assign",
                        "previousState": MissionState.QUEUED.value,
                        "newState": MissionState.ASSIGNED.value,
                        "actor": "orchestrator",
                        "reason": f"Assigned to {agent_id}",
                    })
                except Exception:
                    pass
                try:
                    await event_bus.publish_stream(
                        "mission.events",
                        MessageEnvelope(
                            sender_id="orchestrator",
                            recipient_id=agent_id,
                            message_type="mission.assigned",
                            payload={"mission_id": mid, "agent_id": agent_id}
                        )
                    )
                except Exception:
                    pass
                MISSION_TRANSITIONS.labels(MissionState.QUEUED.value, MissionState.ASSIGNED.value).inc()
                mv = await self.redis.hgetall(k)
                return MissionStatus.model_validate({
                    "id": mv["id"],
                    "title": mv["title"],
                    "state": MissionState.ASSIGNED,
                    "priority": int(mv["priority"]),
                    "agent_id": mv["agent_id"] or None,
                    "created_at": datetime.fromisoformat(mv["created_at"]),
                    "updated_at": datetime.fromisoformat(mv["updated_at"]),
                })
            scored.sort(key=lambda t: t[0], reverse=True)
            agent_id = scored[0][1].id
            mid = v["id"]

            await self.redis.hset(k, mapping={
                "state": MissionState.ASSIGNED.value,
                "agent_id": agent_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

            # Persistence & Audit
            try:
                await db.mission.update(
                    where={"id": mid},
                    data={"status": MissionState.ASSIGNED.value, "agentId": agent_id}
                )
                await db.auditlog.create({
                    "missionId": mid,
                    "transition": "assign",
                    "previousState": MissionState.QUEUED.value,
                    "newState": MissionState.ASSIGNED.value,
                    "actor": "orchestrator",
                    "reason": f"Assigned to {agent_id}",
                })
            except Exception as e:
                logger.error(f"Persistence failed for assignment {mid}: {e}")

            # Event Stream
            try:
                await event_bus.publish_stream(
                    "mission.events",
                    MessageEnvelope(
                        sender_id="orchestrator",
                        recipient_id=agent_id,
                        message_type="mission.assigned",
                        payload={"mission_id": mid, "agent_id": agent_id}
                    )
                )
            except Exception as e:
                logger.error(f"Event publish failed for assignment {mid}: {e}")

            MISSION_TRANSITIONS.labels(MissionState.QUEUED.value, MissionState.ASSIGNED.value).inc()
            mv = await self.redis.hgetall(k)
            return MissionStatus.model_validate({
                "id": mv["id"],
                "title": mv["title"],
                "state": MissionState.ASSIGNED,
                "priority": int(mv["priority"]),
                "agent_id": mv["agent_id"] or None,
                "created_at": datetime.fromisoformat(mv["created_at"]),
                "updated_at": datetime.fromisoformat(mv["updated_at"]),
            })
        return None

    async def _transition(self, mission_id: str, to_state: MissionState) -> MissionStatus | None:
        await self._ensure_redis()
        k = await self._key(mission_id)
        v = await self.redis.hgetall(k)
        if not v:
            return None
        from_state = v.get("state", "")
        await self.redis.hset(k, mapping={
            "state": to_state.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        try:
            if to_state == MissionState.FAILED:
                agent_id = v.get("agent_id", "") if v.get("agent_id") else ""
                if agent_id:
                    fkey = f"agent:{agent_id}:failures"
                    try:
                        cnt = await self.redis.incr(fkey)
                        await self.redis.expire(fkey, 300)
                        if cnt >= 3:
                            await self.redis.set(f"cb:open:{agent_id}", "1", ex=60)
                    except Exception:
                        pass
        except Exception:
            pass

        # Persistence & Audit
        try:
            await db.mission.update(
                where={"id": mission_id},
                data={"status": to_state.value}
            )
            await db.auditlog.create({
                "missionId": mission_id,
                "transition": "update",
                "previousState": from_state,
                "newState": to_state.value,
                "actor": "orchestrator",
                "reason": f"Transition to {to_state.value}",
            })
        except Exception as e:
            logger.error(f"Persistence failed for transition {mission_id}: {e}")

        # Event Stream
        try:
            await event_bus.publish_stream(
                "mission.events",
                MessageEnvelope(
                    sender_id="orchestrator",
                    message_type=f"mission.{to_state.value}",
                    payload={"mission_id": mission_id, "previous_state": from_state, "new_state": to_state.value}
                )
            )
        except Exception as e:
            logger.error(f"Event publish failed for transition {mission_id}: {e}")

        MISSION_TRANSITIONS.labels(from_state or "none", to_state.value).inc()
        mv = await self.redis.hgetall(k)
        return MissionStatus.model_validate({
            "id": mv["id"],
            "title": mv["title"],
            "state": to_state,
            "priority": int(mv["priority"]),
            "agent_id": mv["agent_id"] or None,
            "created_at": datetime.fromisoformat(mv["created_at"]),
            "updated_at": datetime.fromisoformat(mv["updated_at"]),
        })

    async def start(self, mission_id: str) -> MissionStatus | None:
        return await self._transition(mission_id, MissionState.EXECUTING)

    async def verify(self, mission_id: str) -> MissionStatus | None:
        return await self._transition(mission_id, MissionState.VERIFYING)

    async def complete(self, mission_id: str) -> MissionStatus | None:
        return await self._transition(mission_id, MissionState.COMPLETED)

    async def fail(self, mission_id: str) -> MissionStatus | None:
        return await self._transition(mission_id, MissionState.FAILED)

    async def get(self, mission_id: str) -> MissionStatus | None:
        await self._ensure_redis()
        k = await self._key(mission_id)
        v = await self.redis.hgetall(k)
        if not v:
            return None
        return MissionStatus.model_validate({
            "id": v["id"],
            "title": v["title"],
            "state": MissionState(v["state"]),
            "priority": int(v["priority"]),
            "agent_id": v["agent_id"] or None,
            "created_at": datetime.fromisoformat(v["created_at"]),
            "updated_at": datetime.fromisoformat(v["updated_at"]),
        })

    async def list(self, limit: int = 10) -> List[MissionStatus]:
        await self._ensure_redis()
        keys = await self.redis.keys("mission:*")
        items = []
        for k in keys:
            v = await self.redis.hgetall(k)
            if not v:
                continue
            try:
                items.append({
                    "id": v["id"],
                    "title": v["title"],
                    "state": MissionState(v["state"]),
                    "priority": int(v["priority"]),
                    "agent_id": v.get("agent_id") or None,
                    "created_at": datetime.fromisoformat(v["created_at"]),
                    "updated_at": datetime.fromisoformat(v["updated_at"]),
                })
            except Exception:
                continue
        items.sort(key=lambda x: x["created_at"], reverse=True)
        items = items[:limit]
        return [MissionStatus.model_validate(i) for i in items]

    async def audit(self, mission_id: str) -> List[Dict[str, Any]]:
        tries = 0
        import time
        t0 = time.perf_counter()
        while tries < 3:
            try:
                rows = await db.auditlog.find_many(where={"missionId": mission_id}, order={"timestamp": "asc"})
                AUDIT_RETRIEVE_LATENCY.labels("ok").observe(time.perf_counter() - t0)
                return [
                    {
                        "id": getattr(r, "id", None),
                        "missionId": getattr(r, "missionId", None),
                        "transition": getattr(r, "transition", None),
                        "previousState": getattr(r, "previousState", None),
                        "newState": getattr(r, "newState", None),
                        "actor": getattr(r, "actor", None),
                        "reason": getattr(r, "reason", None),
                        "timestamp": getattr(r, "timestamp", None),
                    }
                for r in rows]
            except Exception:
                tries += 1
                await asyncio.sleep(min(0.05 * (2 ** tries), 0.5))
        try:
            AUDIT_RETRIEVE_LATENCY.labels("error").observe(time.perf_counter() - t0)
        except Exception:
            pass
        return []

    async def approve(self, mission_id: str) -> MissionStatus | None:
        await self._ensure_redis()
        k = await self._key(mission_id)
        v = await self.redis.hgetall(k)
        if not v:
            return None
        try:
            await self.redis.hset(k, mapping={"approved": "1", "updated_at": datetime.now(timezone.utc).isoformat()})
        except Exception:
            pass
        try:
            await db.auditlog.create({
                "missionId": mission_id,
                "transition": "approve",
                "previousState": v.get("state", ""),
                "newState": v.get("state", ""),
                "actor": "manager",
                "reason": "Approval",
            })
        except Exception:
            pass
        mv = await self.redis.hgetall(k)
        return MissionStatus.model_validate({
            "id": mv["id"],
            "title": mv["title"],
            "state": MissionState(mv["state"]),
            "priority": int(mv["priority"]),
            "agent_id": mv["agent_id"] or None,
            "created_at": datetime.fromisoformat(mv["created_at"]),
            "updated_at": datetime.fromisoformat(mv["updated_at"]),
        })

    async def submit_report(self, mission_id: str, agent_id: str, report: Dict[str, Any]) -> Dict[str, Any]:
        class AuditEntry(BaseModel):
            missionId: str = Field(min_length=1)
            transition: str = Field(min_length=1)
            previousState: str = Field(min_length=1)
            newState: str = Field(min_length=1)
            actor: str = Field(min_length=1)
            reason: str | None = None
        try:
            root = os.getcwd()
            out_dir = os.path.join(root, "reports")
            os.makedirs(out_dir, exist_ok=True)
            ts = datetime.now(timezone.utc).isoformat().replace(":", "-")
            fname = f"health_check_{agent_id}_{ts}.json"
            fpath = os.path.join(out_dir, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            payload = AuditEntry(
                missionId=mission_id,
                transition="report",
                previousState="n/a",
                newState="n/a",
                actor=agent_id,
                reason="Health check report submitted",
            ).model_dump()
            tries = 0
            while tries < 3:
                try:
                    await db.auditlog.create(payload)
                    break
                except Exception as e:
                    # Check for foreign key violation (Mission not found)
                    # Prisma error handling varies, but usually involves PydanticValidationError or internal error
                    # If mission doesn't exist, we should probably fail early or return specific error
                    # For now, if we can't create audit because mission missing, return specific error
                    if "Foreign key constraint failed" in str(e) or "Record to connect not found" in str(e):
                        return {"ok": False, "error": "Mission not found"}
                    
                    tries += 1
                    await asyncio.sleep(min(0.05 * (2 ** tries), 0.5))
            return {"ok": True, "path": fpath}
        except Exception as e:
            logger.error(f"Report submit failed for mission {mission_id}: {e}")
            return {"ok": False, "error": str(e)}

orchestrator = Orchestrator()
