# 🎓 Testudo Crawler

**AI-Powered Course Monitoring for University of Maryland Students**

![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)
![License](https://img.shields.io/badge/license-Educational-green.svg)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)
![Framework](https://img.shields.io/badge/framework-FastAPI-009688.svg)

Never miss a seat again. Testudo Crawler monitors UMD course registration pages 24/7 and sends instant Telegram alerts when seats become available. Powered by AI to intelligently analyze course pages with natural language instructions.

## Features

📱 **Instant Telegram Notifications**
- Real-time alerts when seats open
- Customizable notification messages
- Per-course recipient configuration

🚀 **Easy Deployment**
- One-click deployment to Render (free tier)
- Local development support
- Structured logging with Logfire integration

## How It Works

```
Testudo Page → Playwright Scraper → AI Analysis → Telegram Alert → You
```

1. **Playwright** scrapes the Testudo course page and extracts text
2. **AI Agent** (Claude/GPT) analyzes the content using your natural language instructions
3. **Telegram Bot** sends notifications when seats are available

Check runs every N minutes → If seats found → Alert sent to your phone

## Self-Hosting Guide

### Prerequisites

Before you begin, you'll need:

- **Python 3.13+** - [Download here](https://www.python.org/downloads/)
- **Anthropic API Key** - [Get free credits](https://console.anthropic.com/)
- **Telegram Bot Token** - [Create bot with BotFather](https://core.telegram.org/bots/tutorial)

### Local Development Setup

**Step 1: Clone the Repository**

```bash
git clone https://github.com/yourusername/testudo-crawler.git
cd testudo-crawler
```

**Step 2: Create Virtual Environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Step 3: Install Dependencies**

```bash
pip install -r requirements.txt
playwright install chromium
```

**Step 4: Configure Environment Variables**

Copy the example environment file and edit with your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-xxxxx
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=123456789

# Optional
AI_PROVIDER=anthropic  # or 'openai'
ANTHROPIC_MODEL=claude-3-haiku-20240307
SCRAPER_TIMEOUT=30
```

**Getting Your Telegram Chat ID:**
1. Start a chat with [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy the "Id" number it shows you
3. Use this as your `TELEGRAM_CHAT_ID`

**Step 5: Configure Courses**

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

**Step 6: Run Locally**

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

Deploy to Render's free tier for 24/7 monitoring (750 hours/month free).

**Step 1: Push to GitHub**

```bash
git remote add origin https://github.com/yourusername/testudo-crawler.git
git add .
git commit -m "Initial commit"
git push -u origin main
```

**Step 2: Deploy to Render**

**Option A: One-Click Deploy (Recommended)**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/yourusername/testudo-crawler)

Click the button above and Render will automatically use the `render.yaml` configuration.

**Option B: Manual Setup**

1. Go to [render.com](https://render.com) and sign up with GitHub
2. Click "New +" → "Web Service"
3. Connect your testudo-crawler repository
4. Configure:
   - **Name:** `testudo-crawler`
   - **Build Command:** `./build.sh`
   - **Start Command:** `python -m uvicorn app.web:app --host 0.0.0.0 --port 10000`
   - **Plan:** Free

**Step 3: Set Environment Variables**

In Render Dashboard → Environment, add:

```
ANTHROPIC_API_KEY=sk-ant-xxxxx
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHI...
TELEGRAM_CHAT_ID=123456789
ANTHROPIC_MODEL=claude-3-haiku-20240307
AI_PROVIDER=anthropic
SCRAPER_TIMEOUT=30
```
### Optional: Logfire Integration

For advanced observability and tracing:

1. Sign up at [logfire.pydantic.dev](https://logfire.pydantic.dev)
2. Add `LOGFIRE_TOKEN=your_token` to your environment variables
3. View structured logs and AI traces in the Logfire dashboard

## Configuration Reference
### Course Configuration

Edit `config/courses.yaml` to define which courses to monitor.

**Required Fields:**
- `id` - Unique identifier for this course
- `name` - Display name for notifications
- `url` - Full Testudo URL with all filters applied
- `user_instructions` - Natural language instructions for the AI

**Optional Fields:**
- `interval` - Check frequency in seconds (default: 300)
- `enabled` - Enable/disable monitoring (default: true)
- `check_start_hour` - Start checking at this hour (default: 8)
- `check_end_hour` - Stop checking at this hour (default: 23)
- `check_timezone` - Timezone for time windows (default: America/New_York)
- `notification_message` - Custom notification template (supports `{course_name}`, `{sections}`, `{course_url}`)

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
    🔥 URGENT: {course_name} has seats!
    Sections available: {sections}
    Register NOW: {course_url}
```

## Architecture

**Technology Stack:**
- **Python 3.13+** - Async/await support
- **FastAPI + Uvicorn** - Web service for deployment
- **Playwright** - Headless browser automation
- **Pydantic AI** - Structured AI outputs
- **Anthropic Claude / OpenAI GPT** - AI analysis
- **python-telegram-bot** - Telegram notifications
- **PyYAML, Structlog, Logfire** - Configuration and observability

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

## Development

### Code Quality

This project uses Black for formatting, Ruff for linting, Mypy for type checking, and Pytest for testing.

### Adding a New Course

1. Get the Testudo URL with all desired filters applied
2. Add a new entry to `config/courses.yaml`
3. Write clear `user_instructions` for the AI (e.g., "Check if section 0101 has open seats")
4. Test locally with `python -m app.runner`

## Troubleshooting

**"Browser not found" error**

```bash
python -m playwright install chromium
```

**"Invalid API key" error**

Verify `ANTHROPIC_API_KEY` is correct in `.env`. Check that your key hasn't expired at [console.anthropic.com](https://console.anthropic.com).

**No Telegram notifications received**

- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check `TELEGRAM_CHAT_ID` matches your chat (test with [@userinfobot](https://t.me/userinfobot))
- Ensure the bot has permission to message you (start a chat with your bot first)

**"Course check failed" in logs**

- Verify the Testudo URL is still valid
- Check that `user_instructions` are clear and specific
- Increase `SCRAPER_TIMEOUT` if pages load slowly

**Render deployment issues**

- Verify all environment variables are set in Render dashboard
- Check build logs for specific errors
- Ensure `courses.yaml` has at least one enabled course

**Need Help?** Open an issue on [GitHub Issues](https://github.com/yourusername/testudo-crawler/issues)

## Contributing

Contributions are welcome! Here's how:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and formatting (`pytest && black .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please ensure tests pass and code is formatted with Black before submitting.

## License

Educational use only. Not affiliated with the University of Maryland.

**Disclaimer:** This tool is for educational purposes. Always follow your university's policies on automated systems.