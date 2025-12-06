"""
FastAPI web service wrapper for Testudo Crawler.
Enables deployment on Render's free tier by providing HTTP endpoints.
Includes Telegram bot webhook for /start command.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, Optional

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.observability.logfire_config import initialize_logfire
from app.runner import TestudoCrawler, setup_signal_handlers

logger = structlog.get_logger(__name__)

# Background task reference
crawler_task: Optional[asyncio.Task] = None
crawler_instance: Optional[TestudoCrawler] = None
start_time: datetime = datetime.now(timezone.utc)


async def run_crawler_background():
    """Run the crawler application as a background task."""
    global crawler_instance

    logger.info("Starting Testudo Crawler background service...")

    try:
        crawler_instance = TestudoCrawler()
        setup_signal_handlers(crawler_instance)
        await crawler_instance.start()
    except Exception as e:
        logger.error("Crawler background task failed", error=str(e), exc_info=True)
        raise


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Manage application lifespan: startup and shutdown.
    Starts the crawler as a background task during startup.
    """
    global crawler_task, start_time

    # Startup
    logger.info("FastAPI application starting...")
    initialize_logfire()

    start_time = datetime.now(timezone.utc)

    # Start crawler background task
    crawler_task = asyncio.create_task(run_crawler_background())
    logger.info("Crawler background task started")

    yield

    # Shutdown
    logger.info("FastAPI application shutting down...")

    if crawler_instance:
        crawler_instance.running = False

    if crawler_task and not crawler_task.done():
        logger.info("Cancelling crawler task...")
        crawler_task.cancel()
        try:
            await crawler_task
        except asyncio.CancelledError:
            logger.info("Crawler task cancelled successfully")

    if crawler_instance:
        await crawler_instance.cleanup()

    logger.info("Shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Testudo Crawler Service",
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
            "service": "Testudo Crawler",
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
    if crawler_task is None:
        task_status = "not_started"
    elif crawler_task.done():
        if crawler_task.exception():
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
    if crawler_instance and crawler_instance.last_check_times:
        health_data["monitored_courses"] = len(crawler_instance.last_check_times)
        health_data["last_checks"] = {
            course_id: check_time.isoformat()
            for course_id, check_time in crawler_instance.last_check_times.items()
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
