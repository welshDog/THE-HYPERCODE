
from fastapi import FastAPI
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    _instrumentator_available = True
except Exception:
    Instrumentator = None
    _instrumentator_available = False
from app.routers import agents, memory, execution, metrics, engine, voice, orchestrator
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.db import db
from contextlib import asynccontextmanager
import asyncio
import json
import time
import random
from datetime import datetime, timezone

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import os
import socket
from urllib.parse import urlparse

settings = get_settings()

# Initialize Logging
configure_logging()

def _host_resolves(host: str) -> bool:
    try:
        socket.gethostbyname(host)
        return True
    except Exception:
        return False

# Initialize OpenTelemetry with conditional OTLP exporter
resource = Resource(attributes={
    "service.name": "hypercode-core",
    "service.version": "2.0.0",
    "deployment.environment": settings.ENVIRONMENT
})

provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

otlp_disabled = os.getenv("OTLP_EXPORTER_DISABLED", "false").lower() in ("1", "true", "yes")
env_is_test = (getattr(settings, "ENVIRONMENT", "").lower() == "test")
otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://jaeger:4318/v1/traces")
parsed = urlparse(otlp_endpoint)
jaeger_resolves = _host_resolves(parsed.hostname or "jaeger")

if not otlp_disabled and not env_is_test and jaeger_resolves:
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

# Initialize Sentry (optional)
if settings.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    bg_tasks = []
    try:
        from app.services.agent_registry import agent_registry
        from app.services.event_bus import event_bus
        from app.schemas.message import MessageEnvelope
        from app.services.orchestrator import orchestrator
        MAX_RETRIES = 5
        async def _heartbeat_sweep():
            while True:
                try:
                    await agent_registry.check_timeouts()
                except Exception:
                    pass
                await asyncio.sleep(30)
        bg_tasks.append(asyncio.create_task(_heartbeat_sweep()))

        async def _mission_event_consumer():
            try:
                await event_bus.ensure_consumer_group("mission.events", "mission-workers")
            except Exception:
                pass
            while True:
                try:
                    entries = await event_bus.read_group("mission.events", "mission-workers", consumer="core", count=10, block_ms=1000)
                    for stream, rows in entries:
                        for entry_id, fields in rows:
                            try:
                                msg_type = fields.get(b"message_type") or fields.get("message_type")
                                if isinstance(msg_type, bytes):
                                    msg_type = msg_type.decode()
                                payload_raw = fields.get(b"payload") or fields.get("payload")
                                if isinstance(payload_raw, bytes):
                                    payload_raw = payload_raw.decode()
                                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
                                if msg_type == "mission.failed":
                                    mid = payload.get("mission_id")
                                    if mid:
                                        rk = f"mission:{mid}:retries"
                                        try:
                                            rc = await event_bus.redis.incr(rk)
                                            await event_bus.redis.expire(rk, 3600)
                                        except Exception:
                                            rc = 1
                                        ok, _ = await event_bus.schedule_retry(mid, rc, base=2.0, factor=2.0, jitter=0.5, max_delay=300.0, max_retries=MAX_RETRIES)
                                        if not ok:
                                            try:
                                                await event_bus.publish_stream(
                                                    "mission.dlq",
                                                    MessageEnvelope(
                                                        sender_id="core",
                                                        message_type="mission.retry.exhausted",
                                                        payload={"mission_id": mid, "retries": rc}
                                                    )
                                                )
                                            except Exception:
                                                pass
                                if msg_type == "mission.completed":
                                    mid = payload.get("mission_id")
                                    if mid:
                                        try:
                                            await event_bus.redis.delete(f"mission:{mid}:retries")
                                        except Exception:
                                            pass
                                await event_bus.ack("mission.events", "mission-workers", entry_id)
                            except Exception:
                                try:
                                    await event_bus.publish_stream(
                                        "mission.dlq",
                                        MessageEnvelope(
                                            sender_id="core",
                                            message_type="mission.consumer.error",
                                            payload={"entry_id": entry_id}
                                        )
                                    )
                                except Exception:
                                    pass
                                try:
                                    await event_bus.ack("mission.events", "mission-workers", entry_id)
                                except Exception:
                                    pass
                except Exception:
                    await asyncio.sleep(1.0)

        async def _retry_scheduler():
            while True:
                try:
                    now = time.time()
                    due = await event_bus.dequeue_due_retries(now)
                    for mid in due:
                        try:
                            if isinstance(mid, bytes):
                                mid = mid.decode()
                            key = f"mission:{mid}"
                            try:
                                await event_bus.redis.hset(key, mapping={
                                    "state": "queued",
                                    "agent_id": "",
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                })
                            except Exception:
                                pass
                            try:
                                await db.auditlog.create({
                                    "missionId": mid,
                                    "transition": "retry",
                                    "previousState": "failed",
                                    "newState": "queued",
                                    "actor": "system",
                                    "reason": "Retry scheduled",
                                })
                            except Exception:
                                pass
                            try:
                                await event_bus.publish_stream(
                                    "mission.events",
                                    MessageEnvelope(
                                        sender_id="orchestrator",
                                        message_type="mission.queued",
                                        payload={"mission_id": mid}
                                    )
                                )
                            except Exception:
                                pass
                            await event_bus.clear_retry(mid)
                        except Exception:
                            continue
                except Exception:
                    pass
                await asyncio.sleep(1.0)

        async def _dlq_consumer():
            try:
                await event_bus.ensure_consumer_group("mission.dlq", "mission-dlq")
            except Exception:
                pass
            while True:
                try:
                    entries = await event_bus.read_group("mission.dlq", "mission-dlq", consumer="core", count=10, block_ms=1000)
                    for stream, rows in entries:
                        for entry_id, fields in rows:
                            try:
                                msg_type = fields.get(b"message_type") or fields.get("message_type")
                                if isinstance(msg_type, bytes):
                                    msg_type = msg_type.decode()
                                payload_raw = fields.get(b"payload") or fields.get("payload")
                                if isinstance(payload_raw, bytes):
                                    payload_raw = payload_raw.decode()
                                payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
                                mid = payload.get("mission_id")
                                try:
                                    await db.auditlog.create({
                                        "missionId": mid or "unknown",
                                        "transition": "dlq",
                                        "previousState": payload.get("previous_state", "unknown"),
                                        "newState": payload.get("new_state", "unknown"),
                                        "actor": "system",
                                        "reason": msg_type,
                                    })
                                except Exception:
                                    pass
                                if payload.get("replay") and mid:
                                    try:
                                        await event_bus.publish_stream(
                                            "mission.events",
                                            MessageEnvelope(
                                                sender_id="dlq",
                                                message_type="mission.queued",
                                                payload={"mission_id": mid}
                                            )
                                        )
                                    except Exception:
                                        pass
                                await event_bus.ack("mission.dlq", "mission-dlq", entry_id)
                            except Exception:
                                await event_bus.ack("mission.dlq", "mission-dlq", entry_id)
                except Exception:
                    await asyncio.sleep(1.0)

        try:
            env_lower = (settings.ENVIRONMENT or "").lower()
        except Exception:
            env_lower = "development"
        if env_lower in ("staging", "production"):
            bg_tasks.append(asyncio.create_task(_mission_event_consumer()))
            bg_tasks.append(asyncio.create_task(_retry_scheduler()))
            bg_tasks.append(asyncio.create_task(_dlq_consumer()))
    except Exception:
        pass
    yield
    for t in bg_tasks:
        try:
            t.cancel()
        except Exception:
            pass
    await db.disconnect()

app = FastAPI(title="HyperCode Core Engine", lifespan=lifespan)

# Instrument FastAPI with OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

if _instrumentator_available:
    Instrumentator().instrument(app).expose(app)
else:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi import Response

    @app.get("/metrics")
    async def metrics_fallback():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])
app.include_router(execution.router, prefix="/execution", tags=["Execution"])
app.include_router(metrics.router, prefix="/metrics", tags=["Metrics"])
app.include_router(engine.router, prefix="/engine", tags=["Engine"])
app.include_router(voice.router, prefix="", tags=["Voice"])
app.include_router(orchestrator.router, prefix="/orchestrator", tags=["Orchestrator"])

@app.get("/health")
async def health_check():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("health_check_manual"):
        return {"status": "healthy"}
