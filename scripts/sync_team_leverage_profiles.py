"""
Team Leverage Profiles Sync Script (Sprint Phase 3)

Fetches team stats by leverage bucket from PBP Stats API.
Populates team_leverage_profiles and player_leverage_usage tables.

Usage:
    python scripts/sync_team_leverage_profiles.py --verbose
    python scripts/sync_team_leverage_profiles.py --verbose --team LAL

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

MAX_RUNTIME_SECONDS = 720  # 12 minutes

sys.path.insert(0, '.')

from utils.pbp_stats_client import get_team_leverage_summary

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

RESUME_STATE_FILE = "cache/leverage_sync_state.json"


def _load_resume_state() -> Optional[Dict]:
    if not os.path.exists(RESUME_STATE_FILE):
        return None
    try:
        with open(RESUME_STATE_FILE, 'r') as f:
            state = json.load(f)
        required = ['completed_teams', 'remaining_teams']
        if not all(k in state for k in required):
            return None
        return state
    except Exception:
        return None


def _save_resume_state(completed: List[str], remaining: List[str]) -> None:
    os.makedirs(os.path.dirname(RESUME_STATE_FILE), exist_ok=True)
    state = {
        "sync_version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "total_teams": len(completed) + len(remaining),
        "completed_teams": completed,
        "remaining_teams": remaining,
        "status": "in_progress" if remaining else "complete"
    }
    temp_file = RESUME_STATE_FILE + ".tmp"
    with open(temp_file, 'w') as f:
        json.dump(state, f, indent=2)
    os.replace(temp_file, RESUME_STATE_FILE)


def _clear_resume_state() -> None:
    if os.path.exists(RESUME_STATE_FILE):
        os.remove(RESUME_STATE_FILE)


def get_db_connection(db_path: str = "ludi.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn


def fetch_leverage_summary(team_abbr: str, verbose: bool = False) -> Optional[Dict]:
    """
    Fetch team leverage summary from PBP Stats API.

    IMPORTANT: The Leverage parameter is effectively required — omitting it
    causes a 500 error. We call per-bucket and aggregate results.

    API response fields: team, off_poss, off_rtg, efg, oreb_pct,
    fta_per_fga, seconds_per_poss_off (no direct Pace field).
    """
    leverage_data = {}

    for bucket in ['VeryHigh', 'High', 'Medium', 'Low']:
        try:
            response = get_team_leverage_summary(CURRENT_SEASON, leverage=bucket)
            if not response:
                if verbose:
                    print(f"   ⚠️ No data for {bucket} leverage")
                continue

            results = response.get('results', [])
            if not results:
                continue

            for row in results:
                if row.get('team', '') != team_abbr:
                    continue

                # Derive pace from seconds_per_poss_off
                # NBA pace = possessions per 48 min per team ≈ 1440 / sec_per_poss
                # (2880s game / 2 teams = 1440s per team's offensive time)
                sec_per_poss = row.get('seconds_per_poss_off', 0)
                pace = round(1440 / sec_per_poss, 1) if sec_per_poss > 0 else 0

                leverage_data[bucket] = {
                    'possessions': row.get('off_poss', 0),
                    'ortg': row.get('off_rtg', 0),
                    'efg_pct': row.get('efg', 0),
                    'pace': pace,
                    'oreb_pct': row.get('oreb_pct', 0),
                    'ft_rate': row.get('fta_per_fga', 0),
                }
                break

        except Exception as e:
            if verbose:
                print(f"   ⚠️ Error fetching {bucket}: {e}")

    # Build "Overall" by combining Medium (largest sample, closest to baseline)
    # Medium has 4000+ possessions vs VeryHigh's 20-50
    if 'Medium' in leverage_data:
        leverage_data['Overall'] = leverage_data['Medium'].copy()

    if verbose:
        print(f"   Found leverage data: {list(leverage_data.keys())}")

    return leverage_data if leverage_data else None


def fetch_player_leverage_usage(team_id: str, verbose: bool = False) -> Dict[str, Dict]:
    """
    Fetch player usage in VeryHigh leverage situations.

    NOTE: PBP Stats get_possessions endpoint returns 500 for 2025-26 season
    (server-side bug). Player leverage usage is now populated from BDL clutch
    stats instead (see scripts/sync_bdl_clutch_usage.py).

    This function is kept for future use when PBP Stats fixes the endpoint.
    """
    if verbose:
        print("   ⚠️ get_possessions broken for 2025-26 — use sync_bdl_clutch_usage.py instead")
    return {}


def fetch_overall_usage(team_id: str, verbose: bool = False) -> Dict[str, Dict]:
    """Placeholder — see fetch_player_leverage_usage note."""
    return {}


def save_team_leverage(conn: sqlite3.Connection, team_abbr: str, team_id: str,
                      leverage_data: Dict, verbose: bool = False) -> bool:
    """Save team leverage profile to database."""
    cursor = conn.cursor()

    vh = leverage_data.get('VeryHigh', {})
    h = leverage_data.get('High', {})
    l = leverage_data.get('Low', {})
    overall = leverage_data.get('Overall', leverage_data.get('All', {}))

    garbage_time_boost = None
    clutch_factor = None
    pace_variance = None

    if l.get('ortg') and overall.get('ortg'):
        garbage_time_boost = l['ortg'] / overall['ortg']
    if vh.get('ortg') and overall.get('ortg'):
        clutch_factor = vh['ortg'] / overall['ortg']
    if vh.get('pace') and l.get('pace'):
        pace_variance = vh['pace'] - l['pace']

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO team_leverage_profiles (
                team_abbr, team_id, season,
                vh_possessions, vh_ortg, vh_efg_pct, vh_pace, vh_oreb_pct, vh_ft_rate,
                h_possessions, h_ortg, h_efg_pct, h_pace, h_oreb_pct, h_ft_rate,
                l_possessions, l_ortg, l_efg_pct, l_pace, l_oreb_pct, l_ft_rate,
                overall_possessions, overall_ortg, overall_efg_pct, overall_pace, overall_oreb_pct, overall_ft_rate,
                garbage_time_boost, clutch_factor, pace_variance,
                synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team_abbr, team_id, CURRENT_SEASON,
            vh.get('possessions'), vh.get('ortg'), vh.get('efg_pct'), vh.get('pace'), vh.get('oreb_pct'), vh.get('ft_rate'),
            h.get('possessions'), h.get('ortg'), h.get('efg_pct'), h.get('pace'), h.get('oreb_pct'), h.get('ft_rate'),
            l.get('possessions'), l.get('ortg'), l.get('efg_pct'), l.get('pace'), l.get('oreb_pct'), l.get('ft_rate'),
            overall.get('possessions'), overall.get('ortg'), overall.get('efg_pct'), overall.get('pace'), overall.get('oreb_pct'), overall.get('ft_rate'),
            garbage_time_boost, clutch_factor, pace_variance,
            datetime.now().isoformat()
        ))
        conn.commit()

        if verbose:
            print(f"   ✅ Saved {team_abbr} leverage profile")
            if pace_variance:
                print(f"      Pace variance: {pace_variance:.1f}")

        return True

    except sqlite3.Error as e:
        if verbose:
            print(f"   ❌ DB error: {e}")
        return False


def save_player_leverage(conn: sqlite3.Connection, team_abbr: str,
                        vh_data: Dict, overall_data: Dict,
                        verbose: bool = False) -> int:
    """Save player leverage usage to database."""
    cursor = conn.cursor()

    all_players = set(vh_data.keys()) | set(overall_data.keys())
    saved = 0

    for player in all_players:
        vh = vh_data.get(player, {})
        overall = overall_data.get(player, {})

        vh_poss = vh.get('vh_poss', 0)
        vh_shots = vh.get('vh_shots', 0)
        total_poss = overall.get('total_poss', 0)
        total_shots = overall.get('total_shots', 0)

        if total_poss == 0:
            continue

        clutch_rate = vh_shots / total_shots if total_shots > 0 else 0

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO player_leverage_usage (
                    player_name, team_abbr, season,
                    vh_possessions, vh_shot_attempts,
                    total_possessions, total_shot_attempts,
                    clutch_usage_rate, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                player, team_abbr, CURRENT_SEASON,
                vh_poss, vh_shots,
                total_poss, total_shots,
                clutch_rate, datetime.now().isoformat()
            ))
            saved += 1

        except sqlite3.Error as e:
            if verbose:
                print(f"   ⚠️ Error saving {player}: {e}")

    conn.commit()

    if verbose:
        print(f"   ✅ Saved {saved} player leverage records")

    return saved


def sync_team(conn: sqlite3.Connection, team_abbr: str,
              verbose: bool = False) -> Dict:
    """Sync leverage data for a single team."""
    team_id = TEAM_IDS.get(team_abbr)
    if not team_id:
        print(f"❌ Unknown team: {team_abbr}")
        return {'success': False, 'players': 0}

    print(f"\n[Leverage] {team_abbr}: Syncing...")

    leverage_data = fetch_leverage_summary(team_abbr, verbose=verbose)
    if not leverage_data:
        print(f"   ❌ No leverage data for {team_abbr}")
        return {'success': False, 'players': 0}

    if not save_team_leverage(conn, team_abbr, team_id, leverage_data, verbose=verbose):
        return {'success': False, 'players': 0}

    vh_data = fetch_player_leverage_usage(team_id, verbose=verbose)
    overall_data = fetch_overall_usage(team_id, verbose=verbose)

    players_saved = save_player_leverage(conn, team_abbr, vh_data, overall_data, verbose=verbose)

    print(f"   ✅ Complete: {players_saved} player records")
    return {'success': True, 'players': players_saved}


def main():
    parser = argparse.ArgumentParser(description="Sync Team Leverage Profiles")
    parser.add_argument('--team', type=str, help="Sync specific team only")
    parser.add_argument('--verbose', '-v', action='store_true')
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

    total_players = 0
    total_teams_success = 0
    _start_time = time.time()

    for i, team in enumerate(teams):
        # Check wall-clock time limit
        if time.time() - _start_time > MAX_RUNTIME_SECONDS:
            print(f"\n⚠️ Runtime limit ({MAX_RUNTIME_SECONDS}s) reached. Saving checkpoint...")
            if args.resume:
                completed_so_far = completed[:i]
                remaining = teams[i:]
                _save_resume_state(completed_so_far, remaining)
            break

        result = sync_team(conn, team, verbose=args.verbose)
        if result['success']:
            total_teams_success += 1
            total_players += result['players']

        if args.resume:
            completed.append(team)
            remaining = teams[i+1:]
            _save_resume_state(completed, remaining)
            if not remaining:
                _clear_resume_state()

    conn.close()

    pace_variance_avg = 0
    try:
        conn2 = get_db_connection()
        c = conn2.cursor()
        c.execute("SELECT AVG(pace_variance) FROM team_leverage_profiles WHERE season = ?", (CURRENT_SEASON,))
        row = c.fetchone()
        if row and row[0]:
            pace_variance_avg = row[0]
        conn2.close()
    except Exception:
        pass

    print(f"\n{'='*50}")
    print(f"Leverage Sync Complete")
    print(f"  Teams: {total_teams_success}/{len(teams)} synced")
    print(f"  Player records: {total_players}")
    print(f"  Avg pace variance: {pace_variance_avg:.1f}")

    # Fail-loud: exit 1 if all teams failed (prevents silent green check)
    if len(teams) > 0 and total_teams_success == 0:
        print(f"\n❌ FATAL: 0/{len(teams)} teams synced — likely DB lock or API failure")
        sys.exit(1)


if __name__ == "__main__":
    main()
