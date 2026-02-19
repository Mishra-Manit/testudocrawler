# Testudo Crawler

**Course monitoring for University of Maryland students**

![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)
![License](https://img.shields.io/badge/license-Educational-green.svg)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
![Framework](https://img.shields.io/badge/framework-FastAPI-009688.svg)

Testudo Crawler monitors UMD course registration pages and sends Telegram alerts when seats open. You can describe what to watch in plain language (for example: specific professors, sections, or time windows).

## Features

**Telegram Notifications**
- Real-time alerts when seats open
- Customizable notification messages
- Per-course recipient configuration

**Deployment**
- One-click deployment to Render (free tier)
- Local development support
- Structured logging with Logfire integration

## How It Works

```
Testudo Page → Playwright Scraper → AI Analysis → Telegram Alert → You
```

1. **Playwright** scrapes the Testudo course page and extracts text
2. **AI Agent** (Claude/GPT) analyzes the content using your instructions
3. **Telegram Bot** sends notifications when seats are available

Checks run every N minutes. If seats are found, you get an alert.

## Self-Hosting Guide

### Prerequisites

You'll need:

- **Python 3.13+** - [Download here](https://www.python.org/downloads/)
- **OpenAI API Key** - [Create one here](https://platform.openai.com/api-keys)
- **Telegram Bot Token** - [Create bot with BotFather](https://core.telegram.org/bots/tutorial)

### Local Development Setup

**Step 1: Clone the Repository**

```bash
git clone https://github.com/Mishra-Manit/testudocrawler.git
cd testudocrawler
```

**Step 2: Install Dependencies**

```bash
pip install -r requirements.txt
playwright install chromium
```

**Step 3: Configure Environment Variables**

```bash
cp .env.example .env
```

```bash
OPENAI_API_KEY=sk-proj-xxxxx
AI_PROVIDER=openai
OPENAI_MODEL=gpt-5-mini
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789
```

Everything else can stay at defaults unless you want to customize behavior.

**Getting Your Telegram Chat ID:**
1. Start a chat with [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy the "Id" number it shows you
3. Use this as your `TELEGRAM_CHAT_ID`

**Step 4: Configure Courses**

Edit `config/courses.yaml` to add the courses you want to monitor:

```yaml
targets:
  - id: "cmsc216_spring26"
    name: "CMSC216 (Kauffman)"
    url: "https://app.testudo.umd.edu/soc/search?courseId=CMSC216&instructor=Kauffman..."
    user_instructions: "Check if there are any open seats for Professor Kauffman's sections"
    interval: 300  # Check every 5 minutes
    enabled: true
    check_start_hour: 8   # 8 AM
    check_end_hour: 23    # 11 PM
```

**Step 5: Run Locally**

```bash
python -m app.runner
```

You should see output like:

```
INFO - Initializing Testudo Crawler...
INFO - Scraper Service initialized successfully
INFO - AI Agent Service initialized successfully
INFO - Telegram Notification Service initialized successfully
INFO - Starting course check: CMSC216 (Kauffman)
```

### Cloud Deployment (Render)

Deploy to Render's free tier for 24/7 monitoring.

**Step 1: Push to GitHub**

```bash
git remote add origin https://github.com/Mishra-Manit/testudocrawler.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

**Step 2: Deploy to Render**

**Option A: One-Click Deploy**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Mishra-Manit/testudocrawler)

Click the button above and Render will use the included `render.yaml` config.

## Usage Examples

### Monitor Specific Professor

```yaml
- id: "cs_professor"
  name: "CMSC132 (Nelson)"
  url: "https://app.testudo.umd.edu/soc/search?courseId=CMSC132&instructor=Nelson..."
  user_instructions: "Check if ANY section taught by Professor Nelson has open seats"
```

### Monitor Specific Section with Time Window

```yaml
- id: "math_section"
  name: "MATH140 Section 0201"
  url: "https://app.testudo.umd.edu/soc/search?courseId=MATH140&sectionId=0201..."
  user_instructions: "Check if section 0201 specifically has open seats"
  check_start_hour: 6   # 6 AM
  check_end_hour: 22    # 10 PM
  interval: 300
```

### Custom Notification Message

```yaml
- id: "priority_course"
  name: "ENGL101"
  url: "https://app.testudo.umd.edu/soc/..."
  user_instructions: "Check for open seats"
  notification_message: |
    URGENT: {course_name} has seats!
    Sections available: {sections}
    Register NOW: {course_url}
```

## Architecture

**Technology Stack:**
- **Python 3.13+** - Runtime
- **FastAPI + Uvicorn** - Web service
- **Playwright** - Browser automation
- **Pydantic AI** - Structured model outputs
- **OpenAI GPT-5 mini (default) / Anthropic Claude (optional)** - Content analysis
- **python-telegram-bot** - Alerts
- **PyYAML, Structlog, Logfire** - Config + observability

**Project Structure:**

```
testudo-crawler/
├── app/
│   ├── runner.py              # Main orchestrator & scheduler
│   ├── web.py                 # FastAPI web service
│   ├── config.py              # Settings management
│   ├── models/schemas.py      # Pydantic data models
│   ├── services/
│   │   ├── scraper.py         # Playwright-based scraper
│   │   ├── ai_agent.py        # AI analysis service
│   │   └── notification.py    # Telegram notifications
│   └── observability/
│       └── logfire_config.py  # Logfire initialization
├── config/courses.yaml        # Course monitoring config
├── tests/                     # Pytest test suite
└── requirements.txt           # Python dependencies
```

**Data Flow:** Scheduler (asyncio) → Scraper (Playwright) → AI Agent (Claude/GPT) → Notification Service (Telegram)

Contributions are welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and formatting (`pytest && black .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please make sure tests pass and code is formatted with Black before submitting.

## License

Educational use only. Not affiliated with the University of Maryland.

**Disclaimer:** This tool is for educational purposes. Always follow your university's policies on automated systems.