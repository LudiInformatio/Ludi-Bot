#!/usr/bin/env python3
"""
LUDI INFORMATIO | GHOST PROTOCOL WOWY BACKFILL
==============================================
Browser-based synchronization of NBA.com Lineup and On/Off data.
Uses "Ghost Protocol" (Visible Playwright) to bypass WAF.

Scope:
- 5-Man Lineups (Advanced)
- Player On/Off Court Stats

Usage:
    python scripts/sync_wowy_backfill.py --days 60
    python scripts/sync_wowy_backfill.py --date 2026-01-17
"""

import sys
import os
import argparse
import sqlite3
import random
import time
import json
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH
from utils.browser_utils import simulate_human_interaction, close_popups, wait_for_selector_safe, setup_page

# Playwright check
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# ============================================================
# DATABASE SETUP
# ============================================================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")  # Retry for 30s on lock instead of failing immediately
    conn.row_factory = sqlite3.Row
    return conn

def ensure_tables_exist():
    """Creates WOWY tables if they don't exist (Self-Healing)."""
    conn = get_db_connection()
    c = conn.cursor()

    # 1. Team Lineups (5-Man)
    c.execute('''
        CREATE TABLE IF NOT EXISTS team_lineups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_date TEXT NOT NULL,
            team_id TEXT,
            team_abbreviation TEXT,
            lineup_players TEXT,
            games_played INTEGER,
            minutes REAL,
            off_rating REAL,
            def_rating REAL,
            net_rating REAL,
            pace REAL,
            ts_pct REAL,
            efg_pct REAL,
            plus_minus REAL,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            lineup_id TEXT,   -- PBP Stats GROUP_ID: dash-separated NBA player IDs
            UNIQUE(game_date, team_abbreviation, lineup_players)
        );
    ''')

    # 2. Player On/Off Stats
    c.execute('''
        CREATE TABLE IF NOT EXISTS player_on_off_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_date TEXT NOT NULL,
            player_id TEXT,
            player_name TEXT,
            team_abbreviation TEXT,
            court_status TEXT,
            games_played INTEGER,
            minutes REAL,
            off_rating REAL,
            def_rating REAL,
            net_rating REAL,
            plus_minus REAL,
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(game_date, player_id, court_status)
        );
    ''')
    
    conn.commit()
    conn.close()

# ============================================================
# DATA MANIFEST
# ============================================================

WOWY_MANIFEST = {
    "lineups": {
        "url": "https://www.nba.com/stats/lineups/advanced?DateFrom={date}&DateTo={date}&GroupQuantity=5&PerMode=Totals",
        "table": "team_lineups",
        "label": "5-Man Lineups",
        "col_map": {
            "LINEUPS": "lineup_players",  # Fixed: was LINEUP, actual is LINEUPS
            "TEAM": "team_abbreviation", 
            "GP": "games_played",
            "MIN": "minutes",
            "OFFRTG": "off_rating",
            "DEFRTG": "def_rating",
            "NETRTG": "net_rating",
            "PACE": "pace",
            "TS%": "ts_pct",
            "eFG%": "efg_pct",
            "+/-": "plus_minus"
        }
    }
    # NOTE: on_off page doesn't have standard table format, removed for now
}

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def format_date_nba(dt_obj):
    return dt_obj.strftime("%m/%d/%Y")

def format_date_db(dt_obj):
    return dt_obj.strftime("%Y-%m-%d")

# ============================================================
# SCRAPING LOGIC
# ============================================================

def handle_pagination(page, label=None):
    """Ensure all rows are visible by selecting 'All' in pagination dropdown."""
    try:
        close_popups(page)
        select_selector = "[class*='Pagination_pageDropdown'] select"
        if page.is_visible(select_selector):
            select_element = page.locator(select_selector)
            is_disabled = select_element.get_attribute("disabled")
            if is_disabled is None:
                select_element.scroll_into_view_if_needed()
                page.select_option(select_selector, value="-1", timeout=10000)
                page.wait_for_timeout(2500)
                print(f"      ✓ Pagination set to 'All'")
            else:
                print(f"      ⚠️  Pagination disabled (low-data day)")
    except Exception as e:
        print(f"      ⚠️  Pagination Error (Non-Critical): {e}")


def scrape_table(page, label):
    """Extract table data with centralized retry logic."""
    print(f"      Scanning {label} table...")

    # Clear popups and simulate human behavior
    close_popups(page)
    simulate_human_interaction(page)

    # Wait for table using existing utility function
    table_selector = "[class*='Crom_table'] tbody tr"
    if not wait_for_selector_safe(page, table_selector, timeout=30000, message=label):
        print(f"      ⚠️  Table not found for {label} (or no data).")
        return []

    # Handle pagination to show all rows
    handle_pagination(page, label)

    # Headers
    headers = page.evaluate("""() => {
        const ths = Array.from(document.querySelectorAll("[class*='Crom_table'] thead th"));
        return ths.map(th => th.innerText.trim());
    }""")
    # Normalize headers (remove non-breaking spaces, newlines)
    headers = [h.replace('\xa0', ' ').replace('\n', ' ') for h in headers]
    print(f"      [DEBUG] Headers: {headers[:10]}...")  # Debug: show first 10 headers
    
    # Rows with HREF extraction (for IDs)
    rows = page.evaluate("""() => {
        const trs = Array.from(document.querySelectorAll("[class*='Crom_table'] tbody tr"));
        return trs.map(tr => {
            const tds = Array.from(tr.querySelectorAll('td'));
            const rowText = tds.map(td => td.innerText.trim());
            // Try to find a link in the first few columns to get IDs
            const anchor = tr.querySelector('td a'); 
            const href = anchor ? anchor.getAttribute('href') : '';
            return { 'data': rowText, 'href': href };
        });
    }""")
    
    print(f"      [DEBUG] Found {len(rows)} rows for {label}")
    return {'headers': headers, 'rows': rows}

def extract_id_from_href(href):
    """Extracts numeric ID from href."""
    if not href: return None
    try:
        # /stats/team/1610612738/lineups... -> 1610612738
        # /stats/player/203999/... -> 203999
        parts = href.split('/')
        for part in parts:
            if part.isdigit() and len(part) > 3:
                return part
        return None
    except Exception:
        return None

def process_item(item_key, data, date_str):
    """Process scraped data into SQLite."""
    if not data or not data['rows']: return 0

    manifest = WOWY_MANIFEST[item_key]
    col_map = manifest['col_map']
    table_name = manifest['table']
    row_errors = 0
    
    headers = data['headers']
    rows = data['rows']
    
    # Map header names to indices
    header_idx = {}
    for i, h in enumerate(headers):
        # NBA.com headers vary slightly, normalize for mapping
        norm_h = h.upper().replace(' ', '') # e.g. "OFF RTG" -> "OFFRTG"
        header_idx[norm_h] = i
        header_idx[h] = i # Keep original too
        
    conn = get_db_connection()
    c = conn.cursor()
    count = 0
    
    for row_obj in rows:
        try:
            row_data = row_obj['data']
            href = row_obj['href']
            
            # Prepare values dict
            db_values = {}
            
            # Extract ID if possible
            extracted_id = extract_id_from_href(href)
            
            # Handle specific table logic
            if item_key == "lineups":
                # Don't add team_id - table uses lineup_id instead
                pass
            elif item_key == "on_off":
                if extracted_id: db_values['player_id'] = extracted_id
                
            # Map columns
            for csv_head, db_col in col_map.items():
                # Normalize csv_head for lookup
                lookup_keys = [csv_head, csv_head.upper().replace(' ', '')]
                
                found_idx = -1
                for key in lookup_keys:
                    if key in header_idx:
                        found_idx = header_idx[key]
                        break
                
                if found_idx != -1 and found_idx < len(row_data):
                    val_str = row_data[found_idx]
                    val = 0.0
                    if val_str and val_str != '-':
                        try:
                            val = float(val_str.replace('%', '').replace(',', ''))
                        except (ValueError, TypeError):
                            val = val_str # Keep as string if not float (e.g. Lineup names)
                    
                    db_values[db_col] = val
            
            # Add metadata
            db_values['game_date'] = date_str
            
            # Calculate possessions from pace and minutes (if available)
            if item_key == "lineups":
                pace = db_values.get('pace', 0)
                minutes = db_values.get('minutes', 0)
                if pace and minutes and pace > 0 and minutes > 0:
                    db_values['possessions'] = round(pace * minutes / 48.0)
            
            # Construct SQL
            cols = list(db_values.keys())
            placeholders = ['?'] * len(cols)
            vals = [db_values[c] for c in cols]
            
            col_str = ", ".join(cols)
            ph_str = ", ".join(placeholders)
            
            # Use simple INSERT OR IGNORE to avoid constraint errors
            # Existing data won't be overwritten
            sql = f'''
                INSERT OR IGNORE INTO {table_name} ({col_str})
                VALUES ({ph_str})
            '''
            
            c.execute(sql, vals)
            count += 1
            
        except Exception as e:
            row_errors += 1
            if row_errors <= 3:  # Only print first 3 to avoid log spam
                print(f"       Row Error: {e}")
            continue

    conn.commit()
    conn.close()
    total_rows = count + row_errors
    if row_errors > 0:
        print(f"      ⚠️  {row_errors}/{total_rows} rows failed to write")
    if total_rows > 0 and row_errors == total_rows:
        print(f"      ❌ ALL {total_rows} rows failed — database may be locked")
        sys.exit(1)
    return count

# ============================================================
# MAIN GHOST PROTOCOL LOOP
# ============================================================

def run_wowy_backfill(start_date, end_date, headless=False):
    print("\n" + "="*60)
    print("👻 WOWY GHOST PROTOCOL BACKFILL")
    print(f"📅 Range: {format_date_db(start_date)} -> {format_date_db(end_date)}")
    print("="*60)
    
    ensure_tables_exist()

    delta = end_date - start_date
    date_list = [start_date + timedelta(days=i) for i in range(delta.days + 1)]

    with sync_playwright() as p:
        # ---------------------------------------------------------
        # BROWSER CONFIGURATION (The "Ghost" Setup)
        # ---------------------------------------------------------
        # Force visible browser on self-hosted to bypass WAF
        is_self_hosted = os.environ.get('IS_SELF_HOSTED') == 'true'
        headless_mode = False if is_self_hosted else headless

        # Inline browser setup with stealth configuration
        browser = p.chromium.launch(
            headless=headless_mode,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-infobars',
                '--window-position=0,0',
                '--ignore-certificate-errors',
                '--ignore-ssl-errors',
                '--disable-extensions',
                '--disable-popup-blocking',
                '--disable-http2'
            ]
        )

        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
            java_script_enabled=True,
            locale='en-US',
            timezone_id='America/New_York'
        )

        # Inject stealth scripts to bypass bot detection
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)

        page = context.new_page()
        setup_page(page)  # Auto-dismiss JS dialogs (alerts/confirms) on any page

        total_lineups = 0
        total_on_off = 0

        for target_date in date_list:
            nba_date = format_date_nba(target_date)
            db_date = format_date_db(target_date)
            
            print(f"\n[{db_date}] Processing...")

            for key, config in WOWY_MANIFEST.items():
                label = config['label']
                url_template = config['url']
                
                try:
                    url = url_template.format(date=nba_date)
                    # Match Ghost Protocol: domcontentloaded + 90s (tolerates redirect chains)
                    # 'commit' throws ERR_ABORTED on redirects; domcontentloaded follows them
                    page.goto(url, wait_until='domcontentloaded', timeout=90000)
                    # Dismiss NBA.com consent / OneTrust popups before scraping
                    close_popups(page)

                    # Scrape
                    data = scrape_table(page, label)
                    
                    # Process
                    count = process_item(key, data, db_date)
                    print(f"   ✓ {label}: {count} records")
                    
                    if key == "lineups": total_lineups += count
                    else: total_on_off += count
                    
                    # Human-like pause
                    time.sleep(random.uniform(2.5, 5.0))
                    
                except Exception as e:
                    print(f"   ❌ {label} Error: {e}")

        browser.close() 
        
        print("\n" + "="*60)
        print("✅ WOWY Backfill Complete")
        print(f"   Lineups: {total_lineups}")
        print(f"   On/Off: {total_on_off}")
        print("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD")
    parser.add_argument("--date", help="Single date YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=60, help="Number of days back to sync (default 60)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (for CI)")
    args = parser.parse_args()

    end = datetime.now()
    if args.end_date:
        end = datetime.strptime(args.end_date, "%Y-%m-%d")
    
    start = end - timedelta(days=args.days)
    if args.start_date:
        start = datetime.strptime(args.start_date, "%Y-%m-%d")
    
    if args.date:
        start = datetime.strptime(args.date, "%Y-%m-%d")
        end = start

    run_wowy_backfill(start, end, headless=args.headless)
