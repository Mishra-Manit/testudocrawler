"""
Pydantic models for data structures and schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


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
    """Result of SMS notification delivery."""

    success: bool = Field(
        description="Whether the notification was sent successfully"
    )
    message_sid: Optional[str] = Field(
        default=None,
        description="Twilio message SID if successful",
    )
    recipient: str = Field(description="Recipient phone number")
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
    check_interval_seconds: int = Field(
        default=300, description="Check interval in seconds (default: 5 minutes)"
    )
    enabled: bool = Field(default=True, description="Whether monitoring is enabled")
