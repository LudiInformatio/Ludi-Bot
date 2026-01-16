#!/usr/bin/env python3
"""
LUDI INFORMATIO | REFEREE DATA BACKFILL ENGINE
Phase 4: Historical Data Population

Purpose:
    - Fetches official referee crews for past games using nba_api
    - Updates 'games' table with comma-separated referee names
    - Enables backtesting of bias models and learning algorithms
    - Optimized to fetch only recent window (default 30 days) to respect API limits

Usage:
    python scripts/backfill_referee_assignments.py [--days 30] [--dry-run]
"""

import sys
import os
import argparse
import sqlite3
import time
from datetime import datetime, timedelta
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH
from nba_api.stats.endpoints import boxscoresummaryv2

# Configuration
API_SLEEP_SECONDS = 0.6  # Respect rate limits (NBA API is strict)


def get_games_needing_backfill(conn: sqlite3.Connection, days: int) -> List[Dict]:
    """
    Find games within the lookback window that are missing referee data.
    """
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    c = conn.cursor()
    
    # Query for games with valid NBA ID but NULL or empty referee_crew
    # Joined with games table filter by date
    c.execute('''
        SELECT game_id, nba_game_id, date, home_team, away_team
        FROM games
        WHERE 
            date >= ? 
            AND nba_game_id IS NOT NULL 
            AND (referee_crew IS NULL OR referee_crew = '')
        ORDER BY date DESC
    ''', (cutoff_date,))
    
    games = []
    for row in c.fetchall():
        games.append({
            'game_id': row[0],
            'nba_game_id': row[1],
            'date': row[2],
            'matchup': f"{row[4]} @ {row[3]}"
        })
    
    return games


def fetch_referees_for_game(nba_game_id: str) -> str:
    """
    Fetch officials from NBA API for a specific game.
    Returns comma-separated string of Full Names.
    """
    try:
        box = boxscoresummaryv2.BoxScoreSummaryV2(game_id=nba_game_id)
        officials_df = box.officials.get_data_frame()
        
        if officials_df.empty:
            return None
            
        # Combine First + Last Name
        # Check column names (they vary sometimes)
        if 'FIRST_NAME' in officials_df.columns and 'LAST_NAME' in officials_df.columns:
            officials_df['FULL_NAME'] = officials_df['FIRST_NAME'] + ' ' + officials_df['LAST_NAME']
            refs = officials_df['FULL_NAME'].tolist()
            return ", ".join(refs)
            
        return None
        
    except Exception as e:
        print(f"      ❌ API Error: {e}")
        return None


def run_backfill(days: int, dry_run: bool = False):
    print("\n" + "=" * 60)
    print("LUDI INFORMATIO | REFEREE BACKFILL ENGINE")
    print(f"Scope: Last {days} days")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        target_games = get_games_needing_backfill(conn, days)
        
        if not target_games:
            print("\n✅ All recent games have referee data. No backfill needed.")
            return

        print(f"\nFound {len(target_games)} games missing referee data.\n")
        
        updated_count = 0
        failed_count = 0
        
        for i, game in enumerate(target_games, 1):
            print(f"[{i}/{len(target_games)}] {game['date']} {game['matchup']} ({game['nba_game_id']})...", end=" ", flush=True)
            
            crew_str = fetch_referees_for_game(game['nba_game_id'])
            
            if crew_str:
                print(f"✅ Found: {crew_str}")
                
                if not dry_run:
                    c = conn.cursor()
                    c.execute('''
                        UPDATE games 
                        SET referee_crew = ? 
                        WHERE game_id = ?
                    ''', (crew_str, game['game_id']))
                    conn.commit()
                
                updated_count += 1
            else:
                print("⚠️  No data found")
                failed_count += 1
            
            # Respect rate limits
            time.sleep(API_SLEEP_SECONDS)
        
        print("\n" + "=" * 60)
        print("BACKFILL SUMMARY")
        print("=" * 60)
        print(f"Games Processed: {len(target_games)}")
        print(f"Updated: {updated_count}")
        print(f"Failed/Missing: {failed_count}")
        print(f"Success Rate: {round(updated_count/len(target_games)*100, 1)}%")
        
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=30, help='Days lookback window (default: 30)')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without updating DB')
    args = parser.parse_args()
    
    run_backfill(args.days, args.dry_run)
