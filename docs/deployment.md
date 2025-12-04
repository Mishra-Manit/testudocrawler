# Deployment Guide

## Prerequisites

- Python 3.11 or higher
- Playwright browser binaries (installed automatically)
- Anthropic API key
- Twilio account with phone number

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd professoralet
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

```bash
playwright install chromium
```

### 5. Configure Environment

Create `.env` file in project root:

```bash
cp .env.example .env  # If example exists
# Edit .env with your credentials
```

Required variables:
- `ANTHROPIC_API_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`
- `RECIPIENT_PHONE_NUMBERS`

### 6. Configure Courses

Edit `config/courses.yaml` with your courses to monitor.

## Running Locally

### Development Mode

```bash
python -m app.runner
```

Or:

```bash
python app/runner.py
```

### Production Mode

```bash
LOG_LEVEL=INFO python -m app.runner
```

## Running as a Service

### systemd (Linux)

Create `/etc/systemd/system/testudo-watchdog.service`:

```ini
[Unit]
Description=Testudo Watchdog - Course Availability Monitor
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/professoralet
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python -m app.runner
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemd-ctl daemon-reload
sudo systemctl enable testudo-watchdog
sudo systemctl start testudo-watchdog
sudo systemctl status testudo-watchdog
```

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Run application
CMD ["python", "-m", "app.runner"]
```

Build and run:

```bash
docker build -t testudo-watchdog .
docker run -d \
  --name testudo-watchdog \
  --env-file .env \
  -v $(pwd)/config:/app/config \
  testudo-watchdog
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  watchdog:
    build: .
    container_name: testudo-watchdog
    env_file:
      - .env
    volumes:
      - ./config:/app/config
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Run:

```bash
docker-compose up -d
docker-compose logs -f
```

## Monitoring

### Logs

Logs are output to stdout/stderr. For production:

```bash
# Redirect to file
python -m app.runner >> watchdog.log 2>&1

# Or use systemd journal
journalctl -u testudo-watchdog -f
```

### Health Checks

The application logs structured information:
- Course check start/completion
- Seat availability status
- Notification delivery status
- Errors and warnings

Monitor logs for:
- `SEATS AVAILABLE!` - Alert sent
- `Course check failed` - Errors to investigate
- `Notifications sent` - Delivery confirmation

## Troubleshooting

### Playwright Browser Issues

```bash
# Reinstall browsers
playwright install chromium --force

# Check browser installation
playwright install-deps chromium
```

### Permission Issues

```bash
# Ensure .env file is readable
chmod 600 .env

# Ensure config directory is readable
chmod 755 config
chmod 644 config/courses.yaml
```

### Port Conflicts

The application doesn't use network ports (no web server), so port conflicts shouldn't occur.

### Memory Issues

If monitoring many courses:
- Increase system memory
- Reduce check intervals
- Monitor fewer courses simultaneously

## Backup and Recovery

### Configuration Backup

```bash
# Backup configuration
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/ .env
```

### Recovery

1. Restore `.env` file
2. Restore `config/courses.yaml`
3. Restart service

## Updates

### Updating Code

```bash
git pull
source venv/bin/activate
pip install -r requirements.txt
# Restart service
```

### Updating Configuration

1. Edit `config/courses.yaml`
2. Restart service (changes take effect immediately on restart)

## Security Considerations

1. **API Keys:**
   - Never commit `.env` to version control
   - Use environment variables in production
   - Rotate keys periodically

2. **File Permissions:**
   - Restrict `.env` file permissions (600)
   - Run service with minimal privileges

3. **Network:**
   - Application only makes outbound connections
   - No inbound ports required
   - Consider firewall rules if needed

## Performance Tuning

### Check Intervals

- Default: 300 seconds (5 minutes)
- High-demand courses: 300 seconds
- Low-priority courses: 600+ seconds

### Concurrent Checks

- Each course runs independently
- No shared state between courses
- System resources determine max concurrent courses

### Resource Usage

- Memory: ~200-500 MB per course (browser instance)
- CPU: Low (mostly idle, spikes during checks)
- Network: Minimal (only during checks)

## Scaling

For monitoring many courses:
1. Run multiple instances (different config files)
2. Use process managers (supervisor, systemd)
3. Consider container orchestration (Kubernetes) for large scale

