"""SP-Today Currency Scraper."""

from __future__ import annotations

import asyncio

from apify import Actor, Event
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

from .routes import router


async def main() -> None:
    """Actor entry point."""
    async with Actor:
        async def on_aborting() -> None:
            await asyncio.sleep(1)
            await Actor.exit()

        Actor.on(Event.ABORTING, on_aborting)

        actor_input = await Actor.get_input() or {}
        start_url = actor_input.get('start_url', 'https://sp-today.com/en/currencies')

        Actor.log.info(f'Starting SP-Today currency scraper at: {start_url}')

        # Pre-navigation hook: inject stealth scripts before every page load
        # to remove signals that reveal headless Chromium to anti-bot systems.
        async def stealth_hook(context: PlaywrightCrawlingContext) -> None:
            await context.page.add_init_script("""
                // Remove navigator.webdriver flag (primary bot signal)
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

                // Spoof realistic plugin list
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                // Spoof realistic language list
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });

                // Make chrome object present (real Chrome has it, headless didn't used to)
                window.chrome = { runtime: {} };
            """)

        crawler = PlaywrightCrawler(
            max_requests_per_crawl=actor_input.get('max_requests_per_crawl', 100),
            request_handler=router,
            headless=True,
            # Disable automation flags at the Chromium level
            browser_launch_options={
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--window-size=1920,1080',
                    '--lang=en-US',
                ],
            },
            # Spoof a real desktop user-agent & viewport
            browser_new_context_options={
                'user_agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
                'viewport': {'width': 1920, 'height': 1080},
                'locale': 'en-US',
                'extra_http_headers': {
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': (
                        'text/html,application/xhtml+xml,application/xml;'
                        'q=0.9,image/avif,image/webp,*/*;q=0.8'
                    ),
                },
            },
            pre_navigation_hooks=[stealth_hook],
        )

        await crawler.run([start_url])

        Actor.log.info('Scraping finished.')
