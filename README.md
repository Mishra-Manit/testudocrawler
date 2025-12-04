# Testudo Watchdog

An intelligent automation agent that monitors the University of Maryland's Testudo schedule of classes for seat availability. Uses a Vision/LLM approach to semantically understand availability, specifically looking for open seats in high-demand sections.

## Features

- **Intelligent Scraping**: Uses Playwright to extract raw text from Testudo pages
- **AI Analysis**: Leverages Claude Haiku via Pydantic AI to semantically parse seat availability
- **WhatsApp Notifications**: Sends instant WhatsApp alerts via Twilio when seats become available
- **Automatic Monitoring**: Scheduler-based runner that checks courses every 5 minutes (configurable)
- **Resilient**: Handles Testudo errors gracefully without crashing
- **Structured Logging**: Comprehensive logging with timestamps and context

## Technology Stack

- **Backend**: Python 3.11+ with asyncio scheduler
- **Web Scraping**: Playwright (Headless Chromium)
- **AI Analysis**: Pydantic AI + Claude 3 Haiku (Anthropic)
- **Notifications**: Twilio WhatsApp
- **Configuration**: Pydantic Settings + YAML
- **Logging**: structlog for structured logging

## Project Structure

```
professoralet/
├── app/
│   ├── runner.py                    # Main scheduler-based runner
│   ├── config.py                    # Settings management
│   ├── models/
│   │   └── schemas.py               # Pydantic data models
│   └── services/
│       ├── scraper.py               # Playwright scraping
│       ├── ai_agent.py              # AI analysis for seat availability
│       └── notification.py          # WhatsApp notifications
├── config/
│   └── courses.yaml                 # Course configuration
├── docs/
│   ├── architecture.md              # System architecture
│   ├── configuration.md             # Configuration guide
│   └── deployment.md                # Deployment guide
├── tests/                           # Test suite
├── .env                             # Environment variables
├── requirements.txt                 # Python dependencies
├── PRD.md                          # Product Requirements Document
└── README.md                       # This file
```

## Installation

### Prerequisites

- Python 3.11 or higher
- Anthropic API key ([Get one here](https://console.anthropic.com/))
- Twilio account ([Sign up here](https://www.twilio.com/try-twilio))

### Step 1: Clone or Navigate to Project

```bash
cd /Users/manitmishra/Desktop/professoralet
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Install Playwright Browsers

```bash
playwright install chromium
```

### Step 5: Configure Environment Variables

Create a `.env` file:

```bash
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Twilio WhatsApp Configuration
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_WHATSAPP_NUMBER=+14155238886  # Twilio Sandbox WhatsApp number
RECIPIENT_WHATSAPP_NUMBER=+1234567890  # Your WhatsApp number

# Application Settings
DEBUG=False
LOG_LEVEL=INFO
SCRAPER_TIMEOUT=30
```

### Step 6: Join Twilio WhatsApp Sandbox

Before you can receive WhatsApp notifications, you need to join the Twilio WhatsApp Sandbox:

1. Go to [Twilio WhatsApp Sandbox](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
2. You'll see a sandbox number (e.g., `+1 415 523 8886`) and a join code (e.g., `join <code>`)
3. Open WhatsApp on your phone and send the join message to the sandbox number
4. You'll receive a confirmation message from Twilio
5. Copy the sandbox number and use it as `TWILIO_WHATSAPP_NUMBER` in your `.env` file
6. Use your own WhatsApp number as `RECIPIENT_WHATSAPP_NUMBER`

**Note**: The sandbox is free and perfect for personal use. Each user needs to join their own sandbox.

### Step 7: Configure Courses

Edit `config/courses.yaml`:

```yaml
targets:
  - id: "cmsc216_spring26"
    name: "CMSC216 (Kauffman)"
    url: "https://app.testudo.umd.edu/soc/search?courseId=CMSC216&sectionId=&termId=202601&_openSectionsOnly=on&creditCompare=%3E%3D&credits=0.0&courseLevelFilter=ALL&instructor=Kauffman%2C+Christopher&_facetoface=on&_blended=on&_online=on"
    interval: 300  # Check every 5 minutes (300 seconds)
    enabled: true
```

## Usage

### Running the Application

Start the watchdog:

```bash
python -m app.runner
```

Or:

```bash
python app/runner.py
```

The application will:
1. Initialize all services (Scraper, AI Agent, WhatsApp Notification)
2. Load course configurations
3. Start monitoring each enabled course at its configured interval
4. Automatically check for seat availability
5. Send WhatsApp alerts when seats become available

### Stopping the Application

Press `Ctrl+C` to gracefully shutdown the application.

## How It Works

1. **The Scraper (Agent 1)**: Accesses pre-filtered Testudo URLs using Playwright, handles dynamic loading, and extracts clean text
2. **The Analyst (Agent 2)**: Processes the raw text using Claude Haiku to determine if "Open" seat counts are greater than 0. Returns structured JSON
3. **The Notifier**: If seats are available, triggers immediate WhatsApp alert via Twilio with specific section numbers

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key | - |
| `ANTHROPIC_MODEL` | No | Claude model to use | `claude-3-haiku-20240307` |
| `TWILIO_ACCOUNT_SID` | Yes | Twilio Account SID | - |
| `TWILIO_AUTH_TOKEN` | Yes | Twilio Auth Token | - |
| `TWILIO_WHATSAPP_NUMBER` | Yes | Twilio Sandbox WhatsApp number | - |
| `RECIPIENT_WHATSAPP_NUMBER` | Yes | Your WhatsApp number | - |
| `DEBUG` | No | Debug mode | `False` |
| `LOG_LEVEL` | No | Logging level | `INFO` |
| `SCRAPER_TIMEOUT` | No | Scraping timeout (seconds) | `30` |

### Course Configuration (config/courses.yaml)

```yaml
targets:
  - id: string                # Unique course identifier
    name: string              # Course name (used in WhatsApp alerts)
    url: string               # Full Testudo URL with filters
    interval: integer         # Check interval in seconds (default: 300)
    enabled: boolean          # Whether to monitor this course
```

See [docs/configuration.md](docs/configuration.md) for detailed configuration guide.

## WhatsApp Alert Format

When seats become available, you'll receive a WhatsApp message:

```
🚨 UMD ALERT: CMSC216 (Kauffman) has open seats!
Sections: 0201, 0204
Link: https://app.testudo.umd.edu/soc/search?...
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
```

### Type Checking

```bash
mypy app/
```

### Linting

```bash
ruff check .
```

## Troubleshooting

### Playwright Installation Issues

```bash
# Install system dependencies (Linux)
playwright install-deps

# Reinstall browsers
playwright install chromium --force
```

### WhatsApp Messages Not Sending

1. Verify you've joined the Twilio WhatsApp Sandbox (see Setup Step 6)
2. Check Twilio credentials in `.env`
3. Verify phone numbers are in E.164 format (+1234567890)
4. Ensure `TWILIO_WHATSAPP_NUMBER` is the correct sandbox number
5. Check logs for Twilio API errors

### Scraping Failures

1. Verify the course URL is accessible in a browser
2. Check if Testudo is returning 502/503 errors (common during registration)
3. Increase `SCRAPER_TIMEOUT` in `.env`
4. Review logs for specific error messages

### AI Analysis Issues

1. Verify `ANTHROPIC_API_KEY` is valid
2. Check API rate limits haven't been exceeded
3. Review AI agent reasoning in logs

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

### Core Components

- **ScraperService**: Browser automation with Playwright, extracts and cleans text
- **AIAgentService**: Semantic parsing of seat availability using Claude Haiku
- **NotificationService**: WhatsApp message delivery via Twilio with retry logic
- **Runner**: Scheduler that orchestrates monitoring loops for each course

## Performance

- **Latency**: Scrape → AI → WhatsApp loop completes in < 20 seconds
- **Accuracy**: Distinguishes between `Open: 0` (Unavailable) and `Open: 1` (Available)
- **Resilience**: Handles Testudo 502/503 errors gracefully

## Deployment

See [docs/deployment.md](docs/deployment.md) for deployment options including:
- Running as a systemd service
- Docker containerization
- Docker Compose setup

## Documentation

- [Architecture](docs/architecture.md) - System design and components
- [Configuration](docs/configuration.md) - Detailed configuration guide
- [Deployment](docs/deployment.md) - Deployment options and best practices
- [PRD](PRD.md) - Product Requirements Document

## Security

- **Environment Variables**: Secrets stored in `.env` (not in version control)
- **Input Validation**: All inputs validated with Pydantic
- **HTTPS**: Secure communication with external APIs
- **No Secret Logging**: Sensitive data masked in logs

## Cost Optimization

- **Claude Haiku**: Cost-effective AI model (~$0.25 per million tokens)
- **Text Cleaning**: Reduces token usage before sending to LLM
- **Smart Retry**: Exponential backoff reduces unnecessary API calls

## License

This project is for educational purposes.

## Support

For issues and questions:
- Review the [PRD.md](PRD.md) for detailed requirements
- Check logs in the console output
- Verify all configuration files are properly formatted
- See [docs/](docs/) for detailed documentation

## Acknowledgments

- [Playwright](https://playwright.dev/) - Browser automation
- [Pydantic AI](https://ai.pydantic.dev/) - AI agent framework
- [Anthropic](https://www.anthropic.com/) - Claude AI models
- [Twilio](https://www.twilio.com/) - WhatsApp messaging

---

**Built with Python, Playwright, Claude AI, and Twilio WhatsApp**
