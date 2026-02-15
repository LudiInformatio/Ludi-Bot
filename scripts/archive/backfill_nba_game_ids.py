#!/usr/bin/env python3
"""
Backfill NBA Game IDs from PBP Stats

This script fetches NBA.com format game IDs from the PBP Stats API
and updates the games table with the correct nba_game_id for each game.

Usage:
    python scripts/backfill_nba_game_ids.py
"""
import sys
import os
import sqlite3
import requests
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "ludi.db"
CURRENT_SEASON = "2025-26"


def fetch_pbp_games():
    """Fetch all games from PBP Stats API for the current season."""
    print(f"[BACKFILL] Fetching games from PBP Stats for {CURRENT_SEASON}...")
    
    url = "https://api.pbpstats.com/get-games/nba"
    params = {
        "Season": CURRENT_SEASON,
        "SeasonType": "Regular Season"
    }
    
    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        games = data.get('results', [])
        print(f"[BACKFILL] Fetched {len(games)} games from PBP Stats")
        return games
    except requests.RequestException as e:
        print(f"[BACKFILL] Error fetching games: {e}")
        return []


def ensure_nba_game_id_column(conn):
    """Add nba_game_id column to games table if it doesn't exist."""
    c = conn.cursor()
    
    # Check if column exists
    c.execute("PRAGMA table_info(games)")
    columns = [col[1] for col in c.fetchall()]
    
    if 'nba_game_id' not in columns:
        print("[BACKFILL] Adding nba_game_id column to games table...")
        c.execute("ALTER TABLE games ADD COLUMN nba_game_id TEXT")
        conn.commit()
        print("[BACKFILL] Column added successfully")
    else:
        print("[BACKFILL] nba_game_id column already exists")


def build_game_lookup(pbp_games):
    """
    Build a lookup dict: (date, home_team, away_team) -> nba_game_id
    
    PBP Stats uses full team IDs, we need to map to abbreviations.
    """
    # PBP Stats team ID to abbreviation mapping
    team_id_to_abbr = {
        '1610612737': 'ATL', '1610612738': 'BOS', '1610612751': 'BKN',
        '1610612766': 'CHA', '1610612741': 'CHI', '1610612739': 'CLE',
        '1610612742': 'DAL', '1610612743': 'DEN', '1610612765': 'DET',
        '1610612744': 'GS', '1610612745': 'HOU', '1610612754': 'IND',
        '1610612746': 'LAC', '1610612747': 'LAL', '1610612763': 'MEM',
        '1610612748': 'MIA', '1610612749': 'MIL', '1610612750': 'MIN',
        '1610612740': 'NOP', '1610612752': 'NY', '1610612760': 'OKC',
        '1610612753': 'ORL', '1610612755': 'PHI', '1610612756': 'PHO',
        '1610612757': 'POR', '1610612758': 'SAC', '1610612759': 'SA',
        '1610612761': 'TOR', '1610612762': 'UTA', '1610612764': 'WAS'
    }
    
    # Alternative abbreviations used in our DB
    abbr_aliases = {
        'GS': ['GS', 'GSW', 'G.S.'],
        'NY': ['NY', 'NYK', 'N.Y.'],
        'NOP': ['NOP', 'NO', 'N.O.'],
        'SA': ['SA', 'SAS', 'S.A.'],
        'PHX': ['PHX', 'PHO'],
    }

    def normalize_team_abbr(abbr: str) -> str:
        """
        Normalize team abbreviations to canonical form.

        This ensures consistent matching regardless of which variant
        appears in The-Odds-API vs PBP Stats API.
        """
        normalizations = {
            'PHO': 'PHX',  # Phoenix Suns
            'GS': 'GSW',   # Golden State Warriors
            'NO': 'NOP',   # New Orleans Pelicans
            'SA': 'SAS',   # San Antonio Spurs
            'NY': 'NYK',   # New York Knicks
        }
        return normalizations.get(abbr, abbr)
    
    lookup = {}
    
    for game in pbp_games:
        nba_game_id = game.get('GameId')
        date = game.get('Date')
        home_abbr = normalize_team_abbr(game.get('HomeTeamAbbreviation', ''))
        away_abbr = normalize_team_abbr(game.get('AwayTeamAbbreviation', ''))

        if nba_game_id and date and home_abbr and away_abbr:
            # Create entries for all possible abbreviation combinations
            for home_var in [home_abbr] + abbr_aliases.get(home_abbr, []):
                for away_var in [away_abbr] + abbr_aliases.get(away_abbr, []):
                    key = (date, home_var.upper(), away_var.upper())
                    lookup[key] = nba_game_id
    
    return lookup


def backfill_game_ids(conn, lookup):
    """Update games table with NBA game IDs."""
    c = conn.cursor()
    
    # Get all games that need updating
    c.execute("""
        SELECT game_id, date, home_team, away_team, nba_game_id 
        FROM games 
        WHERE nba_game_id IS NULL OR nba_game_id = ''
    """)
    games = c.fetchall()
    
    print(f"[BACKFILL] Found {len(games)} games needing NBA game ID update")
    
    updated = 0
    not_found = []
    
    for game_id, date, home_team, away_team, current_nba_id in games:
        # Try to find matching NBA game ID
        key = (date, home_team.upper() if home_team else '', 
               away_team.upper() if away_team else '')
        
        nba_game_id = lookup.get(key)
        
        if nba_game_id:
            c.execute("""
                UPDATE games SET nba_game_id = ? WHERE game_id = ?
            """, (nba_game_id, game_id))
            updated += 1
        else:
            not_found.append((game_id, date, home_team, away_team))
    
    conn.commit()
    
    print(f"[BACKFILL] Updated {updated} games with NBA game IDs")
    
    if not_found:
        print(f"[BACKFILL] Could not find NBA game IDs for {len(not_found)} games:")
        for gid, date, home, away in not_found[:10]:
            print(f"  - {date}: {away} @ {home} (DB ID: {gid})")
        if len(not_found) > 10:
            print(f"  ... and {len(not_found) - 10} more")
    
    return updated, not_found


def main():
    print("=" * 60)
    print("   NBA GAME ID BACKFILL")
    print(f"   Season: {CURRENT_SEASON}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Fetch games from PBP Stats
    pbp_games = fetch_pbp_games()
    if not pbp_games:
        print("[BACKFILL] No games fetched. Exiting.")
        return
    
    # Build lookup
    lookup = build_game_lookup(pbp_games)
    print(f"[BACKFILL] Built lookup table with {len(lookup)} entries")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH, timeout=30)
    
    # Ensure column exists
    ensure_nba_game_id_column(conn)
    
    # Backfill
    updated, not_found = backfill_game_ids(conn, lookup)
    
    # Also update any games that already have NBA format IDs in game_id column
    c = conn.cursor()
    c.execute("""
        UPDATE games 
        SET nba_game_id = game_id 
        WHERE game_id LIKE '002%' 
        AND (nba_game_id IS NULL OR nba_game_id = '')
    """)
    already_nba = c.rowcount
    conn.commit()
    
    if already_nba > 0:
        print(f"[BACKFILL] Copied {already_nba} existing NBA-format game_ids to nba_game_id")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("   BACKFILL COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
