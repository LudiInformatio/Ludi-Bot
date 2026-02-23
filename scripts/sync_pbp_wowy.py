"""
PBP Stats WOWY Sync Script (Phase 6.3 + Phase 6.5c Resume)

Fetches full-season on/off splits from PBP Stats API for top usage players.
Stores in player_season_wowy table for BENEFICIARY confidence scoring.

Usage:
    python scripts/sync_pbp_wowy.py --verbose
    python scripts/sync_pbp_wowy.py --team LAL --verbose
    python scripts/sync_pbp_wowy.py --dry-run --top 5
    python scripts/sync_pbp_wowy.py --resume --verbose   # Resume from previous incomplete run

Author: Ludi Informatio
Date: February 2, 2026 (Phase 6.3)
Updated: February 3, 2026 (Phase 6.5c - Resume capability)
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional

MAX_RUNTIME_SECONDS = 1200  # 20 minutes

# Add project root to path
sys.path.insert(0, '.')

from utils.pbp_stats_client import get_on_off

# NBA team IDs mapping (NBA.com official IDs)
TEAM_IDS = {
    'ATL': '1610612737', 'BOS': '1610612738', 'BKN': '1610612751',
    'CHA': '1610612766', 'CHI': '1610612741', 'CLE': '1610612739',
    'DAL': '1610612742', 'DEN': '1610612743', 'DET': '1610612765',
    'GSW': '1610612744', 'HOU': '1610612745', 'IND': '1610612754',
    'LAC': '1610612746', 'LAL': '1610612747', 'MEM': '1610612763',
    'MIA': '1610612748', 'MIL': '1610612749', 'MIN': '1610612750',
    'NOP': '1610612740', 'NYK': '1610612752', 'OKC': '1610612760',
    'ORL': '1610612753', 'PHI': '1610612755', 'PHX': '1610612756',
    'POR': '1610612757', 'SAC': '1610612758', 'SAS': '1610612759',
    'TOR': '1610612761', 'UTA': '1610612762', 'WAS': '1610612764',
}

CURRENT_SEASON = "2025-26"

# Resume state management
RESUME_STATE_FILE = "cache/pbp_wowy_sync_state.json"


def _load_resume_state() -> Optional[Dict]:
    """
    Load resume state from file if exists and valid.

    Returns:
        Dict with state or None if missing/corrupt
    """
    if not os.path.exists(RESUME_STATE_FILE):
        return None

    try:
        with open(RESUME_STATE_FILE, 'r') as f:
            state = json.load(f)

        # Validate required fields
        required = ['completed_teams', 'remaining_teams', 'status']
        if not all(k in state for k in required):
            print(f"   Warning: Invalid state file, starting fresh")
            return None

        return state
    except Exception as e:
        print(f"   Warning: Error loading state: {e}, starting fresh")
        return None


def _save_resume_state(completed: List[str], remaining: List[str],
                       status: str = "in_progress", reason: str = None) -> None:
    """
    Save resume state to file.

    Args:
        completed: List of completed team abbreviations
        remaining: List of remaining team abbreviations
        status: "in_progress", "paused", or "complete"
        reason: Optional reason for pause (e.g., "timeout", "error")
    """
    os.makedirs(os.path.dirname(RESUME_STATE_FILE), exist_ok=True)

    state = {
        "sync_version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "total_teams": len(completed) + len(remaining),
        "completed_teams": completed,
        "remaining_teams": remaining,
        "last_completed_team": completed[-1] if completed else None,
        "status": status,
        "pause_reason": reason
    }

    # Atomic write (temp file then rename)
    temp_file = RESUME_STATE_FILE + ".tmp"
    with open(temp_file, 'w') as f:
        json.dump(state, f, indent=2)
    os.replace(temp_file, RESUME_STATE_FILE)

    print(f"   State saved: {len(completed)}/{state['total_teams']} teams completed")


def _clear_resume_state() -> None:
    """Delete resume state file on successful completion."""
    if os.path.exists(RESUME_STATE_FILE):
        os.remove(RESUME_STATE_FILE)
        print("   Cleared resume state (sync complete)")


def _is_team_completed(state: Optional[Dict], team_abbr: str) -> bool:
    """Check if team was already completed in previous run."""
    if not state:
        return False
    return team_abbr in state.get('completed_teams', [])


def get_db_connection(db_path: str = "ludi.db") -> sqlite3.Connection:
    """Get database connection."""
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn


def get_top_players(conn: sqlite3.Connection, team_abbr: str, top_n: int = 10) -> List[Dict]:
    """
    Get top N players by usage from players table.

    Resolves Tank01 composite IDs to canonical NBA IDs via player_canonical_ids table.
    This fixes the ~40% API failure rate from unresolved IDs.

    Args:
        conn: Database connection
        team_abbr: Team abbreviation (e.g., 'LAL')
        top_n: Number of players to return (default: 10)

    Returns:
        List of player dicts with player_id (canonical NBA ID), name, team, usg_pct
    """
    cursor = conn.cursor()

    # Join with player_canonical_ids to resolve Tank01 composite IDs to NBA IDs
    # COALESCE prefers canonical_id (which is the proper NBA ID) over raw player_id
    # Use subquery with GROUP BY to deduplicate players (Tank01 sometimes has multiple entries)
    cursor.execute("""
        SELECT player_id, name, team, usg_pct
        FROM (
            SELECT
                COALESCE(c.canonical_id, p.player_id) as player_id,
                c.full_name as name,
                p.team,
                MAX(p.usg_pct) as usg_pct
            FROM players p
            LEFT JOIN player_canonical_ids c
                ON c.normalized_name = LOWER(REPLACE(p.name, '.', ''))
                OR c.canonical_id = p.player_id
                OR c.tank01_aliases LIKE '%' || p.player_id || '%'
            WHERE p.team = ?
                AND p.is_active = 1
                AND p.usg_pct IS NOT NULL
            GROUP BY COALESCE(c.canonical_id, p.player_id)
        )
        ORDER BY usg_pct DESC
        LIMIT ?
    """, (team_abbr, top_n))

    return [dict(row) for row in cursor.fetchall()]


def fetch_player_wowy(player_id: str, team_id: str, season: str = CURRENT_SEASON,
                     verbose: bool = False, leverage: str = None) -> Optional[Dict]:
    """
    Fetch WOWY data for a single player from PBP Stats API.

    Uses stat_type='team' to get team-level on/off stats for when the player
    is on vs off the court.

    Args:
        player_id: NBA.com player ID
        team_id: NBA.com team ID
        season: Season string (default: current season)
        verbose: Print debug info
        leverage: Filter by leverage ("Medium,High,VeryHigh" to skip garbage time)

    Returns:
        Dict with on/off splits or None if API fails
    """
    if verbose:
        print(f"   Fetching WOWY for player {player_id}...")

    try:
        # Use stat_type='team' to get team-level on/off data with leverage filter
        response = get_on_off(team_id, player_id, stat_type="team", season=season,
                            leverage=leverage, use_cache=True)

        if not response:
            if verbose:
                print(f"   ❌ No response from PBP Stats API")
            return None

        # Parse response - format: {'results': [{'Stat': 'Name', 'On': val, 'Off': val}, ...]}
        results = response.get('results', [])

        if not results or not isinstance(results, list):
            if verbose:
                print(f"   ❌ No results in PBP Stats response")
            return None

        def find_stat(stat_name: str) -> Dict:
            """Find a stat row by exact stat name."""
            for row in results:
                if row.get('Stat') == stat_name:
                    return row
            return {}

        # Find the key stats from the team-level response
        ortg_row = find_stat('Pts per 100 Possessions')
        drtg_row = find_stat('Pts per 100 Possessions - Defense')

        # Extract On/Off values (stored as strings, need to convert)
        on_ortg = float(ortg_row.get('On', 0) or 0)
        off_ortg = float(ortg_row.get('Off', 0) or 0)
        on_drtg = float(drtg_row.get('On', 0) or 0)
        off_drtg = float(drtg_row.get('Off', 0) or 0)

        # Calculate NetRtg (ORtg - DRtg)
        on_netrtg = on_ortg - on_drtg
        off_netrtg = off_ortg - off_drtg

        wowy = {
            'on_ortg': on_ortg,
            'off_ortg': off_ortg,
            'on_drtg': on_drtg,
            'off_drtg': off_drtg,
            'on_netrtg': on_netrtg,
            'off_netrtg': off_netrtg,
            'on_possessions': 0,  # Not directly available in team endpoint
            'off_possessions': 0,  # Not directly available in team endpoint
        }

        # Calculate on/off diff (player's impact on team NetRtg)
        wowy['on_off_diff'] = on_netrtg - off_netrtg

        if verbose:
            print(f"   ✅ ORtg On/Off: {on_ortg:.1f} / {off_ortg:.1f}")
            print(f"      DRtg On/Off: {on_drtg:.1f} / {off_drtg:.1f}")
            print(f"      NetRtg On/Off: {on_netrtg:.1f} / {off_netrtg:.1f} (Δ {wowy['on_off_diff']:+.1f})")

        return wowy

    except Exception as e:
        if verbose:
            print(f"   ❌ Error: {e}")
        return None


def save_to_db(conn: sqlite3.Connection, player_id: str, player_name: str,
               team_abbr: str, team_id: str, wowy_data: Dict,
               season: str = CURRENT_SEASON, dry_run: bool = False) -> bool:
    """
    Save WOWY data to player_season_wowy table.
    
    Args:
        conn: Database connection
        player_id: NBA.com player ID
        player_name: Player name
        team_abbr: Team abbreviation (e.g., 'LAL')
        team_id: NBA.com team ID
        wowy_data: WOWY stats dict from fetch_player_wowy()
        season: Season string
        dry_run: If True, don't actually write to DB
        
    Returns:
        True if saved successfully, False otherwise
    """
    if dry_run:
        print(f"   [DRY RUN] Would save: {player_name} ({team_abbr})")
        return True
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO player_season_wowy (
                player_id, player_name, team_abbr, team_id, season,
                on_possessions, on_ortg, on_drtg, on_netrtg,
                off_possessions, off_ortg, off_drtg, off_netrtg,
                on_off_diff, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_id, season) DO UPDATE SET
                team_abbr = excluded.team_abbr,
                team_id = excluded.team_id,
                on_possessions = excluded.on_possessions,
                on_ortg = excluded.on_ortg,
                on_drtg = excluded.on_drtg,
                on_netrtg = excluded.on_netrtg,
                off_possessions = excluded.off_possessions,
                off_ortg = excluded.off_ortg,
                off_drtg = excluded.off_drtg,
                off_netrtg = excluded.off_netrtg,
                on_off_diff = excluded.on_off_diff,
                synced_at = excluded.synced_at
        """, (
            player_id, player_name, team_abbr, team_id, season,
            wowy_data['on_possessions'], wowy_data['on_ortg'],
            wowy_data['on_drtg'], wowy_data['on_netrtg'],
            wowy_data['off_possessions'], wowy_data['off_ortg'],
            wowy_data['off_drtg'], wowy_data['off_netrtg'],
            wowy_data['on_off_diff'], datetime.now().isoformat()
        ))
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        print(f"   ❌ Database error: {e}")
        return False


def sync_team(conn: sqlite3.Connection, team_abbr: str, top_n: int = 10,
              verbose: bool = False, dry_run: bool = False) -> Dict:
    """
    Sync WOWY data for top N players on a team.
    
    Args:
        conn: Database connection
        team_abbr: Team abbreviation (e.g., 'LAL')
        top_n: Number of players to sync (default: 10)
        verbose: Print detailed progress
        dry_run: Don't write to database
        
    Returns:
        Dict with sync stats (success_count, fail_count, players_synced)
    """
    team_id = TEAM_IDS.get(team_abbr)
    if not team_id:
        print(f"❌ Unknown team: {team_abbr}")
        return {'success_count': 0, 'fail_count': 0, 'players_synced': []}
    
    print(f"\n🏀 Syncing WOWY for {team_abbr} (top {top_n} by usage)...")
    
    # Get top players
    players = get_top_players(conn, team_abbr, top_n)
    
    if not players:
        print(f"   ❌ No players found for {team_abbr}")
        return {'success_count': 0, 'fail_count': 0, 'players_synced': []}
    
    print(f"   Found {len(players)} players")
    
    success_count = 0
    fail_count = 0
    players_synced = []
    
    for i, player in enumerate(players, 1):
        player_id = player['player_id']
        player_name = player['name']
        usg = player.get('usg_pct', 0)
        
        print(f"\n   [{i}/{len(players)}] {player_name} (USG: {usg:.1%})")

        # Fetch WOWY data with leverage filter (skip garbage time for 30-40% reduction)
        wowy_data = fetch_player_wowy(player_id, team_id, CURRENT_SEASON, verbose,
                                     leverage="Medium,High,VeryHigh")
        
        if not wowy_data:
            fail_count += 1
            continue
        
        # Save to DB
        if save_to_db(conn, player_id, player_name, team_abbr, team_id,
                     wowy_data, CURRENT_SEASON, dry_run):
            success_count += 1
            players_synced.append(player_name)
        else:
            fail_count += 1
    
    return {
        'success_count': success_count,
        'fail_count': fail_count,
        'players_synced': players_synced
    }


def main():
    parser = argparse.ArgumentParser(
        description="Sync full-season WOWY data from PBP Stats API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Sync all 30 teams (top 10 players each)
  python scripts/sync_pbp_wowy.py --verbose
  
  # Sync single team
  python scripts/sync_pbp_wowy.py --team LAL --verbose
  
  # Test with top 5 players per team without writing
  python scripts/sync_pbp_wowy.py --top 5 --dry-run --verbose
        """
    )
    
    parser.add_argument('--team', type=str,
                       help='Sync single team (e.g., LAL)')
    parser.add_argument('--top', type=int, default=10,
                       help='Number of players per team (default: 10)')
    parser.add_argument('--verbose', action='store_true',
                       help='Print detailed progress')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview without database writes')
    parser.add_argument('--db', type=str, default='ludi.db',
                       help='Database path (default: ludi.db)')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from previous incomplete run (skips completed teams)')

    args = parser.parse_args()
    
    print("="*70)
    print("PBP Stats WOWY Sync - Phase 6.3")
    print("="*70)
    
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No database writes")
    
    # Connect to database
    conn = get_db_connection(args.db)
    
    # Determine teams to sync
    all_teams = [args.team] if args.team else list(TEAM_IDS.keys())

    # Load resume state if --resume flag set
    resume_state = None
    completed_teams = []

    if args.resume:
        resume_state = _load_resume_state()
        if resume_state and resume_state['status'] == 'paused':
            completed_teams = resume_state.get('completed_teams', [])
            print(f"   Resuming from previous run ({len(completed_teams)}/{len(all_teams)} teams completed)")
        elif resume_state and resume_state['status'] == 'in_progress':
            completed_teams = resume_state.get('completed_teams', [])
            print(f"   Resuming from previous run ({len(completed_teams)}/{len(all_teams)} teams completed)")
        elif resume_state:
            print(f"   Previous run was complete, starting fresh")
            resume_state = None

    # Filter out already-completed teams
    if completed_teams:
        teams_to_sync = [t for t in all_teams if t not in completed_teams]
        print(f"   Skipping {len(completed_teams)} completed teams, {len(teams_to_sync)} remaining")
    else:
        teams_to_sync = all_teams

    # Initialize tracking
    total_success = 0
    total_fail = 0
    all_players_synced = []
    newly_completed = []
    _start_time = time.time()

    try:
        for team in teams_to_sync:
            # Check wall-clock time limit
            if time.time() - _start_time > MAX_RUNTIME_SECONDS:
                print(f"\n⚠️ Runtime limit ({MAX_RUNTIME_SECONDS}s) reached. Saving checkpoint...")
                if args.resume and not args.dry_run:
                    all_completed = completed_teams + newly_completed
                    remaining = [t for t in all_teams if t not in all_completed]
                    _save_resume_state(all_completed, remaining, "paused", "runtime_limit")
                break

            try:
                result = sync_team(conn, team, args.top, args.verbose, args.dry_run)

                total_success += result['success_count']
                total_fail += result['fail_count']
                all_players_synced.extend(result['players_synced'])

                # Track completion for resume state
                newly_completed.append(team)

                # Save progress after each team (if --resume enabled)
                if args.resume and not args.dry_run:
                    all_completed = completed_teams + newly_completed
                    remaining = [t for t in all_teams if t not in all_completed]
                    _save_resume_state(all_completed, remaining, "in_progress")

            except Exception as e:
                print(f"   Error syncing {team}: {e}")
                total_fail += 1

                # Save state on error (if --resume enabled)
                if args.resume and not args.dry_run:
                    all_completed = completed_teams + newly_completed
                    remaining = [t for t in all_teams if t not in all_completed]
                    _save_resume_state(all_completed, remaining, "paused", f"error: {str(e)[:100]}")

        # Clear state on successful completion (all teams processed without critical failures)
        if args.resume and not args.dry_run and len(newly_completed) == len(teams_to_sync):
            _clear_resume_state()

        # Summary
        print("\n" + "="*70)
        print("SYNC COMPLETE")
        print("="*70)
        print(f"Success: {total_success} players")
        print(f"Failed: {total_fail} players")
        print(f"Total: {total_success + total_fail} attempted")
        print(f"Teams synced this run: {len(newly_completed)}")
        if completed_teams:
            print(f"Teams resumed from previous: {len(completed_teams)}")

        if not args.dry_run:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM player_season_wowy")
            total_records = cursor.fetchone()[0]
            print(f"Database: {total_records} total WOWY records")

        print("="*70)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
