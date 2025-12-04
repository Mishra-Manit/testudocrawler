"""
AI agent service using Pydantic AI for seat availability analysis.
Uses Claude Haiku for efficient, cost-effective content analysis.
"""

import logging
from typing import Optional

from pydantic_ai import Agent

from app.models.schemas import AvailabilityCheck

logger = logging.getLogger(__name__)


class AIAgentService:
    """Service for analyzing course pages with AI to detect seat availability."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-haiku-20240307",
    ):
        """
        Initialize AI agent service.

        Args:
            api_key: Anthropic API key
            model: Model to use. Set in .env file.
        """
        self.api_key = api_key
        self.model = f"anthropic:{model}"

        # Create Pydantic AI agent with structured output
        self.agent = Agent(
            self.model,
            result_type=AvailabilityCheck,
            system_prompt=self._build_system_prompt(),
        )

        logger.info(f"AI agent initialized with model: {model}")

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the AI agent."""
        return """You are a university scheduling assistant analyzing course registration pages.

Your ONLY goal is to find sections where 'Open' seats are greater than 0.

Analyze the provided text from a course catalog page. Look for patterns like:
- "Seats (Total: X, Open: Y, Waitlist: Z)"
- Section numbers (typically 4 digits like 0201, 0202, etc.)
- Any indication of seat availability

Important guidelines:
- Ignore Waitlist numbers - only care about Open seats
- Ignore Total numbers - only care if Open > 0
- Extract the exact section ID (e.g., "0201", "0204")
- Only mark is_available as true if you find at least one section with Open > 0
- Be precise: if Open is 0 or not found, mark is_available as false
- Provide a brief summary in raw_text_summary of what you observed

Output format:
- is_available: true ONLY if Open > 0 for any section
- sections: list of all sections found with their seat information
- raw_text_summary: brief description of what was seen
"""

    async def check_availability(
        self,
        raw_text: str,
        course_name: Optional[str] = None,
    ) -> AvailabilityCheck:
        """
        Analyze course page text to determine seat availability.

        Args:
            raw_text: Raw text content extracted from the course page
            course_name: Optional course name for context

        Returns:
            AvailabilityCheck with seat availability information
        """
        try:
            # Build the prompt
            prompt = self._build_analysis_prompt(
                raw_text=raw_text,
                course_name=course_name,
            )

            logger.info(
                f"Analyzing availability for {course_name or 'course'} "
                f"({len(raw_text)} chars)"
            )

            # Run the agent with structured output
            result = await self.agent.run(prompt)

            # Extract the structured data
            availability_check = result.data

            logger.info(
                f"Analysis complete: "
                f"is_available={availability_check.is_available}, "
                f"found {len(availability_check.sections)} sections"
            )

            return availability_check

        except Exception as e:
            logger.error(f"AI analysis failed: {e}", exc_info=True)
            # Return unavailable result on error
            return AvailabilityCheck(
                is_available=False,
                sections=[],
                raw_text_summary=f"Analysis failed due to error: {str(e)}",
            )

    def _build_analysis_prompt(
        self,
        raw_text: str,
        course_name: Optional[str] = None,
    ) -> str:
        """Build the analysis prompt with course information."""
        # Truncate page text if too long (Claude Haiku context limits)
        max_text_length = 15000  # Keep reasonable for Haiku
        if len(raw_text) > max_text_length:
            logger.warning(
                f"Page text too long ({len(raw_text)} chars), "
                f"truncating to {max_text_length}"
            )
            raw_text = raw_text[:max_text_length] + "\n\n[Content truncated...]"

        course_context = f"Course: {course_name}\n\n" if course_name else ""

        prompt = f"""Analyze this course registration page text to find sections with open seats.

{course_context}**Page Content:**
{raw_text}

---

Your task:
1. Look for section numbers (typically 4 digits like 0201, 0202, etc.)
2. For each section, find the seat information pattern: "Seats (Total: X, Open: Y, Waitlist: Z)"
3. Extract sections where Open > 0
4. Return is_available=true ONLY if at least one section has Open > 0
5. Include all sections found (even if Open=0) in the sections list
6. Provide a brief summary of what you observed

Remember: Only mark is_available as true if Open seats > 0 for any section.
"""

        return prompt

    async def test_connection(self) -> bool:
        """
        Test connection to Anthropic API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Simple test prompt
            result = await self.agent.run(
                "Respond with a simple availability check: is_available=false, sections=[], raw_text_summary='test'"
            )
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
