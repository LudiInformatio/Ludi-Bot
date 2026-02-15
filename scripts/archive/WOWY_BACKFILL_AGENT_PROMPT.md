# WOWY Backfill Script - Agent Task Prompt

## Objective
Build a Ghost Protocol-based WOWY (With Or Without You) data backfill script that scrapes NBA.com lineup and on/off court stats, storing them in SQLite.

---

## Context & Validated Approach

We have **validated** that Ghost Protocol (Playwright browser scraping) works for NBA.com stats pages. Key findings:

1. **JSON API doesn't work** - Direct calls to `stats.nba.com` timeout/blocked
2. **Ghost Protocol WORKS** with these settings:
   - `headless=False` (visible browser required)
   - `--disable-http2` flag (forces HTTP/1.1)
   - Full anti-detection setup (webdriver hiding, user-agent spoofing)

**Tested successfully**: 25 lineups scraped in 4.75s from Jan 17, 2026.

---

## Files to Reference

### 1. Working Test Script (use this pattern)
```
scripts/test_wowy_hybrid.py
```
Contains the EXACT Playwright configuration that works.

### 2. Existing Ghost Protocol (DATA_MANIFEST pattern)
```
scripts/sync_browser_backfill.py
```
Shows the production pattern for:
- Date range iteration
- Multiple stat types via DATA_MANIFEST
- Table scraping with `scrape_table()`
- Player ID extraction from hrefs
- Pagination handling ("All" rows)
- Database upsert pattern

### 3. Database Schema
```
database.py
```
Contains table definitions. WOWY tables already created:
- `team_lineups` - 5-man lineup stats
- `player_on_off_stats` - Player on/off court splits

---

## URLs to Scrape

### Lineup Stats (5-man units)
```
https://www.nba.com/stats/lineups/advanced?DateFrom={MM/DD/YYYY}&DateTo={MM/DD/YYYY}&GroupQuantity=5&PerMode=Totals
```

### Player On/Off Stats
```
https://www.nba.com/stats/players/on-off-court?DateFrom={MM/DD/YYYY}&DateTo={MM/DD/YYYY}&PerMode=Totals
```

---

## Required Playwright Configuration (CRITICAL)

```python
browser = p.chromium.launch(
    headless=False,  # REQUIRED - visible browser
    args=[
        '--disable-blink-features=AutomationControlled',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-infobars',
        '--ignore-certificate-errors',
        '--ignore-ssl-errors',
        '--disable-http2'  # REQUIRED - forces HTTP/1.1
    ]
)
context = browser.new_context(
    viewport={'width': 1366, 'height': 768},
    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ignore_https_errors=True,
    java_script_enabled=True
)
context.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
""")
```

---

## Database Tables (Already Created)

### team_lineups
```sql
CREATE TABLE IF NOT EXISTS team_lineups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    team_id TEXT,
    team_abbreviation TEXT,
    lineup_players TEXT,  -- "Player1 - Player2 - Player3 - Player4 - Player5"
    games_played INTEGER,
    minutes REAL,
    off_rating REAL,
    def_rating REAL,
    net_rating REAL,
    pace REAL,
    ts_pct REAL,
    efg_pct REAL,
    plus_minus REAL,
    UNIQUE(game_date, team_abbreviation, lineup_players)
);
```

### player_on_off_stats
```sql
CREATE TABLE IF NOT EXISTS player_on_off_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_date TEXT NOT NULL,
    player_id TEXT,
    player_name TEXT,
    team_abbreviation TEXT,
    court_status TEXT,  -- 'On' or 'Off'
    games_played INTEGER,
    minutes REAL,
    off_rating REAL,
    def_rating REAL,
    net_rating REAL,
    plus_minus REAL,
    UNIQUE(game_date, player_id, court_status)
);
```

---

## Script Requirements

### 1. File Location
```
scripts/sync_wowy_backfill.py
```

### 2. Command Line Interface
```bash
# Backfill last 60 days (DEFAULT)
python scripts/sync_wowy_backfill.py --days 60

# Or explicit date range
python scripts/sync_wowy_backfill.py --start-date 2025-11-19 --end-date 2026-01-17

# Single day test
python scripts/sync_wowy_backfill.py --date 2026-01-17
```

### 3. Features Required
- [ ] Date range iteration (like sync_browser_backfill.py)
- [ ] Scrape both lineup stats AND on/off stats per day
- [ ] Handle pagination (click "All" to show all rows)
- [ ] Extract player IDs from href links where available
- [ ] Upsert pattern (INSERT OR REPLACE)
- [ ] Progress logging with date and record counts
- [ ] Rate limiting (2-4 second delay between pages)
- [ ] Error handling with retries (3 attempts per page)
- [ ] Skip days that already have data (optional --force flag)

### 4. DATA_MANIFEST Pattern
```python
WOWY_MANIFEST = {
    "lineups": {
        "url": "https://www.nba.com/stats/lineups/advanced?DateFrom={date}&DateTo={date}&GroupQuantity=5&PerMode=Totals",
        "table": "team_lineups",
        "label": "5-Man Lineups",
        "col_map": {
            "LINEUP": "lineup_players",
            "TEAM": "team_abbreviation", 
            "GP": "games_played",
            "MIN": "minutes",
            "OFF RTG": "off_rating",
            "DEF RTG": "def_rating",
            "NET RTG": "net_rating",
            "PACE": "pace",
            "TS%": "ts_pct",
            "eFG%": "efg_pct",
            "+/-": "plus_minus"
        }
    },
    "on_off": {
        "url": "https://www.nba.com/stats/players/on-off-court?DateFrom={date}&DateTo={date}&PerMode=Totals",
        "table": "player_on_off_stats",
        "label": "Player On/Off",
        "col_map": {
            "PLAYER": "player_name",
            "TEAM": "team_abbreviation",
            "COURT STATUS": "court_status",  # May need special handling
            "GP": "games_played",
            "MIN": "minutes",
            "OFF RTG": "off_rating",
            "DEF RTG": "def_rating",
            "NET RTG": "net_rating",
            "+/-": "plus_minus"
        }
    }
}
```

---

## Expected Output

```
============================================================
👻 WOWY GHOST PROTOCOL BACKFILL
📅 Range: 2025-11-19 -> 2026-01-17 (60 days)
============================================================

[2025-11-19] Processing...
   ✓ 5-Man Lineups: 42 records
   ✓ Player On/Off: 156 records

[2025-11-20] Processing...
   ✓ 5-Man Lineups: 38 records
   ✓ Player On/Off: 148 records

...

============================================================
✅ WOWY Backfill Complete
   Total Days: 60
   Lineups: ~2,400 records
   On/Off: ~9,360 records
============================================================
```

---

## Testing

After creating the script, test with:
```bash
# Single day test
python scripts/sync_wowy_backfill.py --date 2026-01-17

# Verify data
sqlite3 ludi.db "SELECT COUNT(*) FROM team_lineups WHERE game_date = '2026-01-17';"
sqlite3 ludi.db "SELECT COUNT(*) FROM player_on_off_stats WHERE game_date = '2026-01-17';"
```

---

## Notes

1. **Browser will be visible** - This is required for NBA.com to work
2. **Takes ~5-10 seconds per page** - Budget accordingly for full backfill
3. **No parallel execution** - One page at a time to avoid detection
4. **Backfill start**: 2025-11-19 (60 days ago)
5. **Current date**: 2026-01-18
6. **Total days**: 60

---

## Success Criteria

1. Script runs without errors for a single day
2. Data correctly inserted into both tables
3. Handles missing data gracefully (some days may have no games)
4. Progress visible in terminal
5. Can resume interrupted backfill (skips existing dates)
