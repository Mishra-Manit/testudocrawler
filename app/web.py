"""
FastAPI web service wrapper for Testudo Watchdog.
Enables deployment on Render's free tier by providing HTTP endpoints.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Optional

import structlog
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.observability.logfire_config import initialize_logfire
from app.runner import TestudoWatchdog, setup_signal_handlers

logger = structlog.get_logger(__name__)

# Background task reference
watchdog_task: Optional[asyncio.Task] = None
watchdog_instance: Optional[TestudoWatchdog] = None
start_time: datetime = datetime.now(timezone.utc)


async def run_watchdog_background():
    """Run the watchdog application as a background task."""
    global watchdog_instance

    logger.info("Starting Testudo Watchdog background service...")

    try:
        watchdog_instance = TestudoWatchdog()
        setup_signal_handlers(watchdog_instance)
        await watchdog_instance.start()
    except Exception as e:
        logger.error("Watchdog background task failed", error=str(e), exc_info=True)
        raise


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Manage application lifespan: startup and shutdown.
    Starts the watchdog as a background task during startup.
    """
    global watchdog_task, start_time

    # Startup
    logger.info("FastAPI application starting...")
    initialize_logfire()

    start_time = datetime.now(timezone.utc)
    watchdog_task = asyncio.create_task(run_watchdog_background())
    logger.info("Watchdog background task started")

    yield

    # Shutdown
    logger.info("FastAPI application shutting down...")

    if watchdog_instance:
        watchdog_instance.running = False

    if watchdog_task and not watchdog_task.done():
        logger.info("Cancelling watchdog task...")
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            logger.info("Watchdog task cancelled successfully")

    if watchdog_instance:
        await watchdog_instance.cleanup()

    logger.info("Shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Testudo Watchdog Service",
    description="Course availability monitoring service with web endpoint for Render deployment",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> JSONResponse:
    """
    Root endpoint - confirms service is alive.
    Render will ping this endpoint to keep the service active.
    """
    uptime = (datetime.now(timezone.utc) - start_time).total_seconds()

    return JSONResponse(
        content={
            "status": "alive",
            "service": "Testudo Watchdog",
            "uptime_seconds": round(uptime, 2),
            "message": "Course monitoring service is running",
        }
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """
    Health check endpoint for monitoring and load balancers.
    Returns detailed service status.
    """
    uptime = (datetime.now(timezone.utc) - start_time).total_seconds()

    # Check if background task is running
    task_status = "unknown"
    if watchdog_task is None:
        task_status = "not_started"
    elif watchdog_task.done():
        if watchdog_task.exception():
            task_status = "failed"
        else:
            task_status = "completed"
    else:
        task_status = "running"

    # Determine overall health
    is_healthy = task_status in ["running", "not_started"]

    health_data = {
        "status": "healthy" if is_healthy else "unhealthy",
        "uptime_seconds": round(uptime, 2),
        "background_task_status": task_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Include course monitoring stats if available
    if watchdog_instance and watchdog_instance.last_check_times:
        health_data["monitored_courses"] = len(watchdog_instance.last_check_times)
        health_data["last_checks"] = {
            course_id: check_time.isoformat()
            for course_id, check_time in watchdog_instance.last_check_times.items()
        }

    response_status = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=health_data, status_code=response_status)


@app.get("/ping", status_code=status.HTTP_200_OK)
async def ping() -> Dict[str, str]:
    """
    Simple ping endpoint for uptime monitoring services.
    Returns minimal response for efficiency.
    """
    return {"ping": "pong"}


if __name__ == "__main__":
    import uvicorn

    # Get port from environment variable (Render sets this automatically)
    port = int(os.getenv("PORT", "10000"))

    logger.info(f"Starting web service on port {port}...")

    # Run the FastAPI application
    # host="0.0.0.0" is required for Render to route traffic properly
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True,
    )
