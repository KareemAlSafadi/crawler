"""Request handlers for the SP-Today currency scraper."""

from __future__ import annotations

import re

from apify import Actor
from crawlee.crawlers import PlaywrightCrawlingContext
from crawlee.router import Router

router: Router[PlaywrightCrawlingContext] = Router()

BASE_URL = 'https://sp-today.com'
LIST_LABEL = 'CURRENCY_LIST'
DETAIL_LABEL = 'CURRENCY_DETAIL'


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

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

        if detail_url:
            # Enqueue the detail page; pass the list_data as user_data.
            await context.add_requests([
                {
                    'url': detail_url,
                    'label': DETAIL_LABEL,
                    'user_data': {'list_data': list_data},
                }
            ])
        else:
            # No detail link – push what we have immediately.
            Actor.log.warning(f'No detail URL for {code}, pushing list data only.')
            await context.push_data(list_data)


# ---------------------------------------------------------------------------
# Detail page handler  →  https://sp-today.com/en/currency/<slug>
# ---------------------------------------------------------------------------

@router.handler(DETAIL_LABEL)
async def detail_handler(context: PlaywrightCrawlingContext) -> None:
    """Scrape a single currency detail page and push the merged record."""
    url = context.request.url
    list_data: dict = context.request.user_data.get('list_data', {})
    code = list_data.get('code', url)

    Actor.log.info(f'Scraping detail page for {code}: {url}')

    page = context.page

    # Wait for the stat cards / info block to appear.
    try:
        await page.wait_for_selector('h1', timeout=30_000)
    except Exception:
        Actor.log.warning(f'Timeout waiting for detail page content for {code}.')

    # --- Helper to get text by a label ---
    async def get_stat(label_text: str) -> str | None:
        """Find a value cell that sits next to a label matching label_text."""
        # The detail page uses <dt>/<dd> or adjacent sibling patterns.
        # Try multiple common patterns.

        # Pattern 1: <div> containing a <p> label and <p> value
        elements = await page.query_selector_all('div.flex.flex-col, div.grid > div')
        for el in elements:
            txt = await el.inner_text()
            if label_text.lower() in txt.lower():
                # The value is usually the second line / second child.
                lines = [l.strip() for l in txt.splitlines() if l.strip()]
                for i, line in enumerate(lines):
                    if label_text.lower() in line.lower() and i + 1 < len(lines):
                        return lines[i + 1]

        # Pattern 2: generic text search among all <p>/<span> siblings
        labels = await page.query_selector_all('p, span, dt, td')
        for lbl in labels:
            lbl_txt = _clean(await lbl.inner_text())
            if lbl_txt.lower() == label_text.lower():
                # Try next sibling
                sibling = await page.evaluate(
                    """(el) => {
                        let sib = el.nextElementSibling;
                        return sib ? sib.innerText : null;
                    }""",
                    lbl,
                )
                if sibling:
                    return _clean(sibling)
        return None

    # --- Scrape detail stats ---
    # Grab all visible text from the stats section; look for known labels.
    stats_text = ''
    stats_container = await page.query_selector('main, article, [class*="container"]')
    if stats_container:
        stats_text = await stats_container.inner_text()

    # Use regex extraction as a robust fallback.
    def extract_after(label: str, text: str) -> str | None:
        pattern = rf'{re.escape(label)}\s*\n?\s*([^\n]+)'
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    previous_close_raw = extract_after('Previous Close', stats_text)
    last_update_raw    = extract_after('Last Update', stats_text) or extract_after('Updated', stats_text)
    open_price_raw     = extract_after('Open', stats_text)
    avg_price_raw      = extract_after('Average', stats_text)

    # --- History table ---
    history: list[dict] = []
    history_rows = await page.query_selector_all('table tbody tr')
    for hr in history_rows:
        cells = await hr.query_selector_all('td')
        if len(cells) >= 2:
            period_el = cells[0]
            rate_el   = cells[1]
            period = _clean(await period_el.inner_text())
            rate   = _clean(await rate_el.inner_text())
            if period and rate:
                history.append({'period': period, 'rate_raw': rate, 'rate': _parse_number(rate)})

    # --- City-specific rates ---
    city_rates: list[dict] = []
    city_rows = await page.query_selector_all('[class*="city"] tr, [class*="cities"] tr')
    for cr in city_rows:
        cells = await cr.query_selector_all('td')
        if len(cells) >= 3:
            city    = _clean(await cells[0].inner_text())
            c_buy   = _clean(await cells[1].inner_text())
            c_sell  = _clean(await cells[2].inner_text())
            if city:
                city_rates.append({
                    'city': city,
                    'buy_raw': c_buy,
                    'sell_raw': c_sell,
                    'buy': _parse_number(c_buy),
                    'sell': _parse_number(c_sell),
                })

    detail_data = {
        'previous_close': _parse_number(previous_close_raw),
        'previous_close_raw': previous_close_raw,
        'open_price': _parse_number(open_price_raw),
        'open_price_raw': open_price_raw,
        'average_price': _parse_number(avg_price_raw),
        'average_price_raw': avg_price_raw,
        'last_update': last_update_raw,
        'price_history': history,
        'city_rates': city_rates,
    }

    # Merge list data + detail data and push.
    record = {**list_data, **detail_data}
    await context.push_data(record)
    Actor.log.info(f'Pushed record for {code} ({list_data.get("name", "")})')


# ---------------------------------------------------------------------------
# Default handler  →  catches the first request (list page) if no label set
# ---------------------------------------------------------------------------

@router.default_handler
async def default_handler(context: PlaywrightCrawlingContext) -> None:
    """Route the initial un-labelled request to the list handler."""
    # NOTE: context.request.label is read-only in Crawlee 1.6+ (frozen Pydantic model).
    # We simply delegate directly to list_handler instead of re-labelling.
    await list_handler(context)
