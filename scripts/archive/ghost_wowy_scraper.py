#!/usr/bin/env python3
"""
Ghost Protocol v2.1 - WOWY Edition
Adds lineup and on/off court data scraping to existing tracking pipeline
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
import sqlite3
import time
import json
from datetime import datetime, timedelta
from database import DB_PATH
from utils.browser_utils import close_popups, simulate_human_interaction

# ============================================================
# WOWY DATA MANIFEST
# ============================================================

WOWY_MANIFEST = {
    "lineups": {
        "url": "https://www.nba.com/stats/lineups/advanced?DateFrom={date}&DateTo={date}&GroupQuantity=5&PerMode=Totals",
        "type": "lineup",
        "label": "5-Man Lineups (WOWY)",
        "table": "team_lineups",  # New table
        "col_map": {
            "GROUP_NAME": "lineup_players",  # Player names in lineup
            "GROUP_ID": "lineup_id",  # Hyphen-separated player IDs
            "TEAM_ABBREVIATION": "team_abbreviation",
            "GP": "games_played",
            "MIN": "minutes",
            "OFFRTG": "off_rating",
            "DEFRTG": "def_rating",
            "NETRTG": "net_rating",
            "AST%": "ast_pct",
            "OREB%": "oreb_pct",
            "DREB%": "dreb_pct",
            "REB%": "reb_pct",
            "TOV%": "tov_pct",
            "eFG%": "efg_pct",
            "TS%": "ts_pct",
            "PACE": "pace",
            "PIE": "pie",
            "POSS": "possessions"
        }
    },
    "on_off": {
        "url": "https://www.nba.com/stats/players/on-off-court?DateFrom={date}&DateTo={date}&PerMode=Totals",
        "type": "on_off",
        "label": "Player On/Off Court",
        "table": "player_on_off_stats",  # New table
        "col_map": {
            "PLAYER_ID": "player_id",
            "PLAYER_NAME": "player_name",
            "TEAM_ABBREVIATION": "team_abbreviation",
            "COURT_STATUS": "court_status",  # "On" or "Off"
            "MIN": "minutes",
            "OFFRTG": "off_rating",
            "DEFRTG": "def_rating",
            "NETRTG": "net_rating",
            "AST%": "ast_pct",
            "REB%": "reb_pct",
            "TOV%": "tov_pct",
            "eFG%": "efg_pct",
            "TS%": "ts_pct",
            "PACE": "pace",
            "PIE": "pie"
        }
    }
}

def create_wowy_tables(conn):
    """Create tables for lineup and on/off data"""
    cursor = conn.cursor()
    
    # Team Lineups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_lineups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_date TEXT,
            lineup_id TEXT,
            lineup_players TEXT,
            team_abbreviation TEXT,
            games_played INTEGER,
            minutes REAL,
            off_rating REAL,
            def_rating REAL,
            net_rating REAL,
            ast_pct REAL,
            oreb_pct REAL,
            dreb_pct REAL,
            reb_pct REAL,
            tov_pct REAL,
            efg_pct REAL,
            ts_pct REAL,
            pace REAL,
            pie REAL,
            possessions INTEGER,
            created_at TEXT,
            UNIQUE(game_date, lineup_id)
        )
    ''')
    
    # Player On/Off Stats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_on_off_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_date TEXT,
            player_id TEXT,
            player_name TEXT,
            team_abbreviation TEXT,
            court_status TEXT,
            minutes REAL,
            off_rating REAL,
            def_rating REAL,
            net_rating REAL,
            ast_pct REAL,
            reb_pct REAL,
            tov_pct REAL,
            efg_pct REAL,
            ts_pct REAL,
            pace REAL,
            pie REAL,
            created_at TEXT,
            UNIQUE(game_date, player_id, court_status)
        )
    ''')
    
    conn.commit()
    print("✅ WOWY tables created/verified")

def scrape_wowy_data(date_str, data_type, config, page):
    """
    Scrape lineup or on/off data for a date using Ghost Protocol
    """
    url = config['url'].format(date=date_str)
    print(f"  📡 {config['label']}...", end=" ", flush=True)
    
    try:
        # Navigate with anti-bot measures
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        close_popups(page)
        simulate_human_interaction(page)
        time.sleep(1 + (random.random() * 1))
        
        # Wait for table to load
        page.wait_for_selector('table.Crom_table__p1iZz', timeout=10000)
        
        # Extract data from table
        table_html = page.locator('table.Crom_table__p1iZz').inner_html()
        
        # Parse table (simplified - would need full parsing logic)
        rows = page.locator('table.Crom_table__p1iZz tbody tr').all()
        
        records = []
        for row in rows:
            cells = row.locator('td').all()
            if len(cells) > 0:
                record = {
                    'game_date': date_str,
                    'created_at': datetime.now().isoformat()
                }
                
                # Map columns (simplified - need to match header order)
                for i, cell in enumerate(cells):
                    text = cell.inner_text().strip()
                    # Column mapping logic here
                    record[f'col_{i}'] = text
                
                records.append(record)
        
        print(f"✅ {len(records)} records")
        return records
        
    except Exception as e:
        print(f"❌ {type(e).__name__}: {str(e)[:80]}")
        return []

def main():
    """Test WOWY scraping for a single date"""
    test_date = "2026-01-17"
    
    print(f"🎯 Ghost Protocol v2.1 - WOWY Edition")
    print(f"📅 Testing date: {test_date}")
    print("=" * 60)
    
    # Create tables
    conn = sqlite3.connect(DB_PATH)
    create_wowy_tables(conn)
    
    # Launch browser
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible for testing
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        # Test lineup scraping
        print("\n📊 Scraping Lineup Data...")
        lineup_data = scrape_wowy_data(test_date, 'lineups', WOWY_MANIFEST['lineups'], page)
        
        # Test on/off scraping
        print("\n📊 Scraping On/Off Data...")
        on_off_data = scrape_wowy_data(test_date, 'on_off', WOWY_MANIFEST['on_off'], page)
        
        browser.close()
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ WOWY Test Complete")
    print(f"   Lineups: {len(lineup_data)} records")
    print(f"   On/Off: {len(on_off_data)} records")

if __name__ == '__main__':
    import random
    main()
