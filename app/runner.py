"""
Main runner for Testudo Crawler.
Scheduler-based application that automatically checks course availability.
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Optional
from zoneinfo import ZoneInfo

import structlog

import logfire

from app.config import get_settings
from app.models.schemas import CourseConfig
from app.observability.logfire_config import initialize_logfire, log_event, log_error, log_warning, log_debug
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


class TestudoCrawler:
    """Main crawler application that monitors course availability."""

    def __init__(self):
        """Initialize the crawler application."""
        self.settings = get_settings()
        self.scraper: Optional[ScraperService] = None
        self.ai_agent: Optional[AIAgentService] = None
        self.notification: Optional[NotificationService] = None
        self.running = False
        self.course_tasks: Dict[str, asyncio.Task] = {}
        self.last_check_times: Dict[str, datetime] = {}

    def is_within_check_window(self, course: CourseConfig) -> bool:
        """
        Check if current time is within the configured check window for a course.
        """
        try:
            # Get timezone (defaults to America/New_York for EST/EDT)
            tz = ZoneInfo(course.check_timezone)
            current_time = datetime.now(tz)
            current_hour = current_time.hour
            
            # If start_hour and end_hour are the same and both are None-like, disable check
            if course.check_start_hour is None or course.check_end_hour is None:
                return True
            
            # Simple case: start < end (e.g., 8 < 23)
            if course.check_start_hour <= course.check_end_hour:
                return course.check_start_hour <= current_hour < course.check_end_hour
            
            # Wrap-around case: start > end (e.g., 22 > 6, meaning 10PM-6AM)
            return current_hour >= course.check_start_hour or current_hour < course.check_end_hour
        except Exception as e:
            log_error("error_checking_time_window", course_id=course.id, error=str(e))
            # On error, allow check (fail open for safety)
            return True

    async def initialize(self) -> None:
        """Initialize all services."""
        log_event("initializing_testudo_crawler")

        try:
            # Initialize Scraper Service
            log_event("initializing_scraper_service")
            self.scraper = ScraperService(timeout=self.settings.scraper_timeout)
            await self.scraper.initialize()
            log_event("scraper_service_initialized")

            # Initialize AI Agent Service
            log_event("initializing_ai_agent_service")
            self.ai_agent = AIAgentService(
                provider=self.settings.ai_provider,
                api_key=(
                    self.settings.anthropic_api_key
                    if self.settings.ai_provider == "anthropic"
                    else self.settings.openai_api_key
                ),
                model=(
                    self.settings.anthropic_model
                    if self.settings.ai_provider == "anthropic"
                    else self.settings.openai_model
                ),
            )
            log_event("ai_agent_service_initialized")

            # Initialize Telegram Notification Service
            log_event("initializing_notification_service")
            self.notification = NotificationService(
                bot_token=self.settings.telegram_bot_token,
                default_chat_id=self.settings.telegram_chat_id,
            )
            log_event("notification_service_initialized")

            log_event("all_services_initialized")

        except Exception as e:
            log_error("failed_to_initialize_services", error=str(e), exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        log_event("cleaning_up_resources")

        # Cancel all course monitoring tasks
        for course_id, task in self.course_tasks.items():
            if not task.done():
                log_event("cancelling_monitoring_task", course_id=course_id)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Close scraper
        if self.scraper:
            await self.scraper.close()

        log_event("cleanup_complete")

    def load_course_configs(self) -> list[CourseConfig]:
        """Load course configurations from YAML."""
        config = self.settings.load_courses_config()
        targets = config.get("targets", [])

        courses = []
        for target in targets:
            if not target.get("enabled", True):
                log_event("skipping_disabled_course", course_id=target.get('id', 'unknown'))
                continue

            try:
                # Explicit validation for required user_instructions field
                if "user_instructions" not in target:
                    raise ValueError(
                        f"Course '{target.get('id', 'unknown')}' missing required field "
                        f"'user_instructions'. Please add instructions for what to check."
                    )

                course = CourseConfig(
                    id=target["id"],
                    name=target["name"],
                    url=target["url"],
                    user_instructions=target["user_instructions"],
                    notification_message=target.get("notification_message"),
                    check_interval_seconds=target.get("interval", 300),
                    enabled=target.get("enabled", True),
                    check_start_hour=target.get("check_start_hour", 8),
                    check_end_hour=target.get("check_end_hour", 23),
                    check_timezone=target.get("check_timezone", "America/New_York"),
                )
                courses.append(course)
                log_event("loaded_course", course_id=course.id)

            except Exception as e:
                log_error("failed_to_load_course", course_id=target.get('id', 'unknown'), error=str(e))
                continue  # Continue loading other courses

        log_event("courses_loaded", count=len(courses))
        return courses

    async def check_course(self, course: CourseConfig) -> None:
        """
        Check a single course for seat availability.
        """
        with logfire.span(
            "course_check",
            course_id=course.id,
            course_name=course.name,
        ):
            start_time = time.time()
            log_event("starting_course_check", course_id=course.id, course_name=course.name, url=course.url)

            try:
                # Step 1: Scrape the course page
                log_event("scraping_started", course_id=course.id, url=course.url)
                scrape_result = await self.scraper.scrape_page(course.url)
                page_text = scrape_result["text"]
                log_event("scraping_completed", course_id=course.id, text_length=len(page_text))

                # Step 2: Analyze with AI agent using user instructions
                log_event("starting_agent_work", course_id=course.id, course_name=course.name)
                with logfire.span(
                    "agent_analysis",
                    course_id=course.id,
                    course_name=course.name,
                ):
                    availability = await self.ai_agent.check_availability(
                        raw_text=page_text,
                        course_name=course.name,
                        user_instructions=course.user_instructions,
                    )

                log_event("ai_analysis_complete", course_id=course.id, is_available=availability.is_available, sections_found=len(availability.sections))

                # Step 3: Send notifications if condition is met
                if availability.is_available:
                    open_sections = [s.section_id for s in availability.sections if s.open_seats > 0]
                    log_event("condition_met", course_id=course.id, course_name=course.name, sections=open_sections)

                    with logfire.span(
                        "sending_notification",
                        course_id=course.id,
                        course_name=course.name,
                    ):
                        notification_result = await self.notification.send_availability_alert(
                            course_name=course.name,
                            availability=availability,
                            course_url=course.url,
                            custom_message=course.notification_message,
                        )

                    log_event("notification_sent", course_id=course.id, success=notification_result.success, message_id=notification_result.message_id)
                else:
                    log_event("condition_not_met", course_id=course.id, course_name=course.name)

                # Update last check time
                self.last_check_times[course.id] = datetime.utcnow()

                duration = time.time() - start_time
                log_event("course_check_complete", course_id=course.id, duration_seconds=round(duration, 2), is_available=availability.is_available)

            except Exception as e:
                duration = time.time() - start_time
                log_error("course_check_failed", course_id=course.id, course_name=course.name, error=str(e), duration_seconds=round(duration, 2), exc_info=True)

    async def monitor_course_loop(self, course: CourseConfig) -> None:
        """
        Monitor a single course in a loop with its configured interval.
        """
        log_event("starting_monitoring_loop", course_id=course.id, course_name=course.name, interval_seconds=course.check_interval_seconds, check_window=f"{course.check_start_hour}:00-{course.check_end_hour}:00 {course.check_timezone}")

        while self.running:
            try:
                # Check if we're within the allowed time window
                if self.is_within_check_window(course):
                    await self.check_course(course)
                else:
                    tz = ZoneInfo(course.check_timezone)
                    current_time = datetime.now(tz)
                    log_debug("outside_check_window", course_id=course.id, current_time=current_time.isoformat(), window=f"{course.check_start_hour}:00-{course.check_end_hour}:00")

                # Wait for the configured interval before next check
                log_debug("waiting_for_next_check", course_id=course.id, wait_seconds=course.check_interval_seconds)
                await asyncio.sleep(course.check_interval_seconds)

            except asyncio.CancelledError:
                log_event("monitoring_loop_cancelled", course_id=course.id)
                break
            except Exception as e:
                log_error("error_in_monitoring_loop", course_id=course.id, error=str(e), exc_info=True)
                # Wait a bit before retrying on error
                await asyncio.sleep(60)

    async def run(self) -> None:
        """Run the main monitoring loop."""
        log_event("starting_testudo_crawler")

        # Load course configurations
        courses = self.load_course_configs()

        if not courses:
            log_warning("no_courses_configured")
            return

        # Start monitoring each course in its own task
        self.running = True
        for course in courses:
            task = asyncio.create_task(self.monitor_course_loop(course))
            self.course_tasks[course.id] = task
            log_event("started_monitoring_task", course_id=course.id, course_name=course.name)

        # Wait for all tasks (they run indefinitely)
        try:
            await asyncio.gather(*self.course_tasks.values())
        except asyncio.CancelledError:
            log_event("monitoring_tasks_cancelled")
        finally:
            self.running = False

    async def start(self) -> None:
        """Start the crawler application."""
        try:
            await self.initialize()
            await self.run()
        except KeyboardInterrupt:
            log_event("received_keyboard_interrupt")
        except Exception as e:
            log_error("fatal_error", error=str(e), exc_info=True)
            raise
        finally:
            await self.cleanup()


def setup_signal_handlers(crawler: TestudoCrawler) -> None:
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        log_event("received_signal", signum=signum)
        crawler.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    """Main entry point."""
    # Initialize Logfire observability
    initialize_logfire()

    crawler = TestudoCrawler()
    setup_signal_handlers(crawler)

    try:
        await crawler.start()
    except Exception as e:
        log_error("application_failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

