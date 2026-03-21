#!/usr/bin/env python3
"""
LUDI INFORMATIO | HYBRID WOWY SYNC (TIER 1 + TIER 2)
===================================================
Orchestrator for WOWY lineup data ingestion.
Strategy:
1. Tier 1 (API): standard nba_api (CI-safe, fast, rate-limited)
2. Tier 2 (Ghost): Browser scraping (Local-only, bypasses WAF for diverse datasets)

Usage:
    python scripts/sync_wowy_hybrid.py --days 7  (Tries API -> Fallback to Ghost if local)
    python scripts/sync_wowy_hybrid.py --days 60 --ghost (Forces Ghost Protocol)
"""

import sys
import os
import argparse
import time
import random
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH
from nba_api.stats.endpoints import leaguedashlineups
from scripts.sync_wowy_backfill import run_wowy_backfill
from utils.api_helpers import retry_with_backoff

# Configuration (Updated per community best practices - Feb 15, 2026)
API_RATE_LIMIT = 2.0  # Seconds between API calls (Community recommends 2s to avoid Cloudflare rate limit)
MAX_API_RETRIES = 3
GHOST_THRESHOLD_DAYS = 14  # Use Ghost automatically if > 14 days requested
REQUEST_TIMEOUT = 60  # 60 seconds per request (generous for successful calls)

# Standard headers required for NBA.com (Copied from utils/nba_api_client.py)
HEADERS = {
    'Host': 'stats.nba.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com',
    'x-nba-stats-origin': 'stats',
    'x-nba-stats-token': 'true'
}

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")  # Retry for 30s on lock instead of failing immediately
    conn.row_factory = sqlite3.Row
    return conn

def find_wowy_gap_dates(lookback_days=30):
    """Find dates where canonical_games has games but team_lineups has no data.
    Returns list of date strings (YYYY-MM-DD) that need backfilling."""
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT DISTINCT cg.date
            FROM canonical_games cg
            WHERE cg.date >= date('now', ? || ' days')
              AND cg.date < date('now')
              AND NOT EXISTS (
                  SELECT 1 FROM team_lineups tl
                  WHERE tl.game_date = cg.date
              )
            ORDER BY cg.date
        """, (f"-{lookback_days}",)).fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()

def sync_via_api(target_date: datetime) -> int:
    """
    Tier 1: Fetch single day lineup data via nba_api.
    Returns: Number of records processed.

    Note:
        Enhanced with 120s timeout + retry logic (Phase 6.4)
    """
    nba_date_str = target_date.strftime("%m/%d/%Y")
    db_date_str = target_date.strftime("%Y-%m-%d")

    print(f"   📡 API Request for {nba_date_str}...", flush=True)
    print(f"   [DEBUG] Creating LeagueDashLineups object...", flush=True)

    try:
        # Fetch Advanced Stats (Ratings, Pace, etc)
        print(f"   [DEBUG] Calling NBA API endpoint...", flush=True)
        lineups = leaguedashlineups.LeagueDashLineups(
            season='2025-26',
            season_type_all_star='Regular Season',
            measure_type_detailed_defense='Advanced',
            group_quantity=5,
            league_id_nullable="00",  # NBA league ID
            date_from_nullable=nba_date_str,
            date_to_nullable=nba_date_str,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT  # Using community-recommended 180s timeout
        )
        print(f"   [DEBUG] API object created, waiting {API_RATE_LIMIT}s...", flush=True)

        # Rate limit
        time.sleep(API_RATE_LIMIT)

        print(f"   [DEBUG] Fetching data frames...", flush=True)
        df = lineups.get_data_frames()[0]
        print(f"   [DEBUG] Data frame received, shape: {df.shape}", flush=True)
        
        if df.empty:
            print(f"      ⚠️  No data found for {db_date_str}")
            return 0
            
        # Process and Save
        return save_api_data_to_db(df, db_date_str)
        
    except Exception as e:
        print(f"      ❌ API Error: {e}")
        raise e

def save_api_data_to_db(df: pd.DataFrame, game_date: str) -> int:
    """Maps API dataframe columns to SQLite schema and inserts/upserts."""
    print(f"   [DEBUG] Saving data to DB for {game_date}...", flush=True)
    conn = get_db_connection()
    c = conn.cursor()
    count = 0
    row_errors = 0

    # Ensure columns exist in DataFrame (sometimes missing if no data)
    required_cols = ['GROUP_NAME', 'TEAM_ABBREVIATION', 'GP', 'MIN',
                     'OFF_RATING', 'DEF_RATING', 'NET_RATING', 'PACE',
                     'TS_PCT', 'EFG_PCT']

    print(f"   [DEBUG] Checking required columns...", flush=True)
    if not all(col in df.columns for col in required_cols):
        print("      ⚠️  DataFrame missing required columns", flush=True)
        return 0

    print(f"   [DEBUG] Processing {len(df)} rows...", flush=True)
    for _, row in df.iterrows():
        try:
            # Map API -> DB (columns must match team_lineups schema)
            vals = {
                'game_date': game_date,
                'lineup_players': row['GROUP_NAME'],
                'lineup_id': row.get('GROUP_ID', ''),   # dash-separated NBA player IDs
                'team_abbreviation': row['TEAM_ABBREVIATION'],
                'games_played': int(row['GP']),
                'minutes': float(row['MIN']),
                'off_rating': float(row['OFF_RATING']),
                'def_rating': float(row['DEF_RATING']),
                'net_rating': float(row['NET_RATING']),
                'pace': float(row['PACE']),
                'ts_pct': float(row['TS_PCT']),
                'efg_pct': float(row['EFG_PCT']),
                'possessions': 0
            }

            # Calculate possessions from pace and minutes
            if vals['pace'] > 0 and vals['minutes'] > 0:
                vals['possessions'] = int(round(vals['pace'] * vals['minutes'] / 48.0))

            # UPSERT Logic
            columns = ', '.join(vals.keys())
            placeholders = ', '.join(['?'] * len(vals))
            sql = f'''
                INSERT OR IGNORE INTO team_lineups ({columns})
                VALUES ({placeholders})
            '''
            c.execute(sql, list(vals.values()))
            count += 1
            
        except Exception as e:
            row_errors += 1
            if row_errors <= 3:
                print(f"      ⚠️  Row error: {e}", flush=True)
            continue

    print(f"   [DEBUG] Committing {count} records to database...", flush=True)
    conn.commit()
    conn.close()
    total_rows = count + row_errors
    if row_errors > 0:
        print(f"      ⚠️  {row_errors}/{total_rows} rows failed to write", flush=True)
    if total_rows > 0 and row_errors == total_rows:
        print(f"      ❌ ALL {total_rows} rows failed — database may be locked", flush=True)
        sys.exit(1)
    print(f"   [DEBUG] Database operations complete for {game_date}", flush=True)
    return count

def run_hybrid_sync(start_date: datetime, end_date: datetime, force_ghost: bool = False):
    print("\n" + "="*60)
    print("🔁 WOWY HYBRID SYNC: TIER 1 (API) + TIER 2 (GHOST)")
    print(f"📅 Range: {start_date.strftime('%Y-%m-%d')} -> {end_date.strftime('%Y-%m-%d')}")
    print("="*60)

    # Environment Checks
    is_ci = os.environ.get('CI') == 'true' or os.environ.get('GITHUB_ACTIONS') == 'true' or os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS')
    
    # [NEW] CI Graceful Skip
    # Skip only if NOT self-hosted (Tier 1 API is blocked on Cloud IPs)
    if is_ci and not os.environ.get('IS_SELF_HOSTED'):
        print("\n" + "="*60)
        print("⚠️  CI ENVIRONMENT DETECTED")
        print("="*60)
        print("   The 'LeagueDashLineups' endpoint blocks Cloud/CI IP addresses.")
        print("   Tier 1 (API) cannot run here.")
        print("   ")
        print("   ✅ SKIPPING WOWY SYNC (Graceful Exit)")
        print("   👉 Please run this script LOCALLY to update lineup data:")
        print("      python scripts/sync_wowy_hybrid.py --days 7")
        print("="*60 + "\n")
        return

    num_days = (end_date - start_date).days + 1
    
    # Strategy Selection
    use_ghost = force_ghost
    
    if not use_ghost:
        if num_days > GHOST_THRESHOLD_DAYS:
            print(f"ℹ️  Large date range ({num_days} days) detected. Switching to Ghost Protocol (Local Optimized).")
            use_ghost = True
            
    if use_ghost:
        # Allow Ghost in CI if self-hosted (Tier 2 supported via headless browser)
        if is_ci and not os.environ.get('IS_SELF_HOSTED'):
            print("❌ Cannot run Ghost Protocol in Cloud CI (No browser). Skipping.")
            return

        print("👻 Engaging Ghost Protocol (Browser Mode)...")
        # FORCE VISIBLE MODE for Self-Hosted (Headless is blocked by WAF)
        is_headless = False if os.environ.get('IS_SELF_HOSTED') else is_ci
        run_wowy_backfill(start_date, end_date, headless=is_headless)
        return

    # TIER 1: API EXECUTION
    print("🚀 Engaging Tier 1: nba_api (Headless/Fast)...")
    
    current_date = start_date
    api_failures = 0
    total_records = 0
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"\n[{date_str}] Processing...")
        
        success = False
        for attempt in range(MAX_API_RETRIES):
            try:
                count = sync_via_api(current_date)
                print(f"   ✅ Synced {count} lineup records (committed to database)")
                total_records += count
                success = True
                break
            except Exception as e:
                print(f"      ⚠️  Attempt {attempt+1}/{MAX_API_RETRIES} failed: {e}")
                time.sleep(2 * (attempt + 1)) # Backoff
        
        if not success:
            print(f"   ❌ Failed to sync {date_str} via API.")
            api_failures += 1
            
            # Smart Fallback Logic
            # Allow fallback if local OR self-hosted CI
            can_fallback = not is_ci or os.environ.get('IS_SELF_HOSTED')
            
            if can_fallback and api_failures >= 1:
                print("\n⚠️  Too many API failures. NBA WAF might be blocking.")
                print("   👉 Switching to Tier 2: Ghost Protocol for remaining dates...")
                # FORCE VISIBLE MODE for Self-Hosted (Headless is blocked by WAF)
                is_headless = False if os.environ.get('IS_SELF_HOSTED') else is_ci
                run_wowy_backfill(current_date, end_date, headless=is_headless)
                return

        current_date += timedelta(days=1)

    print("\n" + "="*60)
    print("✅ Hybrid Sync Complete")
    print(f"   Total Records (Tier 1): {total_records}")
    print("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Days to look back")
    parser.add_argument("--ghost", action="store_true", help="Force Ghost Protocol (Browser Mode)")
    parser.add_argument("--gap-fill", action="store_true",
        help="Auto-detect and fill dates missing from team_lineups (last 30 days)")
    parser.add_argument("--gap-fill-days", type=int, default=30,
        help="Lookback window for gap detection (default: 30 days)")
    parser.add_argument("--start-date", help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD")
    
    args = parser.parse_args()

    if args.gap_fill:
        gap_dates = find_wowy_gap_dates(lookback_days=args.gap_fill_days)
        if not gap_dates:
            print("✅ No WOWY gaps detected in last N days.")
            sys.exit(0)
        print(f"🔍 Found {len(gap_dates)} gap date(s): {gap_dates}")
        for date_str in gap_dates:
            target = datetime.strptime(date_str, "%Y-%m-%d")
            run_wowy_backfill(target, target, headless=False)
            time.sleep(random.uniform(3.0, 6.0))
        print("✅ WOWY gap-fill complete.")
        sys.exit(0)
    
    end = datetime.now() - timedelta(days=1)  # Yesterday (most recent completed games)
    if args.end_date:
        end = datetime.strptime(args.end_date, "%Y-%m-%d")

    start = end - timedelta(days=args.days - 1)  # --days 1 = just yesterday; --days 7 = 7 days ending yesterday
    if args.start_date:
        start = datetime.strptime(args.start_date, "%Y-%m-%d")
        
    run_hybrid_sync(start, end, force_ghost=args.ghost)
