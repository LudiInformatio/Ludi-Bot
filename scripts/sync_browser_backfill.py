#!/usr/bin/env python3
"""
LUDI INFORMATIO | GHOST PROTOCOL BACKFILL v2.1 (Stealth Upgrade)
================================================================
Browser-based synchronization of historical NBA tracking data.
Now supports comprehensive tracking, advanced stats, and misc data via DATA_MANIFEST.

Features:
- "Human Ghost" Stealth Mode (Bypasses NBA WAF)
- Random Mouse/Scroll Interactions
- Optimized Wait Strategies (domcontentloaded)

Usage:
    python scripts/sync_browser_backfill.py --days 1 (syncs yesterday)
    python scripts/sync_browser_backfill.py --start-date 2025-11-14 --end-date 2026-01-15
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
from utils.browser_utils import simulate_human_interaction, close_popups

# Playwright check
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

# ============================================================
# DATA MANIFEST (The Map)
# ============================================================

DATA_MANIFEST = {
    "drives": {
        "url": "https://www.nba.com/stats/players/drives?DateFrom={date}&DateTo={date}",
        "type": "tracking",
        "label": "Drives",
        "col_map": {
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
    "pull_up": {
        "url": "https://www.nba.com/stats/players/pullup?DateFrom={date}&DateTo={date}",
        "type": "tracking",
        "label": "Pull Up Shooting",
        "col_map": {
            "FGA": "pull_up_fga",
            "FGM": "pull_up_fgm",
            "3PA": "pull_up_3pa",
            "3PM": "pull_up_3pm",
            "eFG%": "pull_up_efg_pct"
        }
    },
    "speed": {
        "url": "https://www.nba.com/stats/players/speed-distance?DateFrom={date}&DateTo={date}",
        "type": "tracking",
        "label": "Speed & Distance",
        "col_map": {
            "DIST. MILES OFF": "dist_miles_off",
            "DIST. MILES DEF": "dist_miles_def",
            "AVG SPEED OFF": "avg_speed_off",
            "AVG SPEED DEF": "avg_speed_def"
        }
    },
    "advanced": {
        "url": "https://www.nba.com/stats/players/advanced?DateFrom={date}&DateTo={date}",
        "type": "advanced",
        "label": "Advanced Stats",
        "col_map": {
            "OFFRTG": "off_rating",
            "DEFRTG": "def_rating",
            "NETRTG": "net_rating",
            "AST%": "ast_pct",
            "AST/TO": "ast_to",
            "AST RATIO": "ast_ratio",
            "OREB%": "oreb_pct",
            "DREB%": "dreb_pct",
            "REB%": "reb_pct",
            "TOV%": "tov_pct",
            "eFG%": "efg_pct",
            "TS%": "ts_pct",
            "USG%": "usg_pct",
            "PACE": "pace",
            "PIE": "pie"
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
            "FTM": "clutch_ftm",
            "FTA": "clutch_fta"
        }
    },
    "opponent": {
        "url": "https://www.nba.com/stats/players/opponent?DateFrom={date}&DateTo={date}",
        "type": "opponent",
        "label": "Opponent Stats",
        "col_map": {
            "OPP FGM": "opp_fgm",
            "OPP FGA": "opp_fga",
            "OPP FG%": "opp_fg_pct",
            "OPP 3PM": "opp_3pm",
            "OPP 3PA": "opp_3pa",
            "OPP 3P%": "opp_3p_pct",
            "OPP REB": "opp_reb",
            "OPP AST": "opp_ast",
            "OPP TOV": "opp_tov",
            "OPP STL": "opp_stl",
            "OPP BLK": "opp_blk",
            "OPP PTS": "opp_pts"
        }
    },
    "hustle": {
        "url": "https://www.nba.com/stats/players/hustle?DateFrom={date}&DateTo={date}",
        "type": "hustle",
        "label": "Hustle Stats",
        "col_map": {
            "SCREEN ASSISTS": "screen_assists",
            "SCREEN ASSISTS PTS": "screen_assists_pts",
            "DEFLECTIONS": "deflections",
            "LOOSE BALLS RECOVERED": "loose_balls_recovered",
            "CHARGES DRAWN": "charges_drawn",
            "CONTESTED 2PT SHOTS": "contested_2pt_shots",
            "CONTESTED 3PT SHOTS": "contested_3pt_shots",
            "CONTESTED SHOTS": "contested_shots"
        }
    },
    "closest_defender": {
        "url": "https://www.nba.com/stats/players/shots-closest-defender?DateFrom={date}&DateTo={date}",
        "type": "closest_defender",
        "label": "Closest Defender",
        "distance_ranges": [
            {"param": "0-2 Feet - Very Tight", "db_col": "very_tight_fga", "add_to_contested": True},
            {"param": "2-4 Feet - Tight", "db_col": "tight_fga", "add_to_contested": True},
            {"param": "4-6 Feet - Open", "db_col": "open_fga", "add_to_contested": False},
            {"param": "6+ Feet - Wide Open", "db_col": "wide_open_fga", "add_to_contested": False}
        ],
        "col_map": {
            "FGA": "fga_value"
        }
    }
}

# Updated User Agents (Modern Chrome/Firefox)
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.1; rv:109.0) Gecko/20100101 Firefox/119.0"
]

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def handle_pagination(page, category_label=None):
    """Ensure all rows are visible by selecting 'All' in pagination."""
    try:
        close_popups(page)

        select_selector = ".Pagination_pageDropdown__KgjBU select"
        if page.is_visible(select_selector):
            # Check if dropdown is disabled before attempting to select
            select_element = page.locator(select_selector)
            is_disabled = select_element.get_attribute("disabled")

            if is_disabled is None:
                # Dropdown is enabled - proceed with selection
                select_element.scroll_into_view_if_needed()
                page.select_option(select_selector, value="-1", timeout=10000)

                # Increase wait for slower-loading tables
                slow_categories = ["Speed & Distance", "Opponent Stats", "Hustle Stats"]
                wait_ms = 4000 if category_label in slow_categories else 2000
                page.wait_for_timeout(wait_ms)
                print(f"      ✓ Pagination set to 'All' (full dataset)")
            else:
                # Dropdown is disabled - skip gracefully
                print(f"      ⚠️  Pagination disabled (low-data day, using default view)")
    except Exception as e:
        print(f"      ⚠️  Pagination Error (Non-Critical): {e}")

def format_date_nba(dt_obj):
    return dt_obj.strftime("%m/%d/%Y")

def format_date_db(dt_obj):
    return dt_obj.strftime("%Y-%m-%d")

# ============================================================
# GENERIC SCRAPING & PROCESSING
# ============================================================

def scrape_table(page, label):
    """Extract generic table data."""
    print(f"      Scanning {label} table...")
    
    # Clear any blocking popups first
    close_popups(page)
    
    # Simulate human attention before scanning
    simulate_human_interaction(page)
    
    # First wait for table to appear with RETRIES
    slow_categories = ["Speed & Distance", "Opponent Stats", "Hustle Stats"]
    # Increased timeout to 30s
    timeout = 30000 if label in slow_categories else 20000
    
    table_found = False
    for attempt in range(3):
        try:
            page.wait_for_selector("table.Crom_table__p1iZz", timeout=timeout)
            table_found = True
            break
        except Exception:
            if attempt < 2:
                print(f"      ⏳ Retry {attempt+1}/3: Table not found, waiting...")
                simulate_human_interaction(page) # Trigger load
                page.wait_for_timeout(3000)
    
    if not table_found:
        print("      ⚠️  Table not found (or no games this day).")
        return []
    
    # Then handle pagination to show all rows
    handle_pagination(page, label)

    # Headers - use LAST header row only (handles multi-row headers like Closest Defender page)
    headers = page.evaluate('''() => {
        const headerRows = Array.from(document.querySelectorAll('table.Crom_table__p1iZz thead tr'));
        if (headerRows.length === 0) return [];
        const lastRow = headerRows[headerRows.length - 1];
        const ths = Array.from(lastRow.querySelectorAll('th'));
        return ths.map(th => th.innerText.trim());
    }''')
    headers = [h.replace('\xa0', ' ').replace('\n', ' ') for h in headers]
    # print(f"      [DEBUG] Headers: {headers}")
    
    # Rows with HREF extraction
    rows = page.evaluate('''() => {
        const trs = Array.from(document.querySelectorAll('table.Crom_table__p1iZz tbody tr'));
        return trs.map(tr => {
            const tds = Array.from(tr.querySelectorAll('td'));
            const rowText = tds.map(td => td.innerText.trim());
            const anchor = tr.querySelector('td:first-child a');
            const href = anchor ? anchor.getAttribute('href') : '';
            return { 'data': rowText, 'href': href };
        });
    }''')
    
    print(f"      [DEBUG] Found {len(rows)} rows for {label}")
    return {'headers': headers, 'rows': rows}

def process_item(item_key, data, date_str):
    """Generic processor based on manifest type."""
    if not data or not data['rows']: return 0

    manifest_entry = DATA_MANIFEST[item_key]
    col_map = manifest_entry['col_map']
    table_type = manifest_entry['type']
    target_table = "player_game_tracking"
    if table_type == "advanced": target_table = "player_game_advanced"
    if table_type == "clutch": target_table = "player_clutch_stats"

    # Reverting to specific functions for safety in this iteration
    # as generic SQL construction is error-prone without an ORM.
    if table_type == "tracking":
        return process_tracking_row(data, date_str, col_map)
    elif table_type == "advanced":
        return process_advanced_row(data, date_str, col_map)
    elif table_type == "clutch":
        return process_clutch_row(data, date_str, col_map)
    elif table_type == "opponent":
        return process_opponent_row(data, date_str, col_map)
    elif table_type == "hustle":
        return process_hustle_row(data, date_str, col_map)
    # closest_defender is handled specially in main loop, not here
    return 0

def extract_id_from_href(href):
    """Extracts numeric ID from href like /stats/player/1630639/?..."""
    try:
        # Expected: /stats/player/1630639/... or /player/1630639/...
        parts = href.split('/')
        for part in parts:
            if part.isdigit() and len(part) > 4: # Simple heuristic
                return part
        return None
    except Exception:
        return None

def process_tracking_row(data, date_str, col_map):
    headers = data['headers']
    rows = data['rows']
    
    # Map header names to indices
    header_idx = {h: i for i, h in enumerate(headers)}
    if 'PLAYER' not in header_idx: 
        print(f"      ⚠️  'PLAYER' column not found in headers: {headers}")
        return 0
    
    conn = get_db_connection()
    c = conn.cursor()
    count = 0
    
    for row_obj in rows:
        try:
            row_data = row_obj['data']
            href = row_obj['href']
            
            player_name = row_data[header_idx['PLAYER']]
            team_val = row_data[header_idx.get('TEAM', 1)] 
            
            # ID Extraction
            pid = extract_id_from_href(href)
            if not pid:
                # Fallback to slug if no ID found (unlikely)
                pid = player_name.lower().replace(" ", "_").replace(".", "").replace("'", "")
            
            # Build updates
            updates = []
            values = []
            
            for csv_head, db_col in col_map.items():
                if csv_head in header_idx:
                    val_str = row_data[header_idx[csv_head]]
                    val = 0.0
                    if val_str != '-':
                        val = float(val_str.replace('%', ''))
                    updates.append(f"{db_col} = ?")
                    values.append(val)
            
            if not updates: continue
            
            # Add identifiers for WHERE/INSERT
            base_values = values.copy()
            
            cols = [m[1] for m in col_map.items() if m[0] in header_idx]
            placeholders = ['?'] * len(cols)
            
            col_names = ", ".join(cols)
            val_placeholders = ", ".join(placeholders)
            
            update_excluded = ", ".join([f"{col} = excluded.{col}" for col in cols])
            
            sql_clean = f'''
                INSERT INTO player_game_tracking (
                    nba_player_id, player_name, game_date, team_abbr, nba_game_id, synced_at, {col_names}
                ) VALUES (?, ?, ?, ?, 'GHOST', CURRENT_TIMESTAMP, {val_placeholders})
                ON CONFLICT(nba_player_id, game_date) DO UPDATE SET
                {update_excluded}, synced_at = CURRENT_TIMESTAMP
            '''
            
            params = [pid, player_name, date_str, team_val] + base_values
            
            c.execute(sql_clean, params)
            count += 1
        except Exception as e:
            # print(f"       Row Error: {e}")
            continue
            
    conn.commit()
    conn.close()
    return count

def process_advanced_row(data, date_str, col_map):
    headers = data['headers']
    rows = data['rows']
    header_idx = {h: i for i, h in enumerate(headers)}
    if 'PLAYER' not in header_idx: return 0
    
    conn = get_db_connection()
    c = conn.cursor()
    count = 0
    
    for row_obj in rows:
        try:
            row_data = row_obj['data']
            href = row_obj['href']
            
            player_name = row_data[header_idx['PLAYER']]
            team_val = row_data[header_idx.get('TEAM', 1)]
            
            pid = extract_id_from_href(href)
            if not pid:
                pid = player_name.lower().replace(" ", "_").replace(".", "").replace("'", "")
            
            values = []
            cols = []
            for csv_head, db_col in col_map.items():
                if csv_head in header_idx:
                    val_str = row_data[header_idx[csv_head]]
                    val = 0.0
                    if val_str != '-':
                        val = float(val_str.replace('%', ''))
                    cols.append(db_col)
                    values.append(val)
            
            col_names = ", ".join(cols)
            placeholders = ", ".join(['?'] * len(cols))
            update_excluded = ", ".join([f"{col} = excluded.{col}" for col in cols])
            
            sql = f'''
                INSERT INTO player_game_advanced (
                    player_id, player_name, game_date, team_abbrev, nba_game_id, synced_at, {col_names}
                ) VALUES (?, ?, ?, ?, 'GHOST', CURRENT_TIMESTAMP, {placeholders})
                ON CONFLICT(player_id, game_date) DO UPDATE SET
                {update_excluded}, synced_at = CURRENT_TIMESTAMP
            '''
            
            params = [pid, player_name, date_str, team_val] + values
            c.execute(sql, params)
            count += 1
        except Exception:
            continue
    conn.commit()
    conn.close()
    return count

def process_clutch_row(data, date_str, col_map):
    headers = data['headers']
    rows = data['rows']
    header_idx = {h: i for i, h in enumerate(headers)}
    if 'PLAYER' not in header_idx: return 0
    
    conn = get_db_connection()
    c = conn.cursor()
    count = 0
    
    for row_obj in rows:
        try:
            row_data = row_obj['data']
            href = row_obj['href']
            
            player_name = row_data[header_idx['PLAYER']]
            team_val = row_data[header_idx.get('TEAM', 1)]
            
            pid = extract_id_from_href(href)
            if not pid:
                pid = player_name.lower().replace(" ", "_").replace(".", "").replace("'", "")
            
            values = []
            cols = []
            for csv_head, db_col in col_map.items():
                if csv_head in header_idx:
                    val_str = row_data[header_idx[csv_head]]
                    val = 0.0
                    if val_str != '-':
                        val = float(val_str.replace('%', ''))
                    cols.append(db_col)
                    values.append(val)
            
            col_names = ", ".join(cols)
            placeholders = ", ".join(['?'] * len(cols))
            update_excluded = ", ".join([f"{col} = excluded.{col}" for col in cols])
            
            # Note: Clutch table uses 'nba_player_id' as key alias in DB schema
            sql = f'''
                INSERT INTO player_clutch_stats (
                    nba_player_id, player_name, game_date, team_abbr, synced_at, {col_names}
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, {placeholders})
                ON CONFLICT(nba_player_id, game_date) DO UPDATE SET
                {update_excluded}, synced_at = CURRENT_TIMESTAMP
            '''
            
            params = [pid, player_name, date_str, team_val] + values
            c.execute(sql, params)
            count += 1
        except Exception:
            continue
    conn.commit()
    conn.close()
    return count

def process_opponent_row(data, date_str, col_map):
    headers = data['headers']
    rows = data['rows']
    header_idx = {h: i for i, h in enumerate(headers)}
    # The opponent table uses "VS PLAYER" as the name column
    name_col = "VS PLAYER" if "VS PLAYER" in header_idx else "PLAYER"
    if name_col not in header_idx: return 0
    
    conn = get_db_connection()
    c = conn.cursor()
    count = 0
    
    for row_obj in rows:
        try:
            row_data = row_obj['data']
            href = row_obj['href']
            
            player_name = row_data[header_idx[name_col]]
            team_val = row_data[header_idx.get('TEAM', 1)]
            
            pid = extract_id_from_href(href)
            if not pid:
                pid = player_name.lower().replace(" ", "_").replace(".", "").replace("'", "")
            
            values = []
            cols = []
            for csv_head, db_col in col_map.items():
                if csv_head in header_idx:
                    val_str = row_data[header_idx[csv_head]]
                    val = 0.0
                    if val_str != '-':
                        val = float(val_str.replace('%', ''))
                    cols.append(db_col)
                    values.append(val)
            
            col_names = ", ".join(cols)
            placeholders = ", ".join(['?'] * len(cols))
            update_excluded = ", ".join([f"{col} = excluded.{col}" for col in cols])
            
            sql = f'''
                INSERT INTO player_game_opponent (
                    player_id, player_name, team_abbrev, game_date, nba_game_id, synced_at, {col_names}
                ) VALUES (?, ?, ?, ?, 'GHOST', CURRENT_TIMESTAMP, {placeholders})
                ON CONFLICT(player_id, game_date) DO UPDATE SET
                {update_excluded}, synced_at = CURRENT_TIMESTAMP
            '''
            
            params = [pid, player_name, team_val, date_str] + values
            c.execute(sql, params)
            count += 1
        except Exception:
            continue
    conn.commit()
    conn.close()
    return count

def process_hustle_row(data, date_str, col_map):
    headers = data['headers']
    rows = data['rows']
    header_idx = {h: i for i, h in enumerate(headers)}
    if 'PLAYER' not in header_idx: return 0
    
    conn = get_db_connection()
    c = conn.cursor()
    count = 0
    
    for row_obj in rows:
        try:
            row_data = row_obj['data']
            href = row_obj['href']
            
            player_name = row_data[header_idx['PLAYER']]
            team_val = row_data[header_idx.get('TEAM', 1)]
            
            pid = extract_id_from_href(href)
            if not pid:
                pid = player_name.lower().replace(" ", "_").replace(".", "").replace("'", "")
            
            values = []
            cols = []
            for csv_head, db_col in col_map.items():
                if csv_head in header_idx:
                    val_str = row_data[header_idx[csv_head]]
                    val = 0.0
                    if val_str != '-':
                        val = float(val_str.replace('%', ''))
                    cols.append(db_col)
                    values.append(val)
            
            col_names = ", ".join(cols)
            placeholders = ", ".join(['?'] * len(cols))
            update_excluded = ", ".join([f"{col} = excluded.{col}" for col in cols])
            
            sql = f'''
                INSERT INTO player_game_hustle (
                    player_id, player_name, team_abbrev, game_date, nba_game_id, synced_at, {col_names}
                ) VALUES (?, ?, ?, ?, 'GHOST', CURRENT_TIMESTAMP, {placeholders})
                ON CONFLICT(player_id, game_date) DO UPDATE SET
                {update_excluded}, synced_at = CURRENT_TIMESTAMP
            '''
            
            params = [pid, player_name, team_val, date_str] + values
            c.execute(sql, params)
            count += 1
        except Exception:
            continue
    conn.commit()
    conn.close()
    return count


def process_closest_defender(page, date_str, nba_date):
    """
    Special handler for Closest Defender data.
    Scrapes all 4 distance ranges and aggregates into shot difficulty columns.

    Returns: number of records updated
    """
    from urllib.parse import quote

    config = DATA_MANIFEST['closest_defender']
    base_url = config['url'].format(date=nba_date)
    distance_ranges = config['distance_ranges']

    # Accumulator: player_id -> {player_name, team, very_tight_fga, tight_fga, open_fga, wide_open_fga}
    player_data = {}

    for range_config in distance_ranges:
        param_value = range_config['param']
        db_col = range_config['db_col']

        # Build URL with distance range filter
        url = f"{base_url}&CloseDefDistRange={quote(param_value)}"

        try:
            print(f"      Scraping {param_value}...")
            page.goto(url, wait_until='domcontentloaded', timeout=90000)

            # Use standard table scraping
            data = scrape_table(page, f"Closest Defender ({param_value})")

            if not data or not data.get('rows'):
                print(f"         ⚠️ No data for {param_value}")
                continue

            headers = data['headers']
            rows = data['rows']
            header_idx = {h: i for i, h in enumerate(headers)}

            if 'PLAYER' not in header_idx or 'FGA' not in header_idx:
                print(f"         ⚠️ Missing PLAYER or FGA column")
                continue

            for row_obj in rows:
                try:
                    row_data = row_obj['data']
                    href = row_obj['href']

                    player_name = row_data[header_idx['PLAYER']]
                    team_val = row_data[header_idx.get('TEAM', 1)]
                    fga_str = row_data[header_idx['FGA']]

                    pid = extract_id_from_href(href)
                    if not pid:
                        pid = player_name.lower().replace(" ", "_").replace(".", "").replace("'", "")

                    fga = 0
                    if fga_str and fga_str != '-':
                        fga = int(float(fga_str))

                    # Initialize player entry if not exists
                    if pid not in player_data:
                        player_data[pid] = {
                            'player_name': player_name,
                            'team': team_val,
                            'very_tight_fga': 0,
                            'tight_fga': 0,
                            'open_fga': 0,
                            'wide_open_fga': 0
                        }

                    # Set the appropriate column
                    player_data[pid][db_col] = fga

                except Exception as e:
                    continue

            # Human-like pause between range scrapes
            time.sleep(random.uniform(2.0, 4.0))

        except Exception as e:
            print(f"         ❌ Error scraping {param_value}: {e}")
            continue

    # Now write all accumulated data to database
    if not player_data:
        return 0

    conn = get_db_connection()
    c = conn.cursor()
    count = 0

    for pid, pdata in player_data.items():
        try:
            # Calculate contested_fga = very_tight (0-2ft) + tight (2-4ft)
            contested_fga = pdata['very_tight_fga'] + pdata['tight_fga']

            sql = '''
                INSERT INTO player_game_tracking (
                    nba_player_id, player_name, game_date, team_abbr, nba_game_id, synced_at,
                    contested_fga, tight_fga, open_fga, wide_open_fga
                ) VALUES (?, ?, ?, ?, 'GHOST', CURRENT_TIMESTAMP, ?, ?, ?, ?)
                ON CONFLICT(nba_player_id, game_date) DO UPDATE SET
                    contested_fga = excluded.contested_fga,
                    tight_fga = excluded.tight_fga,
                    open_fga = excluded.open_fga,
                    wide_open_fga = excluded.wide_open_fga,
                    synced_at = CURRENT_TIMESTAMP
            '''

            params = [
                pid, pdata['player_name'], date_str, pdata['team'],
                contested_fga, pdata['tight_fga'], pdata['open_fga'], pdata['wide_open_fga']
            ]
            c.execute(sql, params)
            count += 1
        except Exception as e:
            continue

    conn.commit()
    conn.close()
    return count


# ============================================================
# MAIN GHOST PROTOCOL LOOP
# ============================================================

def run_ghost_protocol(start_date, end_date, headless=False, closest_only=False):
    print("\n" + "="*50)
    print(f"👻 LUDI GHOST PROTOCOL v2.1 | HUMAN STEALTH MODE")
    print(f"📅 Range: {start_date} -> {end_date}")
    print(f"🖥️  Mode: {'Headless' if headless else 'Visible Browser'}")
    print("="*50)

    delta = end_date - start_date
    date_list = [start_date + timedelta(days=i) for i in range(delta.days + 1)]

    with sync_playwright() as p:
        # Browser Launch Args for Stealth
        # Force visible browser on self-hosted to bypass WAF
        is_self_hosted = os.environ.get('IS_SELF_HOSTED') == 'true'
        headless_mode = False if is_self_hosted else headless

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
                '--disable-http2'  # Force HTTP/1.1 to avoid protocol errors
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
        
        # INJECT STEALTH SCRIPTS
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            window.chrome = { runtime: {} };
        """)
        
        page = context.new_page()

        for target_date in date_list:
            nba_date = format_date_nba(target_date)
            db_date = format_date_db(target_date)
            
            print(f"\n[{db_date}] Processing...")

            if not closest_only:
                # Iterate through Manifest (skip closest_defender - handled separately)
                for key, config in DATA_MANIFEST.items():
                    # Skip closest_defender - it requires special multi-page handling
                    if config['type'] == 'closest_defender':
                        continue

                    label = config['label']
                    url_template = config['url']

                    try:
                        url = url_template.format(date=nba_date)

                        # 1. Navigate with optimized wait strategy
                        # Use 'domcontentloaded' to avoid hanging on ads/tracking pixels
                        # Increase timeout to 90s for safety
                        page.goto(url, wait_until='domcontentloaded', timeout=90000)

                        # 2. Scrape (includes human interaction)
                        data = scrape_table(page, label)

                        # 3. Process
                        count = process_item(key, data, db_date)
                        print(f"   ✓ {label}: {count} records")

                        # Human-like pause between tables
                        time.sleep(random.uniform(3.0, 6.0))

                    except Exception as e:
                        print(f"   ❌ {label} Error: {e}")

            # Process Closest Defender separately (requires scraping 4 distance ranges)
            try:
                print(f"   📊 Closest Defender (4 distance ranges)...")
                count = process_closest_defender(page, db_date, nba_date)
                print(f"   ✓ Closest Defender: {count} records")
            except Exception as e:
                print(f"   ❌ Closest Defender Error: {e}")

        browser.close()
        print("\n✅ Ghost Protocol Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD")
    parser.add_argument("--days", type=int, help="Number of days back to sync (1 = yesterday)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (for CI)")
    parser.add_argument("--closest-only", action="store_true", help="Only sync closest defender data")
    args = parser.parse_args()

    end = datetime.now()
    if args.end_date:
        end = datetime.strptime(args.end_date, "%Y-%m-%d")
    
    start = end
    if args.start_date:
        start = datetime.strptime(args.start_date, "%Y-%m-%d")
    elif args.days:
        start = end - timedelta(days=args.days)
        if args.days == 1:
            end = start

    run_ghost_protocol(start, end, headless=args.headless, closest_only=args.closest_only)
