#!/usr/bin/env python3
"""
LUDI INFORMATIO | EXTERNAL INTELLIGENCE SYNCER
Phase 5: Betting Trend Scraper (Playwright Ghost Browser)

Purpose:
    - Run weekly (Mondays)
    - Scrapes Covers.com for O/U records
    - Scrapes OddsShark for Home ATS bias
    - Updates `referee_profiles` with betting trends

Usage:
    python scripts/sync_external_intelligence.py [--dry-run]
"""

import sys
import os
import argparse
import sqlite3
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH

# Playwright import with graceful fallback
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not installed. Run: pip install playwright && playwright install chromium")


def scrape_covers_ou(page, max_retries: int = 3) -> List[Dict]:
    """
    Extract O/U records from Covers.com using Playwright with retry logic.
    """
    url = "https://www.covers.com/sport/basketball/nba/referees/statistics/2025-2026?sortedby=ou"
    
    for attempt in range(max_retries):
        try:
            print(f"   🌐 Navigating to Covers.com (attempt {attempt+1}/{max_retries})...")
            page.goto(url, timeout=60000, wait_until='networkidle')
            page.wait_for_selector("table tbody tr", timeout=30000)
            
            # Execute JS to extract table data
            data = page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('table tbody tr'));
                return rows.map(row => {
                    const cells = Array.from(row.querySelectorAll('td'));
                    if (cells.length < 8) return null;
                    const nameLink = cells[1].querySelector('a');
                    return {
                        name: nameLink ? nameLink.innerText.trim() : cells[1].innerText.trim(),
                        ou: cells[3].innerText.trim(),  // O/U record like "19-9"
                        total: cells[7].innerText.trim() // Avg Total
                    };
                }).filter(r => r !== null);
            }''')
            
            print(f"   ✅ Extracted {len(data)} referees from Covers (O/U)")
            return data
            
        except Exception as e:
            wait_time = 5 * (2 ** attempt)  # 5s, 10s, 20s
            print(f"   ⚠️  Attempt {attempt+1} failed: {str(e)[:100]}")
            if attempt < max_retries - 1:
                print(f"   ⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ Covers scrape failed after {max_retries} attempts")
                return []


def scrape_oddsshark_ats(page, max_retries: int = 3) -> List[Dict]:
    """
    Extract Home ATS records from OddsShark using Playwright with retry logic.
    """
    url = "https://www.oddsshark.com/nba/referee-handicapping-statistics"
    
    for attempt in range(max_retries):
        try:
            print(f"   🌐 Navigating to OddsShark (attempt {attempt+1}/{max_retries})...")
            page.goto(url, timeout=60000, wait_until='networkidle')
            page.wait_for_selector("table tbody tr", timeout=30000)
            
            data = page.evaluate('''() => {
                const rows = Array.from(document.querySelectorAll('table tbody tr'));
                return rows.map(row => {
                    const cells = Array.from(row.querySelectorAll('td'));
                    if (cells.length < 8) return null;
                    const nameCell = cells[0];
                    const nameLink = nameCell.querySelector('a');
                    return {
                        name: nameLink ? nameLink.innerText.trim() : nameCell.innerText.trim(),
                        home_ats_w: cells[5] ? cells[5].innerText.trim() : '0',
                        home_ats_l: cells[6] ? cells[6].innerText.trim() : '0'
                    };
                }).filter(r => r !== null);
            }''')
            
            print(f"   ✅ Extracted {len(data)} referees from OddsShark (ATS)")
            return data
            
        except Exception as e:
            wait_time = 5 * (2 ** attempt)  # 5s, 10s, 20s
            print(f"   ⚠️  Attempt {attempt+1} failed: {str(e)[:100]}")
            if attempt < max_retries - 1:
                print(f"   ⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ OddsShark scrape failed after {max_retries} attempts")
                return []


def update_database(covers_data: List[Dict], oddsshark_data: List[Dict], dry_run: bool = False):
    """
    Update referee_profiles with the scraped betting intelligence.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Build lookup for OddsShark data
    ats_lookup = {}
    for ref in oddsshark_data:
        name = ref.get('name', '').strip()
        if name:
            try:
                wins = int(ref.get('home_ats_w', 0))
                losses = int(ref.get('home_ats_l', 0))
                total = wins + losses
                bias = round(wins / total, 3) if total > 0 else 0.5
                ats_lookup[name.lower()] = {
                    'record': f"{wins}-{losses}",
                    'bias': bias
                }
            except ValueError:
                pass  # Skip if parsing fails
    
    updated = 0
    for ref in covers_data:
        name = ref.get('name', '').strip()
        ou_str = ref.get('ou', '0-0')
        total_str = ref.get('total', '0')
        
        if not name:
            continue
        
        # Parse O/U
        ou_match = re.match(r'(\d+)-(\d+)', ou_str)
        if ou_match:
            over_wins = int(ou_match.group(1))
            under_wins = int(ou_match.group(2))
            games = over_wins + under_wins
            ou_pct = round(over_wins / games, 3) if games > 0 else 0.5
        else:
            ou_pct = 0.5
        
        # Parse Avg Total
        try:
            avg_total = float(total_str) if total_str else None
        except ValueError:
            avg_total = None
            
        # Match ATS data
        ats_data = ats_lookup.get(name.lower(), {'record': None, 'bias': None})
        
        if dry_run:
            print(f"   📊 {name}: O/U {ou_str} ({ou_pct*100:.1f}% Over) | ATS: {ats_data['record']}")
            updated += 1
            continue
        
        # Update database
        c.execute('''
            UPDATE referee_profiles
            SET ou_record = ?, ou_percentage = ?, avg_total = ?,
                home_ats_record = ?, home_ats_bias = ?,
                last_updated = CURRENT_TIMESTAMP, data_source = 'covers-oddsshark'
            WHERE LOWER(referee_name) = LOWER(?)
        ''', (ou_str, ou_pct, avg_total, ats_data['record'], ats_data['bias'], name))
        
        if c.rowcount > 0:
            updated += 1
    
    if not dry_run:
        conn.commit()
        
    conn.close()
    return updated


def run_sync(dry_run: bool = False):
    print("\n" + "=" * 60)
    print("LUDI INFORMATIO | EXTERNAL INTELLIGENCE SYNC")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print("=" * 60)
    
    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright is required. Install with: pip install playwright && playwright install chromium")
        return
    
    covers_data = []
    oddsshark_data = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'  # Required for GitHub Actions
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation', 'notifications'],
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br'
            }
        )
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
        """)
        
        try:
            covers_data = scrape_covers_ou(page)
        except Exception as e:
            print(f"   ⚠️  Covers scrape failed: {e}")
            
        try:
            oddsshark_data = scrape_oddsshark_ats(page)
        except Exception as e:
            print(f"   ⚠️  OddsShark scrape failed: {e}")
            
        browser.close()
    
    if covers_data or oddsshark_data:
        updated = update_database(covers_data, oddsshark_data, dry_run)
        if dry_run:
            print(f"\n   🔍 Dry run complete. Previewed {updated} refs.")
        else:
            sources = []
            if covers_data:
                sources.append(f"Covers ({len(covers_data)} refs)")
            if oddsshark_data:
                sources.append(f"OddsShark ({len(oddsshark_data)} refs)")
            print(f"\n   ✅ Updated {updated} referee profiles from: {', '.join(sources)}")
    else:
        print("   ⚠️  No data scraped from either source. Workflow will continue without betting intel update.")
        print("   💡 Tip: Check GitHub Actions logs for detailed error information")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview without updating DB')
    args = parser.parse_args()
    
    run_sync(args.dry_run)
