#!/usr/bin/env python3
"""
PBP Stats Backfill Script
Backfills shot_quality table for a date range using the PBP Stats API.
No rate limits - runs quickly (~4-5 min for 60 days of games).

Usage:
    python scripts/sync_pbp_backfill.py --start 2025-11-14 --end 2026-01-13
"""
import sys
import os
import sqlite3
import argparse
import time
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pbp_stats_client import get_shot_quality, get_game_stats

DB_PATH = "ludi.db"


def get_all_games_in_range(start_date, end_date):
    """Get all game IDs from the games table within date range."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        SELECT game_id, date FROM games
        WHERE date >= ? AND date <= ?
        ORDER BY date
    ''', (start_date, end_date))

    games = [(row[0], row[1]) for row in c.fetchall()]
    conn.close()

    return games


def get_synced_game_ids():
    """Get game IDs already in shot_quality table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT DISTINCT game_id FROM shot_quality')
    synced = set(row[0] for row in c.fetchall())
    conn.close()

    return synced


def sync_game_shot_quality(game_id, conn):
    """Fetch and store shot quality data for a single game."""
    c = conn.cursor()

    # Fetch from PBP Stats
    shot_data = get_shot_quality(game_id)
    if not shot_data:
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
            pass  # Skip duplicates silently

    return inserted


def run_backfill(start_date, end_date):
    """Run the full backfill for PBP Stats data."""
    print("=" * 60)
    print("   PBP STATS HISTORICAL BACKFILL")
    print(f"   Date Range: {start_date} to {end_date}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Get all games in range
    all_games = get_all_games_in_range(start_date, end_date)
    print(f"\n[BACKFILL] Found {len(all_games)} total games in range")

    # Get already synced
    synced = get_synced_game_ids()
    print(f"[BACKFILL] Already synced: {len(synced)} games")

    # Filter to unsynced
    to_sync = [(gid, date) for gid, date in all_games if gid not in synced]
    print(f"[BACKFILL] Remaining to sync: {len(to_sync)} games\n")

    if not to_sync:
        print("[BACKFILL] All games already synced. Exiting.")
        return

    # Connect to database
    conn = sqlite3.connect(DB_PATH, timeout=30)

    total_inserted = 0
    start_time = time.time()

    for i, (game_id, game_date) in enumerate(to_sync, 1):
        print(f"[{i}/{len(to_sync)}] {game_date} - {game_id}...", end=" ")

        inserted = sync_game_shot_quality(game_id, conn)
        total_inserted += inserted

        print(f"{inserted} players")
        conn.commit()

        # Light delay (optional, PBP Stats has no rate limits)
        time.sleep(0.3)

    conn.close()

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print(f"   BACKFILL COMPLETE")
    print(f"   Games Processed: {len(to_sync)}")
    print(f"   Records Inserted: {total_inserted}")
    print(f"   Time Elapsed: {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill PBP Stats shot quality data")
    parser.add_argument('--start', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, required=True, help='End date (YYYY-MM-DD)')

    args = parser.parse_args()

    run_backfill(args.start, args.end)
