
import logging
import sys
import structlog
from app.core.config import get_settings

def configure_logging():
    settings = get_settings()
    
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # JSON renderer for production, Console renderer for development
    if settings.ENVIRONMENT == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.LOG_LEVEL.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging to intercept Uvicorn/FastAPI logs
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.LOG_LEVEL.upper(),
    )
