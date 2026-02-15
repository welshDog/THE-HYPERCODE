
import logging
import sys
import structlog
from app.core.config import get_settings

def configure_logging():
    settings = get_settings()
    log_level = settings.LOG_LEVEL.upper()

    # Processors that should be applied to ALL logs (structlog & standard logging)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Configure structlog to wrap standard logging
    structlog.configure(
        processors=shared_processors + [
            # Prepare for standard logging's formatter
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Determine renderer based on environment
    if settings.ENVIRONMENT == "production":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    # Configure standard logging to use structlog's formatter
    formatter = structlog.stdlib.ProcessorFormatter(
        # These run on `logging` entries that did NOT come from structlog
        foreign_pre_chain=shared_processors,
        # These run on ALL entries (both structlog & standard) after pre_chain
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Intercept Uvicorn logs and propagate to root logger
    for _log in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        _logger = logging.getLogger(_log)
        _logger.handlers = []
        _logger.propagate = True
