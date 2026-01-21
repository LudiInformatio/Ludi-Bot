#!/usr/bin/env python3
"""
LUDI INFORMATIO | PARALLEL TRACKING SYNC WORKER
================================================
Parallel wrapper for sync_tracking_complete.py
Uses NBA API via utils/nba_api_client (same as original)

Usage:
    python sync_tracking_parallel.py --chunk_index 0 --total_chunks 4
"""

import sys
import os
import sqlite3
import json
import argparse
import time
import logging
from datetime import datetime
from utils.player_id_resolver import normalize_player_name

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.nba_api_client import get_nba_client

# ============================================================
# CONFIGURATION
# ============================================================

REQUEST_DELAY = 3.0  # Delay between API calls (seconds) - increased to avoid NBA.com rate limits
DB_PATH = 'ludi.db'

# ============================================================
# LOGGING
# ============================================================

def setup_logging(chunk_index):
    """Configure worker-specific logging."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"worker_{chunk_index}.log")
    
    # Clear previous log
    open(log_file, 'w').close()
    
    logging.basicConfig(
        level=logging.INFO,
        format=f'%(asctime)s [Worker {chunk_index}] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

# ============================================================
# DATABASE (WAL-SAFE)
# ============================================================

def get_db_connection():
    """Get WAL-safe database connection."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn

def get_all_players(start_date, end_date):
    """Get players with games in window."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT DISTINCT player_name, team_abbreviation, COUNT(*) as games
        FROM player_game_logs
        WHERE game_date >= ? AND game_date <= ?
        GROUP BY player_name
        HAVING games >= 3
        ORDER BY player_name
    ''', (start_date, end_date))
    
    # Normalize player names from database
    players = []
    for row in c.fetchall():
        raw_name = row[0]
        normalized_name = normalize_player_name(raw_name)
        players.append({'name': normalized_name, 'team': row[1], 'games': row[2]})
    conn.close()
    return players

def get_synced_keys():
    """Get already-synced player-date combos."""
    progress_file = 'logs/tracking_sync_progress.json'
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            data = json.load(f)
            return set(data.get('players_synced', []))
    return set()

def save_synced_key(key, chunk_index):
    """Append synced key to worker-specific progress file."""
    progress_file = f'logs/worker_{chunk_index}_progress.json'
    
    keys = []
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            keys = json.load(f)
    
    keys.append(key)
    
    with open(progress_file, 'w') as f:
        json.dump(keys, f)

# ============================================================
# TRACKING SYNC LOGIC (FROM sync_tracking_complete.py)
# ============================================================

def format_date(date_str):
    """Convert YYYY-MM-DD to MM/DD/YYYY for nba_api."""
    parts = date_str.split('-')
    return f"{parts[1]}/{parts[2]}/{parts[0]}"

def get_player_games(player_name, start_date, end_date):
    """Get games for a player in window."""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        SELECT DISTINCT game_date
        FROM player_game_logs
        WHERE player_name = ? AND game_date >= ? AND game_date <= ?
        ORDER BY game_date
    ''', (player_name, start_date, end_date))
    
    games = [row[0] for row in c.fetchall()]
    conn.close()
    return games

def insert_game_tracking(player, game_date, splits, difficulty):
    """Insert tracking data into database."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Parse shot types
    shot_type = splits.get('shot_type', {})
    shot_data = shot_type.get('data', [])
    headers = shot_type.get('headers', [])
    
    drives_fga = drives_fgm = 0
    catch_shoot_fga = catch_shoot_fgm = 0
    pull_up_fga = pull_up_fgm = 0
    
    if headers and shot_data:
        try:
            group_idx = headers.index('GROUP_VALUE')
            fga_idx = headers.index('FGA')
            fgm_idx = headers.index('FGM')
            
            for row in shot_data:
                shot_type_name = str(row[group_idx]).lower()
                if 'drive' in shot_type_name or 'driving' in shot_type_name:
                    drives_fga += row[fga_idx] or 0
                    drives_fgm += row[fgm_idx] or 0
                elif 'catch' in shot_type_name:
                    catch_shoot_fga += row[fga_idx] or 0
                    catch_shoot_fgm += row[fgm_idx] or 0
                elif 'pull' in shot_type_name or 'pullup' in shot_type_name:
                    pull_up_fga += row[fga_idx] or 0
                    pull_up_fgm += row[fgm_idx] or 0
        except (ValueError, IndexError):
            pass
    
    # Parse shot difficulty
    closest_def = difficulty.get('closest_defender', {})
    def_data = closest_def.get('data', [])
    def_headers = closest_def.get('headers', [])
    
    contested_fga = tight_fga = open_fga = wide_open_fga = 0
    
    if def_headers and def_data:
        try:
            group_col = 'CLOSE_DEF_DIST_RANGE' if 'CLOSE_DEF_DIST_RANGE' in def_headers else 'GROUP_VALUE'
            group_idx = def_headers.index(group_col)
            fga_idx = def_headers.index('FGA')
            
            for row in def_data:
                category = str(row[group_idx]).lower()
                fga = row[fga_idx] or 0
                
                if '0-2' in category or 'very tight' in category:
                    contested_fga += fga
                elif '2-4' in category or ('tight' in category and 'very' not in category):
                    tight_fga += fga
                    contested_fga += fga
                elif '4-6' in category or 'open' in category:
                    if 'wide' not in category:
                        open_fga += fga
                elif '6+' in category or '6 ft' in category or 'wide open' in category:
                    wide_open_fga += fga
        except (ValueError, IndexError):
            pass
    
    c.execute('''
        INSERT OR REPLACE INTO player_game_tracking (
            nba_player_id, player_name, nba_game_id, game_date, team_abbr,
            drives_fga, drives_fgm, catch_shoot_fga, catch_shoot_fgm,
            pull_up_fga, pull_up_fgm, contested_fga, tight_fga,
            open_fga, wide_open_fga, avg_defender_dist, synced_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        player['nba_id'], player['name'], 'UNKNOWN', game_date, player['team'],
        drives_fga, drives_fgm, catch_shoot_fga, catch_shoot_fgm,
        pull_up_fga, pull_up_fgm, contested_fga, tight_fga,
        open_fga, wide_open_fga, 0,
        datetime.now().isoformat()
    ))
    
    conn.commit()
    conn.close()

# ============================================================
# WORKER LOGIC
# ============================================================

def run_worker(chunk_index, total_chunks, season, start_date, end_date):
    """Main worker loop."""
    logger = setup_logging(chunk_index)
    logger.info(f"Starting Worker {chunk_index}/{total_chunks}")
    logger.info(f"Season: {season}, Range: {start_date} to {end_date}")
    
    # Get NBA API client
    client = get_nba_client()
    
    # Get all players and filter to this chunk
    all_players = get_all_players(start_date, end_date)
    my_players = [p for i, p in enumerate(all_players) if i % total_chunks == chunk_index]
    
    logger.info(f"Total players: {len(all_players)}, My chunk: {len(my_players)}")
    
    # Get already synced
    synced = get_synced_keys()
    logger.info(f"Already synced globally: {len(synced)}")
    
    # Process players
    processed = 0
    skipped = 0
    errors = 0
    
    for pi, player in enumerate(my_players, 1):
        # Get NBA player ID
        nba_id = client.get_player_id(player['name'])
        if not nba_id:
            logger.warning(f"[{pi}/{len(my_players)}] {player['name']} - No NBA ID found")
            continue
        
        player['nba_id'] = nba_id
        
        # Get games for this player
        games = get_player_games(player['name'], start_date, end_date)
        logger.info(f"[{pi}/{len(my_players)}] {player['name']} - {len(games)} games")
        
        for gi, game_date in enumerate(games, 1):
            key = f"{nba_id}_{game_date}"
            
            # Skip if already synced
            if key in synced:
                logger.info(f"   [{gi}/{len(games)}] {game_date} - skipped")
                skipped += 1
                continue
            
            try:
                # Fetch from NBA API
                splits = client.get_player_shooting_splits(
                    nba_id,
                    season=season,
                    date_from=format_date(game_date),
                    date_to=format_date(game_date)
                )
                
                difficulty = client.get_player_shot_difficulty(
                    nba_id,
                    season=season,
                    date_from=format_date(game_date),
                    date_to=format_date(game_date)
                )
                
                # Insert to database
                insert_game_tracking(player, game_date, splits, difficulty)
                
                # Mark synced
                synced.add(key)
                save_synced_key(key, chunk_index)
                processed += 1
                
                logger.info(f"   [{gi}/{len(games)}] {game_date} - ✓")
                
                # Rate limit
                time.sleep(REQUEST_DELAY)
                
            except Exception as e:
                logger.error(f"   [{gi}/{len(games)}] {game_date} - ERROR: {e}")
                errors += 1
                time.sleep(REQUEST_DELAY)
    
    # Summary
    logger.info("=" * 50)
    logger.info(f"Worker {chunk_index} COMPLETE")
    logger.info(f"Processed: {processed}, Skipped: {skipped}, Errors: {errors}")
    logger.info("=" * 50)

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Parallel tracking sync worker")
    parser.add_argument("--chunk_index", type=int, required=True)
    parser.add_argument("--total_chunks", type=int, default=4)
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--start-date", default="2025-11-14")
    parser.add_argument("--end-date", default="2026-01-14")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between requests in seconds")
    
    args = parser.parse_args()
    
    # Set global delay
    global REQUEST_DELAY
    REQUEST_DELAY = args.delay
    
    run_worker(args.chunk_index, args.total_chunks, args.season, args.start_date, args.end_date)

if __name__ == "__main__":
    main()
