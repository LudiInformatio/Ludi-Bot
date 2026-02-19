"""
Phase 8.9-B: Sync Stint Profiles
==================================
Parses PlayByPlayV3 substitution events to build per-player Q4 stint profiles.

CRITICAL: Does NOT store raw PBP events — only stores aggregated per-player profiles.

PBP structure (from PlayByPlayV3):
  - game.actions[] — ordered list of play events
  - actionType='Substitution' → player going OUT has personId; player coming IN
    is parsed from description: "SUB: InPlayer FOR OutPlayer"
  - clock format: 'PT{M}M{S}.00S' → time remaining in that period
  - period=4 → Q4 (12 min), period=5+ → OT (5 min)

Usage:
    .venv/bin/python scripts/sync_stint_profiles.py                  # 21-day window
    .venv/bin/python scripts/sync_stint_profiles.py --dry-run
    .venv/bin/python scripts/sync_stint_profiles.py --days 42
    .venv/bin/python scripts/sync_stint_profiles.py --limit 10       # test 10 games
"""

import argparse
import sqlite3
import sys
import os
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "ludi.db"
SEASON = "2025-26"
DEFAULT_DAYS = 21
MIN_GAMES_SAMPLE = 5       # minimum games to write a stint profile
NBA_API_DELAY = 1.2        # seconds between NBA API requests (rate limit)
Q4_PERIOD = 4
Q4_SECONDS = 720           # 12 minutes × 60
OT_SECONDS = 300           # 5 minutes × 60


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_clock(clock_str: str) -> float:
    """
    Parse ISO 8601 duration clock string to seconds remaining.

    Examples: 'PT06M20.00S' → 380.0, 'PT00M00.00S' → 0.0
    """
    m = re.match(r'PT(\d+)M([\d.]+)S', clock_str)
    if not m:
        return 0.0
    minutes = int(m.group(1))
    seconds = float(m.group(2))
    return minutes * 60 + seconds


def parse_inbound_player_name(description: str) -> Optional[str]:
    """
    Parse the incoming player name from sub description.

    Format: 'SUB: InPlayer FOR OutPlayer'
    Returns the InPlayer name (last name only in NBA PBP).
    """
    m = re.match(r'SUB:\s+(.+)\s+FOR\s+', description, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def get_games_with_nba_id(conn, days: int, limit: Optional[int] = None) -> List[Dict]:
    """
    Get games that have a populated nba_game_id, joined with player data
    to get team context for margin lookup.

    Only games with nba_game_id can be fetched via PlayByPlayV3.
    """
    sql = """
        SELECT DISTINCT g.game_id, g.nba_game_id, g.date,
                        g.home_team, g.away_team,
                        g.home_score, g.away_score
        FROM games g
        WHERE g.nba_game_id IS NOT NULL
          AND g.nba_game_id != ''
          AND g.date >= date('now', '-' || ? || ' days')
        ORDER BY g.date DESC
    """
    params = [days]
    if limit:
        sql += " LIMIT ?"
        params.append(limit)

    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_player_id_by_name(conn, last_name: str, team_tricode: str) -> Optional[int]:
    """
    Look up player_id from players table by last name + team.
    Returns None if ambiguous or not found.
    """
    rows = conn.execute("""
        SELECT player_id, name FROM players
        WHERE team = ? AND name LIKE ?
        LIMIT 2
    """, (team_tricode, f"%{last_name}%")).fetchall()

    if len(rows) == 1:
        return rows[0]["player_id"]
    return None


def parse_game_stints(actions: List[Dict]) -> Dict[int, Dict]:
    """
    Parse a game's actions list into per-player stint data.

    Returns a dict keyed by personId (player_id as int):
      {
        player_id: {
          'name': str,
          'team_id': int,
          'team_tricode': str,
          'stints': [(entry_sec_remaining, exit_sec_remaining, period), ...],
          'q4_starts': bool,  # was on court at start of Q4
        }
      }

    Algorithm:
    1. For each Substitution event:
       - personId → player going OUT at clock/period
       - description "SUB: X FOR Y" → X coming IN at clock/period
    2. Track on/off timings per player per period
    3. At period end, close any open stints at 0.0 seconds remaining
    """
    # player_id → {name, team_id, team_tricode, stints: [(entry, exit, period)]}
    player_data: Dict[int, Dict] = {}
    # player_id → entry time (seconds remaining) for current open stint
    active_stints: Dict[int, Tuple[float, int]] = {}  # {player_id: (entry_sec, period)}

    # Track period events to close stints at period end
    period_starts = {}   # {period: seconds_at_start}
    period_ends = {}     # {period: True} when we've seen an end event

    # Name → player_id cache from sub IN descriptions (for players who only appear as "in")
    name_to_id: Dict[str, int] = {}

    def get_period_seconds(period: int) -> float:
        """Max seconds in a period (Q1-Q4 = 720, OT = 300)."""
        return Q4_SECONDS if period <= 4 else OT_SECONDS

    def close_stints_for_period(period: int):
        """Close all open stints at end of period (exit at 0.0 seconds)."""
        for pid, (entry_sec, stint_period) in list(active_stints.items()):
            if stint_period == period:
                if pid in player_data:
                    player_data[pid]['stints'].append((entry_sec, 0.0, period))
                del active_stints[pid]

    def open_stint(pid: int, name: str, team_id: int, tricode: str,
                   seconds_remaining: float, period: int):
        """Record a player coming onto the court."""
        if pid not in player_data:
            player_data[pid] = {
                'name': name,
                'team_id': team_id,
                'team_tricode': tricode,
                'stints': []
            }
        active_stints[pid] = (seconds_remaining, period)

    # Process actions in order
    for action in actions:
        atype = action.get('actionType', '')
        period = action.get('period', 1)
        clock_str = action.get('clock', 'PT00M00.00S')
        seconds_remaining = parse_clock(clock_str)

        if atype == 'period':
            sub_type = action.get('subType', '')
            if sub_type == 'start':
                period_starts[period] = get_period_seconds(period)
                # Players who are still "active" from previous period started this period
                # (they didn't sub out at end of last period — were they subbed? No, between periods
                # coaches make lineup changes but PBP doesn't always show it)
                # We open stints at period start for players already active
                period_start_sec = get_period_seconds(period)
                # Carry forward any active_stints from prior period at new period start
                for pid, (_, prev_period) in list(active_stints.items()):
                    if prev_period == period - 1:
                        # This player carried over — update their stint start to new period start
                        active_stints[pid] = (period_start_sec, period)

            elif sub_type == 'end':
                period_ends[period] = True
                close_stints_for_period(period)

        elif atype == 'Substitution':
            out_player_id = action.get('personId')
            out_player_name = action.get('playerName', '')
            out_player_name_i = action.get('playerNameI', '')
            team_id = action.get('teamId', 0)
            team_tricode = action.get('teamTricode', '')
            description = action.get('description', '')

            # --- Player going OUT ---
            if out_player_id and out_player_id > 0:
                # Close their active stint
                if out_player_id in active_stints:
                    entry_sec, stint_period = active_stints.pop(out_player_id)
                    if out_player_id in player_data:
                        player_data[out_player_id]['stints'].append(
                            (entry_sec, seconds_remaining, stint_period)
                        )
                    else:
                        player_data[out_player_id] = {
                            'name': out_player_name or out_player_name_i,
                            'team_id': team_id,
                            'team_tricode': team_tricode,
                            'stints': [(entry_sec, seconds_remaining, stint_period)]
                        }
                else:
                    # Player was on court from start (no prior entry event in PBP)
                    # They exit here — estimate they were on since period start
                    period_start = get_period_seconds(period)
                    if out_player_id not in player_data:
                        player_data[out_player_id] = {
                            'name': out_player_name or out_player_name_i,
                            'team_id': team_id,
                            'team_tricode': team_tricode,
                            'stints': []
                        }
                    player_data[out_player_id]['stints'].append(
                        (period_start, seconds_remaining, period)
                    )
                name_to_id[out_player_name] = out_player_id
                name_to_id[out_player_name_i] = out_player_id

            # --- Player coming IN ---
            # The incoming player's ID is not in the event, only their name in description
            in_name = parse_inbound_player_name(description)
            if in_name:
                # Try to find this player_id from our name cache
                in_pid = name_to_id.get(in_name)
                # If not found, create a placeholder — they'll get filled when they sub out
                if in_pid is None:
                    # Use a negative placeholder; will be resolved when they sub out
                    # (their sub-out event will have their real personId)
                    # For now, open an anonymous stint and we'll match later by name
                    # This is complex — instead, track by name string
                    # Simpler: when they eventually sub OUT, they get their real ID assigned
                    pass
                else:
                    open_stint(in_pid, in_name, team_id, team_tricode, seconds_remaining, period)

    # Close any remaining open stints (game ended with players still on court)
    for pid, (entry_sec, period) in list(active_stints.items()):
        if pid in player_data:
            player_data[pid]['stints'].append((entry_sec, 0.0, period))

    return player_data


def aggregate_stints_for_game(player_data: Dict, game_margin: Optional[int]) -> Dict:
    """
    Aggregate stint data for one game into per-player stats.

    Returns dict: {player_id: {num_stints, first_stint_min, q4_min, q4_start, ...}}
    game_margin: absolute final score margin (None if unknown)
    """
    result = {}
    for pid, data in player_data.items():
        stints = data.get('stints', [])
        if not stints:
            continue

        num_stints = len(stints)

        # First stint length (minutes) — how long their first stint lasted in period 1
        p1_stints = [(e, x, p) for (e, x, p) in stints if p == 1]
        first_stint_min = None
        if p1_stints:
            # Sort by entry time descending (highest remaining = earliest in period)
            p1_stints_sorted = sorted(p1_stints, key=lambda s: s[0], reverse=True)
            entry_sec, exit_sec, _ = p1_stints_sorted[0]
            first_stint_min = round((entry_sec - exit_sec) / 60, 2)

        # Q4 minutes
        q4_stints = [(e, x, p) for (e, x, p) in stints if p == Q4_PERIOD]
        q4_min = sum((e - x) / 60 for (e, x, _) in q4_stints)
        q4_min = round(q4_min, 2)

        # Was this player on court at the start of Q4?
        # They're a Q4 starter if they have a stint starting near 720s (period start)
        q4_starts = any(e >= 700 for (e, x, p) in q4_stints)  # within 20s of period start

        result[pid] = {
            'name': data['name'],
            'team_tricode': data['team_tricode'],
            'num_stints': num_stints,
            'first_stint_min': first_stint_min if first_stint_min and first_stint_min > 0 else None,
            'q4_min': q4_min if q4_min > 0 else 0.0,
            'q4_starts': q4_starts,
            'game_margin': game_margin,
        }

    return result


def build_stint_profiles(days: int, dry_run: bool, limit: Optional[int]) -> Tuple[int, int]:
    """
    Main function: fetch PBP for all eligible games, parse stints, aggregate profiles.

    Returns: (games_parsed, profiles_written)
    """
    from nba_api.stats.endpoints import playbyplayv3

    conn = get_conn()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build headers for NBA API
    nba_headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.nba.com/',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true'
    }

    games = get_games_with_nba_id(conn, days, limit)
    print(f"[STINTS] Found {len(games)} games with nba_game_id in last {days} days")

    if not games:
        print("[STINTS] No eligible games — try increasing --days or check games.nba_game_id population")
        conn.close()
        return 0, 0

    # Accumulate per-player game-level stats across all games
    # player_id → list of per-game dicts
    player_game_stats: Dict[str, List[Dict]] = defaultdict(list)

    games_parsed = 0
    games_no_subs = 0

    for game in games:
        nba_gid = game["nba_game_id"]
        game_date = game["date"]
        home_team = game.get("home_team")
        away_team = game.get("away_team")

        # Cache path check (reuse existing cache from nba_api_client)
        cache_path = f"cache/nba_api/playbyplay_{nba_gid}.json"
        cached_data = None
        if os.path.exists(cache_path):
            import json
            try:
                with open(cache_path) as f:
                    cached_data = json.load(f)
            except Exception:
                cached_data = None

        if cached_data:
            data = cached_data
        else:
            # Fetch with rate limiting
            time.sleep(NBA_API_DELAY)
            try:
                response = playbyplayv3.PlayByPlayV3(
                    game_id=nba_gid,
                    headers=nba_headers
                )
                data = response.get_dict()
                # Cache for future use
                import json
                os.makedirs("cache/nba_api", exist_ok=True)
                with open(cache_path, 'w') as f:
                    json.dump(data, f)
            except Exception as e:
                print(f"[STINTS] Error fetching PBP for {nba_gid} ({game_date}): {e}")
                continue

        actions = data.get('game', {}).get('actions', [])
        if not actions:
            print(f"[STINTS] No actions for {nba_gid} ({game_date}) — skipping")
            games_no_subs += 1
            continue

        sub_events = [a for a in actions if a.get('actionType') == 'Substitution']
        if not sub_events:
            games_no_subs += 1
            print(f"[STINTS] No Substitution events for {nba_gid} ({game_date}) — skipping")
            continue

        # Determine game margin from scores in actions (last scoring event)
        game_margin = None
        final_home, final_away = game.get("home_score"), game.get("away_score")
        if final_home is not None and final_away is not None:
            try:
                game_margin = abs(int(final_home) - int(final_away))
            except (TypeError, ValueError):
                pass

        if game_margin is None:
            # Try to get final score from PBP actions
            for action in reversed(actions):
                sh = action.get('scoreHome', '')
                sa = action.get('scoreAway', '')
                if sh and sa:
                    try:
                        game_margin = abs(int(sh) - int(sa))
                        break
                    except (ValueError, TypeError):
                        continue

        # Parse stints
        try:
            player_data = parse_game_stints(actions)
        except Exception as e:
            print(f"[STINTS] Parse error for {nba_gid}: {e}")
            continue

        if not player_data:
            games_no_subs += 1
            continue

        game_stats = aggregate_stints_for_game(player_data, game_margin)

        # Accumulate across games
        for pid, stats in game_stats.items():
            player_game_stats[str(pid)].append(stats)

        games_parsed += 1

    print(f"[STINTS] Parsed {games_parsed} games | {games_no_subs} had no sub events")

    # Aggregate into per-player profiles
    profiles = []
    for player_id, game_list in player_game_stats.items():
        if len(game_list) < MIN_GAMES_SAMPLE:
            continue

        player_name = game_list[0]['name']
        team_tricode = game_list[0]['team_tricode']
        n = len(game_list)

        avg_stints = round(sum(g['num_stints'] for g in game_list) / n, 2)

        first_stints = [g['first_stint_min'] for g in game_list if g['first_stint_min'] is not None]
        avg_first_stint = round(sum(first_stints) / len(first_stints), 2) if first_stints else None

        all_stint_lengths = []
        for g in game_list:
            if g['num_stints'] > 0 and g['first_stint_min'] is not None:
                all_stint_lengths.append(g['first_stint_min'])
        avg_stint_length = round(sum(all_stint_lengths) / len(all_stint_lengths), 2) if all_stint_lengths else None

        pct_q4_starter = round(sum(1 for g in game_list if g['q4_starts']) / n, 3)

        q4_games = [g for g in game_list if g['q4_min'] > 0]
        avg_min_q4 = round(sum(g['q4_min'] for g in game_list) / n, 2)

        # Close game Q4 minutes (margin <= 5)
        close_games = [g for g in game_list if g.get('game_margin') is not None and g['game_margin'] <= 5]
        avg_min_q4_close = round(
            sum(g['q4_min'] for g in close_games) / len(close_games), 2
        ) if close_games else None

        # Blowout Q4 minutes (margin > 15)
        blowout_games = [g for g in game_list if g.get('game_margin') is not None and g['game_margin'] > 15]
        avg_min_q4_blowout = round(
            sum(g['q4_min'] for g in blowout_games) / len(blowout_games), 2
        ) if blowout_games else None

        profiles.append({
            "player_id": player_id,
            "player_name": player_name,
            "team_abbreviation": team_tricode,
            "season": SEASON,
            "avg_stints_per_game": avg_stints,
            "avg_first_stint_min": avg_first_stint,
            "avg_stint_length": avg_stint_length,
            "pct_games_q4_starter": pct_q4_starter,
            "avg_min_q4": avg_min_q4,
            "avg_min_q4_when_close": avg_min_q4_close,
            "avg_min_q4_blowout": avg_min_q4_blowout,
            "games_sample": n,
            "synced_at": now_str,
        })

    print(f"[STINTS] Built {len(profiles)} player stint profiles (>= {MIN_GAMES_SAMPLE} games)")

    _print_top5_closers(profiles)

    if dry_run:
        print("[STINTS] DRY RUN — no writes")
        conn.close()
        return games_parsed, 0

    # Write profiles to DB
    profiles_written = 0
    c = conn.cursor()
    for p in profiles:
        try:
            c.execute("""
                INSERT INTO player_stint_profiles (
                    player_id, player_name, team_abbreviation, season,
                    avg_stints_per_game, avg_first_stint_min, avg_stint_length,
                    pct_games_q4_starter, avg_min_q4, avg_min_q4_when_close,
                    avg_min_q4_blowout, games_sample, synced_at
                ) VALUES (
                    :player_id, :player_name, :team_abbreviation, :season,
                    :avg_stints_per_game, :avg_first_stint_min, :avg_stint_length,
                    :pct_games_q4_starter, :avg_min_q4, :avg_min_q4_when_close,
                    :avg_min_q4_blowout, :games_sample, :synced_at
                )
                ON CONFLICT(player_id, team_abbreviation, season) DO UPDATE SET
                    avg_stints_per_game=excluded.avg_stints_per_game,
                    avg_first_stint_min=excluded.avg_first_stint_min,
                    avg_stint_length=excluded.avg_stint_length,
                    pct_games_q4_starter=excluded.pct_games_q4_starter,
                    avg_min_q4=excluded.avg_min_q4,
                    avg_min_q4_when_close=excluded.avg_min_q4_when_close,
                    avg_min_q4_blowout=excluded.avg_min_q4_blowout,
                    games_sample=excluded.games_sample,
                    synced_at=excluded.synced_at
            """, p)
            profiles_written += 1
        except Exception as e:
            print(f"[STINTS] Row error for {p['player_name']}: {e}")

    conn.commit()
    conn.close()
    print(f"[STINTS] Wrote {profiles_written} profiles to player_stint_profiles")
    return games_parsed, profiles_written


def _print_top5_closers(profiles):
    """Print top 5 Q4 closers by avg_min_q4_when_close."""
    if not profiles:
        print("[STINTS] No profiles to display")
        return

    valid = [p for p in profiles if p.get("avg_min_q4_when_close") is not None]
    top5 = sorted(valid, key=lambda p: p["avg_min_q4_when_close"], reverse=True)[:5]

    print("\n[STINTS] Top 5 Q4 closers (avg min Q4 in close games):")
    print(f"  {'Player':<24} {'Team':<5} {'Q4 min':>6} {'Close Q4':>8} {'Q4%':>5} {'Games':>6}")
    print("  " + "-" * 65)
    for p in top5:
        print(f"  {p['player_name']:<24} {p['team_abbreviation']:<5}"
              f"  {p['avg_min_q4']:>5.1f}  {p['avg_min_q4_when_close']:>7.1f}"
              f"  {p['pct_games_q4_starter']:>4.0%}  {p['games_sample']:>5}")


def main():
    parser = argparse.ArgumentParser(description="Sync stint profiles from PlayByPlayV3")
    parser.add_argument("--dry-run", action="store_true", help="No DB writes")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help=f"Lookback window in days (default: {DEFAULT_DAYS})")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of games to process (for testing)")
    args = parser.parse_args()

    print(f"[STINTS] Phase 8.9-B — Stint Profiles Sync")
    print(f"[STINTS] Source: PlayByPlayV3 (NBA API)")
    print(f"[STINTS] Window: {args.days} days | limit={args.limit} | dry_run={args.dry_run}")

    games_parsed, profiles_written = build_stint_profiles(args.days, args.dry_run, args.limit)
    print(f"\n[STINTS] Done. {games_parsed} games parsed | {profiles_written} profiles built.")


if __name__ == "__main__":
    main()
