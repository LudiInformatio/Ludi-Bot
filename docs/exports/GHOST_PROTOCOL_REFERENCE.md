# Ghost Protocol: Browser-Based Web Scraping with Playwright

A reference guide for building a stealth browser automation system that scrapes data from JavaScript-heavy websites protected by Web Application Firewalls (WAFs).

---

## Overview

Ghost Protocol is a Playwright-based scraping engine designed to extract structured data from NBA.com's stats pages — a site protected by aggressive bot detection (WAF, Akamai, cookie consent walls). The system mimics human browsing behavior to avoid detection and extracts HTML table data into a SQLite database.

**Key Design Principles:**
- "Human Ghost" stealth mode — browser fingerprint masking + simulated human behavior
- Manifest-driven architecture — a single config dict defines all scrape targets
- Resilient by default — retries, popup dismissal, pagination handling, gap-fill detection
- ID resolution firewall — ensures scraped data maps to canonical entity IDs before DB writes

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  DATA_MANIFEST (config dict)                    │
│  Defines: URL templates, column mappings,       │
│  target DB tables, and data types               │
├─────────────────────────────────────────────────┤
│                                                 │
│  Ghost Protocol Main Loop                       │
│  ┌─────────────────────────────────────┐        │
│  │ For each date in date_list:         │        │
│  │   For each manifest entry:          │        │
│  │     1. Build URL from template      │        │
│  │     2. Navigate (stealth browser)   │        │
│  │     3. Close popups / consent walls │        │
│  │     4. Handle pagination ("All")    │        │
│  │     5. Scrape HTML table            │        │
│  │     6. Resolve entity IDs           │        │
│  │     7. Upsert to SQLite             │        │
│  │     8. Human-like pause (3-6s)      │        │
│  └─────────────────────────────────────┘        │
│                                                 │
├─────────────────────────────────────────────────┤
│  Supporting Systems                             │
│  - browser_utils.py (stealth + popup handling)  │
│  - ID resolution firewall (entity normalization)│
│  - Gap-fill detection (smart re-scrape logic)   │
│  - GitHub Actions scheduler (cron triggers)     │
└─────────────────────────────────────────────────┘
```

---

## 1. Stealth Browser Setup

The core challenge: sites like NBA.com use WAF/bot detection that blocks headless Chromium. Ghost Protocol defeats this with multiple layers.

### Browser Launch Configuration

```python
from playwright.sync_api import sync_playwright

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ...",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 ...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.1; rv:109.0) Gecko/20100101 Firefox/119.0"
]

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,  # Visible browser bypasses more WAFs
        args=[
            '--disable-blink-features=AutomationControlled',  # Hide automation flag
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-infobars',                             # No "Chrome is being controlled" bar
            '--window-position=0,0',
            '--ignore-certificate-errors',
            '--ignore-ssl-errors',
            '--disable-extensions',
            '--disable-popup-blocking',
            '--disable-http2'  # Force HTTP/1.1 to avoid protocol errors
        ]
    )

    context = browser.new_context(
        user_agent=random.choice(USER_AGENTS),   # Randomize per session
        viewport={'width': 1920, 'height': 1080},
        ignore_https_errors=True,
        java_script_enabled=True,
        locale='en-US',
        timezone_id='America/New_York'
    )
```

### JavaScript Stealth Injection

Injected before any page loads to mask Playwright's fingerprint:

```python
context.add_init_script("""
    // Hide webdriver flag (most common detection vector)
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    // Set realistic language preferences
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en']
    });
    // Fake plugins array (headless Chrome has 0 plugins)
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });
    // Add chrome.runtime (missing in Playwright)
    window.chrome = { runtime: {} };
""")
```

### Key Insight: Headless vs Visible

On a self-hosted runner (local machine), **always use visible browser mode** (`headless=False`). NBA.com's WAF is significantly more aggressive against headless Chromium. The tradeoff is that the machine needs a display (real or virtual via `Xvfb`).

```python
is_self_hosted = os.environ.get('IS_SELF_HOSTED') == 'true'
headless_mode = False if is_self_hosted else headless
```

---

## 2. Human Behavior Simulation

Two layers work together to avoid detection.

### Mouse Movements + Scrolling

Simulates a human "reading" the page. This also triggers lazy-loaded elements that only render after scroll/interaction.

```python
def simulate_human_interaction(page):
    """Random mouse movements + scrolling to mimic human browsing."""
    try:
        # Random mouse movements (2-4 movements per call)
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 1000)
            y = random.randint(100, 800)
            page.mouse.move(x, y, steps=5)  # steps=5 makes it gradual
            time.sleep(random.uniform(0.1, 0.3))

        # Random scroll down
        page.mouse.wheel(0, random.randint(300, 700))
        time.sleep(random.uniform(0.5, 1.0))

        # Sometimes scroll back up (30% chance) — humans don't always scroll one direction
        if random.random() > 0.7:
            page.mouse.wheel(0, -random.randint(100, 300))
            time.sleep(random.uniform(0.2, 0.5))
    except Exception:
        pass  # Never let interaction errors break the scrape
```

### Inter-Page Delays

Between each page navigation, insert a random human-like pause:

```python
# Between different data categories on the same date
time.sleep(random.uniform(3.0, 6.0))

# Between distance range sub-pages (shorter, same-page context)
time.sleep(random.uniform(2.0, 4.0))
```

---

## 3. Popup & Consent Wall Handling

Modern sites throw cookie banners, newsletter signups, and modal overlays that block DOM access. Ghost Protocol dismisses them proactively.

```python
def close_popups(page):
    """Checks for and closes common popups/consent walls."""
    # 1. Generic consent/accept buttons (text-based matching)
    for sel in [
        'button:has-text("Accept")',
        'button:has-text("I Accept")',
        'button:has-text("Agree")',
        '[id*="consent"] button',
        '[class*="consent"] button',
    ]:
        try:
            if page.is_visible(sel, timeout=2000):
                page.click(sel, timeout=3000)
                page.wait_for_timeout(1000)
                break
        except Exception:
            continue

    # 2. OneTrust cookie banners (industry standard, used by NBA.com)
    for sel in [
        "#onetrust-accept-btn-handler",
        "#onetrust-reject-all-handler",
        ".onetrust-close-btn-handler"
    ]:
        try:
            if page.is_visible(sel, timeout=1000):
                page.click(sel, timeout=2000)
                time.sleep(1)
                break
        except Exception:
            continue

    # 3. Generic close buttons (modals, newsletters, overlays)
    close_selectors = [
        ".close-button", "button.close", "[aria-label='Close']",
        ".modal-close", "button[class*='close']",
        "[data-testid='modal-close']",
        # Site-specific selectors
        ".os-react-modal-close",  # OddsShark
        "[class*='newsletter'] button[class*='close']",
    ]
    for sel in close_selectors:
        try:
            if page.is_visible(sel, timeout=500):
                page.click(sel, timeout=1000)
                time.sleep(0.5)
        except Exception:
            continue
```

Also register a JS dialog handler to auto-dismiss `alert()`/`confirm()` calls that would otherwise hang Playwright:

```python
page.on('dialog', lambda dialog: dialog.accept())
```

---

## 4. Manifest-Driven Scraping

Instead of writing separate scraping logic per data source, define a **DATA_MANIFEST** — a single dict that maps data categories to URLs, column mappings, and target DB tables.

### The Manifest Pattern

```python
DATA_MANIFEST = {
    "drives": {
        "url": "https://www.nba.com/stats/players/drives?DateFrom={date}&DateTo={date}",
        "type": "tracking",          # Determines target DB table
        "label": "Drives",           # Human-readable label for logs
        "col_map": {                 # HTML column header -> DB column name
            "FGA": "drives_fga",
            "FGM": "drives_fgm",
            "PTS": "drives_pts",
            "PASS%": "drives_pass_pct"
        }
    },
    "catch_shoot": {
        "url": "https://www.nba.com/stats/players/catch-shoot?DateFrom={date}&DateTo={date}",
        "type": "tracking",
        "label": "Catch & Shoot",
        "col_map": {
            "FGA": "catch_shoot_fga",
            "FGM": "catch_shoot_fgm",
            "3PA": "catch_shoot_3pa",
            "3PM": "catch_shoot_3pm"
        }
    },
    "advanced": {
        "url": "https://www.nba.com/stats/players/advanced?DateFrom={date}&DateTo={date}",
        "type": "advanced",
        "label": "Advanced Stats",
        "col_map": {
            "OFFRTG": "off_rating",
            "DEFRTG": "def_rating",
            "USG%": "usg_pct",
            "PACE": "pace",
            "TS%": "ts_pct",
            # ... more columns
        }
    },
    "clutch": {
        "url": "https://www.nba.com/stats/players/clutch-traditional?DateFrom={date}&DateTo={date}&PerMode=Totals",
        "type": "clutch",
        "label": "Clutch Traditional",
        "col_map": {
            "MIN": "clutch_min",
            "PTS": "clutch_pts",
            "FGM": "clutch_fgm",
            "FGA": "clutch_fga",
        }
    },
    # Special case: requires multi-page scraping (4 distance ranges)
    "closest_defender": {
        "url": "https://www.nba.com/stats/players/shots-closest-defender?DateFrom={date}&DateTo={date}",
        "type": "closest_defender",
        "label": "Closest Defender",
        "distance_ranges": [
            {"param": "0-2 Feet - Very Tight", "db_col": "very_tight_fga"},
            {"param": "2-4 Feet - Tight",      "db_col": "tight_fga"},
            {"param": "4-6 Feet - Open",        "db_col": "open_fga"},
            {"param": "6+ Feet - Wide Open",    "db_col": "wide_open_fga"}
        ],
        "col_map": { "FGA": "fga_value" }
    }
}
```

### Why This Pattern Works

1. **Adding new data sources** = adding a dict entry, not writing new functions
2. **Column mappings** decouple HTML headers from DB schema
3. **Type routing** maps to the correct DB table and processor
4. **URL templates** with `{date}` placeholders keep date logic centralized
5. **Special cases** (like closest_defender needing 4 sub-pages) are handled by dedicated processors while still being declared in the manifest

---

## 5. Generic Table Scraper

The core extraction function works on any HTML table using Playwright's `page.evaluate()` to run JavaScript in the browser context.

```python
def scrape_table(page, label):
    """Extract headers + rows from any HTML stats table."""
    # 1. Close any blocking popups
    close_popups(page)

    # 2. Simulate human attention (triggers lazy-loaded content)
    simulate_human_interaction(page)

    # 3. Wait for table to appear (with retries)
    table_found = False
    for attempt in range(3):
        try:
            page.wait_for_selector("[class*='Crom_table']", timeout=20000)
            table_found = True
            break
        except Exception:
            if attempt < 2:
                simulate_human_interaction(page)  # Trigger load
                page.wait_for_timeout(3000)

    if not table_found:
        return []

    # 4. Set pagination to "All" (show every row, not just page 1)
    handle_pagination(page, label)

    # 5. Extract headers via JavaScript
    headers = page.evaluate("""() => {
        const headerRows = Array.from(
            document.querySelectorAll("[class*='Crom_table'] thead tr")
        );
        if (headerRows.length === 0) return [];
        // Use LAST header row (handles multi-row headers)
        const lastRow = headerRows[headerRows.length - 1];
        return Array.from(lastRow.querySelectorAll('th'))
            .map(th => th.innerText.trim());
    }""")

    # 6. Extract rows + href (for entity ID extraction)
    rows = page.evaluate("""() => {
        const trs = Array.from(
            document.querySelectorAll("[class*='Crom_table'] tbody tr")
        );
        return trs.map(tr => {
            const tds = Array.from(tr.querySelectorAll('td'));
            const rowText = tds.map(td => td.innerText.trim());
            // Extract player profile link for ID resolution
            const anchor = tr.querySelector('td:first-child a');
            const href = anchor ? anchor.getAttribute('href') : '';
            return { 'data': rowText, 'href': href };
        });
    }""")

    return {'headers': headers, 'rows': rows}
```

### Pagination Handling

NBA.com tables paginate by default (25 rows per page). Ghost Protocol selects "All" to get every row in one pass.

```python
def handle_pagination(page, category_label=None):
    """Set table pagination to 'All' with retry logic."""
    select_selector = "[class*='Pagination_pageDropdown'] select"

    for attempt in range(3):
        select_element = page.locator(select_selector)
        is_disabled = select_element.get_attribute("disabled")

        if is_disabled is None:
            # Dropdown enabled — select "All" (value="-1")
            select_element.scroll_into_view_if_needed()
            page.select_option(select_selector, value="-1", timeout=10000)

            # Wait for table to re-render (slower tables need more time)
            slow_categories = ["Speed & Distance", "Opponent Stats", "Hustle Stats"]
            wait_ms = 4000 if category_label in slow_categories else 2000
            page.wait_for_timeout(wait_ms)
            return
        else:
            # Dropdown temporarily disabled during table load — retry
            close_popups(page)
            page.wait_for_timeout(3000)
```

---

## 6. Entity ID Resolution

Scraped data contains raw IDs (from profile URLs like `/stats/player/1630639/`). Before writing to the database, these must be resolved to canonical IDs to prevent duplicates.

```python
def extract_id_from_href(href):
    """Extract numeric ID from href like /stats/player/1630639/..."""
    parts = href.split('/')
    for part in parts:
        if part.isdigit() and len(part) > 4:
            return part
    return None

# Before every DB write:
raw_pid = extract_id_from_href(href)
player_name = normalize_name(player_name)  # "Lastname, Firstname" -> "Firstname Lastname"
canonical_id = id_firewall.resolve(raw_pid, player_name)
```

### The 4-Tier ID Firewall

1. **Tier 1 (Exact):** ID is already canonical format — pass through
2. **Tier 2 (Alias):** Check alias lookup tables for known mappings
3. **Tier 3 (Name):** Fuzzy name match + auto-register new alias
4. **Tier 4 (Fallback):** Log warning, return raw ID for manual review

This prevents "ID contamination" — different sources using different ID formats for the same entity.

---

## 7. Database Upsert Pattern

All writes use SQLite's `ON CONFLICT ... DO UPDATE` (upsert) pattern, so re-scraping the same date is safe and idempotent.

```python
sql = '''
    INSERT INTO player_game_tracking (
        nba_player_id, player_name, game_date, team_abbr,
        nba_game_id, synced_at, drives_fga, drives_fgm, drives_pts
    ) VALUES (?, ?, ?, ?, 'GHOST', CURRENT_TIMESTAMP, ?, ?, ?)
    ON CONFLICT(nba_player_id, game_date) DO UPDATE SET
        drives_fga = excluded.drives_fga,
        drives_fgm = excluded.drives_fgm,
        drives_pts = excluded.drives_pts,
        synced_at = CURRENT_TIMESTAMP
'''
```

**Key details:**
- `nba_game_id = 'GHOST'` — marks records as browser-scraped (vs API-sourced)
- `synced_at = CURRENT_TIMESTAMP` — always updated on re-scrape for data freshness tracking
- Unique constraint on `(nba_player_id, game_date)` — one row per player per date

---

## 8. Smart Gap-Fill Mode

Rather than re-scraping everything, Ghost Protocol can detect which dates have incomplete data and only re-scrape those.

```python
def find_gap_dates(lookback_days=14):
    """Query DB for dates with missing or incomplete tracking data."""
    rows = conn.execute("""
        SELECT
            cg.date AS game_date,
            COUNT(DISTINCT cg.canonical_game_id) AS games,
            COALESCE(t.total_rows, 0) AS tracking_rows,
            ROUND(SUM(CASE WHEN drives_fga > 0 THEN 1.0 ELSE 0 END)
                  / COUNT(*) * 100, 0) AS drives_pct,
            ROUND(SUM(CASE WHEN avg_speed_off > 0 THEN 1.0 ELSE 0 END)
                  / COUNT(*) * 100, 0) AS speed_pct
        FROM canonical_games cg
        LEFT JOIN (
            SELECT game_date, COUNT(*) AS total_rows, ...
            FROM player_game_tracking GROUP BY game_date
        ) t ON t.game_date = cg.date
        WHERE cg.date >= date('now', '-14 days')
          AND cg.date < date('now')
        GROUP BY cg.date
    """).fetchall()

    gap_dates = []
    for row in rows:
        if tracking_rows == 0:
            gap_dates.append((game_date, 'NO_DATA'))
        elif drives_pct < 40:
            gap_dates.append((game_date, 'LOW_DRIVES'))
        elif speed_pct < 70:
            gap_dates.append((game_date, 'LOW_SPEED'))

    return gap_dates
```

**Thresholds** are based on observed healthy baselines:
- Drives: ~65% of players should have data
- Speed: ~99% of players should have data
- Catch & Shoot: ~80% of players should have data

If a date falls below these thresholds, it's flagged for re-scrape.

---

## 9. Scheduling & Orchestration

Ghost Protocol runs on a cron schedule via GitHub Actions:

```yaml
on:
  schedule:
    # Sunday — weekly full sweep (last 7 days)
    - cron: '0 10 * * 0'
    # Thursday — smart gap-fill (only incomplete dates)
    - cron: '0 10 * * 4'

steps:
  - name: Install Playwright browsers
    run: .venv/bin/python -m playwright install chromium

  - name: Run Ghost Protocol sync
    timeout-minutes: 300  # 5-hour timeout for large sweeps
    run: |
      DAY_OF_WEEK=$(date +%u)
      if [ "$DAY_OF_WEEK" = "4" ]; then
        # Thursday: smart gap-fill
        python scripts/sync_browser_backfill.py --gap-fill --skip-advanced
      else
        # Sunday: full 7-day sweep
        python scripts/sync_browser_backfill.py --days 7 --skip-advanced
      fi
```

### CLI Options

```bash
# Sync yesterday only
python scripts/sync_browser_backfill.py --days 1

# Sync a specific date range
python scripts/sync_browser_backfill.py --start-date 2025-11-14 --end-date 2026-01-15

# Smart gap-fill (auto-detect incomplete dates, last 14 days)
python scripts/sync_browser_backfill.py --gap-fill

# Only sync closest defender data (4 distance ranges)
python scripts/sync_browser_backfill.py --days 3 --closest-only

# Skip advanced stats (if another source handles those)
python scripts/sync_browser_backfill.py --days 7 --skip-advanced
```

### Self-Hosted Runner Note

The workflow uses `caffeinate -i` (macOS) to prevent the machine from sleeping during long scrapes:

```bash
caffeinate -i python scripts/sync_browser_backfill.py --days 7
```

---

## 10. Multi-Page Scraping (Special Cases)

Some data requires scraping the same URL with different query parameters. Example: Closest Defender has 4 distance ranges, each a separate page.

```python
def process_closest_defender(page, date_str, nba_date):
    """Scrape 4 distance ranges and aggregate into shot difficulty columns."""
    distance_ranges = [
        {"param": "0-2 Feet - Very Tight", "db_col": "very_tight_fga"},
        {"param": "2-4 Feet - Tight",      "db_col": "tight_fga"},
        {"param": "4-6 Feet - Open",        "db_col": "open_fga"},
        {"param": "6+ Feet - Wide Open",    "db_col": "wide_open_fga"}
    ]

    # Accumulator: player_id -> {columns...}
    player_data = {}

    for range_config in distance_ranges:
        url = f"{base_url}&CloseDefDistRange={quote(range_config['param'])}"
        page.goto(url, wait_until='domcontentloaded', timeout=90000)
        data = scrape_table(page, f"Closest Defender ({range_config['param']})")

        for row in data['rows']:
            pid = resolve_id(row)
            if pid not in player_data:
                player_data[pid] = {col: 0 for col in all_cols}
            player_data[pid][range_config['db_col']] = int(fga_value)

        time.sleep(random.uniform(2.0, 4.0))  # Human-like delay between sub-pages

    # Derive computed columns
    for pid, pdata in player_data.items():
        pdata['contested_fga'] = pdata['very_tight_fga'] + pdata['tight_fga']

    # Batch upsert all accumulated data
    write_to_db(player_data)
```

---

## 11. Error Resilience Patterns

### Navigation Timeout Handling

Use `domcontentloaded` instead of `load` to avoid hanging on third-party scripts:

```python
page.goto(url, wait_until='domcontentloaded', timeout=90000)
```

### Table Load Retries

If the table doesn't appear, simulate interaction (to trigger lazy loading) and retry:

```python
for attempt in range(3):
    try:
        page.wait_for_selector("[class*='Crom_table']", timeout=20000)
        break
    except Exception:
        simulate_human_interaction(page)
        page.wait_for_timeout(3000)
```

### Row-Level Error Isolation

Individual row failures never crash the entire scrape:

```python
for row_obj in rows:
    try:
        # ... process row ...
        count += 1
    except Exception:
        continue  # Skip bad rows, keep going
```

### Graceful Degradation

If a category fails entirely, log it and move to the next:

```python
try:
    data = scrape_table(page, label)
    count = process_item(key, data, db_date)
    print(f"   OK {label}: {count} records")
except Exception as e:
    print(f"   FAIL {label}: {e}")
    # Don't abort — continue to next category
```

---

## 12. Adapting for Your Project

To adapt Ghost Protocol for a different website:

1. **Update `USER_AGENTS`** with current browser versions
2. **Update `close_popups()`** with the target site's popup selectors
3. **Create your `DATA_MANIFEST`** with the target site's URLs and table structures
4. **Update `scrape_table()`** CSS selectors to match the target site's table classes
5. **Implement your own ID resolution** if you need entity deduplication
6. **Set up your DB schema** with appropriate unique constraints for upserts
7. **Tune timing**: adjust `time.sleep()` ranges based on target site's rate limiting
8. **Test visible browser first** — only move to headless after confirming stealth works

### Checklist for New Sites

- [ ] Identify table CSS selectors (inspect the DOM)
- [ ] Map HTML column headers to your DB columns
- [ ] Identify pagination controls (select dropdown? next button? infinite scroll?)
- [ ] Catalog all popup/modal selectors that might block interaction
- [ ] Check if the site requires cookies/session state
- [ ] Test with `headless=False` first to see what the browser sees
- [ ] Add `caffeinate` (macOS) or equivalent for long-running scrapes

---

## Summary

| Component | Purpose |
|-----------|---------|
| Stealth browser args | Mask Playwright as regular Chrome |
| JS init script | Override `navigator.webdriver`, fake plugins |
| `simulate_human_interaction()` | Random mouse/scroll to trigger lazy content |
| `close_popups()` | Dismiss consent walls + modals |
| `DATA_MANIFEST` | Declarative config for all scrape targets |
| `scrape_table()` | Generic HTML table extraction via `page.evaluate()` |
| `handle_pagination()` | Force "Show All" rows in paginated tables |
| `extract_id_from_href()` | Pull entity IDs from profile links |
| ID Firewall (4-tier) | Resolve raw IDs to canonical format |
| `ON CONFLICT DO UPDATE` | Idempotent upserts for safe re-scraping |
| `find_gap_dates()` | Smart detection of incomplete data |
| GitHub Actions cron | Sunday sweep + Thursday gap-fill |
