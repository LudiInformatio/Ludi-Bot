"""
PBP Stats Four Factor WOWY Sync Script (Sprint Phase 3)

Fetches four-factor on/off splits from PBP Stats API for top usage players.
Updates existing player_season_wowy table with Four Factor columns (eFG%, TOV%, OREB%, FT Rate, Pace).

Usage:
    python scripts/sync_four_factor_wowy.py --verbose
    python scripts/sync_four_factor_wowy.py --team LAL --verbose
    python scripts/sync_four_factor_wowy.py --dry-run --top 5
    python scripts/sync_four_factor_wowy.py --resume --verbose

Author: Ludi Informatio
Date: February 14, 2026 (Sprint Phase 3)
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

MAX_RUNTIME_SECONDS = 1200  # 20 minutes

sys.path.insert(0, '.')

from utils.pbp_stats_client import get_four_factor_on_off, get_on_off

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

RESUME_STATE_FILE = "cache/four_factor_sync_state.json"


def _load_resume_state() -> Optional[Dict]:
    if not os.path.exists(RESUME_STATE_FILE):
        return None
    try:
        with open(RESUME_STATE_FILE, 'r') as f:
            state = json.load(f)
        required = ['completed_teams', 'remaining_teams', 'status']
        if not all(k in state for k in required):
            return None
        return state
    except Exception as e:
        print(f"   Warning: Error loading state: {e}")
        return None


def _save_resume_state(completed: List[str], remaining: List[str],
                       status: str = "in_progress", reason: str = None) -> None:
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
    temp_file = RESUME_STATE_FILE + ".tmp"
    with open(temp_file, 'w') as f:
        json.dump(state, f, indent=2)
    os.replace(temp_file, RESUME_STATE_FILE)
    print(f"   State saved: {len(completed)}/{state['total_teams']} teams")


def _clear_resume_state() -> None:
    if os.path.exists(RESUME_STATE_FILE):
        os.remove(RESUME_STATE_FILE)
        print("   Cleared resume state")


def get_db_connection(db_path: str = "ludi.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn


def get_players_with_wowy(conn: sqlite3.Connection, team_abbr: str) -> List[Dict]:
    """Get players who already have WOWY data for this team."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT player_id, player_name, team_abbr
        FROM player_season_wowy
        WHERE team_abbr = ? AND season = ?
    """, (team_abbr, CURRENT_SEASON))
    return [dict(row) for row in cursor.fetchall()]


def fetch_four_factor(player_id: str, team_id: str,
                      verbose: bool = False) -> Optional[Dict]:
    """
    Fetch four-factor on/off data + Pace from PBP Stats API.

    The four-factor endpoint returns eFG%, TOV%, OREB%, FTr (Dean Oliver's 4 factors).
    Pace is NOT in the four-factor response — we pull it from get_on_off() separately.

    Returns:
        Dict with on_efg, off_efg, on_tov_pct, off_tov_pct, on_oreb_pct, off_oreb_pct,
               on_ft_rate, off_ft_rate, on_pace, off_pace
    """
    if verbose:
        print(f"   Fetching four factor for player {player_id}...")

    try:
        response = get_four_factor_on_off(team_id, player_id, season=CURRENT_SEASON)

        if not response:
            if verbose:
                print(f"   ❌ No response from API")
            return None

        offense_results = response.get('offense_results', [])
        if not offense_results:
            if verbose:
                print(f"   ❌ No offense results in response")
            return None

        def find_stat(results, stat_name):
            for row in results:
                if row.get('stat') == stat_name:
                    return row
            return {}

        on_efg_row = find_stat(offense_results, 'eFG%')
        on_oreb_row = find_stat(offense_results, 'OReb%')
        on_ft_row = find_stat(offense_results, 'FTr')
        on_tov_row = find_stat(offense_results, 'TOV%')

        ff = {
            'on_efg_pct': on_efg_row.get('On', 0) or 0,
            'off_efg_pct': on_efg_row.get('Off', 0) or 0,
            'on_tov_pct': on_tov_row.get('On', 0) or 0,
            'off_tov_pct': on_tov_row.get('Off', 0) or 0,
            'on_oreb_pct': on_oreb_row.get('On', 0) or 0,
            'off_oreb_pct': on_oreb_row.get('Off', 0) or 0,
            'on_ft_rate': on_ft_row.get('On', 0) or 0,
            'off_ft_rate': on_ft_row.get('Off', 0) or 0,
            'on_pace': 0,
            'off_pace': 0,
        }

        # Pull Pace from get_on_off() (four-factor endpoint doesn't include it)
        # Response format: results = {stat_name: [player_rows...]}, where each row
        # has On/Off values for that stat. SecondsPerPossOff gives team pace context.
        # We derive pace as 1440 / seconds_per_poss for standard NBA pace units.
        try:
            on_off_resp = get_on_off(team_id, player_id, season=CURRENT_SEASON)
            if on_off_resp:
                results = on_off_resp.get('results', {})
                sec_per_poss = results.get('SecondsPerPossOff', [])
                # Find the team-level row (first row with valid minutes)
                for row in sec_per_poss:
                    on_val = float(row.get('On', 0) or 0)
                    off_val = float(row.get('Off', 0) or 0)
                    mins_on = row.get('MinutesOn', 0) or 0
                    if mins_on > 100 and on_val > 0 and off_val > 0:
                        # Convert seconds_per_poss to pace (possessions per 48 min)
                        ff['on_pace'] = round(1440 / on_val, 1)
                        ff['off_pace'] = round(1440 / off_val, 1)
                        break
        except Exception as e:
            if verbose:
                print(f"   ⚠️ Pace fetch failed (non-critical): {e}")

        if verbose:
            print(f"   ✅ eFG%: {ff['on_efg_pct']:.1%} / {ff['off_efg_pct']:.1%}")
            print(f"      TOV%: {ff['on_tov_pct']:.1%} / {ff['off_tov_pct']:.1%}")
            print(f"      OREB%: {ff['on_oreb_pct']:.1%} / {ff['off_oreb_pct']:.1%}")
            print(f"      Pace: {ff['on_pace']:.1f} / {ff['off_pace']:.1f}")

        return ff

    except Exception as e:
        if verbose:
            print(f"   ❌ Error: {e}")
        return None


def update_player_four_factor(conn: sqlite3.Connection, player_id: str,
                              ff_data: Dict, verbose: bool = False) -> bool:
    """Update player_season_wowy with four factor data."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE player_season_wowy SET
                on_efg_pct = ?, off_efg_pct = ?,
                on_tov_pct = ?, off_tov_pct = ?,
                on_oreb_pct = ?, off_oreb_pct = ?,
                on_ft_rate = ?, off_ft_rate = ?,
                on_pace = ?, off_pace = ?
            WHERE player_id = ? AND season = ?
        """, (
            ff_data['on_efg_pct'], ff_data['off_efg_pct'],
            ff_data['on_tov_pct'], ff_data['off_tov_pct'],
            ff_data['on_oreb_pct'], ff_data['off_oreb_pct'],
            ff_data['on_ft_rate'], ff_data['off_ft_rate'],
            ff_data['on_pace'], ff_data['off_pace'],
            player_id, CURRENT_SEASON
        ))
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        if verbose:
            print(f"   ❌ DB error: {e}")
        return False


def sync_team(conn: sqlite3.Connection, team_abbr: str,
              verbose: bool = False, dry_run: bool = False) -> Dict:
    """Sync four factor data for all players with existing WOWY data."""
    team_id = TEAM_IDS.get(team_abbr)
    if not team_id:
        print(f"❌ Unknown team: {team_abbr}")
        return {'success_count': 0, 'fail_count': 0}

    print(f"\n[Four Factor] {team_abbr}: Syncing...")

    players = get_players_with_wowy(conn, team_abbr)
    if not players:
        print(f"   ❌ No WOWY players found for {team_abbr}")
        return {'success_count': 0, 'fail_count': 0}

    print(f"   Found {len(players)} players with WOWY data")

    success_count = 0
    fail_count = 0

    for player in players:
        ff_data = fetch_four_factor(player['player_id'], team_id, verbose=verbose)
        if ff_data:
            if not dry_run:
                if update_player_four_factor(conn, player['player_id'], ff_data, verbose=verbose):
                    success_count += 1
                    if verbose:
                        print(f"   ✅ {player['player_name']} updated")
                else:
                    fail_count += 1
            else:
                success_count += 1
        else:
            fail_count += 1

    print(f"   Results: {success_count}/{len(players)} updated")
    return {'success_count': success_count, 'fail_count': fail_count}


def main():
    parser = argparse.ArgumentParser(description="Sync Four Factor WOWY data")
    parser.add_argument('--team', type=str, help="Sync specific team only")
    parser.add_argument('--top', type=int, default=10, help="Top N players per team")
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--dry-run', action='store_true', help="Don't write to DB")
    parser.add_argument('--resume', action='store_true', help="Resume from previous run")
    args = parser.parse_args()

    conn = get_db_connection()

    if args.team:
        teams = [args.team]
    else:
        teams = list(TEAM_IDS.keys())

    if args.resume:
        state = _load_resume_state()
        if state and state.get('remaining_teams'):
            teams = state['remaining_teams']
            completed = state.get('completed_teams', [])
        else:
            print("No resume state found, starting fresh")
            completed = []
    else:
        completed = []

    total_success = 0
    total_fail = 0
    _start_time = time.time()

    for i, team in enumerate(teams):
        # Check wall-clock time limit
        if time.time() - _start_time > MAX_RUNTIME_SECONDS:
            print(f"\n⚠️ Runtime limit ({MAX_RUNTIME_SECONDS}s) reached. Saving checkpoint...")
            if args.resume and not args.dry_run:
                completed_so_far = completed[:i]
                remaining = teams[i:]
                _save_resume_state(completed_so_far, remaining, status="paused", reason="runtime_limit")
            break

        result = sync_team(conn, team, verbose=args.verbose, dry_run=args.dry_run)
        total_success += result['success_count']
        total_fail += result['fail_count']

        if args.resume and not args.dry_run:
            completed.append(team)
            remaining = teams[i+1:]
            _save_resume_state(completed, remaining, status="in_progress")
            if not remaining:
                _clear_resume_state()

    conn.close()

    print(f"\n{'='*50}")
    print(f"Four Factor Sync Complete")
    print(f"  Total: {total_success + total_fail} players")
    print(f"  Success: {total_success}")
    print(f"  Failed: {total_fail}")


if __name__ == "__main__":
    main()
