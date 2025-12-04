"""
Simple Logfire configuration.
Initializes Logfire with automatic pydantic-ai instrumentation.
"""

import logfire

from app.config import get_settings

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
        return  # Skip if no token configured

    # Configure Logfire
    logfire.configure(
        token=settings.logfire_token,
        service_name="testudo-watchdog",
    )

    # Auto-instrument pydantic-ai
    # This captures: agent runs, model calls, tokens, latency, tool usage
    logfire.instrument_pydantic_ai()

    _initialized = True
