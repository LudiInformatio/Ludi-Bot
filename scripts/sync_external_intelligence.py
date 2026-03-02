#!/usr/bin/env python3
"""
LUDI INFORMATIO | EXTERNAL INTELLIGENCE SYNCER
Phase 5 v2: Betting Trend Scraper (Playwright Ghost Browser)

Purpose:
    - Run weekly (Mondays via weekly_referee_sync.yml)
    - Scrapes Covers.com for O/U records, ATS, PPG, margins, games worked
    - Scrapes OddsShark for Home ATS bias + Home/Away Fouls per game
    - Updates `referee_profiles` with betting trends
    - Cleans duplicate (#N) badge-suffix rows on first run

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
from typing import Dict, List, Optional, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH
from utils.browser_utils import close_popups, setup_page, simulate_human_interaction, wait_for_selector_safe

# Playwright import with graceful fallback
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not installed. Run: pip install playwright && playwright install chromium")


# --- Name normalization ---

def _normalize_ref_name(name: str) -> str:
    """Normalize referee name for DB matching.

    Strips badge suffix (#N), normalizes periods/dots in initials,
    and trims whitespace. Both Covers and OddsShark may format names
    differently from our DB (e.g. "J.B. DeRosa" vs "JB DeRosa").

    Returns lowercased name for case-insensitive matching.
    """
    # Strip (#N) badge suffix: "Aaron Smith (#51)" → "Aaron Smith"
    name = re.sub(r'\s*\(#\d+\)', '', name)
    # Normalize periods in initials: "J.B." → "JB", "Jr." → "Jr"
    name = re.sub(r'\.(?=\s|$)', '', name)  # Remove trailing dots
    name = re.sub(r'\.', '', name)          # Remove remaining dots
    return name.strip().lower()


def _build_ref_name_lookup(conn) -> Dict[str, str]:
    """Build a lookup: normalized_name → actual DB referee_name.

    Handles both clean rows ("Aaron Smith") and duplicate rows
    ("Aaron Smith (#51)") — prefers the clean row.
    """
    c = conn.cursor()
    c.execute("SELECT referee_name FROM referee_profiles")
    lookup = {}
    for (db_name,) in c.fetchall():
        norm = _normalize_ref_name(db_name)
        # Prefer clean rows (no parenthetical) over (#N) duplicates
        if norm not in lookup or '(' not in db_name:
            lookup[norm] = db_name
    return lookup


# --- Covers.com scraper ---

def scrape_covers_ou(page, max_retries: int = 3) -> List[Dict]:
    """Extract referee stats from Covers.com using header-based column matching.

    Covers table columns (2025-26): #, Name, ATS, O/U, PPG, Pts-A/G, Pts-M/G, Total
    Previous version only scraped O/U and Total using hardcoded indices.
    Now extracts ALL columns and maps by header text.
    """
    url = "https://www.covers.com/sport/basketball/nba/referees/statistics/2025-2026?sortedby=ou"

    for attempt in range(max_retries):
        try:
            print(f"   🌐 Navigating to Covers.com (attempt {attempt+1}/{max_retries})...")
            page.goto(url, timeout=60000, wait_until='domcontentloaded')
            close_popups(page)
            simulate_human_interaction(page)
            if not wait_for_selector_safe(page, "table tbody tr", timeout=30000, message="Covers Table"):
                print("   ❌ Timeout waiting for Covers table (even after popup check)")
                continue

            # Header-based extraction — resilient to column reordering
            data = page.evaluate('''() => {
                const table = document.querySelector('table');
                if (!table) return [];

                // Build header index map from <th> elements
                const headers = Array.from(table.querySelectorAll('thead th'))
                    .map((th, i) => [th.innerText.trim().toLowerCase(), i]);
                const hmap = Object.fromEntries(headers);

                // Column indices (with fallbacks to known positions)
                const iNum   = hmap['#']       ?? 0;
                const iName  = hmap['name']    ?? 1;
                const iATS   = hmap['ats']     ?? 2;
                const iOU    = hmap['o/u']     ?? 3;
                const iPPG   = hmap['ppg']     ?? 4;
                const iPtsA  = hmap['pts-a/g'] ?? 5;
                const iPtsM  = hmap['pts-m/g'] ?? 6;
                const iTotal = hmap['total']   ?? 7;

                const rows = Array.from(table.querySelectorAll('tbody tr'));
                return rows.map(row => {
                    const cells = Array.from(row.querySelectorAll('td'));
                    if (cells.length < 4) return null;
                    const nameLink = cells[iName] ? cells[iName].querySelector('a') : null;
                    return {
                        games_worked: cells[iNum]   ? cells[iNum].innerText.trim()   : '',
                        name:         nameLink      ? nameLink.innerText.trim()       :
                                      cells[iName]  ? cells[iName].innerText.trim()   : '',
                        ats:          cells[iATS]   ? cells[iATS].innerText.trim()    : '',
                        ou:           cells[iOU]    ? cells[iOU].innerText.trim()     : '',
                        ppg:          cells[iPPG]   ? cells[iPPG].innerText.trim()    : '',
                        pts_allowed:  cells[iPtsA]  ? cells[iPtsA].innerText.trim()   : '',
                        pts_made:     cells[iPtsM]  ? cells[iPtsM].innerText.trim()   : '',
                        total:        cells[iTotal] ? cells[iTotal].innerText.trim()  : ''
                    };
                }).filter(r => r !== null && r.name.length > 0);
            }''')

            print(f"   ✅ Extracted {len(data)} referees from Covers (all columns)")
            return data

        except Exception as e:
            wait_time = 5 * (2 ** attempt)
            print(f"   ⚠️  Attempt {attempt+1} failed: {str(e)[:100]}")
            if attempt < max_retries - 1:
                print(f"   ⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ Covers scrape failed after {max_retries} attempts")
                return []


# --- OddsShark scraper ---

def scrape_oddsshark_ats(page, max_retries: int = 3) -> List[Dict]:
    """Extract referee stats from OddsShark using header-based column matching.

    OddsShark table columns (2025-26):
      Referee, Home Scoring, Away Scoring, Home Wins, Home Losses,
      ATS Home Wins, ATS Home Losses, ATS Home Pushes, Home Fouls, Away Fouls

    Previous version only scraped ATS Home W/L using hardcoded indices.
    Now extracts ALL columns including the critical Home/Away Fouls.
    """
    url = "https://www.oddsshark.com/nba/referee-handicapping-statistics"

    for attempt in range(max_retries):
        try:
            print(f"   🌐 Navigating to OddsShark (attempt {attempt+1}/{max_retries})...")
            page.goto(url, timeout=60000, wait_until='domcontentloaded')
            close_popups(page)
            simulate_human_interaction(page)
            if not wait_for_selector_safe(page, "table tbody tr", timeout=30000, message="OddsShark Table"):
                print("   ❌ Timeout waiting for OddsShark table (even after popup check)")
                continue

            # Header-based extraction — resilient to column reordering
            data = page.evaluate('''() => {
                const table = document.querySelector('table');
                if (!table) return [];

                // Build header index map — normalize by lowercasing + trimming
                const headers = Array.from(table.querySelectorAll('thead th'))
                    .map((th, i) => [th.innerText.trim().toLowerCase(), i]);
                const hmap = Object.fromEntries(headers);

                // Column indices (with fallbacks to known positions)
                const iName    = hmap['referee']           ?? 0;
                const iHomeScr = hmap['home scoring']      ?? 1;
                const iAwayScr = hmap['away scoring']      ?? 2;
                const iHomeW   = hmap['home wins']         ?? 3;
                const iHomeL   = hmap['home losses']       ?? 4;
                const iATSW    = hmap['ats home wins']     ?? 5;
                const iATSL    = hmap['ats home losses']   ?? 6;
                const iATSP    = hmap['ats home pushes']   ?? 7;
                const iHFouls  = hmap['home fouls']        ?? 8;
                const iAFouls  = hmap['away fouls']        ?? 9;

                const rows = Array.from(table.querySelectorAll('tbody tr'));
                return rows.map(row => {
                    const cells = Array.from(row.querySelectorAll('td'));
                    if (cells.length < 6) return null;
                    const nameCell = cells[iName];
                    const nameLink = nameCell ? nameCell.querySelector('a') : null;
                    return {
                        name:         nameLink   ? nameLink.innerText.trim()         :
                                      nameCell   ? nameCell.innerText.trim()          : '',
                        home_scoring: cells[iHomeScr] ? cells[iHomeScr].innerText.trim() : '',
                        away_scoring: cells[iAwayScr] ? cells[iAwayScr].innerText.trim() : '',
                        home_wins:    cells[iHomeW]   ? cells[iHomeW].innerText.trim()   : '0',
                        home_losses:  cells[iHomeL]   ? cells[iHomeL].innerText.trim()   : '0',
                        home_ats_w:   cells[iATSW]    ? cells[iATSW].innerText.trim()    : '0',
                        home_ats_l:   cells[iATSL]    ? cells[iATSL].innerText.trim()    : '0',
                        home_ats_p:   cells[iATSP]    ? cells[iATSP].innerText.trim()    : '0',
                        home_fouls:   cells[iHFouls]  ? cells[iHFouls].innerText.trim()  : '',
                        away_fouls:   cells[iAFouls]  ? cells[iAFouls].innerText.trim()  : ''
                    };
                }).filter(r => r !== null && r.name.length > 0);
            }''')

            print(f"   ✅ Extracted {len(data)} referees from OddsShark (all columns)")
            return data

        except Exception as e:
            wait_time = 5 * (2 ** attempt)
            print(f"   ⚠️  Attempt {attempt+1} failed: {str(e)[:100]}")
            if attempt < max_retries - 1:
                print(f"   ⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ OddsShark scrape failed after {max_retries} attempts")
                return []


# --- Duplicate cleanup ---

def _cleanup_duplicate_rows(conn, dry_run: bool = False) -> int:
    """Remove (#N) badge-suffix duplicate rows from referee_profiles.

    The DB has both "Aaron Smith" and "Aaron Smith (#51)" — the bare row
    has the correct badge_number column and fresh data, so the suffixed
    duplicate is stale. Delete it if the bare-name row exists.
    """
    c = conn.cursor()
    c.execute("""
        SELECT rp.referee_name
        FROM referee_profiles rp
        WHERE rp.referee_name LIKE '%(%'
          AND EXISTS (
              SELECT 1 FROM referee_profiles rp2
              WHERE rp2.referee_name NOT LIKE '%(%'
              AND LOWER(REPLACE(REPLACE(rp2.referee_name, '.', ''), ' ', ''))
                = LOWER(REPLACE(REPLACE(
                    SUBSTR(rp.referee_name, 1, INSTR(rp.referee_name, '(') - 2),
                    '.', ''), ' ', ''))
          )
    """)
    dupes = [row[0] for row in c.fetchall()]

    if dry_run:
        for d in dupes:
            print(f"   🗑️  Would delete duplicate: {d}")
        return len(dupes)

    if dupes:
        placeholders = ','.join(['?'] * len(dupes))
        c.execute(f"DELETE FROM referee_profiles WHERE referee_name IN ({placeholders})", dupes)
        conn.commit()
        print(f"   🧹 Cleaned {len(dupes)} duplicate (#N) rows from referee_profiles")

    return len(dupes)


# --- Style recalculation ---

def _recalculate_style(fouls_per_ref: float) -> str:
    """Determine whistle style from per-ref fouls average.

    Uses the per-ref scale (~11-14 range from internal game logs).
    OddsShark fouls are converted: (home + away) / 3 refs.
    Thresholds derived from 2025-26 rolling_21d_fouls distribution.
    """
    if fouls_per_ref >= 13.5:
        return 'STRICT'
    elif fouls_per_ref <= 11.0:
        return 'LENIENT'
    return 'NEUTRAL'


# --- DB update ---

def update_database(covers_data: List[Dict], oddsshark_data: List[Dict],
                    dry_run: bool = False) -> Tuple[int, int]:
    """Update referee_profiles with scraped betting intelligence.

    Returns (covers_updated, oddsshark_updated) counts.
    Uses normalized name matching to handle formatting differences.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Build normalized lookup: norm_name → DB referee_name
    ref_lookup = _build_ref_name_lookup(conn)

    # --- OddsShark: ATS + Home/Away Fouls ---
    oddsshark_updated = 0
    fouls_lookup = {}  # norm_name → fouls_per_ref (for Covers fallback)

    for ref in oddsshark_data:
        raw_name = ref.get('name', '').strip()
        if not raw_name:
            continue

        norm = _normalize_ref_name(raw_name)
        db_name = ref_lookup.get(norm)
        if not db_name:
            continue

        # Parse ATS
        try:
            ats_w = int(ref.get('home_ats_w', 0))
            ats_l = int(ref.get('home_ats_l', 0))
            ats_p = int(ref.get('home_ats_p', 0))
            ats_total = ats_w + ats_l + ats_p
            ats_bias = round(ats_w / (ats_w + ats_l), 3) if (ats_w + ats_l) > 0 else 0.5
            ats_record = f"{ats_w}-{ats_l}" + (f"-{ats_p}" if ats_p > 0 else "")
        except (ValueError, ZeroDivisionError):
            ats_record = None
            ats_bias = None

        # Parse Home/Away Fouls — the gold data from OddsShark
        # These are per-team averages. Divide total by 3 for per-ref scale
        # to match rolling_21d_fouls (internal L10).
        fouls_per_ref = None
        style = None
        try:
            home_f = float(ref.get('home_fouls', ''))
            away_f = float(ref.get('away_fouls', ''))
            fouls_per_ref = round((home_f + away_f) / 3.0, 2)
            style = _recalculate_style(fouls_per_ref)
            fouls_lookup[norm] = fouls_per_ref
        except (ValueError, TypeError):
            pass

        if dry_run:
            fouls_str = f"fouls/ref={fouls_per_ref:.1f} ({style})" if fouls_per_ref else "no fouls"
            print(f"   📊 OddsShark {db_name}: ATS {ats_record} (bias {ats_bias}) | {fouls_str}")
            oddsshark_updated += 1
            continue

        # Build dynamic UPDATE — only set fields we successfully parsed
        sets = ["home_ats_record = ?", "home_ats_bias = ?",
                "last_updated = CURRENT_TIMESTAMP"]
        params = [ats_record, ats_bias]

        if fouls_per_ref is not None:
            sets.append("avg_fouls_per_game = ?")
            params.append(fouls_per_ref)
        if style is not None:
            sets.append("style = ?")
            params.append(style)

        params.append(db_name)
        c.execute(f"UPDATE referee_profiles SET {', '.join(sets)} WHERE referee_name = ?", params)
        if c.rowcount > 0:
            oddsshark_updated += 1

    # --- Covers: O/U + games_worked + ATS record ---
    covers_updated = 0
    for ref in covers_data:
        raw_name = ref.get('name', '').strip()
        if not raw_name:
            continue

        norm = _normalize_ref_name(raw_name)
        db_name = ref_lookup.get(norm)
        if not db_name:
            continue

        # Parse O/U record
        ou_str = ref.get('ou', '0-0')
        ou_match = re.match(r'(\d+)-(\d+)', ou_str)
        if ou_match:
            over_wins = int(ou_match.group(1))
            under_wins = int(ou_match.group(2))
            games = over_wins + under_wins
            ou_pct = round(over_wins / games, 3) if games > 0 else 0.5
        else:
            ou_pct = 0.5

        # Parse avg total
        try:
            avg_total = float(ref.get('total', '')) if ref.get('total') else None
        except ValueError:
            avg_total = None

        # Derive games_worked from O/U record (over + under = total games)
        # Covers '#' column is blank — O/U record is the reliable source
        games_worked = (over_wins + under_wins) if ou_match else None

        if dry_run:
            print(f"   📊 Covers  {db_name}: O/U {ou_str} ({ou_pct*100:.1f}%) "
                  f"| Total {avg_total} | Games {games_worked}")
            covers_updated += 1
            continue

        # Build dynamic UPDATE
        sets = ["ou_record = ?", "ou_percentage = ?",
                "last_updated = CURRENT_TIMESTAMP", "data_source = 'covers-oddsshark'"]
        params = [ou_str, ou_pct]

        if avg_total is not None:
            sets.append("avg_total = ?")
            params.append(avg_total)
        if games_worked is not None:
            sets.append("games_worked = ?")
            params.append(games_worked)

        params.append(db_name)
        c.execute(f"UPDATE referee_profiles SET {', '.join(sets)} WHERE referee_name = ?", params)
        if c.rowcount > 0:
            covers_updated += 1

    if not dry_run:
        conn.commit()

    conn.close()
    return covers_updated, oddsshark_updated


# --- Main sync ---

def run_sync(dry_run: bool = False):
    print("\n" + "=" * 60)
    print("LUDI INFORMATIO | EXTERNAL INTELLIGENCE SYNC v2")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print("=" * 60)

    if not PLAYWRIGHT_AVAILABLE:
        print("❌ Playwright is required. Install with: pip install playwright && playwright install chromium")
        return

    # Step 0: Clean duplicate (#N) rows before scraping
    print("\n   🧹 Step 0: Checking for duplicate referee rows...")
    conn = sqlite3.connect(DB_PATH)
    dupes_cleaned = _cleanup_duplicate_rows(conn, dry_run)
    conn.close()
    if dupes_cleaned > 0:
        print(f"   {'Would clean' if dry_run else 'Cleaned'} {dupes_cleaned} duplicate rows")
    else:
        print("   No duplicates found")

    covers_data = []
    oddsshark_data = []

    # Determine headless mode based on environment
    is_self_hosted = os.environ.get('IS_SELF_HOSTED') == 'true'
    headless_mode = False if is_self_hosted else True

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless_mode,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
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
        # Pattern 11: setup_page() immediately after new_page()
        setup_page(page)
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
        """)

        print("\n   📡 Step 1: Scraping Covers.com...")
        try:
            covers_data = scrape_covers_ou(page)
        except Exception as e:
            print(f"   ⚠️  Covers scrape failed: {e}")

        print("\n   📡 Step 2: Scraping OddsShark...")
        try:
            oddsshark_data = scrape_oddsshark_ats(page)
        except Exception as e:
            print(f"   ⚠️  OddsShark scrape failed: {e}")

        browser.close()

    if covers_data or oddsshark_data:
        print("\n   💾 Step 3: Updating database...")
        covers_updated, oddsshark_updated = update_database(
            covers_data, oddsshark_data, dry_run)

        if dry_run:
            print(f"\n   🔍 Dry run complete. Covers: {covers_updated} | OddsShark: {oddsshark_updated}")
        else:
            sources = []
            if covers_data:
                sources.append(f"Covers ({len(covers_data)} scraped → {covers_updated} matched)")
            if oddsshark_data:
                sources.append(f"OddsShark ({len(oddsshark_data)} scraped → {oddsshark_updated} matched)")
            print(f"\n   ✅ Sync complete: {', '.join(sources)}")
    else:
        print("\n   ⚠️  No data scraped from either source.")
        print("   💡 Check GitHub Actions logs for detailed error information")
        sys.exit(1)  # Fail loud — workflow should know scraping failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync referee betting trends from Covers.com and OddsShark")
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without updating DB')
    args = parser.parse_args()

    run_sync(args.dry_run)
