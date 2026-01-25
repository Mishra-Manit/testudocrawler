"""
Pydantic models for data structures and schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SectionStatus(BaseModel):
    """Represents the seat availability status for a course section."""

    section_id: str = Field(
        ..., description="The 4-digit section number, e.g., '0201'"
    )
    open_seats: int = Field(..., description="The number of open seats found")
    total_seats: int = Field(..., description="The total number of seats")
    waitlist: int = Field(
        default=0, description="The number of waitlist spots"
    )


class AvailabilityCheck(BaseModel):
    """Result of AI analysis for seat availability."""

    is_available: bool = Field(
        ...,
        description="True if ANY section has open_seats > 0",
    )
    sections: list[SectionStatus] = Field(
        default_factory=list,
        description="List of available sections with seat information",
    )
    raw_text_summary: str = Field(
        ...,
        description="Brief summary of what was seen in the page text",
    )


class NotificationResult(BaseModel):
    """Result of Telegram notification delivery."""

    success: bool = Field(
        description="Whether the notification was sent successfully"
    )
    message_id: Optional[int] = Field(
        default=None,
        description="Telegram message ID if successful",
    )
    recipient: str = Field(description="Recipient chat ID")
    error: Optional[str] = Field(
        default=None,
        description="Error message if delivery failed",
    )
    sent_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the notification was sent",
    )


class CourseConfig(BaseModel):
    """Configuration model for a course to monitor."""

    id: str = Field(..., description="Unique identifier for the course")
    name: str = Field(..., description="Course name")
    url: str = Field(..., description="The exact URL with filters applied")
    user_instructions: str = Field(
        ...,
        description="Natural language instructions for what to check on the page"
    )
    notification_message: Optional[str] = Field(
        default=None,
        description="Custom notification message (optional). Defaults to generic alert if not provided."
    )
    check_interval_seconds: int = Field(
        default=300, description="Check interval in seconds (default: 5 minutes)"
    )
    enabled: bool = Field(default=True, description="Whether monitoring is enabled")
    check_start_hour: int = Field(
        default=8, description="Start hour (0-23) for checking. 8 = 8AM EST. Use null to disable time restrictions."
    )
    check_end_hour: int = Field(
        default=23, description="End hour (0-23) for checking. 23 = 11PM EST. Checks must finish before this hour."
    )
    check_timezone: str = Field(
        default="America/New_York", description="Timezone for checking hours (e.g. 'America/New_York' for EST/EDT)"
    )

    @field_validator("user_instructions")
    @classmethod
    def validate_user_instructions(cls, v: str) -> str:
        """Validate user instructions are reasonable."""
        v = v.strip()
        if not v:
            raise ValueError("user_instructions cannot be empty")
        if len(v) < 10:
            raise ValueError(
                "user_instructions too short - please provide clear instructions"
            )
        if len(v) > 1000:
            raise ValueError(
                "user_instructions too long - please keep under 1000 characters"
            )
        return v
