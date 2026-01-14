#!/usr/bin/env python3
"""
Daily PBP Stats Sync Script
Fetches shot quality and WOWY data for yesterday's full slate.
Runs at 3:00 AM EST via GitHub Actions.
"""
import sqlite3
import argparse
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pbp_stats_client import get_shot_quality, get_game_stats
from utils.time_utils import get_est_yesterday, get_est_today

DB_PATH = "ludi.db"


def get_yesterday_games():
    """Get all game IDs from yesterday's slate."""
    yesterday = get_est_yesterday()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Query games table for yesterday's games
    c.execute('''
        SELECT game_id FROM games 
        WHERE date = ? OR date LIKE ?
    ''', (yesterday, f"{yesterday}%"))
    
    games = [row[0] for row in c.fetchall()]
    conn.close()
    
    print(f"[PBP_SYNC] Found {len(games)} games from {yesterday}")
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
    
    print(f"[PBP_SYNC] Found {len(games)} games for {target_date}")
    return games


def sync_shot_quality(game_id, conn):
    """Fetch and store shot quality data for a single game."""
    c = conn.cursor()
    
    # Check if already synced
    c.execute('SELECT COUNT(*) FROM shot_quality WHERE game_id = ?', (game_id,))
    if c.fetchone()[0] > 0:
        print(f"  [SKIP] Game {game_id} already synced")
        return 0
    
    # Fetch from PBP Stats
    shot_data = get_shot_quality(game_id)
    if not shot_data:
        print(f"  [WARN] No shot data returned for {game_id}")
        return 0
    
    # Insert all players
    inserted = 0
    for player in shot_data:
        try:
            c.execute('''
                INSERT OR REPLACE INTO shot_quality (
                    game_id, player_id, player_name,
                    shot_quality_avg, shot_distance_avg,
                    shots_taken, shots_made, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pbp_stats')
            ''', (
                game_id,
                player.get('player_id'),
                player.get('player_name'),
                player.get('shot_quality_avg'),
                player.get('shot_distance_avg'),
                player.get('shots_taken'),
                player.get('shots_made')
            ))
            inserted += 1
        except Exception as e:
            print(f"  [ERROR] Insert failed for {player.get('player_name')}: {e}")
    
    return inserted


def run_daily_sync(target_date=None):
    """Run the full daily sync for PBP Stats data."""
    print("=" * 60)
    print("   PBP STATS DAILY SYNC")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Get games
    if target_date:
        games = get_games_for_date(target_date)
        date_str = target_date
    else:
        games, date_str = get_yesterday_games()
    
    if not games:
        print("[PBP_SYNC] No games found. Exiting.")
        return
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    
    total_inserted = 0
    for i, game_id in enumerate(games, 1):
        print(f"[{i}/{len(games)}] Processing {game_id}...")
        inserted = sync_shot_quality(game_id, conn)
        total_inserted += inserted
        conn.commit()
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"   ✅ SYNC COMPLETE")
    print(f"   Games Processed: {len(games)}")
    print(f"   Records Inserted: {total_inserted}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync PBP Stats shot quality data")
    parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD), default: yesterday')
    parser.add_argument('--mode', type=str, default='daily', choices=['daily', 'full_slate'],
                       help='Sync mode (daily=yesterday only, full_slate=all available)')
    
    args = parser.parse_args()
    
    run_daily_sync(target_date=args.date)
