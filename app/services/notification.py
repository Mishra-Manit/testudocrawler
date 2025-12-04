"""
Notification service for sending SMS alerts via Twilio.
Handles async SMS delivery, formatting, and error handling.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from app.models.schemas import AvailabilityCheck, NotificationResult

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending SMS notifications via Twilio."""

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
    ):
        """
        Initialize notification service.

        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Phone number to send SMS from
        """
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number
        logger.info("Notification service initialized")

    async def send_sms(
        self,
        to_number: str,
        message: str,
        max_retries: int = 3,
    ) -> NotificationResult:
        """
        Send SMS asynchronously with retry logic.

        Args:
            to_number: Recipient phone number
            message: Message content
            max_retries: Maximum number of retry attempts

        Returns:
            NotificationResult with delivery status
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    f"Sending SMS to {to_number} "
                    f"(attempt {attempt}/{max_retries})"
                )

                # Run Twilio API call in thread pool (Twilio SDK is synchronous)
                loop = asyncio.get_event_loop()
                twilio_message = await loop.run_in_executor(
                    None,
                    lambda: self.client.messages.create(
                        to=to_number,
                        from_=self.from_number,
                        body=message,
                    ),
                )

                logger.info(
                    f"SMS sent successfully to {to_number} "
                    f"(SID: {twilio_message.sid})"
                )

                return NotificationResult(
                    success=True,
                    message_sid=twilio_message.sid,
                    recipient=to_number,
                    sent_at=datetime.utcnow(),
                )

            except TwilioRestException as e:
                logger.error(
                    f"Twilio error sending to {to_number} "
                    f"(attempt {attempt}): {e.msg}"
                )

                if attempt < max_retries:
                    # Exponential backoff
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    return NotificationResult(
                        success=False,
                        recipient=to_number,
                        error=f"Twilio error: {e.msg}",
                        sent_at=datetime.utcnow(),
                    )

            except Exception as e:
                logger.error(
                    f"Unexpected error sending to {to_number} "
                    f"(attempt {attempt}): {e}"
                )

                if attempt < max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    return NotificationResult(
                        success=False,
                        recipient=to_number,
                        error=f"Unexpected error: {str(e)}",
                        sent_at=datetime.utcnow(),
                    )

        # This should never be reached
        return NotificationResult(
            success=False,
            recipient=to_number,
            error="Max retries exceeded",
            sent_at=datetime.utcnow(),
        )

    async def send_availability_alert(
        self,
        recipients: list[str],
        course_name: str,
        availability: AvailabilityCheck,
        course_url: str,
    ) -> list[NotificationResult]:
        """
        Send seat availability alert to multiple recipients.

        Args:
            recipients: List of phone numbers to notify
            course_name: Name of the course
            availability: Availability check results
            course_url: URL to the course registration page

        Returns:
            List of NotificationResult for each recipient
        """
        message = self._format_availability_alert(
            course_name=course_name,
            availability=availability,
            course_url=course_url,
        )

        logger.info(
            f"Sending availability alert to {len(recipients)} recipients: {course_name}"
        )

        # Send to all recipients concurrently
        tasks = [self.send_sms(recipient, message) for recipient in recipients]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions in results
        notification_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to send to {recipients[i]}: {result}")
                notification_results.append(
                    NotificationResult(
                        success=False,
                        recipient=recipients[i],
                        error=str(result),
                        sent_at=datetime.utcnow(),
                    )
                )
            else:
                notification_results.append(result)

        successful = sum(1 for r in notification_results if r.success)
        logger.info(
            f"Alert sent: {successful}/{len(recipients)} successful deliveries"
        )

        return notification_results

    def _format_availability_alert(
        self,
        course_name: str,
        availability: AvailabilityCheck,
        course_url: str,
    ) -> str:
        """
        Format seat availability alert message per PRD specification.

        Args:
            course_name: Name of the course
            availability: Availability check results
            course_url: URL to the course page

        Returns:
            Formatted SMS message
        """
        # Extract section numbers with open seats
        available_sections = [
            section.section_id
            for section in availability.sections
            if section.open_seats > 0
        ]

        sections_str = ", ".join(available_sections)

        # Format message per PRD spec
        message = (
            f"🚨 UMD ALERT: {course_name} has open seats!\n"
            f"Sections: {sections_str}\n"
            f"Link: {course_url}"
        )

        return message

    async def test_connection(self) -> bool:
        """
        Test Twilio API connection without sending SMS.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Validate credentials by fetching account info
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.api.accounts(
                    self.client.account_sid
                ).fetch(),
            )
            logger.info("Twilio connection test successful")
            return True
        except Exception as e:
            logger.error(f"Twilio connection test failed: {e}")
            return False
