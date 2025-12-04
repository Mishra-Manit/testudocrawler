# Configuration Guide

## Environment Variables

Create a `.env` file in the project root with the following variables:

### Required Variables

```bash
# Anthropic API Configuration
ANTHROPIC_API_KEY=sk-ant-xxx

# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_PHONE_NUMBER=+15550000000

# Recipient phone number
RECIPIENT_PHONE_NUMBER=+15559998888
```

### Optional Variables

```bash
# Application Settings
DEBUG=false
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
SCRAPER_TIMEOUT=30  # Seconds to wait for page load
AI_TIMEOUT=10  # Seconds to wait for AI response

# Anthropic Model (default: claude-3-haiku-20240307)
ANTHROPIC_MODEL=claude-3-haiku-20240307
```

## Course Configuration

Configure courses to monitor in `config/courses.yaml`:

### Basic Structure

```yaml
targets:
  - id: "unique_course_id"
    name: "Course Name"
    url: "https://app.testudo.umd.edu/soc/search?..."
    interval: 300  # Check interval in seconds (default: 300 = 5 minutes)
    enabled: true  # Enable/disable monitoring for this course
```

### Example Configuration

```yaml
targets:
  - id: "cmsc216_spring26"
    name: "CMSC216 (Kauffman)"
    url: "https://app.testudo.umd.edu/soc/search?courseId=CMSC216&sectionId=&termId=202601&_openSectionsOnly=on&creditCompare=%3E%3D&credits=0.0&courseLevelFilter=ALL&instructor=Kauffman%2C+Christopher&_facetoface=on&_blended=on&_online=on"
    interval: 300
    enabled: true

  - id: "cmsc330_fall26"
    name: "CMSC330"
    url: "https://app.testudo.umd.edu/soc/search?courseId=CMSC330&termId=202601"
    interval: 600  # Check every 10 minutes
    enabled: true
```

### Field Descriptions

- **`id`** (required): Unique identifier for the course (used in logs)
- **`name`** (required): Display name for the course (used in SMS alerts)
- **`url`** (required): Full Testudo URL with all filters applied
  - Must include query parameters for course, term, instructor, etc.
  - Use the exact URL from Testudo's search results
- **`interval`** (optional): Check interval in seconds
  - Default: 300 (5 minutes)
  - Minimum recommended: 60 seconds (to avoid rate limiting)
- **`enabled`** (optional): Whether to monitor this course
  - Default: `true`
  - Set to `false` to temporarily disable without deleting

## Getting Testudo URLs

1. Go to [Testudo Schedule of Classes](https://app.testudo.umd.edu/soc/)
2. Apply your filters:
   - Course ID (e.g., CMSC216)
   - Term (e.g., Spring 2026)
   - Instructor (e.g., Kauffman)
   - Other filters as needed
3. Copy the full URL from your browser's address bar
4. Paste it into the `url` field in `config/courses.yaml`

### URL Parameters

Common Testudo URL parameters:
- `courseId`: Course identifier (e.g., CMSC216)
- `termId`: Term identifier (e.g., 202601 for Spring 2026)
- `instructor`: Instructor name (URL-encoded)
- `_openSectionsOnly`: Filter to show only open sections
- `_facetoface`, `_blended`, `_online`: Delivery method filters

## Configuration Validation

The application validates configuration on startup:
- Missing required environment variables → Error on startup
- Invalid YAML syntax → Error on startup
- Missing `targets` key → Error on startup
- Invalid course URLs → Error during first check (logged)

## Best Practices

1. **Check Intervals:**
   - Use 300 seconds (5 minutes) for high-demand courses
   - Use 600+ seconds for less critical courses
   - Avoid intervals < 60 seconds (may trigger rate limiting)

2. **URL Configuration:**
   - Always use the full URL with all filters applied
   - Test the URL in a browser first to ensure it works
   - Include `_openSectionsOnly=on` if you only want open sections

3. **Multiple Courses:**
   - Each course runs independently with its own interval
   - No limit on number of courses (within reason)
   - Consider system resources if monitoring many courses

4. **Disabling Courses:**
   - Set `enabled: false` instead of deleting entries
   - Useful for temporary disabling or testing

## Troubleshooting

### Configuration Not Loading

- Check file path: `config/courses.yaml` relative to project root
- Validate YAML syntax (use online YAML validator)
- Check file permissions

### Environment Variables Not Found

- Ensure `.env` file exists in project root
- Check variable names match exactly (case-sensitive in some systems)
- Verify no extra spaces or quotes in `.env` file

### Invalid URLs

- Test URLs in browser first
- Ensure URLs are properly URL-encoded
- Check for typos in course IDs or term IDs

