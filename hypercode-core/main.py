
from fastapi import FastAPI
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    _instrumentator_available = True
except Exception:
    Instrumentator = None
    _instrumentator_available = False
from app.routers import agents, memory, execution, metrics
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.db import db
from contextlib import asynccontextmanager

# OpenTelemetry Imports
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

settings = get_settings()

# Initialize Logging
configure_logging()

# Initialize OpenTelemetry
resource = Resource(attributes={
    "service.name": "hypercode-core",
    "service.version": "2.0.0",
    "deployment.environment": settings.ENVIRONMENT
})

provider = TracerProvider(resource=resource)
# Use Jaeger OTLP HTTP port
otlp_exporter = OTLPSpanExporter(endpoint="http://jaeger:4318/v1/traces")
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

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
    yield
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

@app.get("/health")
async def health_check():
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("health_check_manual"):
        return {"status": "healthy"}
