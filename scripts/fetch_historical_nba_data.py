#!/usr/bin/env python3
"""
LUDI INFORMATIO | Historical NBA Data Fetch Script
===================================================
Fetches historical tracking data for backtesting shot quality and defender metrics.

Phase 1.2 of nba_api historical backtest plan.

Usage:
    ./venv/bin/python scripts/fetch_historical_nba_data.py

    # Or with options:
    ./venv/bin/python scripts/fetch_historical_nba_data.py --days 60 --min-mpg 15 --limit 10

Output:
    data/raw_nba_data/shot_quality_history.csv
    data/raw_nba_data/workload_history.csv
    data/raw_nba_data/matchup_history.csv
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pandas as pd
from tqdm import tqdm

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.nba_api_client import get_nba_client


# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH = "ludi.db"
OUTPUT_DIR = "data/raw_nba_data"
SEASON = "2025-26"

# Default parameters
DEFAULT_DAYS = 60  # Last 60 days of data
DEFAULT_MIN_MPG = 15  # Minimum minutes per game threshold
DEFAULT_PLAYER_LIMIT = None  # None = all qualifying players


# =============================================================================
# DATABASE QUERIES
# =============================================================================

def get_active_rotation_players(
    db_path: str,
    days: int = 60,
    min_mpg: float = 15.0,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Query ludi.db to find active rotation players.

    Criteria: Players averaging >15 MPG over the last N days.

    Args:
        db_path: Path to SQLite database
        days: Number of days to look back
        min_mpg: Minimum minutes per game threshold
        limit: Optional limit on number of players returned

    Returns:
        List of player dicts with: player_id, player_name, team, avg_mpg, games_played
    """
    conn = sqlite3.connect(db_path)

    # Calculate date threshold
    date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    query = """
    SELECT
        player_id,
        player_name,
        team_abbreviation as team,
        AVG(minutes) as avg_mpg,
        COUNT(*) as games_played
    FROM player_game_logs
    WHERE game_date >= ?
      AND minutes > 0
      AND player_id < 10000000  -- Filter for valid NBA player IDs (6-7 digits max)
      AND player_id > 0
    GROUP BY player_id, player_name, team_abbreviation
    HAVING AVG(minutes) >= ?
    ORDER BY AVG(minutes) DESC
    """

    if limit:
        query += f" LIMIT {limit}"

    cursor = conn.execute(query, (date_threshold, min_mpg))
    columns = ['player_id', 'player_name', 'team', 'avg_mpg', 'games_played']

    players = []
    for row in cursor.fetchall():
        players.append(dict(zip(columns, row)))

    conn.close()
    return players


# =============================================================================
# DATA EXTRACTION HELPERS
# =============================================================================

def _get_col_idx(headers: List, col_name: str) -> int:
    """Safely get column index from headers."""
    try:
        return headers.index(col_name)
    except ValueError:
        return -1


def _safe_get(row: List, idx: int, default=None):
    """Safely get value from row at index."""
    if idx >= 0 and idx < len(row):
        return row[idx]
    return default


def extract_shot_quality_data(
    player_id: int,
    player_name: str,
    team: str,
    splits_data: Dict,
    difficulty_data: Dict
) -> Dict[str, Any]:
    """
    Extract shot quality metrics from API responses.

    Returns:
        Dict with player info and shot quality metrics
    """
    result = {
        'player_id': player_id,
        'player_name': player_name,
        'team': team,
        'fetch_date': datetime.now().strftime('%Y-%m-%d'),

        # Overall stats
        'total_fgm': None,
        'total_fga': None,
        'total_fg_pct': None,

        # Shot area percentages (from splits)
        'restricted_area_fga': None,
        'restricted_area_fg_pct': None,
        'paint_non_ra_fga': None,
        'paint_non_ra_fg_pct': None,
        'midrange_fga': None,
        'midrange_fg_pct': None,
        'corner_3_fga': None,
        'corner_3_fg_pct': None,
        'above_break_3_fga': None,
        'above_break_3_fg_pct': None,

        # Defender distance (from difficulty)
        'very_tight_fga': None,  # 0-2 ft
        'very_tight_fg_pct': None,
        'tight_fga': None,  # 2-4 ft
        'tight_fg_pct': None,
        'open_fga': None,  # 4-6 ft
        'open_fg_pct': None,
        'wide_open_fga': None,  # 6+ ft
        'wide_open_fg_pct': None,

        # Contested shot ratio (calculated)
        'contested_shot_pct': None,  # (very_tight + tight) / total
    }

    # Extract overall stats
    if splits_data and 'overall' in splits_data:
        overall = splits_data['overall']
        headers = overall.get('headers', [])
        data = overall.get('data', [])

        if headers and data and len(data) > 0:
            fgm_idx = _get_col_idx(headers, 'FGM')
            fga_idx = _get_col_idx(headers, 'FGA')
            fg_pct_idx = _get_col_idx(headers, 'FG_PCT')

            row = data[0]
            result['total_fgm'] = _safe_get(row, fgm_idx)
            result['total_fga'] = _safe_get(row, fga_idx)
            result['total_fg_pct'] = _safe_get(row, fg_pct_idx)

    # Extract shot area data
    if splits_data and 'shot_area' in splits_data:
        shot_area = splits_data['shot_area']
        headers = shot_area.get('headers', [])
        data = shot_area.get('data', [])

        if headers and data:
            area_idx = _get_col_idx(headers, 'GROUP_VALUE')
            fga_idx = _get_col_idx(headers, 'FGA')
            fg_pct_idx = _get_col_idx(headers, 'FG_PCT')

            for row in data:
                area = _safe_get(row, area_idx, '')
                fga = _safe_get(row, fga_idx)
                fg_pct = _safe_get(row, fg_pct_idx)

                if 'Restricted' in str(area):
                    result['restricted_area_fga'] = fga
                    result['restricted_area_fg_pct'] = fg_pct
                elif 'Paint' in str(area) and 'Non' in str(area):
                    result['paint_non_ra_fga'] = fga
                    result['paint_non_ra_fg_pct'] = fg_pct
                elif 'Mid-Range' in str(area):
                    result['midrange_fga'] = fga
                    result['midrange_fg_pct'] = fg_pct
                elif 'Corner' in str(area):
                    result['corner_3_fga'] = fga
                    result['corner_3_fg_pct'] = fg_pct
                elif 'Above' in str(area) and 'Break' in str(area):
                    result['above_break_3_fga'] = fga
                    result['above_break_3_fg_pct'] = fg_pct

    # Extract defender distance data
    if difficulty_data and 'closest_defender' in difficulty_data:
        defender = difficulty_data['closest_defender']
        headers = defender.get('headers', [])
        data = defender.get('data', [])

        if headers and data:
            dist_idx = _get_col_idx(headers, 'CLOSE_DEF_DIST_RANGE')
            fga_idx = _get_col_idx(headers, 'FGA')
            fg_pct_idx = _get_col_idx(headers, 'FG_PCT')

            total_fga = 0
            contested_fga = 0

            for row in data:
                dist = _safe_get(row, dist_idx, '')
                fga = _safe_get(row, fga_idx, 0) or 0
                fg_pct = _safe_get(row, fg_pct_idx)

                total_fga += fga

                if '0-2' in str(dist):
                    result['very_tight_fga'] = fga
                    result['very_tight_fg_pct'] = fg_pct
                    contested_fga += fga
                elif '2-4' in str(dist):
                    result['tight_fga'] = fga
                    result['tight_fg_pct'] = fg_pct
                    contested_fga += fga
                elif '4-6' in str(dist):
                    result['open_fga'] = fga
                    result['open_fg_pct'] = fg_pct
                elif '6+' in str(dist) or 'Open' in str(dist):
                    result['wide_open_fga'] = fga
                    result['wide_open_fg_pct'] = fg_pct

            # Calculate contested shot percentage
            if total_fga > 0:
                result['contested_shot_pct'] = round(contested_fga / total_fga, 3)

    return result


def extract_workload_data(
    player_id: int,
    player_name: str,
    team: str,
    tracking_data: Dict
) -> Dict[str, Any]:
    """
    Extract workload metrics from tracking API response.
    """
    result = {
        'player_id': player_id,
        'player_name': player_name,
        'team': team,
        'fetch_date': datetime.now().strftime('%Y-%m-%d'),

        # Games played
        'games_played': None,

        # Rebounding workload
        'total_reb': None,
        'oreb': None,
        'dreb': None,
        'contested_reb': None,
        'uncontested_reb': None,
        'contested_reb_pct': None,

        # Passing workload
        'total_passes': None,
        'total_assists': None,
    }

    # Extract rebounding data from 'overall' (not 'contested')
    if tracking_data and 'rebounding' in tracking_data:
        reb_data = tracking_data['rebounding']

        # Check for error
        if isinstance(reb_data, dict) and 'error' in reb_data:
            pass  # Skip if error
        elif 'overall' in reb_data:
            overall = reb_data['overall']
            headers = overall.get('headers', [])
            data = overall.get('data', [])

            if headers and data and len(data) > 0:
                row = data[0]
                g_idx = _get_col_idx(headers, 'G')
                reb_idx = _get_col_idx(headers, 'REB')
                oreb_idx = _get_col_idx(headers, 'OREB')
                dreb_idx = _get_col_idx(headers, 'DREB')
                c_reb_idx = _get_col_idx(headers, 'C_REB')
                uc_reb_idx = _get_col_idx(headers, 'UC_REB')
                c_pct_idx = _get_col_idx(headers, 'C_REB_PCT')

                result['games_played'] = _safe_get(row, g_idx)
                result['total_reb'] = _safe_get(row, reb_idx)
                result['oreb'] = _safe_get(row, oreb_idx)
                result['dreb'] = _safe_get(row, dreb_idx)
                result['contested_reb'] = _safe_get(row, c_reb_idx)
                result['uncontested_reb'] = _safe_get(row, uc_reb_idx)
                result['contested_reb_pct'] = _safe_get(row, c_pct_idx)

    # Extract passing data
    if tracking_data and 'passing' in tracking_data:
        pass_data = tracking_data['passing']

        # Check for error
        if isinstance(pass_data, dict) and 'error' in pass_data:
            pass
        elif 'passes_made' in pass_data:
            passes = pass_data['passes_made']
            headers = passes.get('headers', [])
            data = passes.get('data', [])

            if headers and data:
                pass_idx = _get_col_idx(headers, 'PASS')
                ast_idx = _get_col_idx(headers, 'AST')

                total_passes = 0
                total_ast = 0

                for row in data:
                    passes_val = _safe_get(row, pass_idx, 0) or 0
                    ast_val = _safe_get(row, ast_idx, 0) or 0
                    total_passes += passes_val
                    total_ast += ast_val

                result['total_passes'] = total_passes
                result['total_assists'] = total_ast

    return result


def extract_matchup_data(
    player_id: int,
    player_name: str,
    team: str,
    matchup_data: Dict
) -> List[Dict[str, Any]]:
    """
    Extract defender matchup metrics from get_player_offensive_matchups() response.

    Uses boxscorematchupsv3 data aggregated across recent games.

    Returns list of dicts (one per defender faced).
    """
    results = []

    # Check if we have valid data from get_player_offensive_matchups()
    if not matchup_data:
        return results

    # Handle error case
    if 'error' in matchup_data:
        return results

    # Extract games analyzed count
    games_analyzed = matchup_data.get('games_analyzed', 0)

    # Extract primary defenders list
    primary_defenders = matchup_data.get('primary_defenders', [])

    for defender in primary_defenders:
        results.append({
            'player_id': player_id,
            'player_name': player_name,
            'team': team,
            'fetch_date': datetime.now().strftime('%Y-%m-%d'),
            'games_sampled': games_analyzed,
            'defender_id': defender.get('defender_id'),
            'defender_name': defender.get('defender_name'),
            'matchup_minutes': defender.get('matchup_minutes', 0),
            'fga_vs_defender': defender.get('fga', 0),
            'fgm_vs_defender': defender.get('fgm', 0),
            'fg_pct_vs_defender': defender.get('fg_pct', 0.0),
            'games_vs_defender': defender.get('games', 0),
        })

    return results


# =============================================================================
# MAIN FETCH LOGIC
# =============================================================================

def fetch_historical_data(
    days: int = DEFAULT_DAYS,
    min_mpg: float = DEFAULT_MIN_MPG,
    player_limit: Optional[int] = DEFAULT_PLAYER_LIMIT,
    verbose: bool = True
) -> Dict[str, pd.DataFrame]:
    """
    Main function to fetch historical NBA data for backtesting.

    Args:
        days: Number of days to look back
        min_mpg: Minimum minutes per game threshold
        player_limit: Optional limit on players to fetch (for testing)
        verbose: Print progress messages

    Returns:
        Dict with 3 DataFrames: shot_quality, workload, matchups
    """
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Calculate date range
    date_to = datetime.now()
    date_from = date_to - timedelta(days=days)
    date_from_str = date_from.strftime('%m/%d/%Y')
    date_to_str = date_to.strftime('%m/%d/%Y')

    if verbose:
        print(f"\n{'='*60}")
        print(f"   LUDI HISTORICAL NBA DATA FETCH")
        print(f"   Date Range: {date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}")
        print(f"   Season: {SEASON}")
        print(f"{'='*60}")

    # Step 1: Get qualifying players from database
    if verbose:
        print(f"\n[1/4] Querying database for players with >{min_mpg} MPG...")

    players = get_active_rotation_players(
        DB_PATH,
        days=days,
        min_mpg=min_mpg,
        limit=player_limit
    )

    if verbose:
        print(f"   Found {len(players)} qualifying players")

    if not players:
        print("   ERROR: No players found matching criteria!")
        return {}

    # Step 2: Initialize NBA API client
    client = get_nba_client()

    # Step 3: Fetch data for each player
    shot_quality_records = []
    workload_records = []
    matchup_records = []

    failed_players = []

    if verbose:
        print(f"\n[2/4] Fetching NBA API data (4 endpoints per player)...")
        print(f"   Estimated time: ~{len(players) * 4 / 60:.1f} minutes at 1 req/sec")

    # Use tqdm for progress bar
    for player in tqdm(players, desc="Fetching player data", disable=not verbose):
        player_id = player['player_id']
        player_name = player['player_name']
        team = player['team']

        try:
            # Fetch shooting splits (with date range)
            splits = client.get_player_shooting_splits(
                player_id=player_id,
                season=SEASON,
                date_from=date_from_str,
                date_to=date_to_str
            )

            # Fetch shot difficulty (with date range)
            difficulty = client.get_player_shot_difficulty(
                player_id=player_id,
                season=SEASON,
                date_from=date_from_str,
                date_to=date_to_str
            )

            # Fetch tracking data
            tracking = client.get_player_tracking(
                player_id=player_id,
                season=SEASON
            )

            # Fetch matchup data using boxscorematchupsv3 (aggregated over last 5 games)
            matchups = client.get_player_offensive_matchups(
                player_id=player_id,
                season=SEASON,
                last_n_games=5
            )

            # Extract and store data
            shot_quality = extract_shot_quality_data(
                player_id, player_name, team, splits, difficulty
            )
            shot_quality_records.append(shot_quality)

            workload = extract_workload_data(
                player_id, player_name, team, tracking
            )
            workload_records.append(workload)

            matchup_list = extract_matchup_data(
                player_id, player_name, team, matchups
            )
            matchup_records.extend(matchup_list)

        except Exception as e:
            failed_players.append({
                'player_id': player_id,
                'player_name': player_name,
                'error': str(e)[:100]
            })
            continue

    # Step 4: Convert to DataFrames and save
    if verbose:
        print(f"\n[3/4] Processing results...")
        print(f"   Shot quality records: {len(shot_quality_records)}")
        print(f"   Workload records: {len(workload_records)}")
        print(f"   Matchup records: {len(matchup_records)}")
        if failed_players:
            print(f"   Failed players: {len(failed_players)}")

    result = {}

    # Shot Quality CSV
    if shot_quality_records:
        df_shot_quality = pd.DataFrame(shot_quality_records)
        shot_quality_path = os.path.join(OUTPUT_DIR, 'shot_quality_history.csv')
        df_shot_quality.to_csv(shot_quality_path, index=False)
        result['shot_quality'] = df_shot_quality
        if verbose:
            print(f"   Saved: {shot_quality_path}")

    # Workload CSV
    if workload_records:
        df_workload = pd.DataFrame(workload_records)
        workload_path = os.path.join(OUTPUT_DIR, 'workload_history.csv')
        df_workload.to_csv(workload_path, index=False)
        result['workload'] = df_workload
        if verbose:
            print(f"   Saved: {workload_path}")

    # Matchup CSV
    if matchup_records:
        df_matchups = pd.DataFrame(matchup_records)
        matchup_path = os.path.join(OUTPUT_DIR, 'matchup_history.csv')
        df_matchups.to_csv(matchup_path, index=False)
        result['matchups'] = df_matchups
        if verbose:
            print(f"   Saved: {matchup_path}")

    # Save failed players log
    if failed_players:
        df_failed = pd.DataFrame(failed_players)
        failed_path = os.path.join(OUTPUT_DIR, 'failed_players.csv')
        df_failed.to_csv(failed_path, index=False)
        if verbose:
            print(f"   Saved: {failed_path}")

    if verbose:
        print(f"\n[4/4] Complete!")
        print(f"{'='*60}")

    return result


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Fetch historical NBA tracking data for backtesting'
    )
    parser.add_argument(
        '--days', type=int, default=DEFAULT_DAYS,
        help=f'Number of days to look back (default: {DEFAULT_DAYS})'
    )
    parser.add_argument(
        '--min-mpg', type=float, default=DEFAULT_MIN_MPG,
        help=f'Minimum minutes per game threshold (default: {DEFAULT_MIN_MPG})'
    )
    parser.add_argument(
        '--limit', type=int, default=None,
        help='Limit number of players to fetch (for testing)'
    )
    parser.add_argument(
        '--quiet', action='store_true',
        help='Suppress progress output'
    )

    args = parser.parse_args()

    fetch_historical_data(
        days=args.days,
        min_mpg=args.min_mpg,
        player_limit=args.limit,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
