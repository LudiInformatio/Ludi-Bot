"""
Phase 8.9-B: Sync Stagger Stats
================================
Builds two-man pairing (stagger) data from player_game_logs.

NOTE: PBP Stats has NO get-stagger-stats endpoint (confirmed via OpenAPI spec at
https://api.pbpstats.com/openapi.json). This script builds equivalent data from
our existing player_game_logs table instead — more accurate because it uses our
actual game data rather than a third-party API.

"Stagger stats" = Player A's individual stats when partner B is ON vs OFF the court.
Positive pts_delta (pts_without - pts_with) means A benefits when B sits.

Usage:
    .venv/bin/python scripts/sync_stagger_stats.py              # full run
    .venv/bin/python scripts/sync_stagger_stats.py --dry-run   # no writes
    .venv/bin/python scripts/sync_stagger_stats.py --season 2025-26 --days 60
"""

import argparse
import sqlite3
import sys
import os
from datetime import datetime

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "ludi.db"
SEASON = "2025-26"
DEFAULT_DAYS = 60         # lookback window
MIN_GAMES_TOGETHER = 5    # minimum games_with to store a pair
MIN_GAMES_WITHOUT = 3     # minimum games_without to compute delta
# Only consider "significant" partners (played enough to be relevant)
MIN_PARTNER_GAMES = 15    # partner must have played this many games total in window


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.row_factory = sqlite3.Row
    return conn


def build_stagger_stats(days: int, season: str, dry_run: bool) -> int:
    """
    Build player_stagger_stats rows from player_game_logs.

    Strategy:
      1. Find all player pairs on same team with >= MIN_GAMES_TOGETHER games
      2. For each pair (A, B):
         - games_with: both A and B played >= 10 min
         - games_without: A played >= 10 min, B played < 5 min OR missing
      3. Compute per-game averages for each condition
      4. Store with pts_delta = pts_without - pts_with

    ortg_with/ortg_without: left NULL (not available at game level without possession data)
    usg_with/usg_without: approximated as per-36 FGA
    """
    conn = get_conn()
    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows_written = 0

    print(f"[STAGGER] Building stagger stats for last {days} days (season {season})...")

    # Step 1: Find all player pairs with enough shared games on the same team
    pairs_query = """
        SELECT
            A.player_id    AS player_id,
            A.player_name  AS player_name,
            B.player_id    AS partner_id,
            B.player_name  AS partner_name,
            A.team_abbreviation AS team,
            COUNT(*)       AS games_together
        FROM player_game_logs A
        JOIN player_game_logs B
            ON A.game_id = B.game_id
           AND A.team_abbreviation = B.team_abbreviation
           AND A.player_id < B.player_id   -- avoid duplicates
        WHERE A.game_date >= date('now', '-' || ? || ' days')
          AND A.minutes >= 10
          AND B.minutes >= 10
          AND A.player_id IS NOT NULL
          AND B.player_id IS NOT NULL
        GROUP BY A.player_id, B.player_id, A.team_abbreviation
        HAVING COUNT(*) >= ?
        ORDER BY games_together DESC
    """

    pairs = conn.execute(pairs_query, (days, MIN_GAMES_TOGETHER)).fetchall()
    print(f"[STAGGER] Found {len(pairs)} pairs with >= {MIN_GAMES_TOGETHER} games together")

    if not pairs:
        print("[STAGGER] No pairs found — check if player_game_logs has data for the window")
        conn.close()
        return 0

    # Step 2: For each pair, compute with/without stats in both directions
    # We store both (A|partner=B) and (B|partner=A) as separate rows
    pair_set = set()  # track which pairs we process to avoid double work
    rows_to_insert = []

    for pair in pairs:
        a_id = pair["player_id"]
        a_name = pair["player_name"]
        b_id = pair["partner_id"]
        b_name = pair["partner_name"]
        team = pair["team"]

        if (a_id, b_id, team) in pair_set:
            continue
        pair_set.add((a_id, b_id, team))

        # Compute stats for each direction: (A when B on/off) and (B when A on/off)
        for player_id, player_name, partner_id, partner_name in [
            (a_id, a_name, b_id, b_name),
            (b_id, b_name, a_id, a_name),
        ]:
            stats = _compute_with_without(conn, player_id, partner_id, team, days)
            if stats is None:
                continue

            # Only store if we have enough samples
            if stats["games_with"] < MIN_GAMES_TOGETHER:
                continue
            if stats["games_without"] < MIN_GAMES_WITHOUT:
                continue

            # Compute deltas: positive = benefits when partner sits
            pts_delta = None
            ast_delta = None
            reb_delta = None
            usg_delta = None
            if stats["pts_without"] is not None and stats["pts_with"] is not None:
                pts_delta = round(stats["pts_without"] - stats["pts_with"], 2)
            if stats["ast_without"] is not None and stats["ast_with"] is not None:
                ast_delta = round(stats["ast_without"] - stats["ast_with"], 2)
            if stats["reb_without"] is not None and stats["reb_with"] is not None:
                reb_delta = round(stats["reb_without"] - stats["reb_with"], 2)
            if stats["usg_without"] is not None and stats["usg_with"] is not None:
                usg_delta = round(stats["usg_without"] - stats["usg_with"], 4)

            rows_to_insert.append({
                "player_id": str(player_id),
                "player_name": player_name,
                "team_abbreviation": team,
                "partner_player_id": str(partner_id),
                "partner_player_name": partner_name,
                "season": season,
                "min_with": stats["min_with"],
                "pts_with": stats["pts_with"],
                "ast_with": stats["ast_with"],
                "reb_with": stats["reb_with"],
                "usg_with": stats["usg_with"],
                "ortg_with": None,  # not available at game level
                "min_without": stats["min_without"],
                "pts_without": stats["pts_without"],
                "ast_without": stats["ast_without"],
                "reb_without": stats["reb_without"],
                "usg_without": stats["usg_without"],
                "ortg_without": None,  # not available at game level
                "pts_delta": pts_delta,
                "ast_delta": ast_delta,
                "reb_delta": reb_delta,
                "usg_delta": usg_delta,
                "games_sample": stats["games_with"] + stats["games_without"],
                "synced_at": synced_at,
            })

    print(f"[STAGGER] Computed {len(rows_to_insert)} pair-direction rows")

    if dry_run:
        print("[STAGGER] DRY RUN — no writes")
        _print_top5(rows_to_insert)
        conn.close()
        return 0

    # Step 3: Write to DB
    if rows_to_insert:
        c = conn.cursor()
        for row in rows_to_insert:
            try:
                c.execute("""
                    INSERT INTO player_stagger_stats (
                        player_id, player_name, team_abbreviation,
                        partner_player_id, partner_player_name, season,
                        min_with, pts_with, ast_with, reb_with, usg_with, ortg_with,
                        min_without, pts_without, ast_without, reb_without, usg_without, ortg_without,
                        pts_delta, ast_delta, reb_delta, usg_delta,
                        games_sample, synced_at
                    ) VALUES (
                        :player_id, :player_name, :team_abbreviation,
                        :partner_player_id, :partner_player_name, :season,
                        :min_with, :pts_with, :ast_with, :reb_with, :usg_with, :ortg_with,
                        :min_without, :pts_without, :ast_without, :reb_without, :usg_without, :ortg_without,
                        :pts_delta, :ast_delta, :reb_delta, :usg_delta,
                        :games_sample, :synced_at
                    )
                    ON CONFLICT(player_id, partner_player_id, team_abbreviation, season) DO UPDATE SET
                        min_with=excluded.min_with,
                        pts_with=excluded.pts_with,
                        ast_with=excluded.ast_with,
                        reb_with=excluded.reb_with,
                        usg_with=excluded.usg_with,
                        min_without=excluded.min_without,
                        pts_without=excluded.pts_without,
                        ast_without=excluded.ast_without,
                        reb_without=excluded.reb_without,
                        usg_without=excluded.usg_without,
                        pts_delta=excluded.pts_delta,
                        ast_delta=excluded.ast_delta,
                        reb_delta=excluded.reb_delta,
                        usg_delta=excluded.usg_delta,
                        games_sample=excluded.games_sample,
                        synced_at=excluded.synced_at
                """, row)
                rows_written += 1
            except Exception as e:
                print(f"[STAGGER] Row error for {row['player_name']} / {row['partner_player_name']}: {e}")

        conn.commit()
        print(f"[STAGGER] Wrote {rows_written} rows to player_stagger_stats")

    _print_top5(rows_to_insert)
    conn.close()
    return rows_written


def _compute_with_without(conn, player_id, partner_id, team, days):
    """
    For player_id, compute per-game averages when partner_id is:
      - WITH: partner played >= 10 min in same game
      - WITHOUT: partner played < 5 min OR absent from game logs

    Returns dict with with/without stats, or None if insufficient data.
    usg approximated as per-36 FGA (not raw game FGA which varies with minutes).
    """
    # WITH stats: both player and partner played >= 10 min
    with_row = conn.execute("""
        SELECT
            COUNT(*) AS games,
            AVG(P.minutes) AS avg_min,
            AVG(P.pts) AS avg_pts,
            AVG(P.ast) AS avg_ast,
            AVG(P.reb) AS avg_reb,
            -- per-36 FGA as usage proxy (avoids minute-length bias)
            AVG(CASE WHEN P.minutes > 0 THEN P.fga * 36.0 / P.minutes ELSE NULL END) AS per36_fga
        FROM player_game_logs P
        JOIN player_game_logs Q
            ON P.game_id = Q.game_id
           AND P.team_abbreviation = Q.team_abbreviation
        WHERE P.player_id = ?
          AND Q.player_id = ?
          AND P.team_abbreviation = ?
          AND P.game_date >= date('now', '-' || ? || ' days')
          AND P.minutes >= 10
          AND Q.minutes >= 10
    """, (player_id, partner_id, team, days)).fetchone()

    # WITHOUT stats: player played >= 10 min, partner played < 5 min or absent
    without_row = conn.execute("""
        SELECT
            COUNT(*) AS games,
            AVG(P.minutes) AS avg_min,
            AVG(P.pts) AS avg_pts,
            AVG(P.ast) AS avg_ast,
            AVG(P.reb) AS avg_reb,
            AVG(CASE WHEN P.minutes > 0 THEN P.fga * 36.0 / P.minutes ELSE NULL END) AS per36_fga
        FROM player_game_logs P
        LEFT JOIN player_game_logs Q
            ON P.game_id = Q.game_id
           AND P.team_abbreviation = Q.team_abbreviation
           AND Q.player_id = ?
        WHERE P.player_id = ?
          AND P.team_abbreviation = ?
          AND P.game_date >= date('now', '-' || ? || ' days')
          AND P.minutes >= 10
          AND (Q.player_id IS NULL OR Q.minutes < 5)  -- partner absent or DNP
    """, (partner_id, player_id, team, days)).fetchone()

    if not with_row or not without_row:
        return None

    def _r(v, n=2):
        return round(v, n) if v is not None else None

    return {
        "games_with": with_row["games"] or 0,
        "min_with": _r(with_row["avg_min"]),
        "pts_with": _r(with_row["avg_pts"]),
        "ast_with": _r(with_row["avg_ast"]),
        "reb_with": _r(with_row["avg_reb"]),
        "usg_with": _r(with_row["per36_fga"], 3),
        "games_without": without_row["games"] or 0,
        "min_without": _r(without_row["avg_min"]),
        "pts_without": _r(without_row["avg_pts"]),
        "ast_without": _r(without_row["avg_ast"]),
        "reb_without": _r(without_row["avg_reb"]),
        "usg_without": _r(without_row["per36_fga"], 3),
    }


def _print_top5(rows):
    """Print top 5 pairs by pts_delta."""
    if not rows:
        print("[STAGGER] No rows to display")
        return

    valid = [r for r in rows if r.get("pts_delta") is not None]
    top5 = sorted(valid, key=lambda r: r["pts_delta"], reverse=True)[:5]

    print("\n[STAGGER] Top 5 pairs by pts_delta (pts boost when partner sits):")
    print(f"  {'Player':<22} {'Partner':<22} {'Team':<5} {'pts_delta':>9} {'usg_delta':>9} {'sample':>6}")
    print("  " + "-" * 80)
    for r in top5:
        print(f"  {r['player_name']:<22} {r['partner_player_name']:<22} {r['team_abbreviation']:<5}"
              f"  {r['pts_delta']:>8.1f}  {(r['usg_delta'] or 0):>8.2f}  {r['games_sample']:>5}")


def main():
    parser = argparse.ArgumentParser(description="Sync stagger stats from player_game_logs")
    parser.add_argument("--dry-run", action="store_true", help="No DB writes")
    parser.add_argument("--season", default=SEASON, help="Season string (default: 2025-26)")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help="Lookback window in days (default: 60)")
    args = parser.parse_args()

    print(f"[STAGGER] Phase 8.9-B — Stagger Stats Sync")
    print(f"[STAGGER] Source: player_game_logs (PBP Stats has no stagger endpoint)")
    print(f"[STAGGER] Window: {args.days} days | Season: {args.season} | dry_run={args.dry_run}")

    n = build_stagger_stats(args.days, args.season, args.dry_run)
    print(f"\n[STAGGER] Done. {n} pairs synced.")


if __name__ == "__main__":
    main()
