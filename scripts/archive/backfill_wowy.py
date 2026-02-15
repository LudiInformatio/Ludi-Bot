#!/usr/bin/env python3
"""
LUDI INFORMATIO | WOWY HISTORICAL BACKFILL
==========================================
Backfills WOWY (With-Or-Without-You) stats from PBP Stats API.

Usage:
    python scripts/backfill_wowy.py                  # Full season backfill
    python scripts/backfill_wowy.py --days 7        # Last 7 days only
    python scripts/backfill_wowy.py --start 2026-01-01 --end 2026-01-18
"""

import sys
import os
import sqlite3
import argparse
import requests
import time
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH

BASE_URL = "https://api.pbpstats.com"
CURRENT_SEASON = "2025-26"

def get_session():
    """Create a session with retry logic."""
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    session = requests.Session()
    retry = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

session = get_session()


def get_all_games():
    """Fetch all games for the season from PBP Stats."""
    url = f"{BASE_URL}/get-games/nba"
    params = {"Season": CURRENT_SEASON, "SeasonType": "Regular Season"}
    
    try:
        response = session.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get('results', [])
    except Exception as e:
        print(f"❌ Error fetching games: {e}")
        return []


def get_lineup_stats(game_id):
    """Fetch lineup stats for a game."""
    url = f"{BASE_URL}/get-game-stats"
    params = {"GameId": game_id, "Type": "Lineup"}
    
    try:
        response = session.get(url, params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"      ⚠️ Error fetching lineup stats: {e}")
        return None


def calculate_wowy_from_lineups(lineup_data, team_abbrev):
    """
    Calculate on/off splits for each player from lineup data.
    
    Returns dict: player_id -> {on_court_stats, off_court_stats}
    """
    player_stats = defaultdict(lambda: {
        'on_court_poss': 0, 'on_court_pts': 0, 'on_court_minutes': 0,
        'off_court_poss': 0, 'off_court_pts': 0, 'off_court_minutes': 0
    })
    
    # Collect all players who appeared in any lineup
    all_players = set()
    
    for lineup in lineup_data:
        lineup_id = lineup.get('LineupId', '')
        player_ids = lineup_id.split('-') if lineup_id else []
        all_players.update(player_ids)
        
        poss = lineup.get('OffPoss', 0)
        pts = lineup.get('Pts', 0)
        minutes = lineup.get('Minutes', 0)
        
        # Track on-court stats
        for pid in player_ids:
            player_stats[pid]['on_court_poss'] += poss
            player_stats[pid]['on_court_pts'] += pts
            player_stats[pid]['on_court_minutes'] += minutes
    
    # Calculate off-court stats (when NOT in lineup)
    for lineup in lineup_data:
        lineup_id = lineup.get('LineupId', '')
        in_lineup = set(lineup_id.split('-')) if lineup_id else set()
        off_court = all_players - in_lineup
        
        poss = lineup.get('OffPoss', 0)
        pts = lineup.get('Pts', 0)
        minutes = lineup.get('Minutes', 0)
        
        for pid in off_court:
            player_stats[pid]['off_court_poss'] += poss
            player_stats[pid]['off_court_pts'] += pts
            player_stats[pid]['off_court_minutes'] += minutes
    
    # Calculate per-100 ratings
    results = {}
    for pid, stats in player_stats.items():
        on_poss = stats['on_court_poss']
        off_poss = stats['off_court_poss']
        
        on_rating = (stats['on_court_pts'] / on_poss * 100) if on_poss > 0 else 0
        off_rating = (stats['off_court_pts'] / off_poss * 100) if off_poss > 0 else 0
        
        results[pid] = {
            'on_court_minutes': stats['on_court_minutes'],
            'off_court_minutes': stats['off_court_minutes'],
            'on_court_off_rtg': round(on_rating, 1),
            'off_court_off_rtg': round(off_rating, 1),
            'on_off_diff': round(on_rating - off_rating, 1),
            'on_court_pts_per_100': round(on_rating, 1),
            'off_court_pts_per_100': round(off_rating, 1),
            'on_court_possessions': on_poss,
            'off_court_possessions': off_poss
        }
    
    return results


def sync_wowy_for_game(conn, game):
    """Process a single game and insert WOWY stats."""
    game_id = game['GameId']
    game_date = game['Date']
    home_team = game['HomeTeamAbbreviation']
    away_team = game['AwayTeamAbbreviation']
    
    # Fetch lineup stats
    data = get_lineup_stats(game_id)
    if not data:
        return 0
    
    cursor = conn.cursor()
    total_inserted = 0
    
    # Process both teams
    for team_key, team_abbrev in [('home', home_team), ('away', away_team)]:
        lineup_data = data.get(team_key, [])
        if not lineup_data:
            continue
        
        wowy = calculate_wowy_from_lineups(lineup_data, team_abbrev)
        
        # Get player names from players table
        for player_id, stats in wowy.items():
            cursor.execute("SELECT name FROM players WHERE player_id = ?", (player_id,))
            row = cursor.fetchone()
            player_name = row[0] if row else f"Player_{player_id}"
            
            try:
                cursor.execute('''
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
            except Exception as e:
                print(f"      Error inserting {player_name}: {e}")
    
    conn.commit()
    return total_inserted


def run_backfill(start_date=None, end_date=None, days=None):
    """Main backfill function."""
    print("\n" + "="*60)
    print("📊 LUDI WOWY BACKFILL (With-Or-Without-You)")
    print("="*60)
    
    # Determine date range
    if days:
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    elif not start_date:
        start_date = "2025-10-21"  # Season start
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 Date Range: {start_date} → {end_date}")
    
    # Fetch all games
    print("\n🔄 Fetching game list from PBP Stats...")
    all_games = get_all_games()
    
    if not all_games:
        print("❌ No games found")
        return
    
    # Filter to date range
    games = [g for g in all_games if start_date <= g['Date'] <= end_date]
    print(f"🎮 Found {len(games)} games in date range (out of {len(all_games)} total)")
    
    if not games:
        print("⚠️ No games in specified date range")
        return
    
    # Check what we already have
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT game_id FROM player_wowy_stats")
    existing_games = {row[0] for row in cursor.fetchall()}
    
    new_games = [g for g in games if g['GameId'] not in existing_games]
    print(f"📈 New games to process: {len(new_games)} (skipping {len(games) - len(new_games)} already synced)")
    
    if not new_games:
        print("✅ All games already synced!")
        conn.close()
        return
    
    # Process games
    print("\n" + "-"*60)
    total_records = 0
    processed = 0
    
    for game in sorted(new_games, key=lambda x: x['Date']):
        processed += 1
        date_str = game['Date']
        game_id = game['GameId']
        matchup = f"{game['AwayTeamAbbreviation']} @ {game['HomeTeamAbbreviation']}"
        
        print(f"[{processed}/{len(new_games)}] {date_str} | {matchup} ({game_id})...", end=" ")
        
        count = sync_wowy_for_game(conn, game)
        total_records += count
        
        if count > 0:
            print(f"✅ {count} players")
        else:
            print("⚠️ No data")
        
        time.sleep(0.2)  # Rate limit
    
    conn.close()
    
    # Summary
    print("\n" + "="*60)
    print(f"✅ WOWY BACKFILL COMPLETE")
    print(f"   Games processed: {processed}")
    print(f"   Records inserted: {total_records}")
    print("="*60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill WOWY stats")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="Days back from today")
    args = parser.parse_args()
    
    run_backfill(start_date=args.start, end_date=args.end, days=args.days)
