# Testudo Watchdog

Monitors UMD Testudo course pages for seat availability and sends WhatsApp notifications.

## Quick Start

```bash
# 1. Setup environment
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. Configure .env (see Environment Variables below)
cp .env.example .env

# 3. Configure courses (see config/courses.yaml)

# 4. Run
python -m app.runner
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `TWILIO_ACCOUNT_SID` | Yes | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | Yes | Twilio Auth Token |
| `TWILIO_WHATSAPP_NUMBER` | Yes | Twilio Sandbox number |
| `RECIPIENT_WHATSAPP_NUMBER` | No | Global fallback recipient |
| `AI_PROVIDER` | No | `anthropic` or `openai` (default: anthropic) |

## Course Configuration

Edit `config/courses.yaml`:

```yaml
targets:
  - id: "cmsc216_spring26"
    name: "CMSC216 (Kauffman)"
    url: "https://app.testudo.umd.edu/soc/search?..."
    user_instructions: "Check if there are open seats for Kauffman"
    interval: 300
    enabled: true
    recipients:  # Optional: per-course recipients
      - "+12025551234"
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier |
| `name` | Yes | Display name for notifications |
| `url` | Yes | Testudo URL with filters |
| `user_instructions` | Yes | What to check (AI prompt) |
| `interval` | No | Check frequency in seconds (default: 300) |
| `enabled` | No | Enable/disable (default: true) |
| `recipients` | No | Per-course WhatsApp recipients |
| `notification_message` | No | Custom message template |

## Architecture

```
Scraper (Playwright) -> AI Agent (Claude) -> Notifier (Twilio WhatsApp)
```

## Development

```bash
pytest              # Run tests
black .             # Format code
mypy app/           # Type check
ruff check .        # Lint
```

## License

Educational use.
