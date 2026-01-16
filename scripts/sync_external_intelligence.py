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


def scrape_covers_ou(page) -> List[Dict]:
    """
    Extract O/U records from Covers.com using Playwright.
    """
    url = "https://www.covers.com/sport/basketball/nba/referees/statistics/2025-2026?sortedby=ou"
    print(f"   🌐 Navigating to Covers.com...")
    page.goto(url, timeout=30000)
    page.wait_for_selector("table tbody tr", timeout=15000)
    
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


def scrape_oddsshark_ats(page) -> List[Dict]:
    """
    Extract Home ATS records from OddsShark using Playwright.
    """
    url = "https://www.oddsshark.com/nba/referee-handicapping-statistics"
    print(f"   🌐 Navigating to OddsShark...")
    page.goto(url, timeout=30000)
    page.wait_for_selector("table tbody tr", timeout=15000)
    
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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = context.new_page()
        
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
            print(f"\n   ✅ Updated {updated} referee profiles with betting intelligence.")
    else:
        print("   ❌ No data scraped. Check network or site availability.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview without updating DB')
    args = parser.parse_args()
    
    run_sync(args.dry_run)
