# Architecture Overview

## System Design

Testudo Watchdog is a scheduler-based monitoring system that automatically checks UMD Testudo course pages for seat availability. Unlike traditional scrapers that break when HTML structures change, this system uses a Vision/LLM approach for semantic understanding.

## Core Components

### 1. Scraper Service (`app/services/scraper.py`)

**Purpose:** Extracts raw text content from Testudo course pages using Playwright.

**Key Features:**
- Browser automation with Playwright (headless Chromium)
- Dynamic page loading with network idle detection
- Selector-based waiting for course sections
- Text extraction and cleaning (whitespace normalization)
- Retry logic with exponential backoff
- Resource blocking for faster loading (images, fonts, etc.)

**Workflow:**
1. Navigate to pre-filtered Testudo URL
2. Wait for DOM to stabilize (`networkidle` or specific selectors)
3. Extract `innerText` from body/main container
4. Clean text (strip excessive whitespace, normalize)
5. Return cleaned text string

### 2. AI Agent Service (`app/services/ai_agent.py`)

**Purpose:** Analyzes scraped text using Claude Haiku to detect seat availability.

**Key Features:**
- Uses Pydantic AI with structured output
- Semantic parsing of seat patterns: `Seats (Total: X, Open: Y, Waitlist: Z)`
- Section ID extraction (4-digit codes like "0201")
- Returns structured `AvailabilityCheck` model

**System Prompt:**
- Focuses ONLY on finding sections where `Open > 0`
- Ignores Waitlist and Total numbers
- Extracts exact section IDs
- Provides reasoning summary

**Output Format:**
```python
AvailabilityCheck(
    is_available: bool,  # True if ANY section has open_seats > 0
    sections: List[SectionStatus],  # All sections found
    raw_text_summary: str  # Brief description
)
```

### 3. Notification Service (`app/services/notification.py`)

**Purpose:** Sends SMS alerts via Twilio when seats become available.

**Key Features:**
- Async SMS delivery
- Retry logic with exponential backoff
- Multi-recipient support
- Formatted messages per PRD spec

**Message Format:**
```
🚨 UMD ALERT: [Course Name] has open seats!
Sections: [0201, 0204]
Link: [URL]
```

### 4. Runner (`app/runner.py`)

**Purpose:** Main scheduler that orchestrates the monitoring loop.

**Key Features:**
- Service initialization and lifecycle management
- Per-course monitoring loops with configurable intervals
- Graceful shutdown handling (SIGINT/SIGTERM)
- Structured logging with `structlog`
- Error handling and recovery

**Workflow:**
1. Initialize all services (Scraper, AI Agent, Notification)
2. Load course configurations from YAML
3. Start monitoring loop for each enabled course
4. Each course runs independently with its own interval
5. On seat availability: trigger notification
6. Continue monitoring until shutdown

## Data Flow

```
┌─────────────┐
│   Runner    │
│  (Scheduler)│
└──────┬──────┘
       │
       ├───> Scraper Service
       │     └───> Playwright → Testudo URL → Clean Text
       │
       ├───> AI Agent Service
       │     └───> Claude Haiku → AvailabilityCheck
       │
       └───> Notification Service (if available)
             └───> Twilio → SMS Alert
```

## Configuration

### Environment Variables (`.env`)
- `ANTHROPIC_API_KEY`: Anthropic API key
- `TWILIO_ACCOUNT_SID`: Twilio account SID
- `TWILIO_AUTH_TOKEN`: Twilio auth token
- `TWILIO_PHONE_NUMBER`: Twilio phone number (sender)
- `RECIPIENT_PHONE_NUMBERS`: Comma-separated recipient numbers
- `SCRAPER_TIMEOUT`: Scraper timeout in seconds (default: 30)
- `LOG_LEVEL`: Logging level (default: INFO)

### Course Configuration (`config/courses.yaml`)
- YAML file with `targets` array
- Each target defines: `id`, `name`, `url`, `interval`, `enabled`
- Per-course check intervals (default: 300 seconds / 5 minutes)

## Error Handling

- **Scraper failures:** Retry with exponential backoff (3 attempts)
- **AI analysis failures:** Return `is_available=False` with error summary
- **Notification failures:** Retry up to 3 times, log failures
- **Monitoring loop errors:** Log error, wait 60s, continue monitoring

## Logging

Structured logging using `structlog`:
- JSON format (when not TTY) or colored console output (when TTY)
- Includes timestamps, log levels, context (course_id, etc.)
- Tracks durations, status, and errors

## Performance Considerations

- **Latency Target:** Scrape → AI → SMS loop completes in < 20 seconds
- **Concurrency:** Each course monitored independently (no shared state)
- **Resource Usage:** Headless browser, single browser instance reused
- **Token Optimization:** Text cleaning reduces LLM token usage

## Resilience

- Handles Testudo 502/503 errors gracefully
- Continues monitoring even if individual checks fail
- Graceful shutdown on SIGINT/SIGTERM
- Browser instance cleanup on exit

