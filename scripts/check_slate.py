#!/usr/bin/env python3
"""
Check Today's NBA Slate (Phase 8 — Schedule Awareness)

Smart local-first check: queries nba_calendar table first (free, instant),
falls back to live BDL API only if the table is stale or missing.

Used as a pre-flight gate in GitHub Actions workflows.

Usage:
    python scripts/check_slate.py [--date YYYY-MM-DD] [--db ludi.db]

Exit Codes:
    0 = games today (pipeline should run)
    2 = no games today (workflow should skip gracefully — NOT an error)

GitHub Actions Output (written to $GITHUB_OUTPUT when available):
    has_games      = true / false
    season_phase   = regular / playoffs / allstar_break / offseason / preseason / unknown
    is_extended_break = true / false  (no games for 7+ consecutive days)
    game_count     = integer

FAIL-OPEN: any unexpected exception → exit 0 (assume games, let pipeline decide)
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

# Allow running from project root or scripts/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.environ.get("LUDI_DB_PATH", "ludi.db")
STALE_DAYS = 8  # nba_calendar is considered stale if not synced within this many days


def _write_github_output(key: str, value: str):
    """Write key=value to $GITHUB_OUTPUT if running inside GitHub Actions."""
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        try:
            with open(gh_output, "a") as f:
                f.write(f"{key}={value}\n")
        except OSError:
            pass  # Don't crash if GITHUB_OUTPUT file isn't writable


def _is_fresh(synced_at: str) -> bool:
    """Return True if synced_at is within STALE_DAYS."""
    try:
        sync_dt = datetime.fromisoformat(synced_at.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        return (now_dt - sync_dt).days <= STALE_DAYS
    except (ValueError, TypeError):
        return False


def _check_extended_break(conn: sqlite3.Connection, date_str: str) -> bool:
    """
    Return True if there are no games for 7+ consecutive days starting from date_str.
    Looks ahead 14 days to detect off-season / All-Star break gaps.
    """
    try:
        date_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        future_end = str(date_dt + timedelta(days=14))
        rows = conn.execute(
            """
            SELECT has_games FROM nba_calendar
            WHERE date > ? AND date <= ?
            ORDER BY date ASC
            """,
            (date_str, future_end),
        ).fetchall()

        if not rows:
            return False  # No data — can't determine

        # Check for a 7+ day no-game streak starting from today
        consecutive_off = 0
        for row in rows:
            if row[0] == 0:
                consecutive_off += 1
                if consecutive_off >= 7:
                    return True
            else:
                break  # Games found — not an extended break

        return False
    except Exception:
        return False


def _check_bdl_live(date_str: str) -> tuple:
    """
    Fallback: query BDL directly for today's games.
    Returns (has_games: bool, game_count: int, season_phase: str, is_extended_break: bool)
    """
    try:
        from utils.bdl_client import BDLClient
        bdl = BDLClient()
        response = bdl.get_games(date=date_str)

        # Guard against error responses — BDL may return non-dict or dict without 'data'
        if not isinstance(response, dict) or 'data' not in response:
            print(f"⚠️  BDL returned unexpected response (possibly auth error) — failing open")
            return True, 0, "unknown", False

        games = response.get("data", [])
        if not isinstance(games, list):
            print(f"⚠️  BDL 'data' field is not a list — failing open")
            return True, 0, "unknown", False

        game_count = len(games)
        has_games = game_count > 0

        # Date-aware phase inference
        month = int(date_str[5:7])
        if has_games:
            if month == 10 and game_count <= 4:
                phase = "preseason"
            elif month in (4, 5, 6):
                phase = "playoffs"
            else:
                phase = "regular"
        else:
            # Be precise: All-Star break is mid-February only, not any gameless day
            if month in (7, 8, 9):
                phase = "offseason"
            elif month == 2:
                phase = "allstar_break"
            else:
                # Could be API error, rest day, or schedule gap — don't assume break
                phase = "no_games_today"

        return has_games, game_count, phase, False  # Can't check extended break without DB history
    except Exception as e:
        print(f"⚠️  BDL live check failed: {e} — failing open (assuming games exist)")
        return True, 0, "unknown", False


def check_slate(date_str: str = None, db_path: str = None) -> tuple:
    """
    Check whether there are NBA games on the given date.

    Returns:
        (has_games: bool, game_count: int, season_phase: str, is_extended_break: bool)
    """
    if date_str is None:
        date_str = str(datetime.now(timezone.utc).date())
    if db_path is None:
        db_path = DB_PATH

    # --- Try nba_calendar table first (fast, free, purpose-built) ---
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        conn.row_factory = sqlite3.Row

        row = conn.execute(
            "SELECT has_games, game_count, season_phase, synced_at FROM nba_calendar WHERE date = ?",
            (date_str,),
        ).fetchone()

        if row and _is_fresh(row["synced_at"]):
            has_games = row["has_games"] == 1
            game_count = row["game_count"]
            phase = row["season_phase"]
            is_ext = _check_extended_break(conn, date_str) if not has_games else False
            conn.close()
            return has_games, game_count, phase, is_ext

        conn.close()

        # Table is stale or date not found — fall back to live BDL
        print("⚠️  nba_calendar stale or missing for this date — falling back to live BDL check")
        print("   Run: python scripts/sync_season_schedule.py --days 30")

    except sqlite3.Error as e:
        print(f"⚠️  DB error reading nba_calendar: {e} — falling back to live BDL check")

    # --- Fallback: live BDL ---
    return _check_bdl_live(date_str)


def main():
    parser = argparse.ArgumentParser(
        description="Check NBA game slate for a given date",
        epilog="""
Exit codes:
  0 = games today (run the pipeline)
  2 = no games today (skip gracefully)
        """,
    )
    parser.add_argument(
        "--date", type=str, default=None,
        help="Date to check (YYYY-MM-DD, default: today)"
    )
    parser.add_argument(
        "--db", type=str, default=None,
        help="Database path (default: ludi.db)"
    )
    args = parser.parse_args()

    try:
        has_games, game_count, phase, is_extended_break = check_slate(
            date_str=args.date, db_path=args.db
        )
    except Exception as e:
        # FAIL-OPEN: unexpected error → assume games exist
        print(f"⚠️  check_slate() raised unexpected error: {e}")
        print("   Failing open — assuming games exist. Let pipeline decide.")
        _write_github_output("has_games", "true")
        _write_github_output("season_phase", "unknown")
        _write_github_output("is_extended_break", "false")
        _write_github_output("game_count", "0")
        sys.exit(0)

    date_label = args.date or str(datetime.now(timezone.utc).date())

    # Write GitHub Actions outputs
    _write_github_output("has_games", "true" if has_games else "false")
    _write_github_output("season_phase", phase)
    _write_github_output("is_extended_break", "true" if is_extended_break else "false")
    _write_github_output("game_count", str(game_count))

    if has_games:
        print(f"✅ {date_label}: {game_count} game(s) scheduled — phase={phase}")
        sys.exit(0)
    else:
        ext_label = " (extended break)" if is_extended_break else ""
        print(f"📅 {date_label}: No NBA games today — phase={phase}{ext_label}")
        sys.exit(2)


if __name__ == "__main__":
    main()
