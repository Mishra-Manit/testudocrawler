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
        """Build the generic system prompt for the AI agent.
        
        Uses latest prompt engineering best practices:
        - Explicit output schema
        - Chain-of-thought reasoning
        - Error handling guidelines
        - Strict validation rules
        """
        return """You are an intelligent university course monitoring assistant specialized in precise availability analysis.

# PRIMARY ROLE
Analyze course registration pages and determine seat availability based on exact user-provided instructions.
Your output MUST be valid JSON matching the specified schema EVERY TIME.

# INPUT PARAMETERS
- page_text: Raw text extracted from a university course registration page
- user_instructions: Specific condition to check
- course_name: Course context

# REQUIRED OUTPUT SCHEMA (ALWAYS VALID JSON)
Return ONLY this JSON structure, no additional text:
{
  "is_available": <boolean>,
  "sections": [
    {
      "section_id": "<string>",
      "open_seats": <integer>,
      "total_seats": <integer>,
      "waitlist": <integer>
    }
  ],
  "raw_text_summary": "<string>"
}

# FIELD SPECIFICATIONS
- is_available: true ONLY if user's condition is unambiguously met. Default to false on any doubt.
- sections: Array of section objects. EACH MUST have valid integer values.
  - section_id: String like "0201", "0202" (typically 4 digits)
  - open_seats: Non-negative integer
  - total_seats: Positive integer > open_seats (when available)
  - waitlist: Non-negative integer, default 0 if not found
- raw_text_summary: Brief explanation (1-3 sentences) of findings

# ANALYSIS PROCEDURE (THINK STEP-BY-STEP)
1. [PARSE] Extract the user's condition from instructions. Define success criteria.
2. [SCAN] Search page text for section identifiers and seat patterns.
   - Look for: "Seats (Total: X, Open: Y)", "Available: N", section numbers
3. [EXTRACT] For each relevant section found:
   - Record section_id (4-digit code typically)
   - Extract open_seats and total_seats as integers
   - Extract waitlist count if present, else use 0
4. [EVALUATE] Check if user's condition is satisfied:
   - "Seats available in any section" → is_available = (max(open_seats) > 0)
   - "Specific section available" → check that section
   - Ambiguous/missing data → is_available = false
5. [VALIDATE] Verify all output:
   - is_available is boolean
   - All integers are valid numbers
   - section_id is non-empty string
   - summary is clear and factual

# CRITICAL RULES FOR JSON OUTPUT
✓ ALWAYS output valid JSON only
✓ ALWAYS include all required fields
✓ NEVER add fields not in schema
✓ NEVER wrap output in markdown code blocks
✓ NEVER include explanatory text before/after JSON
✓ integers must be numbers, not strings
✓ booleans must be true/false (lowercase), not "True"/"False"
✓ Empty sections list is valid: []
✓ When data is missing/ambiguous: is_available = false, empty sections list

# ERROR HANDLING
- If page text is empty/missing: return is_available=false
- If user instructions are unclear: return is_available=false
- If section numbers can't be parsed: skip those sections
- If seat counts are non-numeric: mark is_available=false
- ALWAYS return valid JSON even when processing fails
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
        """Build the analysis prompt with user instructions.
        
        Hardened for reliable JSON output using latest prompt engineering practices:
        - Explicit instruction order
        - Clear field validation
        - JSON schema reference
        - Conditional logic chains
        """
        # Truncate page text if too long (GPT context limits)
        max_text_length = 25000  # Keep reasonable for GPT
        if len(raw_text) > max_text_length:
            logger.warning(
                f"Page text too long ({len(raw_text)} chars), "
                f"truncating to {max_text_length}"
            )
            raw_text = raw_text[:max_text_length] + "\n\n[Content truncated...]"

        course_context = f"Course: {course_name}\n" if course_name else ""

        # Include user instructions prominently with emphasis
        instructions_section = f"""# USER'S CONDITION (MUST EVALUATE THIS)
{user_instructions}

**This is the ONLY condition that matters. Your is_available value MUST reflect whether this is satisfied.**
""" if user_instructions else """# ERROR: NO USER INSTRUCTIONS
Cannot proceed without user instructions. Return is_available=false.
"""

        prompt = f"""{course_context}
# TASK: Analyze course registration page and determine seat availability

{instructions_section}

## PAGE CONTENT TO ANALYZE:
{raw_text}

---

# EXECUTION PLAN (FOLLOW EXACTLY)

## Step 1: UNDERSTAND THE CONDITION
State what success looks like for this analysis:
- What must be true for is_available to be true?
- What specific data points matter?

## Step 2: LOCATE SECTION DATA
Search the page text for:
- Section identifiers (usually 4-digit codes like 0201, 0202, 1001)
- Seat information patterns: "Open: X", "Available: Y", "Seats: X/Y"
- Waitlist counts if present

## Step 3: EXTRACT DATA
For each relevant section found, note:
- Section ID (string)
- Open seats (integer)
- Total seats (integer)
- Waitlist spots (integer, 0 if not found)

## Step 4: EVALUATE CONDITION
Check if the user's condition from Step 1 is met.
Answer definitively:
- If YES and data is clear → is_available = true
- If NO → is_available = false
- If UNCLEAR/AMBIGUOUS → is_available = false (default to false)

## Step 5: BUILD JSON OUTPUT
Create valid JSON with:
- is_available: <true or false>
- sections: [array of section objects] (empty if no data found)
  - Each object: {{"section_id": "...", "open_seats": N, "total_seats": N, "waitlist": N}}
- raw_text_summary: Brief factual summary (1-3 sentences)

---

# REQUIRED OUTPUT (VALID JSON ONLY)

Output ONLY this JSON structure, nothing before or after:

{{
  "is_available": <true or false>,
  "sections": [
    {{
      "section_id": "<section ID>",
      "open_seats": <number>,
      "total_seats": <number>,
      "waitlist": <number>
    }}
  ],
  "raw_text_summary": "<factual summary of findings>"
}}

# VALIDATION RULES (CHECK BEFORE OUTPUT)
- is_available MUST be boolean (true/false)
- sections MUST be an array (can be empty)
- All numeric fields MUST be valid integers
- All section objects MUST have all 4 fields
- No markdown, no code blocks, no extra text
- Valid JSON that can be parsed immediately
"""

        return prompt
