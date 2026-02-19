#!/usr/bin/env python3
"""
Sync Season Schedule (Phase 8 — Schedule Awareness)

Queries BDL get_games() for the next 30 days (+ last 7 days backfill) and
upserts into the nba_calendar table with inferred season_phase.

Runs weekly (Sundays) via data_sync.yml. Zero API cost on GOAT tier.

Usage:
    python scripts/sync_season_schedule.py [--days 30] [--dry-run]

Exit Codes:
    0 = success (always, never blocks other steps)
"""

import argparse
import sqlite3
import sys
import os
from datetime import datetime, timedelta, timezone

# Allow running from project root or scripts/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.bdl_client import BDLClient
except ImportError:
    print("⚠️  Could not import BDLClient — check PYTHONPATH")
    sys.exit(0)


CURRENT_SEASON = "2025-26"
DB_PATH = os.environ.get("LUDI_DB_PATH", "ludi.db")


def infer_phase(date_str: str, game_count: int) -> str:
    """
    Infer the NBA season phase for a given date and game count.

    Uses date ranges (month) as a simple heuristic — accurate enough for
    workflow gating without needing an external calendar API.
    """
    month = int(date_str[5:7])

    if game_count > 0:
        if month == 10 and game_count <= 4:
            return "preseason"
        elif month in (4, 5, 6):
            return "playoffs"
        else:
            return "regular"
    else:
        # No games — determine why
        if month in (7, 8, 9):
            return "offseason"
        elif month == 2:
            # February no-game window is typically All-Star break
            return "allstar_break"
        else:
            return "offseason"


def get_db_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def sync_schedule(forward_days: int = 30, dry_run: bool = False) -> bool:
    """
    Sync NBA calendar for the next `forward_days` days + last 7 days backfill.

    Returns True on success, False on error.
    """
    bdl = BDLClient()
    conn = get_db_connection(DB_PATH)

    today = datetime.now(timezone.utc).date()
    # Backfill 7 days to ensure no gaps from a missed sync
    start_date = today - timedelta(days=7)
    end_date = today + timedelta(days=forward_days)

    dates_to_check = []
    d = start_date
    while d <= end_date:
        dates_to_check.append(str(d))
        d += timedelta(days=1)

    print(f"📅 Syncing {len(dates_to_check)} dates ({start_date} → {end_date})...")

    game_days = 0
    off_days = 0
    errors = 0
    phase_counts: dict = {}

    synced_at = datetime.now(timezone.utc).isoformat()

    for date_str in dates_to_check:
        try:
            response = bdl.get_games(date=date_str)
            games = response.get("data", []) if isinstance(response, dict) else []
            game_count = len(games)
            has_games = 1 if game_count > 0 else 0
            phase = infer_phase(date_str, game_count)

            phase_counts[phase] = phase_counts.get(phase, 0) + 1
            if has_games:
                game_days += 1
            else:
                off_days += 1

            if not dry_run:
                conn.execute(
                    """
                    INSERT INTO nba_calendar (date, season, has_games, game_count, season_phase, synced_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        has_games    = excluded.has_games,
                        game_count   = excluded.game_count,
                        season_phase = excluded.season_phase,
                        synced_at    = excluded.synced_at
                    """,
                    (date_str, CURRENT_SEASON, has_games, game_count, phase, synced_at),
                )

        except Exception as e:
            print(f"   ⚠️  {date_str}: error — {e}")
            errors += 1
            continue

    if not dry_run:
        conn.commit()
    conn.close()

    # Determine current phase (today's entry)
    today_str = str(today)
    current_phase = "unknown"
    try:
        conn2 = get_db_connection(DB_PATH)
        row = conn2.execute(
            "SELECT season_phase, game_count FROM nba_calendar WHERE date = ?", (today_str,)
        ).fetchone()
        if row:
            current_phase = row["season_phase"]
            today_count = row["game_count"]
        conn2.close()
    except Exception:
        today_count = 0

    prefix = "[DRY RUN] " if dry_run else ""
    print(
        f"\n{prefix}✅ Synced {len(dates_to_check)} dates: "
        f"{game_days} game days, {off_days} off days"
        + (f", {errors} errors" if errors else "")
    )
    print(f"   Current phase: {current_phase} (today: {today_count} games)")
    if phase_counts:
        for p, count in sorted(phase_counts.items()):
            print(f"   {p}: {count} dates")

    return errors == 0


def main():
    parser = argparse.ArgumentParser(
        description="Sync NBA season schedule into nba_calendar table"
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Number of forward days to sync (default: 30)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Query BDL but do not write to database"
    )
    args = parser.parse_args()

    success = sync_schedule(forward_days=args.days, dry_run=args.dry_run)
    # Always exit 0 — never let schedule sync block other data sync steps
    sys.exit(0)


if __name__ == "__main__":
    main()
