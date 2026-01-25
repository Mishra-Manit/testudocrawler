"""
Main runner for Testudo Crawler.
Scheduler-based application that automatically checks course availability.
"""

import asyncio
import signal
import sys
import time
from datetime import datetime
from typing import Dict, Optional
from zoneinfo import ZoneInfo

import logfire

from app.config import get_settings
from app.models.schemas import CourseConfig
from app.observability.logfire_config import (
    configure_structlog,
    initialize_logfire,
    log_event,
    log_error,
    log_warning,
    log_debug,
)
from app.services.ai_agent import AIAgentService
from app.services.notification import NotificationService
from app.services.scraper import ScraperService


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
        try:
            self.scraper = ScraperService(timeout=self.settings.scraper_timeout)
            await self.scraper.initialize()

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

            self.notification = NotificationService(
                bot_token=self.settings.telegram_bot_token,
                default_chat_id=self.settings.telegram_chat_id,
            )
            log_event("services_initialized")
        except Exception as e:
            log_error("failed_to_initialize_services", error=str(e), exc_info=True)
            raise

    async def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        for task in self.course_tasks.values():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

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
                continue

            try:
                if "user_instructions" not in target:
                    raise ValueError(f"Course '{target.get('id', 'unknown')}' missing 'user_instructions'")

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
            except Exception as e:
                log_error("failed_to_load_course", course_id=target.get('id', 'unknown'), error=str(e))

        log_event("courses_loaded", count=len(courses))
        return courses

    async def check_course(self, course: CourseConfig) -> None:
        """Check a single course for seat availability."""
        start_time = time.time()
        try:
            scrape_result = await self.scraper.scrape_page(course.url)
            page_text = scrape_result["text"]

            availability = await self.ai_agent.check_availability(
                raw_text=page_text,
                course_name=course.name,
                user_instructions=course.user_instructions,
            )

            if availability.is_available:
                await self.notification.send_availability_alert(
                    course_name=course.name,
                    availability=availability,
                    course_url=course.url,
                    custom_message=course.notification_message,
                )
                log_event("seats_available", course_id=course.id, sections=[s.section_id for s in availability.sections if s.open_seats > 0])

            log_debug("course_checked", course_id=course.id, available=availability.is_available, duration=round(time.time() - start_time, 2))
        except Exception as e:
            log_error("course_check_failed", course_id=course.id, error=str(e), duration=round(time.time() - start_time, 2))

    async def monitor_course_loop(self, course: CourseConfig) -> None:
        """Monitor a single course in a loop with its configured interval."""
        while self.running:
            try:
                if self.is_within_check_window(course):
                    await self.check_course(course)
                await asyncio.sleep(course.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log_error("monitor_loop_error", course_id=course.id, error=str(e))
                await asyncio.sleep(60)

    async def run(self) -> None:
        """Run the main monitoring loop."""
        courses = self.load_course_configs()
        if not courses:
            log_warning("no_courses_configured")
            return

        self.running = True
        for course in courses:
            self.course_tasks[course.id] = asyncio.create_task(self.monitor_course_loop(course))

        log_event("crawler_started", course_count=len(courses))
        try:
            await asyncio.gather(*self.course_tasks.values())
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False

    async def start(self) -> None:
        """Start the crawler application."""
        try:
            await self.initialize()
            await self.run()
        except Exception as e:
            log_error("fatal_error", error=str(e), exc_info=True)
            raise
        finally:
            await self.cleanup()


async def main() -> None:
    """Main entry point."""
    configure_structlog()
    initialize_logfire()

    crawler = TestudoCrawler()

    def handle_signal(signum, frame):
        crawler.running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        await crawler.start()
    except Exception as e:
        log_error("application_failed", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

