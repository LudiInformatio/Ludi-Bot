#!/usr/bin/env python3
"""
Daily NBA API Tracking Sync Script
Fetches tracking data for yesterday's full slate (all games, all players).
Runs at 4:00 AM EST via GitHub Actions (isolated heavy sync).

This script uses parallel processing to optimize ingestion speed.
"""
import sqlite3
import argparse
from datetime import datetime
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.time_utils import get_est_yesterday

DB_PATH = "ludi.db"
MAX_WORKERS = 2  # Reduced from 5 to prevent timeouts


def get_yesterday_game_ids():
    """Get all game IDs from yesterday's slate."""
    yesterday = get_est_yesterday()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT game_id FROM games 
        WHERE date = ? OR date LIKE ?
    ''', (yesterday, f"{yesterday}%"))
    
    games = [row[0] for row in c.fetchall()]
    conn.close()
    
    print(f"[TRACKING_SYNC] Found {len(games)} games from {yesterday}")
    return games, yesterday


def get_games_for_date(target_date):
    """Get all game IDs for a specific date."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''
        SELECT game_id FROM games 
        WHERE date = ? OR date LIKE ?
    ''', (target_date, f"{target_date}%"))
    
    games = [row[0] for row in c.fetchall()]
    conn.close()
    
    return games


def fetch_tracking_for_game(game_id):
    """
    Fetch NBA API tracking data for a single game.
    Returns list of player tracking records.
    
    Note: This is a placeholder that should connect to the existing
    sync_tracking_complete.py logic or nba_api endpoints.
    """
    # Import here to avoid circular imports
    try:
        from nba_api.stats.endpoints import boxscoreadvancedv2
        from nba_api.stats.endpoints import boxscoreplayertrackv2
        
        # Fetch advanced box score (defensive stats, etc.)
        try:
            adv = boxscoreadvancedv2.BoxScoreAdvancedV2(game_id=game_id)
            player_stats = adv.player_stats.get_data_frame()
            
            records = []
            for _, row in player_stats.iterrows():
                records.append({
                    'game_id': game_id,
                    'player_id': row.get('PLAYER_ID'),
                    'player_name': row.get('PLAYER_NAME'),
                    'team_id': row.get('TEAM_ID'),
                    'off_rating': row.get('OFF_RATING'),
                    'def_rating': row.get('DEF_RATING'),
                    'net_rating': row.get('NET_RATING'),
                    'ts_pct': row.get('TS_PCT'),
                    'efg_pct': row.get('EFG_PCT'),
                    'usg_pct': row.get('USG_PCT'),
                    'pace': row.get('PACE')
                })
            
            return records
        except Exception as e:
            print(f"  [ERROR] Failed to fetch tracking for {game_id}: {e}")
            return []
            
    except ImportError:
        print("[TRACKING_SYNC] nba_api not available, skipping tracking fetch")
        return []


def save_tracking_data(records, conn):
    """Save tracking records to database."""
    if not records:
        return 0
    
    c = conn.cursor()
    inserted = 0
    
    for rec in records:
        try:
            c.execute('''
                INSERT OR REPLACE INTO tracking_data (
                    game_id, player_id, player_name, team_id,
                    off_rating, def_rating, net_rating,
                    ts_pct, efg_pct, usg_pct, pace
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                rec['game_id'],
                rec['player_id'],
                rec['player_name'],
                rec['team_id'],
                rec.get('off_rating'),
                rec.get('def_rating'),
                rec.get('net_rating'),
                rec.get('ts_pct'),
                rec.get('efg_pct'),
                rec.get('usg_pct'),
                rec.get('pace')
            ))
            inserted += 1
        except Exception as e:
            print(f"  [ERROR] Insert failed: {e}")
    
    return inserted


def check_game_synced(game_id):
    """Check if game tracking data already exists."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM tracking_data WHERE game_id = ?', (game_id,))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

def process_game(game_id):
    """Process a single game (for parallel execution)."""
    # Rate limit (3.0s delay per thread)
    time.sleep(3.0)
    
    # Check if already done (Resume capability)
    if check_game_synced(game_id):
        return {
            'game_id': game_id,
            'records': [],
            'count': 0,
            'elapsed': 0,
            'skipped': True
        }

    start = time.time()
    records = fetch_tracking_for_game(game_id)
    elapsed = time.time() - start
    
    return {
        'game_id': game_id,
        'records': records,
        'count': len(records),
        'elapsed': elapsed,
        'skipped': False
    }


def run_daily_sync(target_date=None, parallel=True):
    """Run the full daily tracking sync."""
    print("=" * 60)
    print("   NBA API TRACKING DAILY SYNC")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Mode: {'Parallel' if parallel else 'Sequential'} ({MAX_WORKERS} workers)")
    print("=" * 60)
    
    # Get games
    if target_date:
        games = get_games_for_date(target_date)
        date_str = target_date
    else:
        games, date_str = get_yesterday_game_ids()
    
    if not games:
        print("[TRACKING_SYNC] No games found. Exiting.")
        return
    
    print(f"[TRACKING_SYNC] Processing {len(games)} games for {date_str}")
    
    # Process games
    conn = sqlite3.connect(DB_PATH)
    total_inserted = 0
    
    if parallel:
        # Parallel processing
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(process_game, gid): gid for gid in games}
            
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                game_id = result['game_id']
                
                if result.get('skipped'):
                    print(f"[{i}/{len(games)}] {game_id}: Skipped (Already Synced)")
                elif result['records']:
                    inserted = save_tracking_data(result['records'], conn)
                    total_inserted += inserted
                    conn.commit()
                    print(f"[{i}/{len(games)}] {game_id}: {inserted} records ({result['elapsed']:.1f}s)")
                else:
                    print(f"[{i}/{len(games)}] {game_id}: No data")
    else:
        # Sequential processing (fallback)
        for i, game_id in enumerate(games, 1):
            result = process_game(game_id)
            if result['records']:
                inserted = save_tracking_data(result['records'], conn)
                total_inserted += inserted
                conn.commit()
                print(f"[{i}/{len(games)}] {game_id}: {inserted} records")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"   ✅ TRACKING SYNC COMPLETE")
    print(f"   Games Processed: {len(games)}")
    print(f"   Records Inserted: {total_inserted}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync NBA API tracking data")
    parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD), default: yesterday')
    parser.add_argument('--sequential', action='store_true', help='Use sequential processing instead of parallel')
    
    args = parser.parse_args()
    
    run_daily_sync(target_date=args.date, parallel=not args.sequential)
