
### **Product Requirements Document (PRD)**

## 1\. Product Overview

**Testudo Watchdog** is an intelligent automation agent designed to monitor the University of Maryland's schedule of classes (Testudo). Unlike standard scrapers that break when HTML structures change, this system uses a "Vision/LLM" approach. It extracts raw text from the page and uses a Lightweight LLM (Claude Haiku) to semantically understand availability, specifically looking for open seats in high-demand sections (e.g., CMSC216 with Prof. Kauffman).

### 1.1 Core Workflow

1.  **The Scraper (Agent 1):** Accesses specific, pre-filtered Testudo URLs using Playwright, handles dynamic loading, and extracts clean text.
2.  **The Analyst (Agent 2):** Processes the raw text using Claude Haiku to determine if "Open" seat counts are greater than 0. Returns a structured JSON object.
3.  **The Notifier:** If the Analyst returns `is_available: true`, the system triggers an immediate SMS via Twilio with the specific section number.

These two agents need to be run one after another
-----

## 2\. Functional Requirements

### 2.1 Agent 1: The Scraper (Playwright)

**FR-1.1: Dynamic Page Loading**

  * The agent must navigate to complex, pre-filtered URLs (containing query parameters for `courseId`, `instructor`, `termId`, etc.).
  * **Critical:** The agent must wait for the DOM state `networkidle` or specific selectors (e.g., `.section-id`) to ensure the table data is fully rendered before scraping.

**FR-1.2: Content Extraction & Cleaning**

  * The agent must extract the `innerText` of the main container holding the course sections.
  * **Cleaning:** It must strip excessive whitespace, newlines, and hidden header text to minimize token usage before sending to the LLM.
  * **Output:** A raw string block representing the current state of the page.

### 2.2 Agent 2: The Analyst (AI/Haiku)

**FR-2.1: Semantic Parsing**

  * **Input:** The raw string from Agent 1.
  * **Model:** Claude 3 Haiku (via Pydantic AI).
  * **Prompt Engineering:** The system prompt must instruct Haiku to look for the pattern `Seats (Total: X, Open: Y, Waitlist: Z)` associated with specific section numbers (e.g., `0201`).

**FR-2.2: Structured Output**

  * The agent must strictly output a JSON object (enforced by Pydantic) containing:
      * `is_available` (boolean): True ONLY if `Open > 0` for any section.
      * `available_sections` (list[str]): A list of section IDs (e.g., `["0201", "0204"]`) that have open seats.
      * `reasoning` (str): A brief validation string (e.g., "Found 1 open seat in section 0201").

### 2.3 Notification System

**FR-3.1: Conditional Trigger**

  * The system acts **only** if `is_available` is `True`.

**FR-3.2: SMS Composition**

  * **Provider:** Twilio.
  * **Message Format:**
    > "🚨 UMD ALERT: [Course Name] has open seats\!
    > Sections: [Section Numbers]
    > Link: [Original URL]"

-----

## 3\. Technical Specifications

### 3.1 Technology Stack

  * **Backend:** Python 3.11+ (FastAPI for the runner/endpoints).
  * **Browser Automation:** Playwright (Headless Chromium).
  * **AI Inference:** Pydantic AI wrapping Anthropic Claude 3 Haiku.
  * **Notifications:** Twilio SDK.

### 3.2 Data Models (Pydantic)

**The AI Analysis Result:**

```python
from pydantic import BaseModel, Field
from typing import List

class SectionStatus(BaseModel):
    section_id: str = Field(..., description="The 4 digit section number, e.g., '0201'")
    open_seats: int = Field(..., description="The number of open seats found")

class AvailabilityCheck(BaseModel):
    is_available: bool = Field(..., description="True if ANY section has open_seats > 0")
    sections: List[SectionStatus] = Field(default_factory=list, description="List of available sections")
    raw_text_summary: str = Field(..., description="Brief summary of what was seen")
```

**Configuration (YAML):**

```yaml
courses:
  - id: "cmsc216_kauffman"
    name: "CMSC216 (Kauffman)"
    # The exact URL with filters applied
    target_url: "https://app.testudo.umd.edu/soc/search?courseId=CMSC216&instructor=Kauffman..."
    check_interval_seconds: 60
    enabled: true
```

-----

## 4\. Implementation Steps (Agent Logic)

### Step 1: Scraper Logic (`services/scraper.py`)

```python
async def get_page_content(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 1. Open Website
        await page.goto(url)
        
        # 2. Wait for Load (Testudo is slow)
        try:
            # Wait for the specific container that holds sections
            await page.wait_for_selector('.course-sections', timeout=15000)
        except TimeoutError:
            return "Error: Page load timeout"

        # 3. Grab & Clean Text
        content = await page.inner_text("body")
        # Basic cleanup to save tokens
        clean_content = " ".join(content.split())
        
        await browser.close()
        return clean_content
```

### Step 2: AI Logic (`services/agent.py`)

```python
from pydantic_ai import Agent

agent = Agent(
    'claude-3-haiku-20240307',
    result_type=AvailabilityCheck,
    system_prompt=(
        "You are a university scheduling assistant. "
        "Analyze the provided text from a course catalog. "
        "Your ONLY goal is to find sections where 'Open' seats are greater than 0. "
        "Ignore Waitlist numbers. Ignore Total numbers. "
        "If specific sections are listed (like 0201, 0202), extract them."
    )
)

async def check_availability(raw_text: str):
    result = await agent.run(raw_text)
    return result.data
```

### Step 3: Integration Logic (`main.py`)

```python
@app.post("/check-course")
async def run_check(course_config: CourseConfig):
    # 1. Scrape
    raw_text = await scraper.get_page_content(course_config.target_url)
    
    # 2. Analyze
    analysis = await agent.check_availability(raw_text)
    
    # 3. Trigger
    if analysis.is_available:
        msg = f"SEATS OPEN for {course_config.name}! Sections: {[s.section_id for s in analysis.sections]}"
        await send_sms(msg, course_config.target_url)
        return {"status": "alert_sent", "details": analysis}
        
    return {"status": "no_seats", "details": analysis}
```

-----

## 5\. Configuration Guide

### Environment Variables (`.env`)

```bash
# Services
ANTHROPIC_API_KEY=sk-ant-xxx
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_FROM_NUMBER=+15550000000

# User
MY_PHONE_NUMBER=+15559998888
```

### Course Config (`config/courses.yaml`)

To monitor the specific Kauffman link you provided:

```yaml
targets:
  - id: "cmsc216_spring26"
    name: "CMSC216 (Kauffman)"
    url: "https://app.testudo.umd.edu/soc/search?courseId=CMSC216&sectionId=&termId=202601&_openSectionsOnly=on&creditCompare=%3E%3D&credits=0.0&courseLevelFilter=ALL&instructor=Kauffman%2C+Christopher&_facetoface=on&_blended=on&_online=on"
    interval: 120
```

## 6\. Success Criteria

1.  **Latency:** The Scrape -\> AI -\> SMS loop must complete in under 20 seconds.
2.  **Accuracy:** The AI must distinguish between `Seats: (Total: 30, Open: 0)` (Unavailable) and `Seats: (Total: 30, Open: 1)` (Available).
3.  **Resilience:** If Testudo throws a 502/503 error (common during registration), the scraper handles it gracefully without crashing the app.

## 7\. Next Steps for Developer

1.  **Initialize Project:** Set up the FastAPI structure as defined.
2.  **Test Scraper:** Run the Playwright script against the URL and print the `clean_content` to console to ensure Testudo isn't blocking the bot (Cloudflare).
3.  **Test Haiku:** Copy that printed text, paste it into the Anthropic console, and test the prompt to ensure it reliably extracts the "Open" number.