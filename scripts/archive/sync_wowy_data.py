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

from utils.player_id_resolver import normalize_player_name
from database import DB_PATH
from utils.pbp_stats_client import get_game_stats

# Note: TEAM_ID_MAP moved to top of file
# Note: TEAM_ID_MAP moved to top of file
# --- HELPERS ---

def parse_minutes(min_val):
    """Convert MM:SS string or numeric value to decimal minutes."""
    if min_val is None:
        return 0.0
    if isinstance(min_val, (int, float)):
        return float(min_val)
    if isinstance(min_val, str) and ':' in min_val:
        try:
            parts = min_val.split(':')
            if len(parts) == 2:
                return float(parts[0]) + float(parts[1]) / 60.0
        except (ValueError, IndexError):
            pass
    try:
        return float(min_val)
    except (ValueError, TypeError):
        return 0.0

TEAM_ID_MAP = {
    'ATL': '1610612737', 'BOS': '1610612738', 'CLE': '1610612739', 'NOP': '1610612740',
    'CHI': '1610612741', 'DAL': '1610612742', 'DEN': '1610612743', 'GSW': '1610612744', 'GS': '1610612744',
    'HOU': '1610612745', 'LAC': '1610612746', 'LAL': '1610612747', 'MIA': '1610612748',
    'MIL': '1610612749', 'MIN': '1610612750', 'BKN': '1610612751', 'NYK': '1610612752', 'NY': '1610612752',
    'ORL': '1610612753', 'IND': '1610612754', 'PHI': '1610612755', 'PHX': '1610612756', 'PHO': '1610612756',
    'POR': '1610612757', 'SAC': '1610612758', 'SAS': '1610612759', 'SA': '1610612759', 'OKC': '1610612760',
    'TOR': '1610612761', 'UTA': '1610612762', 'MEM': '1610612763', 'WAS': '1610612764',
    'DET': '1610612765', 'CHA': '1610612766'
}

from utils.pbp_stats_client import get_game_logs

def get_yesterday_game_ids():
    """Get all game IDs from yesterday."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    c = conn.cursor()
    
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    c.execute("SELECT DISTINCT game_id, COALESCE(nba_game_id, '') FROM games WHERE date = ?", (yesterday,))
    # Store both IDs
    game_data = [{'id': row[0], 'nba_id': row[1]} for row in c.fetchall()]
    conn.close()
    
    return game_data, yesterday

def resolve_nba_game_id(tank01_id):
    """
    Auto-Heal: Resolve Tank01 ID (20260119_MIL@ATL) to NBA ID (0022500xxx).
    Strategy: Ask API for HOME team's game logs on that date.
    """
    try:
        if "@" not in tank01_id or "_" not in tank01_id:
            return None
            
        # Parse 20260119_MIL@ATL
        date_part, teams = tank01_id.split('_')
        # date_part is YYYYMMDD -> YYYY-MM-DD
        game_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        _, home_abbr = teams.split('@')
        
        home_team_id = TEAM_ID_MAP.get(home_abbr)
        if not home_team_id:
            print(f"   ⚠️ Unknown team abbr: {home_abbr}")
            return None
            
        print(f"   🔧 resolving NBA ID for {home_abbr} on {game_date}...")
        logs = get_game_logs(home_team_id, "Team", "2025-26")
        
        if not logs or 'multi_row_table_data' not in logs:
            return None
            
        logs_data = logs['multi_row_table_data']
        for log in logs_data:
            # PBP Stats API returns a dict per game
            # log is a dict like {'GameId': '0022...', 'Date': '2026-01-19', 'TeamId': '...', ...}
            # We don't need isinstance check if we trust the API, but keeping it safe
            if isinstance(log, dict):
                log_date = log.get('Date', '')
                if log_date == game_date:
                    nba_id = log.get('GameId')
                    print(f"   ✅ FOUND: {tank01_id} -> {nba_id}")
                    
                    # Persist to DB immediately (Heal it)
                    conn = sqlite3.connect(DB_PATH)
                    c = conn.cursor()
                    c.execute("UPDATE games SET nba_game_id = ? WHERE game_id = ?", (nba_id, tank01_id))
                    conn.commit()
                    conn.close()
                    return nba_id
        
        return None
    except Exception as e:
        print(f"   ❌ Resolution Error: {e}")
        return None

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
        # PBP Stats uses EntityId for dash-separated player IDs
        lineup_id = lineup.get('EntityId', '')
        player_ids = lineup_id.split('-')
        
        off_poss = float(lineup.get('OffPoss', 0))
        # PBP Stats uses MM:SS for Minutes in some lineup contexts
        minutes = parse_minutes(lineup.get('Minutes', 0))
        points = float(lineup.get('Points', 0))
        
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

def sync_wowy_for_game(game_id, nba_id, game_date):
    """Fetch and sync WOWY data for a single game."""
    try:
        target_id = game_id # Default
        
        # 1. Resolve ID if needed
        if nba_id:
            target_id = nba_id
        elif "@" in game_id: # Tank01 ID detected
            print(f"   🔍 Custom ID detected ({game_id}). Checking for NBA ID...")
            resolved = resolve_nba_game_id(game_id)
            if resolved:
                target_id = resolved
            else:
                print(f"   ⚠️ Could not resolve NBA ID for {game_id}. Skipping.")
                return 0

        # Get lineup data from PBP Stats
        result = get_game_stats(target_id, stat_type='Lineup')
        
        if not result or 'stats' not in result:
            print(f"   ⚠️ No lineup data for {target_id}")
            return 0
        
        conn = sqlite3.connect(DB_PATH, timeout=30)
        c = conn.cursor()
        
        total_inserted = 0
        
        # Process both home and away teams
        for team_key in ['Home', 'Away']:
            if team_key not in result['stats']:
                continue
            
            periods_data = result['stats'][team_key]
            # NBA.com Lineup data from PBP Stats is dict-based (FullGame, 1, 2...)
            lineup_data = []
            if isinstance(periods_data, dict):
                # Prefer 'FullGame' for whole game splits
                if 'FullGame' in periods_data:
                    lineup_data = periods_data['FullGame']
                else:
                    # Merge all periods (e.g. '1', '2', '3', '4')
                    for p_key, p_list in periods_data.items():
                        if isinstance(p_list, list):
                            lineup_data.extend(p_list)
            elif isinstance(periods_data, list):
                lineup_data = periods_data
            
            # Infer team abbreviation
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
                raw_player_name = player_row[0] if player_row else "Unknown"
                player_name = normalize_player_name(raw_player_name)
                
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
        c.execute("SELECT DISTINCT game_id, COALESCE(nba_game_id, '') FROM games WHERE date = ?", (target_date,))
        game_data = [{'id': row[0], 'nba_id': row[1]} for row in c.fetchall()]
        conn.close()
        date_str = target_date
    else:
        # Sync yesterday by default
        game_data, date_str = get_yesterday_game_ids()
    
    if not game_data:
        print(f"⚠️ No games found for {date_str}")
        return
    
    print(f"📅 Date: {date_str}")
    print(f"🎮 Games: {len(game_data)}")
    print()
    
    total_records = 0
    for g in game_data:
        print(f"Processing {g['id']}...")
        count = sync_wowy_for_game(g['id'], g['nba_id'], date_str)
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
