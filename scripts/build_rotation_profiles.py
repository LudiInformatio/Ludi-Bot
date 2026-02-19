#!/usr/bin/env python3
"""
Phase 8.9 — Build Rotation Profiles
Computes per-player situational minutes from game logs and populates:
  - rotation_profiles  (avg/situational minutes per player)
  - beneficiary_minutes (when player X is out, who gets extra run?)

Usage:
  python scripts/build_rotation_profiles.py                   # full run
  python scripts/build_rotation_profiles.py --dry-run          # print only, no writes
  python scripts/build_rotation_profiles.py --window-days 14   # shorter window
  python scripts/build_rotation_profiles.py --min-games 5      # stricter filter
"""

import argparse
import sqlite3
import sys
import os
from datetime import datetime, date

# Allow running from repo root or scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ---------------------------------------------------------------------------
# PART A — rotation_profiles
# ---------------------------------------------------------------------------

def build_rotation_profiles(conn, window_days: int, min_games: int, dry_run: bool) -> int:
    """
    For each player with >= min_games in the window, compute:
      - overall avg/std/min/max minutes
      - situational avgs: starter vs bench, blowout win/loss, close game, B2B
      - depth_order and position from depth_charts

    Returns number of profiles upserted.
    """
    cutoff = f"date('now', '-{window_days} days')"
    computed_at = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

    # Pull all qualifying player-game rows joined with game outcome data.
    # team_margin = positive if player's team won by that margin.
    sql = f"""
        SELECT
            pgl.player_id,
            pgl.player_name,
            pgl.team_abbreviation,
            pgl.game_date,
            pgl.minutes,
            -- Team margin from the player's perspective
            CASE
                WHEN g.home_team = pgl.team_abbreviation
                    THEN COALESCE(g.home_score, 0) - COALESCE(g.away_score, 0)
                ELSE COALESCE(g.away_score, 0) - COALESCE(g.home_score, 0)
            END AS team_margin
        FROM player_game_logs pgl
        JOIN games g
            ON pgl.game_date = g.date
            AND (g.home_team = pgl.team_abbreviation OR g.away_team = pgl.team_abbreviation)
        WHERE pgl.game_date >= {cutoff}
        ORDER BY pgl.player_id, pgl.team_abbreviation, pgl.game_date
    """
    rows = conn.execute(sql).fetchall()

    if not rows:
        print("  [WARNING] No player_game_logs rows found — nothing to process.")
        return 0

    # Group by (player_id, team_abbreviation)
    from collections import defaultdict
    groups = defaultdict(list)
    for r in rows:
        groups[(r['player_id'], r['team_abbreviation'])].append(dict(r))

    # Pull depth_charts for depth_order + position lookup
    dc_lookup = {}  # (player_id) -> (depth_order, position)
    try:
        dc_rows = conn.execute("""
            SELECT player_id, depth_order, position FROM depth_charts
        """).fetchall()
        for dc in dc_rows:
            if dc['player_id'] and dc['player_id'] not in dc_lookup:
                dc_lookup[str(dc['player_id'])] = (dc['depth_order'], dc['position'])
    except Exception as e:
        print(f"  [WARN] depth_charts lookup failed: {e}")

    # Phase 8.12: build current-team lookup (players.team = today's truth)
    current_teams = {}  # player_id -> current team per players table
    try:
        team_rows = conn.execute("SELECT player_id, team FROM players WHERE is_active = 1").fetchall()
        for tr in team_rows:
            if tr['player_id']:
                current_teams[str(tr['player_id'])] = tr['team']
    except Exception as e:
        print(f"  [WARN] current_teams lookup failed: {e}")

    profiles = []
    for (player_id, team_abbr), game_rows in groups.items():
        if len(game_rows) < min_games:
            continue

        player_name = game_rows[0]['player_name']

        # B2B detection: sort by date, flag games where previous team game was 1 day prior
        game_rows.sort(key=lambda x: x['game_date'])
        dates = [r['game_date'] for r in game_rows]
        is_b2b_flags = [False] * len(game_rows)
        for i in range(1, len(game_rows)):
            try:
                d0 = date.fromisoformat(dates[i - 1])
                d1 = date.fromisoformat(dates[i])
                if (d1 - d0).days == 1:
                    is_b2b_flags[i] = True
            except Exception:
                pass

        all_minutes = [r['minutes'] for r in game_rows]
        played_minutes = [m for m in all_minutes if m > 0]

        if not played_minutes:
            continue

        n = len(played_minutes)
        avg_m = sum(played_minutes) / n
        # SQLite has no STDDEV — compute in Python
        variance = sum((x - avg_m) ** 2 for x in played_minutes) / n if n > 1 else 0.0
        std_m = variance ** 0.5

        # Situational: blowout win (margin > 15), blowout loss (< -15), close (|margin| <= 5), B2B
        blowout_win_mins = [r['minutes'] for r in game_rows if r['team_margin'] > 15 and r['minutes'] > 0]
        blowout_loss_mins = [r['minutes'] for r in game_rows if r['team_margin'] < -15 and r['minutes'] > 0]
        close_mins = [r['minutes'] for r, b2b in zip(game_rows, is_b2b_flags)
                      if abs(r['team_margin']) <= 5 and r['minutes'] > 0]
        b2b_mins = [r['minutes'] for r, b2b in zip(game_rows, is_b2b_flags) if b2b and r['minutes'] > 0]

        def safe_avg(lst):
            return round(sum(lst) / len(lst), 2) if lst else None

        # Starter approximation: use depth_charts depth_order == 1 as proxy
        dc = dc_lookup.get(str(player_id), (None, None))
        depth_order = dc[0]
        position = dc[1]
        games_started = 1 if depth_order == 1 else 0  # simple proxy
        start_rate = 1.0 if depth_order == 1 else (0.0 if depth_order and depth_order > 1 else 0.5)
        avg_min_starter = avg_m if start_rate >= 0.7 else None
        avg_min_bench = avg_m if start_rate < 0.3 else None

        # Phase 8.12: count games on current team only (detects recently-traded players)
        current_team = current_teams.get(str(player_id))
        if current_team and current_team == team_abbr:
            try:
                ct_row = conn.execute("""
                    SELECT COUNT(*) FROM player_game_logs
                    WHERE player_id = ? AND team_abbreviation = ?
                      AND game_date >= date('now', '-60 days')
                """, (str(player_id), current_team)).fetchone()
                games_on_current = ct_row[0] if ct_row else None
            except Exception:
                games_on_current = None
        else:
            games_on_current = None  # Stale row — not the player's current team

        profiles.append({
            'player_id': str(player_id),
            'player_name': player_name,
            'team_abbreviation': team_abbr,
            'avg_minutes': round(avg_m, 2),
            'std_minutes': round(std_m, 2),
            'min_minutes': round(min(played_minutes), 1),
            'max_minutes': round(max(played_minutes), 1),
            'games_started': games_started,
            'games_played': n,
            'start_rate': start_rate,
            'avg_min_as_starter': avg_min_starter,
            'avg_min_off_bench': avg_min_bench,
            'avg_min_blowout_win': safe_avg(blowout_win_mins),
            'avg_min_blowout_loss': safe_avg(blowout_loss_mins),
            'avg_min_close_game': safe_avg(close_mins),
            'avg_min_b2b': safe_avg(b2b_mins),
            'depth_order': depth_order,
            'position': position,
            'window_days': window_days,
            'games_on_current_team': games_on_current,
            'computed_at': computed_at,
        })

    if dry_run:
        print(f"\n  [DRY RUN] Would upsert {len(profiles)} rotation profiles")
        for p in sorted(profiles, key=lambda x: x['avg_minutes'], reverse=True)[:10]:
            print(f"    {p['player_name']:<25} {p['team_abbreviation']}  "
                  f"avg={p['avg_minutes']:.1f}  "
                  f"blowout_win={p['avg_min_blowout_win'] or 'n/a'}  "
                  f"close={p['avg_min_close_game'] or 'n/a'}  "
                  f"b2b={p['avg_min_b2b'] or 'n/a'}")
        return len(profiles)

    # Write to DB
    upsert_sql = """
        INSERT INTO rotation_profiles (
            player_id, player_name, team_abbreviation,
            avg_minutes, std_minutes, min_minutes, max_minutes,
            games_started, games_played, start_rate,
            avg_min_as_starter, avg_min_off_bench,
            avg_min_blowout_win, avg_min_blowout_loss,
            avg_min_close_game, avg_min_b2b,
            depth_order, position, window_days, games_on_current_team, computed_at
        ) VALUES (
            :player_id, :player_name, :team_abbreviation,
            :avg_minutes, :std_minutes, :min_minutes, :max_minutes,
            :games_started, :games_played, :start_rate,
            :avg_min_as_starter, :avg_min_off_bench,
            :avg_min_blowout_win, :avg_min_blowout_loss,
            :avg_min_close_game, :avg_min_b2b,
            :depth_order, :position, :window_days, :games_on_current_team, :computed_at
        )
        ON CONFLICT(player_id, team_abbreviation, window_days) DO UPDATE SET
            player_name=excluded.player_name,
            avg_minutes=excluded.avg_minutes,
            std_minutes=excluded.std_minutes,
            min_minutes=excluded.min_minutes,
            max_minutes=excluded.max_minutes,
            games_started=excluded.games_started,
            games_played=excluded.games_played,
            start_rate=excluded.start_rate,
            avg_min_as_starter=excluded.avg_min_as_starter,
            avg_min_off_bench=excluded.avg_min_off_bench,
            avg_min_blowout_win=excluded.avg_min_blowout_win,
            avg_min_blowout_loss=excluded.avg_min_blowout_loss,
            avg_min_close_game=excluded.avg_min_close_game,
            avg_min_b2b=excluded.avg_min_b2b,
            depth_order=excluded.depth_order,
            position=excluded.position,
            games_on_current_team=excluded.games_on_current_team,
            computed_at=excluded.computed_at
    """
    conn.executemany(upsert_sql, profiles)
    conn.commit()
    return len(profiles)


# ---------------------------------------------------------------------------
# PART B — beneficiary_minutes
# ---------------------------------------------------------------------------

def build_beneficiary_minutes(conn, window_days: int, min_games: int, dry_run: bool) -> int:
    """
    For each player who was absent on a team game day (DNP / injured),
    measure how much extra time their teammates got vs when they played.

    Only records pairs where games_without >= 2 AND minutes_delta > 1.0.
    Returns number of beneficiary relationships upserted.
    """
    computed_at = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    cutoff_date = f"date('now', '-{window_days} days')"

    # Step 0 — get all team game dates in window
    all_team_games = conn.execute(f"""
        SELECT date, home_team AS team FROM games WHERE date >= {cutoff_date}
        UNION ALL
        SELECT date, away_team AS team FROM games WHERE date >= {cutoff_date}
        ORDER BY team, date
    """).fetchall()

    team_game_dates = {}  # team_abbr -> sorted list of dates
    for row in all_team_games:
        team_game_dates.setdefault(row[1], []).append(row[0])

    # Step 1 — get all player appearances in window (player_id, team, date)
    player_dates = conn.execute(f"""
        SELECT player_id, player_name, team_abbreviation, game_date
        FROM player_game_logs
        WHERE game_date >= {cutoff_date}
        ORDER BY player_id, team_abbreviation, game_date
    """).fetchall()

    from collections import defaultdict
    # player_presence[(player_id, team)] = set of dates they played
    player_presence = defaultdict(set)
    player_name_map = {}
    for r in player_dates:
        key = (str(r['player_id']), r['team_abbreviation'])
        player_presence[key].add(r['game_date'])
        player_name_map[str(r['player_id'])] = r['player_name']

    beneficiary_rows = []

    for (out_player_id, team_abbr), played_dates in player_presence.items():
        team_dates = team_game_dates.get(team_abbr, [])
        if not team_dates:
            continue

        # Filter: player must have played >= min_games (not permanently DNP)
        if len(played_dates) < min_games:
            continue

        # Absent dates = team played but player didn't
        all_team_date_set = set(team_dates)
        absent_dates = sorted(all_team_date_set - played_dates)

        if len(absent_dates) < 2:
            continue  # Need >= 2 absences for meaningful signal

        # For each absent date, get teammate minutes
        teammate_without = defaultdict(list)  # beneficiary_id -> [minutes]
        for absent_date in absent_dates:
            rows = conn.execute("""
                SELECT player_id, player_name, minutes
                FROM player_game_logs
                WHERE game_date = ? AND team_abbreviation = ? AND player_id != ? AND minutes > 0
            """, (absent_date, team_abbr, out_player_id)).fetchall()
            for r in rows:
                teammate_without[str(r['player_id'])].append(r['minutes'])
                player_name_map[str(r['player_id'])] = r['player_name']

        if not teammate_without:
            continue

        # Step 3 — avg minutes WITH out_player (dates player played)
        played_dates_list = sorted(played_dates)
        placeholders = ','.join(['?'] * len(played_dates_list))
        teammate_with = {}
        rows = conn.execute(f"""
            SELECT player_id, AVG(minutes) as avg_with
            FROM player_game_logs
            WHERE game_date IN ({placeholders})
              AND team_abbreviation = ?
              AND player_id != ?
              AND minutes > 0
            GROUP BY player_id
        """, (*played_dates_list, team_abbr, out_player_id)).fetchall()
        for r in rows:
            teammate_with[str(r['player_id'])] = r['avg_with']

        # Step 4 — compute delta, filter noise
        out_player_name = player_name_map.get(out_player_id, out_player_id)
        for beneficiary_id, without_mins in teammate_without.items():
            games_without = len(without_mins)
            if games_without < 2:
                continue
            avg_without = sum(without_mins) / games_without
            avg_with = teammate_with.get(beneficiary_id)
            if avg_with is None:
                continue
            minutes_delta = avg_without - avg_with
            if minutes_delta <= 1.0:
                continue

            sample_dates = sorted(absent_dates)
            beneficiary_rows.append({
                'out_player_id': out_player_id,
                'out_player_name': out_player_name,
                'team_abbreviation': team_abbr,
                'beneficiary_player_id': beneficiary_id,
                'beneficiary_player_name': player_name_map.get(beneficiary_id, beneficiary_id),
                'games_without': games_without,
                'avg_minutes_without': round(avg_without, 2),
                'avg_minutes_with': round(avg_with, 2),
                'minutes_delta': round(minutes_delta, 2),
                'sample_start': sample_dates[0],
                'sample_end': sample_dates[-1],
                'computed_at': computed_at,
            })

    if dry_run:
        print(f"\n  [DRY RUN] Would upsert {len(beneficiary_rows)} beneficiary relationships")
        top5 = sorted(beneficiary_rows, key=lambda x: x['minutes_delta'], reverse=True)[:5]
        for b in top5:
            print(f"    When {b['out_player_name']:<22} OUT → "
                  f"{b['beneficiary_player_name']:<22} +{b['minutes_delta']:.1f} min "
                  f"({b['games_without']} games)")
        return len(beneficiary_rows)

    if not beneficiary_rows:
        return 0

    upsert_sql = """
        INSERT INTO beneficiary_minutes (
            out_player_id, out_player_name, team_abbreviation,
            beneficiary_player_id, beneficiary_player_name,
            games_without, avg_minutes_without, avg_minutes_with,
            minutes_delta, sample_start, sample_end, computed_at
        ) VALUES (
            :out_player_id, :out_player_name, :team_abbreviation,
            :beneficiary_player_id, :beneficiary_player_name,
            :games_without, :avg_minutes_without, :avg_minutes_with,
            :minutes_delta, :sample_start, :sample_end, :computed_at
        )
        ON CONFLICT(out_player_id, beneficiary_player_id, team_abbreviation) DO UPDATE SET
            out_player_name=excluded.out_player_name,
            beneficiary_player_name=excluded.beneficiary_player_name,
            games_without=excluded.games_without,
            avg_minutes_without=excluded.avg_minutes_without,
            avg_minutes_with=excluded.avg_minutes_with,
            minutes_delta=excluded.minutes_delta,
            sample_start=excluded.sample_start,
            sample_end=excluded.sample_end,
            computed_at=excluded.computed_at
    """
    conn.executemany(upsert_sql, beneficiary_rows)
    conn.commit()
    return len(beneficiary_rows)


# ---------------------------------------------------------------------------
# PART C — Rotation Trends (L7 vs L21)
# ---------------------------------------------------------------------------

def _print_rotation_trends(conn):
    """Compare L7 vs L21 minutes to find players trending up/down."""
    try:
        rows = conn.execute("""
            SELECT rp.player_name, rp.team_abbreviation, rp.avg_minutes as l21,
                   (SELECT AVG(pgl.minutes) FROM player_game_logs pgl
                    WHERE pgl.player_id = rp.player_id
                    AND pgl.game_date >= date('now', '-7 days')
                    AND pgl.minutes > 0) as l7
            FROM rotation_profiles rp
            WHERE rp.window_days = 21
            ORDER BY rp.avg_minutes DESC
        """).fetchall()
    except Exception as e:
        print(f"  [WARN] Rotation trends query failed: {e}")
        return

    trending_up = [(r['player_name'], r['team_abbreviation'], r['l21'], r['l7'])
                   for r in rows if r['l7'] and r['l7'] > r['l21'] and abs(r['l7'] - r['l21']) >= 3.0]
    trending_down = [(r['player_name'], r['team_abbreviation'], r['l21'], r['l7'])
                     for r in rows if r['l7'] and r['l7'] < r['l21'] and abs(r['l7'] - r['l21']) >= 3.0]

    print("\n=== ROTATION TRENDS (L7 vs L21) ===")
    if trending_up:
        print("TRENDING UP (getting more run):")
        for name, team, l21, l7 in sorted(trending_up, key=lambda x: x[3] - x[2], reverse=True)[:8]:
            print(f"  {name:<25} ({team})  {l21:.1f} → {l7:.1f} min  (+{l7 - l21:.1f})")
    else:
        print("  (no players trending up ≥3 min)")

    if trending_down:
        print("TRENDING DOWN (losing minutes):")
        for name, team, l21, l7 in sorted(trending_down, key=lambda x: x[2] - x[3], reverse=True)[:8]:
            print(f"  {name:<25} ({team})  {l21:.1f} → {l7:.1f} min  ({l7 - l21:.1f})")
    else:
        print("  (no players trending down ≥3 min)")


# ---------------------------------------------------------------------------
# PART D — Phase 8.12: Stale Profile Cleanup
# ---------------------------------------------------------------------------

def _cleanup_stale_profiles(conn, dry_run: bool) -> int:
    """
    Remove rotation_profiles rows for active players who no longer play for that team.
    Uses players.team as the current-team source of truth.

    Returns number of stale rows removed (or found if dry_run).
    """
    try:
        stale = conn.execute("""
            SELECT rp.player_id, rp.player_name, rp.team_abbreviation, p.team AS current_team
            FROM rotation_profiles rp
            JOIN players p ON rp.player_id = p.player_id
            WHERE p.team != rp.team_abbreviation
              AND p.is_active = 1
        """).fetchall()
    except Exception as e:
        print(f"  [WARN] Stale profiles query failed: {e}")
        return 0

    if not stale:
        print("  [STALE-PROFILES] None found — all clean")
        return 0

    for row in stale:
        print(f"  [STALE-PROFILES] {row['player_name']}: removing "
              f"{row['team_abbreviation']} profile (now {row['current_team']})")

    if not dry_run:
        for row in stale:
            conn.execute("""
                DELETE FROM rotation_profiles
                WHERE player_id = ? AND team_abbreviation = ?
            """, (row['player_id'], row['team_abbreviation']))
        conn.commit()

    return len(stale)


def _cleanup_stale_beneficiaries(conn, dry_run: bool) -> int:
    """
    Remove beneficiary_minutes rows where the out_player is no longer on that team.
    Uses players.team as the current-team source of truth.

    Returns number of stale rows removed (or found if dry_run).
    """
    try:
        stale = conn.execute("""
            SELECT bm.out_player_id, bm.out_player_name, bm.team_abbreviation,
                   p.team AS current_team
            FROM beneficiary_minutes bm
            JOIN players p ON bm.out_player_id = p.player_id
            WHERE p.team != bm.team_abbreviation
              AND p.is_active = 1
        """).fetchall()
    except Exception as e:
        print(f"  [WARN] Stale beneficiaries query failed: {e}")
        return 0

    if not stale:
        print("  [STALE-BENE] None found — all clean")
        return 0

    for row in stale:
        print(f"  [STALE-BENE] {row['out_player_name']}: removing "
              f"{row['team_abbreviation']} beneficiary rows (now {row['current_team']})")

    if not dry_run:
        for row in stale:
            conn.execute("""
                DELETE FROM beneficiary_minutes
                WHERE out_player_id = ? AND team_abbreviation = ?
            """, (row['out_player_id'], row['team_abbreviation']))
        conn.commit()

    return len(stale)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Build rotation profiles and beneficiary minutes')
    parser.add_argument('--dry-run', action='store_true', help='Print output without writing to DB')
    parser.add_argument('--window-days', type=int, default=21, help='Lookback window in days (default: 21)')
    parser.add_argument('--min-games', type=int, default=3, help='Minimum games required (default: 3)')
    args = parser.parse_args()

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Building rotation profiles "
          f"(window={args.window_days}d, min_games={args.min_games})")

    conn = _get_conn()

    # Part A
    print("\n--- Part A: rotation_profiles ---")
    n_profiles = build_rotation_profiles(conn, args.window_days, args.min_games, args.dry_run)
    print(f"  {'Would write' if args.dry_run else 'Wrote'} {n_profiles} rotation profiles")

    # Part B
    print("\n--- Part B: beneficiary_minutes ---")
    n_bene = build_beneficiary_minutes(conn, args.window_days, args.min_games, args.dry_run)
    print(f"  {'Would write' if args.dry_run else 'Wrote'} {n_bene} beneficiary relationships")

    # Part C — trends (only meaningful after profiles are written)
    if not args.dry_run:
        _print_rotation_trends(conn)

    # Part D — Phase 8.12: Stale profile cleanup (runs after build so new rows are written first)
    print("\n--- Part D: Stale Profile Cleanup (Phase 8.12) ---")
    n_stale_profiles = _cleanup_stale_profiles(conn, args.dry_run)
    n_stale_bene = _cleanup_stale_beneficiaries(conn, args.dry_run)
    print(f"  {'Would remove' if args.dry_run else 'Removed'} {n_stale_profiles} stale rotation profiles")
    print(f"  {'Would remove' if args.dry_run else 'Removed'} {n_stale_bene} stale beneficiary rows")

    conn.close()

    print(f"\n✅ Done: {n_profiles} rotation profiles | {n_bene} beneficiary relationships | "
          f"{n_stale_profiles} stale profiles removed")


if __name__ == '__main__':
    main()
