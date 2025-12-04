"""
Main runner for Testudo Watchdog.
Scheduler-based application that automatically checks course availability.
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Optional

import structlog

from app.config import get_settings
from app.models.schemas import CourseConfig
from app.services.ai_agent import AIAgentService
from app.services.notification import NotificationService
from app.services.scraper import ScraperService

# Configure structured logging
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
        structlog.processors.JSONRenderer() if sys.stdout.isatty() is False
        else structlog.dev.ConsoleRenderer(colors=True),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class TestudoWatchdog:
    """Main watchdog application that monitors course availability."""

    def __init__(self):
        """Initialize the watchdog application."""
        self.settings = get_settings()
        self.scraper: Optional[ScraperService] = None
        self.ai_agent: Optional[AIAgentService] = None
        self.notification: Optional[NotificationService] = None
        self.running = False
        self.course_tasks: Dict[str, asyncio.Task] = {}
        self.last_check_times: Dict[str, datetime] = {}

    async def initialize(self) -> None:
        """Initialize all services."""
        logger.info("Initializing Testudo Watchdog...")

        try:
            # Initialize Scraper Service
            logger.info("Initializing Scraper Service...")
            self.scraper = ScraperService(timeout=self.settings.scraper_timeout)
            await self.scraper.initialize()
            logger.info("Scraper Service initialized successfully")

            # Initialize AI Agent Service
            logger.info("Initializing AI Agent Service...")
            self.ai_agent = AIAgentService(
                api_key=self.settings.anthropic_api_key,
                model=self.settings.anthropic_model,
            )
            logger.info("AI Agent Service initialized successfully")

            # Initialize Notification Service
            logger.info("Initializing Notification Service...")
            self.notification = NotificationService(
                account_sid=self.settings.twilio_account_sid,
                auth_token=self.settings.twilio_auth_token,
                from_number=self.settings.twilio_phone_number,
            )
            logger.info("Notification Service initialized successfully")

            logger.info("All services initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize services", error=str(e), exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        logger.info("Cleaning up resources...")

        # Cancel all course monitoring tasks
        for course_id, task in self.course_tasks.items():
            if not task.done():
                logger.info(f"Cancelling monitoring task for course: {course_id}")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close scraper
        if self.scraper:
            await self.scraper.close()

        logger.info("Cleanup complete")

    def load_course_configs(self) -> list[CourseConfig]:
        """Load course configurations from YAML."""
        config = self.settings.load_courses_config()
        targets = config.get("targets", [])

        courses = []
        for target in targets:
            if not target.get("enabled", True):
                logger.info(
                    f"Skipping disabled course: {target.get('id', 'unknown')}"
                )
                continue

            course = CourseConfig(
                id=target["id"],
                name=target["name"],
                url=target["url"],
                check_interval_seconds=target.get("interval", 300),
                enabled=target.get("enabled", True),
            )
            courses.append(course)

        logger.info(f"Loaded {len(courses)} enabled course(s) to monitor")
        return courses

    async def check_course(self, course: CourseConfig) -> None:
        """
        Check a single course for seat availability.

        Args:
            course: Course configuration to check
        """
        start_time = time.time()
        logger.info(
            "Starting course check",
            course_id=course.id,
            course_name=course.name,
            url=course.url,
        )

        try:
            # Step 1: Scrape the course page
            scrape_result = await self.scraper.scrape_page(course.url)
            page_text = scrape_result["text"]
            logger.info(
                "Scraping complete",
                course_id=course.id,
                text_length=len(page_text),
            )

            # Step 2: Analyze with AI agent
            availability = await self.ai_agent.check_availability(
                raw_text=page_text,
                course_name=course.name,
            )

            logger.info(
                "AI analysis complete",
                course_id=course.id,
                is_available=availability.is_available,
                sections_found=len(availability.sections),
            )

            # Step 3: Send notifications if seats are available
            if availability.is_available:
                logger.warning(
                    "SEATS AVAILABLE!",
                    course_id=course.id,
                    course_name=course.name,
                    sections=[
                        s.section_id for s in availability.sections if s.open_seats > 0
                    ],
                )

                notification_results = await self.notification.send_availability_alert(
                    recipients=self.settings.recipient_phone_numbers,
                    course_name=course.name,
                    availability=availability,
                    course_url=course.url,
                )

                successful_notifications = sum(
                    1 for r in notification_results if r.success
                )
                logger.info(
                    "Notifications sent",
                    course_id=course.id,
                    successful=successful_notifications,
                    total=len(notification_results),
                )
            else:
                logger.info(
                    "No seats available",
                    course_id=course.id,
                    course_name=course.name,
                )

            # Update last check time
            self.last_check_times[course.id] = datetime.utcnow()

            duration = time.time() - start_time
            logger.info(
                "Course check complete",
                course_id=course.id,
                duration_seconds=round(duration, 2),
                is_available=availability.is_available,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Course check failed",
                course_id=course.id,
                course_name=course.name,
                error=str(e),
                duration_seconds=round(duration, 2),
                exc_info=True,
            )

    async def monitor_course_loop(self, course: CourseConfig) -> None:
        """
        Monitor a single course in a loop with its configured interval.

        Args:
            course: Course configuration to monitor
        """
        logger.info(
            "Starting monitoring loop",
            course_id=course.id,
            course_name=course.name,
            interval_seconds=course.check_interval_seconds,
        )

        while self.running:
            try:
                await self.check_course(course)

                # Wait for the configured interval before next check
                logger.debug(
                    "Waiting for next check",
                    course_id=course.id,
                    wait_seconds=course.check_interval_seconds,
                )
                await asyncio.sleep(course.check_interval_seconds)

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled", course_id=course.id)
                break
            except Exception as e:
                logger.error(
                    "Error in monitoring loop",
                    course_id=course.id,
                    error=str(e),
                    exc_info=True,
                )
                # Wait a bit before retrying on error
                await asyncio.sleep(60)

    async def run(self) -> None:
        """Run the main monitoring loop."""
        logger.info("Starting Testudo Watchdog")

        # Load course configurations
        courses = self.load_course_configs()

        if not courses:
            logger.warning("No courses configured for monitoring")
            return

        # Start monitoring each course in its own task
        self.running = True
        for course in courses:
            task = asyncio.create_task(self.monitor_course_loop(course))
            self.course_tasks[course.id] = task
            logger.info(
                "Started monitoring task",
                course_id=course.id,
                course_name=course.name,
            )

        # Wait for all tasks (they run indefinitely)
        try:
            await asyncio.gather(*self.course_tasks.values())
        except asyncio.CancelledError:
            logger.info("Monitoring tasks cancelled")
        finally:
            self.running = False

    async def start(self) -> None:
        """Start the watchdog application."""
        try:
            await self.initialize()
            await self.run()
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
        except Exception as e:
            logger.error("Fatal error", error=str(e), exc_info=True)
            raise
        finally:
            await self.cleanup()


def setup_signal_handlers(watchdog: TestudoWatchdog) -> None:
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        watchdog.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    """Main entry point."""
    watchdog = TestudoWatchdog()
    setup_signal_handlers(watchdog)

    try:
        await watchdog.start()
    except Exception as e:
        logger.error("Application failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

