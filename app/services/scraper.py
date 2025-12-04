"""
Web scraping service using Playwright for browser automation.
Handles page loading, text extraction, and retry logic.
"""

import asyncio
import logging
import re
from typing import Optional

from playwright.async_api import Browser, Page, async_playwright

logger = logging.getLogger(__name__)


class ScraperService:
    """Service for scraping university course pages using Playwright."""

    def __init__(self, timeout: int = 30):
        """
        Initialize scraper service.

        Args:
            timeout: Maximum time to wait for page loading (in seconds)
        """
        self.timeout = timeout * 1000  # Convert to milliseconds for Playwright
        self.browser: Optional[Browser] = None
        self._playwright = None

    async def initialize(self) -> None:
        """Initialize Playwright browser instance."""
        if self.browser is None:
            logger.info("Initializing Playwright browser...")
            self._playwright = await async_playwright().start()
            self.browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            logger.info("Playwright browser initialized successfully")

    async def close(self) -> None:
        """Close Playwright browser and cleanup resources."""
        if self.browser:
            logger.info("Closing Playwright browser...")
            await self.browser.close()
            self.browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            logger.info("Playwright browser closed successfully")

    async def scrape_page(
        self,
        url: str,
        max_retries: int = 3,
        wait_for_network_idle: bool = True,
    ) -> dict[str, str]:
        """
        Scrape a course page and extract text content.

        Args:
            url: URL of the course page to scrape
            max_retries: Maximum number of retry attempts on failure
            wait_for_network_idle: Whether to wait for network to be idle

        Returns:
            Dictionary with 'text' (page content) and 'title' (page title)

        Raises:
            Exception: If scraping fails after all retry attempts
        """
        if self.browser is None:
            await self.initialize()

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Scraping {url} (attempt {attempt}/{max_retries})")

                # Create new browser context for isolation
                context = await self.browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                )

                # Block unnecessary resources for faster loading
                await context.route(
                    "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot}",
                    lambda route: route.abort(),
                )

                page = await context.new_page()

                try:
                    # Navigate to URL with timeout
                    await page.goto(
                        url,
                        timeout=self.timeout,
                        wait_until="domcontentloaded",
                    )

                    # Wait for network to be idle if requested
                    if wait_for_network_idle:
                        try:
                            await page.wait_for_load_state(
                                "networkidle",
                                timeout=self.timeout,
                            )
                        except Exception as e:
                            logger.warning(
                                f"Network idle timeout (continuing anyway): {e}"
                            )

                    # Try to wait for specific selectors (per PRD)
                    # Fallback to networkidle if selectors not found
                    try:
                        await page.wait_for_selector(
                            ".course-sections, .section-id, [class*='section']",
                            timeout=5000,
                        )
                    except Exception:
                        # Selector not found, continue with body extraction
                        pass

                    # Extract text content from body (main container)
                    text_content = await page.inner_text("body")
                    page_title = await page.title()

                    # Clean text: strip excessive whitespace and newlines (per PRD)
                    # Join all whitespace sequences into single spaces
                    clean_content = re.sub(r"\s+", " ", text_content.strip())
                    text_content = clean_content

                    logger.info(
                        f"Successfully scraped {url} "
                        f"({len(text_content)} characters)"
                    )

                    return {
                        "text": text_content,
                        "title": page_title,
                        "url": url,
                    }

                finally:
                    # Always close the page and context
                    await page.close()
                    await context.close()

            except Exception as e:
                logger.error(f"Scraping attempt {attempt} failed for {url}: {e}")

                if attempt < max_retries:
                    # Exponential backoff: 2s, 4s, 8s
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"All {max_retries} scraping attempts failed for {url}"
                    )
                    raise

        # This should never be reached, but just in case
        raise Exception(f"Failed to scrape {url} after {max_retries} attempts")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
