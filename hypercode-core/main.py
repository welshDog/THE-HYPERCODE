
from fastapi import FastAPI
import sentry_sdk
from prometheus_fastapi_instrumentator import Instrumentator
from app.routers import agents, memory, execution
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()

# Initialize Logging
configure_logging()

# Initialize Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

app = FastAPI(title="HyperCode Core Engine")

# Initialize Prometheus
Instrumentator().instrument(app).expose(app)

app.include_router(agents.router, prefix="/agents", tags=["Agents"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])
app.include_router(execution.router, prefix="/execution", tags=["Execution"])

@app.get("/health")
def health_check():
    return {"status": "healthy"}
