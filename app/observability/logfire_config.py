"""
Simple Logfire configuration.
Initializes Logfire with automatic pydantic-ai instrumentation.
"""

import sys

import logfire
import structlog

from app.config import get_settings


def configure_structlog():
    """Configure structured logging with appropriate renderer based on environment."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not sys.stdout.isatty()
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger(__name__)

_initialized = False


def initialize_logfire():
    """
    Initialize Logfire once.

    Configures Logfire SDK and enables automatic pydantic-ai instrumentation
    which captures: agent runs, model calls, tokens, latency, tool usage, and errors.
    """
    global _initialized
    if _initialized:
        return

    settings = get_settings()
    if not settings.logfire_token:
        return

    logfire.configure(
        token=settings.logfire_token,
        service_name="testudo-crawler",
    )

    logfire.instrument_pydantic_ai()
    _initialized = True


def log_event(event: str, **kwargs) -> None:
    logfire.info(event, **kwargs)
    logger.info(event, **kwargs)

def log_error(event: str, **kwargs) -> None:
    logfire.error(event, **kwargs)
    logger.error(event, **kwargs)

def log_warning(event: str, **kwargs) -> None:
    logfire.warn(event, **kwargs)
    logger.warning(event, **kwargs)

def log_debug(event: str, **kwargs) -> None:
    logfire.debug(event, **kwargs)
    logger.debug(event, **kwargs)
