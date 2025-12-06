#!/bin/bash

# Start script for Testudo Crawler Web Service
# This script activates the virtual environment and starts the web service

set -e  # Exit on error

echo "Starting Testudo Crawler Web Service..."
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please run 'python -m venv venv' first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Get port from environment variable or use default
PORT=${PORT:-8000}

echo "✓ Virtual environment activated"
echo "✓ Starting web service on port $PORT"
echo ""
echo "Access the service at:"
echo "  http://localhost:$PORT/"
echo "  http://localhost:$PORT/health"
echo "  http://localhost:$PORT/ping"
echo "  http://localhost:$PORT/docs (API documentation)"
echo ""
echo "Press Ctrl+C to stop the service"
echo ""

# Start the web service with uvicorn
python -m uvicorn app.web:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --reload \
    --log-level info
