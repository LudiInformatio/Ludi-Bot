#!/usr/bin/env python3
"""
LUDI INFORMATIO | WOWY SYNC (With-Or-Without-You)
===================================================
Fetches lineup-level data from PBP Stats API to calculate player on/off court splits.

Schedule: Daily 9:00 AM EST (before game notes populate at 10 AM)
Purpose: Identify beneficiaries when star players are OUT

Usage:
    python scripts/sync_wowy_data.py --days 1  (yesterday only)
    python scripts/sync_wowy_data.py --date 2026-01-17
"""

import sys
import os
import argparse
import sqlite3
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH
from utils.pbp_stats_client import get_game_stats

def get_yesterday_game_ids():
    """Get all game IDs from yesterday."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    c.execute("SELECT DISTINCT game_id FROM games WHERE date = ?", (yesterday,))
    game_ids = [row[0] for row in c.fetchall()]
    conn.close()
    
    return game_ids, yesterday

def calculate_player_wowy(lineup_data, team_abbrev):
    """
    Calculate on/off splits for each player from lineup data.
    
    Args:
        lineup_data: List of lineup dicts from PBP Stats API
        team_abbrev: Team abbreviation (e.g., 'MIL')
        
    Returns:
        Dict mapping player_id -> {on_court_stats, off_court_stats}
    """
    player_stats = {}
    
    for lineup in lineup_data:
        lineup_id = lineup.get('LineupId', '')
        player_ids = lineup_id.split('-')
        
        off_poss = lineup.get('OffPoss', 0)
        off_rating = lineup.get('OffRtg', 0)
        minutes = lineup.get('TimeOnCourt', 0) / 60.0 if 'TimeOnCourt' in lineup else 0
        points = lineup.get('Pts', 0)
        
        # Track each player in this lineup
        for pid in player_ids:
            if pid not in player_stats:
                player_stats[pid] = {
                    'on_court_poss': 0,
                    'on_court_pts': 0,
                    'on_court_minutes': 0,
                    'off_court_poss': 0,
                    'off_court_pts': 0,
                    'off_court_minutes': 0
                }
            
            # This player was on court
            player_stats[pid]['on_court_poss'] += off_poss
            player_stats[pid]['on_court_pts'] += points
            player_stats[pid]['on_court_minutes'] += minutes
        
        # For all team players NOT in this lineup, track off-court stats
        all_team_players = set()
        for lineup2 in lineup_data:
            all_team_players.update(lineup2.get('LineupId', '').split('-'))
        
        off_court_players = all_team_players - set(player_ids)
        for pid in off_court_players:
            if pid not in player_stats:
                player_stats[pid] = {
                    'on_court_poss': 0,
                    'on_court_pts': 0,
                    'on_court_minutes': 0,
                    'off_court_poss': 0,
                    'off_court_pts': 0,
                    'off_court_minutes': 0
                }
            
            player_stats[pid]['off_court_poss'] += off_poss
            player_stats[pid]['off_court_pts'] += points
            player_stats[pid]['off_court_minutes'] += minutes
    
    # Calculate per-100 possession ratings
    wowy_results = {}
    for pid, stats in player_stats.items():
        on_poss = stats['on_court_poss']
        off_poss = stats['off_court_poss']
        
        on_rating = (stats['on_court_pts'] / on_poss * 100) if on_poss > 0 else 0
        off_rating = (stats['off_court_pts'] / off_poss * 100) if off_poss > 0 else 0
        
        wowy_results[pid] = {
            'on_court_minutes': stats['on_court_minutes'],
            'off_court_minutes': stats['off_court_minutes'],
            'on_court_off_rtg': on_rating,
            'off_court_off_rtg': off_rating,
            'on_off_diff': on_rating - off_rating,
            'on_court_pts_per_100': on_rating,
            'off_court_pts_per_100': off_rating,
            'on_court_possessions': on_poss,
            'off_court_possessions': off_poss
        }
    
    return wowy_results

def sync_wowy_for_game(game_id, game_date):
    """Fetch and sync WOWY data for a single game."""
    try:
        # Get lineup data from PBP Stats
        result = get_game_stats(game_id, stat_type='Lineup')
        
        if not result or 'stats' not in result:
            print(f"   ⚠️ No lineup data for {game_id}")
            return 0
        
        conn = sqlite3.connect(DB_PATH, timeout=30)
        c = conn.cursor()
        
        total_inserted = 0
        
        # Process both home and away teams
        for team_key in ['Home', 'Away']:
            if team_key not in result['stats']:
                continue
            
            lineup_data = result['stats'][team_key]
            
            # Infer team abbreviation from first lineup player
            # (This is a simplification - ideally get from games table)
            c.execute("SELECT home_team, away_team FROM games WHERE game_id = ?", (game_id,))
            game_row = c.fetchone()
            if not game_row:
                continue
            
            team_abbrev = game_row[0] if team_key == 'Home' else game_row[1]
            
            # Calculate WOWY splits
            wowy_stats = calculate_player_wowy(lineup_data, team_abbrev)
            
            # Get player names from database
            for player_id, stats in wowy_stats.items():
                c.execute("SELECT name FROM players WHERE player_id = ?", (player_id,))
                player_row = c.fetchone()
                player_name = player_row[0] if player_row else "Unknown"
                
                # Insert or replace
                c.execute('''
                    INSERT OR REPLACE INTO player_wowy_stats (
                        player_id, player_name, team_abbrev, game_date, game_id,
                        on_court_minutes, off_court_minutes,
                        on_court_off_rtg, off_court_off_rtg, on_off_diff,
                        on_court_pts_per_100, off_court_pts_per_100,
                        on_court_possessions, off_court_possessions
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    player_id, player_name, team_abbrev, game_date, game_id,
                    stats['on_court_minutes'], stats['off_court_minutes'],
                    stats['on_court_off_rtg'], stats['off_court_off_rtg'], stats['on_off_diff'],
                    stats['on_court_pts_per_100'], stats['off_court_pts_per_100'],
                    stats['on_court_possessions'], stats['off_court_possessions']
                ))
                total_inserted += 1
        
        conn.commit()
        conn.close()
        
        return total_inserted
    
    except Exception as e:
        print(f"   ❌ Error processing {game_id}: {e}")
        return 0

def run_wowy_sync(target_date=None):
    """Main sync function."""
    print("\n" + "="*50)
    print("📊 LUDI WOWY SYNC (With-Or-Without-You)")
    print("="*50)
    
    if target_date:
        # Sync specific date
        conn = sqlite3.connect(DB_PATH, timeout=30)
        c = conn.cursor()
        c.execute("SELECT DISTINCT game_id FROM games WHERE date = ?", (target_date,))
        game_ids = [row[0] for row in c.fetchall()]
        conn.close()
        date_str = target_date
    else:
        # Sync yesterday by default
        game_ids, date_str = get_yesterday_game_ids()
    
    if not game_ids:
        print(f"⚠️ No games found for {date_str}")
        return
    
    print(f"📅 Date: {date_str}")
    print(f"🎮 Games: {len(game_ids)}")
    print()
    
    total_records = 0
    for game_id in game_ids:
        print(f"Processing {game_id}...")
        count = sync_wowy_for_game(game_id, date_str)
        total_records += count
        print(f"   ✓ {count} player records")
    
    print()
    print(f"✅ WOWY Sync Complete: {total_records} records")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Specific date to sync (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=1, help="Days back from today (default: 1 = yesterday)")
    args = parser.parse_args()
    
    if args.date:
        target_date = args.date
    elif args.days:
        target_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    else:
        target_date = None  # Default to yesterday
    
    run_wowy_sync(target_date)
