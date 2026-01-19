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
    conn = sqlite3.connect(DB_PATH)
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

def handle_pagination(page, label):
    """Ensure all rows are visible by selecting 'All' in pagination."""
    try:
        # Standard NBA.com stats pagination dropdown
        select_selector = ".Pagination_pageDropdown__KgjBU select"
        
        # Check if selector exists before trying to select
        if page.is_visible(select_selector):
            page.select_option(select_selector, value="-1")
            # Wait for reload - Lineups can be heavy
            wait_ms = 4000 if "Lineups" in label else 2500
            page.wait_for_timeout(wait_ms)
        else:
            # Sometimes there's no pagination if data is small, which is fine
            pass
            
    except Exception as e:
        print(f"      ⚠️  Pagination Warning: {e}")

def scrape_table(page, label):
    """Extract table data with retry logic."""
    print(f"      Scanning {label} table...")
    
    timeout = 30000 # 30s timeout for heavy lineup pages
    table_found = False
    
    for attempt in range(3):
        try:
            # Wait for the table body to ensure data is loaded
            page.wait_for_selector("table.Crom_table__p1iZz tbody tr", timeout=timeout)
            table_found = True
            break
        except:
            if attempt < 2:
                print(f"      ⏳ Retry {attempt+1}/3: Table not found, waiting...")
                page.wait_for_timeout(5000)
    
    if not table_found:
        print("      ⚠️  Table not found (or no data for this date).")
        return []
    
    # Handle pagination
    handle_pagination(page, label)

    # Headers
    headers = page.evaluate('''() => {
        const ths = Array.from(document.querySelectorAll('table.Crom_table__p1iZz thead th'));
        return ths.map(th => th.innerText.trim());
    }''')
    # Normalize headers (remove non-breaking spaces, newlines)
    headers = [h.replace('\xa0', ' ').replace('\n', ' ') for h in headers]
    print(f"      [DEBUG] Headers: {headers[:10]}...")  # Debug: show first 10 headers
    
    # Rows with HREF extraction (for IDs)
    rows = page.evaluate('''() => {
        const trs = Array.from(document.querySelectorAll('table.Crom_table__p1iZz tbody tr'));
        return trs.map(tr => {
            const tds = Array.from(tr.querySelectorAll('td'));
            const rowText = tds.map(td => td.innerText.trim());
            // Try to find a link in the first few columns to get IDs
            const anchor = tr.querySelector('td a'); 
            const href = anchor ? anchor.getAttribute('href') : '';
            return { 'data': rowText, 'href': href };
        });
    }''')
    
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
    except:
        return None

def process_item(item_key, data, date_str):
    """Process scraped data into SQLite."""
    if not data or not data['rows']: return 0
    
    manifest = WOWY_MANIFEST[item_key]
    col_map = manifest['col_map']
    table_name = manifest['table']
    
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
                        except:
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
            print(f"       Row Error: {e}")  # Enable debugging
            continue
            
    conn.commit()
    conn.close()
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
        browser = p.chromium.launch(
            headless=headless,  # False for local (Ghost Protocol), True for CI
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
            user_agent=random.choice(USER_AGENTS),
            ignore_https_errors=True,
            java_script_enabled=True
        )
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        page = context.new_page()

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
                    # Go to page
                    page.goto(url, timeout=45000)
                    
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
