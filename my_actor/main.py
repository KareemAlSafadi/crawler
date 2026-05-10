"""SP-Today Currency Scraper.

Scrapes all currency exchange rates against the Syrian Pound from
https://sp-today.com/en/currencies, then visits each currency detail page
to collect the full set of available data fields.
"""

from __future__ import annotations

import asyncio

from apify import Actor, Event
from crawlee.crawlers import PlaywrightCrawler

from .routes import router


async def main() -> None:
    """Actor entry point."""
    async with Actor:
        # Graceful abort handler
        async def on_aborting() -> None:
            await asyncio.sleep(1)
            await Actor.exit()

        Actor.on(Event.ABORTING, on_aborting)

        # Actor input – we hard-code the target URL but let the user override it.
        actor_input = await Actor.get_input() or {}
        start_url = actor_input.get('start_url', 'https://sp-today.com/en/currencies')

        Actor.log.info(f'Starting SP-Today currency scraper at: {start_url}')

        crawler = PlaywrightCrawler(
            # We visit the list page + one detail page per currency (~30 requests).
            max_requests_per_crawl=actor_input.get('max_requests_per_crawl', 100),
            request_handler=router,
            headless=True,
        )

        await crawler.run([start_url])

        Actor.log.info('Scraping finished.')
