"""
Test script for NotificationService.
Demonstrates real Telegram integration by sending a test message.

Usage:
    python tests/test_notification.py

Requirements:
    - Valid Telegram bot token in .env file
    - Telegram chat ID configured

Environment Variables:
    TELEGRAM_BOT_TOKEN: Telegram Bot API token
    TELEGRAM_CHAT_ID: Chat ID to send messages to
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
    """Test the notification service and send a real Telegram message."""
    # Load configuration from environment
    settings = get_settings()

    print(f"\n{'='*60}")
    print(f"Testing Telegram NotificationService")
    print(f"Chat ID: {settings.telegram_chat_id}")
    print(f"{'='*60}\n")

    # Initialize NotificationService
    notification_service = NotificationService(
        bot_token=settings.telegram_bot_token,
        default_chat_id=settings.telegram_chat_id,
    )

    try:
        # Prepare test message
        test_message = (
            "🧪 <b>TEST MESSAGE</b> from UMD Professor Alert System\n\n"
            "This is a test notification to verify Telegram integration.\n"
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        print(f"Sending test Telegram message...")
        print(f"Message:\n{test_message}\n")

        # Send Telegram message
        result = await notification_service.send_message(
            chat_id=settings.telegram_chat_id,
            message=test_message
        )

        # Output the results
        print(f"\n{'='*60}")
        print("NOTIFICATION RESULTS")
        print(f"{'='*60}\n")

        if result.success:
            print(f"✓ Status: SUCCESS")
            print(f"Message ID: {result.message_id}")
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
