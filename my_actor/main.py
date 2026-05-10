"""SP-Today Currency Scraper."""

from __future__ import annotations

import asyncio

from apify import Actor, Event
from crawlee.crawlers import PlaywrightCrawler

from .routes import router

# Realistic desktop Chrome UA (avoids "HeadlessChrome" detection)
_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)


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

        # Build optional Apify proxy configuration (honours the proxy_configuration
        # field from the Actor input if the user has enabled it).
        proxy_configuration = None
        proxy_input = actor_input.get('proxy_configuration')
        if proxy_input:
            proxy_configuration = await Actor.create_proxy_configuration(
                actor_proxy_input=proxy_input,
            )

        crawler = PlaywrightCrawler(
            max_requests_per_crawl=actor_input.get('max_requests_per_crawl', 100),
            request_handler=router,
            headless=True,
            # Pass proxy through crawlee's built-in proxy support
            proxy_configuration=proxy_configuration,
            # browser_launch_options: valid PlaywrightCrawler param in crawlee 1.6.x
            browser_launch_options={
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    # Remove navigator.webdriver=true at the Chromium engine level
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars',
                    '--window-size=1920,1080',
                    '--lang=en-US',
                    # Spoof a real Windows/Chrome user-agent string
                    f'--user-agent={_USER_AGENT}',
                ],
            },
        )

        await crawler.run([start_url])

        Actor.log.info('Scraping finished.')
