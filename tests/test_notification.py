"""
Test script for NotificationService.
Demonstrates real Twilio SMS integration by sending a test message.

Usage:
    python tests/test_notification.py

Requirements:
    - Valid Twilio credentials in .env file
    - At least one recipient phone number configured

Environment Variables:
    TWILIO_ACCOUNT_SID: Twilio account identifier
    TWILIO_AUTH_TOKEN: Twilio authentication token
    TWILIO_PHONE_NUMBER: Phone number to send from
    RECIPIENT_PHONE_NUMBER: Recipient phone number
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.services.notification import NotificationService

# Configure logging to see notification service activity
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def test_notification():
    """Test the notification service and send a real SMS."""
    # Load configuration from environment
    settings = get_settings()

    # Validate recipient is configured
    if not settings.recipient_phone_number:
        raise ValueError(
            "No recipient phone number configured. "
            "Set RECIPIENT_PHONE_NUMBER in .env file."
        )

    # Use the recipient
    test_recipient = settings.recipient_phone_number

    print(f"\n{'='*60}")
    print(f"Testing NotificationService")
    print(f"From: {settings.twilio_phone_number}")
    print(f"To: {test_recipient}")
    print(f"{'='*60}\n")

    # Initialize NotificationService
    notification_service = NotificationService(
        account_sid=settings.twilio_account_sid,
        auth_token=settings.twilio_auth_token,
        from_number=settings.twilio_phone_number,
    )

    try:
        # Prepare test message
        test_message = (
            "TEST MESSAGE from UMD Professor Alert System\n"
            "This is a test notification to verify Twilio SMS integration.\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print(f"Sending test SMS...")
        print(f"Message:\n{test_message}\n")

        # Send SMS
        result = await notification_service.send_sms(
            to_number=test_recipient,
            message=test_message
        )

        # Output the results
        print(f"\n{'='*60}")
        print("NOTIFICATION RESULTS")
        print(f"{'='*60}\n")

        if result.success:
            print(f"✓ Status: SUCCESS")
            print(f"Message SID: {result.message_sid}")
            print(f"Recipient: {result.recipient}")
            print(f"Sent At: {result.sent_at}")
        else:
            print(f"✗ Status: FAILED")
            print(f"Recipient: {result.recipient}")
            print(f"Error: {result.error}")
            print(f"Attempted At: {result.sent_at}")

        print(f"\n{'='*60}\n")

    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_notification())
