"""
AI agent service using Pydantic AI for seat availability analysis.
Uses Claude Haiku for efficient, cost-effective content analysis.
"""

import logging
from typing import Optional

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.models.schemas import AvailabilityCheck

logger = logging.getLogger(__name__)


class AIAgentService:
    """Service for analyzing course pages with AI to detect seat availability."""

    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str
    ):
        """
        Initialize AI agent service with configurable provider.

        Args:
            provider: AI provider to use ('anthropic' or 'openai')
            api_key: API key for the selected provider
            model: Model name to use
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model

        # Create provider-specific model based on configuration
        if provider == "anthropic":
            provider_instance = AnthropicProvider(api_key=api_key)
            model_instance = AnthropicModel(model, provider=provider_instance)
        elif provider == "openai":
            provider_instance = OpenAIProvider(api_key=api_key)
            model_instance = OpenAIResponsesModel(model, provider=provider_instance)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

        # Create Pydantic AI agent with structured output
        self.agent = Agent(
            model_instance,
            output_type=AvailabilityCheck,
            system_prompt=self._build_system_prompt(),
        )

        logger.info(f"AI agent initialized with provider={provider}, model={model}")

    def _build_system_prompt(self) -> str:
        """Build the generic system prompt for the AI agent."""
        return """You are an intelligent university course monitoring assistant.

Your role is to analyze course registration pages and determine availability based on user-provided instructions.

CAPABILITIES:
- You receive raw text extracted from a university course page
- You receive specific user instructions about what to check
- Your job is to follow those instructions and determine if the condition is met

STRUCTURED OUTPUT:
Always return:
- is_available (bool): True if the user's condition is met, False otherwise
- sections (list): Relevant sections with seat information (section_id, open_seats, total_seats, waitlist)
- raw_text_summary (str): Brief explanation of what you found and why

ANALYSIS GUIDELINES:
1. Carefully read the user's instructions
2. Scan the page text for relevant information (look for patterns like "Seats (Total: X, Open: Y, Waitlist: Z)")
3. Extract section numbers (typically 4 digits like 0201, 0202)
4. Determine if the user's condition is satisfied
5. Be precise - if data is ambiguous or missing, mark is_available as false
6. Provide clear reasoning in raw_text_summary

Remember: Your analysis should directly address what the user asked for in their instructions.
"""

    async def check_availability(
        self,
        raw_text: str,
        course_name: Optional[str] = None,
        user_instructions: Optional[str] = None,
    ) -> AvailabilityCheck:
        """
        Analyze course page text based on user instructions.

        Args:
            raw_text: Raw text content extracted from the course page
            course_name: Optional course name for context
            user_instructions: User-defined instructions for what to check

        Returns:
            AvailabilityCheck with seat availability information
        """
        try:
            # Build the prompt with user instructions
            prompt = self._build_analysis_prompt(
                raw_text=raw_text,
                course_name=course_name,
                user_instructions=user_instructions,
            )

            logger.info(
                f"Analyzing {course_name or 'course'} "
                f"({len(raw_text)} chars) with custom instructions"
            )

            # Run the agent with structured output
            result = await self.agent.run(prompt)

            # Extract the structured data
            availability_check = result.output

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
                raw_text_summary=f"Analysis failed: {str(e)}",
            )

    def _build_analysis_prompt(
        self,
        raw_text: str,
        course_name: Optional[str] = None,
        user_instructions: Optional[str] = None,
    ) -> str:
        """Build the analysis prompt with user instructions."""
        # Truncate page text if too long (Claude Haiku context limits)
        max_text_length = 15000  # Keep reasonable for Haiku
        if len(raw_text) > max_text_length:
            logger.warning(
                f"Page text too long ({len(raw_text)} chars), "
                f"truncating to {max_text_length}"
            )
            raw_text = raw_text[:max_text_length] + "\n\n[Content truncated...]"

        course_context = f"Course: {course_name}\n" if course_name else ""

        # Include user instructions prominently
        instructions_section = f"""
USER INSTRUCTIONS:
{user_instructions}

Your task is to follow the above instructions and determine if the condition is met.
""" if user_instructions else """
ERROR: No user instructions provided. Unable to analyze.
"""

        prompt = f"""Analyze this course registration page text.

{course_context}
{instructions_section}

**PAGE CONTENT:**
{raw_text}

---

ANALYSIS STEPS:
1. Read and understand what the user wants to check
2. Scan the page content for relevant section information
3. Look for seat availability patterns
4. Extract section IDs and their seat counts
5. Determine if the user's condition is satisfied
6. Provide structured output with is_available, sections, and a clear summary

Set is_available=true ONLY if the user's condition is clearly met.
"""

        return prompt
