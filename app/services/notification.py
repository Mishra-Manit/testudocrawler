"""
Notification service for sending Telegram alerts.
Handles async Telegram delivery, formatting, and error handling.
Uses native async Telegram Bot API - no thread pool executor needed.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

import structlog

from telegram import Bot
from telegram.error import TelegramError

from app.models.schemas import AvailabilityCheck, NotificationResult

logger = structlog.get_logger(__name__)


class NotificationService:
    """Service for sending Telegram notifications."""

    def __init__(
        self,
        bot_token: str,
        default_chat_id: str,
    ):
        """
        Initialize notification service.

        Args:
            bot_token: Telegram Bot API token
            default_chat_id: Default chat ID to send messages to
        """
        self.bot = Bot(token=bot_token)
        self.default_chat_id = default_chat_id
        logger.info("Telegram notification service initialized")

    async def send_message(
        self,
        chat_id: str,
        message: str,
        max_retries: int = 3,
    ) -> NotificationResult:
        """
        Send Telegram message asynchronously with retry logic.

        Args:
            chat_id: Recipient Telegram chat ID
            message: Message content
            max_retries: Maximum number of retry attempts

        Returns:
            NotificationResult with delivery status
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"Sending Telegram message to chat {chat_id} "
                    f"(attempt {attempt}/{max_retries})"
                )

                # Native async - no run_in_executor needed!
                telegram_message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                )

                logger.info(
                    f"Telegram message sent successfully to chat {chat_id} "
                    f"(message_id: {telegram_message.message_id})"
                )

                return NotificationResult(
                    success=True,
                    message_id=telegram_message.message_id,
                    recipient=chat_id,
                    sent_at=datetime.now(timezone.utc),
                )

            except TelegramError as e:
                logger.error(
                    f"Telegram error sending to chat {chat_id} "
                    f"(attempt {attempt}): {e.message}"
                )

                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    return NotificationResult(
                        success=False,
                        recipient=chat_id,
                        error=f"Telegram error: {e.message}",
                        sent_at=datetime.now(timezone.utc),
                    )

            except Exception as e:
                logger.error(
                    f"Unexpected error sending to chat {chat_id} "
                    f"(attempt {attempt}): {e}"
                )

                if attempt < max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    return NotificationResult(
                        success=False,
                        recipient=chat_id,
                        error=f"Unexpected error: {str(e)}",
                        sent_at=datetime.now(timezone.utc),
                    )

        # This should never be reached
        return NotificationResult(
            success=False,
            recipient=chat_id,
            error="Max retries exceeded",
            sent_at=datetime.now(timezone.utc),
        )

    async def send_availability_alert(
        self,
        course_name: str,
        availability: AvailabilityCheck,
        course_url: str,
        custom_message: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> NotificationResult:
        """
        Send seat availability alert to the configured chat.

        Args:
            course_name: Name of the course
            availability: Availability check results
            course_url: URL to the course registration page
            custom_message: Optional custom message template with {course_name}, {sections}, {course_url} variables
            chat_id: Optional specific chat ID (uses default if not provided)

        Returns:
            NotificationResult with delivery status
        """
        target_chat_id = chat_id or self.default_chat_id

        # Use custom message if provided, otherwise use default format
        if custom_message:
            # Build sections string
            available_sections = [
                s.section_id for s in availability.sections if s.open_seats > 0
            ]
            sections_str = ", ".join(available_sections) if available_sections else "N/A"

            try:
                # Replace template variables
                message = custom_message.format(
                    course_name=course_name,
                    sections=sections_str,
                    course_url=course_url
                )
            except (KeyError, ValueError) as e:
                # Fallback to default format if custom message has issues
                logger.warning(f"Custom message format error: {e}, using default format")
                message = self._format_availability_alert(
                    course_name=course_name,
                    availability=availability,
                    course_url=course_url,
                )
        else:
            message = self._format_availability_alert(
                course_name=course_name,
                availability=availability,
                course_url=course_url,
            )

        logger.info(f"Sending availability alert to chat {target_chat_id}: {course_name}")

        result = await self.send_message(target_chat_id, message)

        if result.success:
            logger.info(f"Alert sent successfully to chat {target_chat_id}")
        else:
            logger.error(f"Failed to send alert to chat {target_chat_id}: {result.error}")

        return result

    def _format_availability_alert(
        self,
        course_name: str,
        availability: AvailabilityCheck,
        course_url: str,
    ) -> str:
        """
        Format seat availability alert message.

        Args:
            course_name: Name of the course
            availability: Availability check results
            course_url: URL to the course page

        Returns:
            Formatted Telegram message
        """
        # Extract section numbers with open seats
        available_sections = [
            section.section_id
            for section in availability.sections
            if section.open_seats > 0
        ]

        sections_str = ", ".join(available_sections)

        # Format message
        message = (
            f"🚨 <b>UMD ALERT:</b> {course_name} has open seats!\n"
            f"<b>Sections:</b> {sections_str}\n"
            f"<b>Link:</b> {course_url}"
        )

        return message
