# SP-Today Currency Exchange Rate Scraper

Scrapes **live currency exchange rates against the Syrian Pound** from [sp-today.com/en/currencies](https://sp-today.com/en/currencies).

For every currency listed on the site the Actor collects data from both the main list page **and** the individual currency detail page, giving you a comprehensive JSON record per currency.

---

## What does SP-Today Currency Scraper do?

This Actor navigates to the SP-Today currency list, reads all listed currencies (USD, EUR, TRY, SAR, AED, GBP, and ~25 more), then visits each currency's dedicated detail page to gather the full set of available data including historical rates and city-specific exchange rates. The final output is pushed to an Apify dataset as structured JSON — ready to download, query, or pipe into other Actors and integrations.

---

## Why use SP-Today Currency Scraper?

- **Live data** – rates reflect what traders on the Syrian black/parallel market are paying right now.
- **Structured output** – every field is numeric where applicable so you can compute spreads, changes, and averages without extra parsing.
- **Comprehensive** – buy price, sell price, day high/low, previous close, open, average, change %, per-city rates, and historical rate tables.
- **Automated** – schedule the Actor to run hourly and you have a ready-made time-series of Syrian Pound exchange rates.

---

## How to use SP-Today Currency Scraper

1. Click **Try for free** on the Apify Store page.
2. Leave the default **Start URL** (`https://sp-today.com/en/currencies`) or change it if needed.
3. Optionally set **Max Requests Per Crawl** (default 100 is sufficient for all currencies).
4. Click **Start** and wait ~2–3 minutes.
5. Go to the **Output** tab to preview the dataset, or download it as JSON/CSV/Excel.

---

## Input

| Field | Type | Default | Description |
|---|---|---|---|
| `start_url` | string | `https://sp-today.com/en/currencies` | The SP-Today currencies list page |
| `max_requests_per_crawl` | integer | `100` | Safety cap on total page requests |
| `proxy_configuration` | object | disabled | Optional Apify proxy settings |

---

## Output

Each item in the dataset represents **one currency** and contains the following fields:

```json
{
  "code": "USD",
  "name": "US Dollar",
  "buy_price": 13370,
  "sell_price": 13380,
  "buy_price_raw": "13,370",
  "sell_price_raw": "13,380",
  "change_percent": "+0.15%",
  "change_direction": "up",
  "day_high": 13400,
  "day_low": 13300,
  "previous_close": 13350,
  "open_price": 13360,
  "average_price": 13365,
  "last_update": "10 May 2026, 14:30",
  "price_history": [
    { "period": "1 week ago", "rate_raw": "13,200", "rate": 13200 },
    { "period": "1 month ago", "rate_raw": "12,800", "rate": 12800 }
  ],
  "city_rates": [
    { "city": "Damascus", "buy_raw": "13,370", "sell_raw": "13,380", "buy": 13370, "sell": 13380 },
    { "city": "Aleppo",   "buy_raw": "13,360", "sell_raw": "13,375", "buy": 13360, "sell": 13375 }
  ],
  "detail_url": "https://sp-today.com/en/currency/us-dollar",
  "source_url": "https://sp-today.com/en/currencies"
}
```

You can download the dataset in various formats such as **JSON, HTML, CSV, or Excel** from the Storage tab.

---

## Data Fields

| Field | Format | Description |
|---|---|---|
| `code` | text | ISO currency code (e.g. `USD`) |
| `name` | text | Full currency name |
| `buy_price` | number | Buy rate in Syrian Pounds |
| `sell_price` | number | Sell rate in Syrian Pounds |
| `change_percent` | text | Percentage change vs previous close |
| `change_direction` | text | `up`, `down`, or `neutral` |
| `day_high` | number | Intraday high |
| `day_low` | number | Intraday low |
| `previous_close` | number | Previous closing rate |
| `open_price` | number | Opening rate of the day |
| `average_price` | number | Average rate |
| `last_update` | text | Timestamp of last rate update |
| `price_history` | array | Historical rates with period labels |
| `city_rates` | array | Per-city buy/sell rates |
| `detail_url` | link | Direct link to the currency detail page |

---

## Pricing / Cost Estimation

The Actor uses a **Playwright (browser) crawler** because sp-today.com renders its rates with JavaScript. Browser-based crawls consume more Compute Units than plain HTTP crawls.

- A full run scraping all ~30 currencies completes in roughly **2–3 minutes**.
- Estimated cost on the free tier: **< 0.5 CU per run**, well within the free monthly allowance.

---

## Tips

- **Scheduling**: Set up a scheduled run every hour to build a live exchange-rate time series.
- **Proxy**: If the site rate-limits requests, enable Apify Residential Proxy in the input.
- **Single currency**: To scrape only one currency, set `start_url` to its detail page (e.g. `https://sp-today.com/en/currency/us-dollar`) and the default handler will still route it correctly.

---

## FAQ & Disclaimer

**Is scraping sp-today.com legal?**
This Actor scrapes publicly available data for informational purposes. Always review the target website's Terms of Service before use. The author is not responsible for any misuse.

**The rates look stale – why?**
The site updates rates in real time. If your data looks old, check the `last_update` field; the site itself may not have published a new rate yet.

**Support / Bugs**
Open an issue in the **Issues** tab on the Apify Store page or contact us via the platform.
