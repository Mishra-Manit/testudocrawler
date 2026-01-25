"""
Simple Logfire configuration.
Initializes Logfire with automatic pydantic-ai instrumentation.
"""

import logfire
import structlog

from app.config import get_settings

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
