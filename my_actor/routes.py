"""Request handlers for the SP-Today currency scraper."""

from __future__ import annotations

import re

from apify import Actor
from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router

router: Router[PlaywrightCrawlingContext] = Router()

BASE_URL = 'https://sp-today.com'
LIST_LABEL = 'CURRENCY_LIST'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STEALTH_JS = """
    // Remove the primary headless-browser signal
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    // Spoof a non-empty plugin list (headless Chrome has 0 plugins)
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    // Spoof realistic language list
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    // Inject the chrome runtime object that real Chrome exposes
    if (!window.chrome) window.chrome = { runtime: {} };
"""


async def _apply_stealth(context: PlaywrightCrawlingContext) -> None:
    """Patch bot-detection signals on the already-loaded page via evaluate().

    Note: evaluate() runs in the current page context AFTER navigation.
    It cannot affect what the server already sent, but it removes signals
    that anti-bot JS on the page might read after initial load.
    """
    try:
        await context.page.evaluate(_STEALTH_JS)
    except Exception as exc:  # noqa: BLE001
        Actor.log.debug(f'Stealth JS injection skipped: {exc}')


def _clean(text: str | None) -> str:
    """Strip whitespace from a text value."""
    return text.strip() if text else ''


def _parse_number(text: str | None) -> float | None:
    """Convert a formatted number string (e.g. '13,370') to float."""
    if not text:
        return None
    cleaned = re.sub(r'[^\d.]', '', text.strip())
    try:
        return float(cleaned)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# List page handler  →  https://sp-today.com/en/currencies
# ---------------------------------------------------------------------------

@router.handler(LIST_LABEL)
async def list_handler(context: PlaywrightCrawlingContext) -> None:
    """Scrape the main currency list and enqueue each detail page."""
    url = context.request.url
    Actor.log.info(f'Scraping currency list: {url}')

    page = context.page

    # Patch any in-page bot-detection scripts that run after initial load.
    await _apply_stealth(context)

    # Wait for the table rows to be rendered by React.
    await page.wait_for_selector('tbody tr', timeout=30_000)

    rows = await page.query_selector_all('tbody tr')
    Actor.log.info(f'Found {len(rows)} currency rows on the list page.')

    for row in rows:
        # --- Currency code & name ---
        code_el = await row.query_selector('td:nth-child(1) span.font-bold')
        name_el = await row.query_selector('td:nth-child(1) span.text-xs')
        code = _clean(await code_el.inner_text() if code_el else None)
        name = _clean(await name_el.inner_text() if name_el else None)

        # --- Buy / Sell ---
        buy_el  = await row.query_selector('td:nth-child(2)')
        sell_el = await row.query_selector('td:nth-child(3)')
        buy_raw  = _clean(await buy_el.inner_text()  if buy_el  else None)
        sell_raw = _clean(await sell_el.inner_text() if sell_el else None)

        # --- Change % ---
        change_el = await row.query_selector('td:nth-child(4)')
        change_raw = _clean(await change_el.inner_text() if change_el else None)
        # Determine direction from colour class
        change_pos_el = await row.query_selector('td:nth-child(4) span.text-emerald-500')
        change_neg_el = await row.query_selector('td:nth-child(4) span.text-red-500')
        change_direction = 'up' if change_pos_el else ('down' if change_neg_el else 'neutral')

        # --- Day high / low ---
        high_el = await row.query_selector('td:nth-child(5)')
        low_el  = await row.query_selector('td:nth-child(6)')
        high_raw = _clean(await high_el.inner_text() if high_el else None)
        low_raw  = _clean(await low_el.inner_text()  if low_el  else None)

        # --- Detail link ---
        link_el = await row.query_selector('td:nth-child(1) a')
        href = await link_el.get_attribute('href') if link_el else None
        detail_url = f"{BASE_URL}{href}" if href and href.startswith('/') else href

        # Build the base record that will be merged with detail-page data.
        list_data = {
            'code': code,
            'name': name,
            'buy_price': _parse_number(buy_raw),
            'sell_price': _parse_number(sell_raw),
            'buy_price_raw': buy_raw,
            'sell_price_raw': sell_raw,
            'change_percent': change_raw,
            'change_direction': change_direction,
            'day_high': _parse_number(high_raw),
            'day_low': _parse_number(low_raw),
            'day_high_raw': high_raw,
            'day_low_raw': low_raw,
            'detail_url': detail_url,
            'source_url': url,
        }

        # Push what we have immediately.
        await context.push_data(list_data)


# ---------------------------------------------------------------------------
# Default handler  →  catches the first request (list page) if no label set
# ---------------------------------------------------------------------------

@router.default_handler
async def default_handler(context: PlaywrightCrawlingContext) -> None:
    """Route the initial un-labelled request to the list handler."""
    # NOTE: context.request.label is read-only in Crawlee 1.6+ (frozen Pydantic model).
    # We simply delegate directly to list_handler instead of re-labelling.
    await list_handler(context)
