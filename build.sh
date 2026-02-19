#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "=========================================="
echo "Building Testudo Crawler for Render"
echo "=========================================="

# 1. Upgrade pip
echo "Step 1/4: Upgrading pip..."
pip install --upgrade pip

# 2. Install Python dependencies
echo "Step 2/4: Installing Python packages..."
pip install -r requirements.txt

# 3. Install Playwright browsers with system dependencies
echo "Step 3/4: Installing Playwright Chromium with system dependencies..."
python -m playwright install chromium --with-deps

# 4. Verify installation
echo "Step 4/4: Verifying Playwright installation..."
python -m playwright install --check-success chromium 2>/dev/null || python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

echo "=========================================="
echo "Build completed successfully!"
echo "=========================================="
