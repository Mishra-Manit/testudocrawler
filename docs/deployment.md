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
- `RECIPIENT_PHONE_NUMBER`

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

## Cloud Deployment (Render)

The application can be deployed to Render's free tier as a web service. This provides 24/7 availability without managing servers.

### Architecture

- **Web Service**: FastAPI with uvicorn (lightweight and professional)
- **Background Task**: ProfessorAlert runs as an asyncio background task
- **Endpoints**:
  - `GET /` - Root endpoint, confirms service is alive
  - `GET /health` - Detailed health check with monitoring stats
  - `GET /ping` - Minimal ping endpoint for external monitors

### Deployment Steps

#### Option 1: One-Click Deploy (Using render.yaml)

1. **Push your code to GitHub** (if not already done)
   ```bash
   git add .
   git commit -m "Add Render deployment configuration"
   git push origin main
   ```

2. **Create a new Web Service on Render**
   - Go to https://dashboard.render.com/
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml`

3. **Configure Environment Variables**
   In the Render dashboard, set these required environment variables:
   - `ANTHROPIC_API_KEY` - Your Anthropic API key
   - `TWILIO_ACCOUNT_SID` - Your Twilio account SID
   - `TWILIO_AUTH_TOKEN` - Your Twilio auth token
   - `TWILIO_PHONE_NUMBER` - Your Twilio phone number (format: +1234567890)
   - `RECIPIENT_PHONE_NUMBER` - Phone number to receive notifications
   - `LOGFIRE_TOKEN` - (Optional) For observability

4. **Deploy**
   - Click "Apply" to deploy
   - Wait for the build to complete (~5-10 minutes)

#### Option 2: Manual Deployment

1. **Create New Web Service**
   - Go to https://dashboard.render.com/
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Build Settings**
   - **Name**: professor-alert (or your preferred name)
   - **Region**: Choose closest to you
   - **Branch**: main
   - **Runtime**: Python
   - **Build Command**:
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt && playwright install chromium && playwright install-deps
     ```
   - **Start Command**:
     ```bash
     python -m uvicorn app.web:app --host 0.0.0.0 --port 10000
     ```

3. **Configure Instance**
   - **Instance Type**: Free

4. **Set Environment Variables**
   Add all required environment variables (see list above)

5. **Create Web Service**
   - Click "Create Web Service"
   - Wait for deployment to complete

### Keeping Service Alive (Free Tier)

Render's free tier spins down after 15 minutes of inactivity. To keep your service alive 24/7:

#### Recommended: External Pinger Services

Use a free external monitoring service to ping your endpoint every 10-14 minutes:

1. **UptimeRobot** (Free: https://uptimerobot.com)
   - Create a new HTTP(s) monitor
   - URL: `https://your-app.onrender.com/ping`
   - Monitoring interval: 5 minutes (free tier)

2. **Freshping** (Free: https://freshping.io)
   - Add a new check
   - URL: `https://your-app.onrender.com/ping`
   - Check interval: 1 minute

3. **Cronitor** (Free tier available: https://cronitor.io)
   - Create a heartbeat monitor
   - Ping URL: `https://your-app.onrender.com/ping`

4. **Healthchecks.io** (Free: https://healthchecks.io)
   - Create a new check with HTTP endpoint
   - URL: `https://your-app.onrender.com/ping`

#### Alternative: Cron-job.org

Set up a scheduled ping using https://cron-job.org:
- URL: `https://your-app.onrender.com/ping`
- Schedule: Every 10 minutes

### Monitoring Your Service

#### Check Service Status

Visit your deployed service URL:
- Root: `https://your-app.onrender.com/` - Shows uptime and status
- Health: `https://your-app.onrender.com/health` - Detailed health metrics

#### View Logs

In Render dashboard:
1. Go to your web service
2. Click "Logs" tab
3. Monitor real-time logs for course checks and notifications

#### Logfire Observability (Optional)

If you set the `LOGFIRE_TOKEN` environment variable:
1. Visit https://logfire.pydantic.dev
2. View detailed traces, metrics, and AI agent performance

### Updating Your Deployment

To update your deployed service:

```bash
git add .
git commit -m "Your update message"
git push origin main
```

Render will automatically detect changes and redeploy.

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

