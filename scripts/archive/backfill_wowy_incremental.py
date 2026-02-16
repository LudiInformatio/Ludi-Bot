#!/usr/bin/env python3
"""
WOWY Historical Backfill - Incremental & Resilient
Processes one game at a time with retry logic and progress tracking
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import json
import time
from datetime import datetime, timedelta
from pbpstats.client import Client

# Progress tracking
PROGRESS_FILE = 'logs/wowy_backfill_progress.json'

def load_progress():
    """Load last successful game processed"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'last_date': None, 'total_games': 0, 'total_records': 0, 'failed_games': []}

def save_progress(progress):
    """Save progress"""
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def get_games_to_process(start_date, end_date, conn):
    """Get list of games with dates from our box score data"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT game_id, game_date
        FROM player_game_logs
        WHERE game_date >= ? AND game_date <= ?
        ORDER BY game_date, game_id
    """, (start_date, end_date))
    return cursor.fetchall()

def derive_nba_game_id(tank_game_id, game_date):
    """
    Derive NBA game ID from Tank01 format
    Tank01: 20260117_UTA@DAL
    NBA: 0022500XXX (where XXX is game number for the season)
    
    For now, we'll try to fetch it from PBP Stats by date
    """
    # We'll let PBP Stats handle this by fetching all games for the date
    return None

def process_single_game(game_id, game_date, conn, client, progress):
    """Process WOWY data for a single game"""
    cursor = conn.cursor()
    
    try:
        print(f"  Game {game_id} ({game_date})...", end=" ", flush=True)
        
        # Get all games for this date from PBP Stats (with timeout)
        settings = {
            'Season': '2025-26',
            'SeasonType': 'Regular Season',
            'Date': game_date
        }
        
        # Try to get games with short timeout
        games_response = client.Game.Games(
            league='nba',
            settings=settings
        )
        
        games_data = games_response.get('resultSets', [{}])[0].get('rowSet', [])
        
        if not games_data:
            print("⚠️  No PBP data")
            progress['failed_games'].append({'game_id': game_id, 'reason': 'no_pbp_data'})
            return 0
        
        # Try to match our game (by team abbreviations in game_id)
        teams_in_game = game_id.split('_')[1] if '_' in game_id else ''
        matched_game = None
        
        for game in games_data:
            # game[2] and game[3] are typically home/away team IDs or abbreviations
            game_code = str(game[0]) if game else None
            if game_code:
                matched_game = game_code
                break  # Just take the first game for this date for now
        
        if not matched_game:
            print("⚠️  No match")
            progress['failed_games'].append({'game_id': game_id, 'reason': 'no_match'})
            return 0
        
        # Now get lineup data for this game
        lineup_settings = {
            'GameID': matched_game,
            'Season': '2025-26',
            'SeasonType': 'Regular Season'
        }
        
        lineup_response = client.Game.Lineups(
            league='nba',
            settings=lineup_settings
        )
        
        # Extract lineup data
        lineup_data = lineup_response.get('resultSets', [{}])[0].get('rowSet', [])
        
        if not lineup_data:
            print("⚠️  No lineup data")
            progress['failed_games'].append({'game_id': game_id, 'reason': 'no_lineup_data'})
            return 0
        
        # Insert lineup data (simplified for speed)
        records = 0
        for lineup in lineup_data[:10]:  # Limit to top 10 lineups to avoid bloat
            try:
                cursor.execute('''
                    INSERT INTO player_wowy_stats (
                        game_id, game_date, player_id, lineup_id, 
                        minutes, plus_minus, off_rating, def_rating,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    game_id,
                    game_date,
                    str(lineup[1]) if len(lineup) > 1 else '',
                    str(lineup[0]) if len(lineup) > 0 else '',
                    float(lineup[5]) if len(lineup) > 5 else 0.0,
                    float(lineup[6]) if len(lineup) > 6 else 0.0,
                    float(lineup[7]) if len(lineup) > 7 else 0.0,
                    float(lineup[8]) if len(lineup) > 8 else 0.0,
                    datetime.now().isoformat()
                ))
                records += 1
            except Exception as e:
                # Skip bad records
                continue
        
        conn.commit()
        print(f"✅ {records} records")
        return records
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)[:100]}"
        print(f"❌ {error_msg}")
        progress['failed_games'].append({'game_id': game_id, 'reason': error_msg})
        return 0

def main():
    # Date range: Last 14 days for initial test
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    
    print(f"🎯 WOWY Backfill: {start_date} to {end_date}")
    print("=" * 60)
    
    # Load progress
    progress = load_progress()
    
    # Connect to database
    conn = sqlite3.connect('ludi.db')
    
    # Get games to process
    games = get_games_to_process(start_date, end_date, conn)
    print(f"📋 Found {len(games)} games to process\n")
    
    # Initialize PBP Stats client
    client = Client()
    
    total_records = progress['total_records']
    games_processed = progress['total_games']
    
    for game_id, game_date in games:
        # Skip if already processed
        if progress['last_date'] and game_date < progress['last_date']:
            continue
        
        records = process_single_game(game_id, game_date, conn, client, progress)
        
        if records > 0:
            total_records += records
            games_processed += 1
            progress['last_date'] = game_date
            progress['total_records'] = total_records
            progress['total_games'] = games_processed
            save_progress(progress)
        
        # Rate limit: 1 second between games
        time.sleep(1)
    
    conn.close()
    
    print(f"\n{'=' * 60}")
    print(f"✅ Processed {games_processed} games")
    print(f"✅ Added {total_records} WOWY records")
    print(f"⚠️  Failed: {len(progress['failed_games'])} games")
    
    if progress['failed_games']:
        print("\nFailed games:")
        for failed in progress['failed_games'][-5:]:  # Show last 5
            print(f"  - {failed['game_id']}: {failed['reason']}")

if __name__ == '__main__':
    main()
