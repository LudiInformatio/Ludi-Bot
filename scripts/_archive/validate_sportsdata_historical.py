# ARCHIVED: 2026-03-03 — 2024-25 validation reference only
"""
SportsDataIO Historical Data Validator
Compares SportsDataIO 2024-25 box scores against our player_game_logs.

What it does:
  - Fetches 5 sample game dates from 2024-25 season (5 API calls)
  - Joins SportsDataIO player stats with our DB by player name
  - Computes mean absolute difference (MAD) per stat: PTS, REB, AST, FGA, FTA
  - Flags outliers (any player off by > 2 in a single stat)
  - Produces a confidence score for the API data source

Usage:
    python scripts/validate_sportsdata_historical.py
    python scripts/validate_sportsdata_historical.py --verbose   # Show per-player diffs
    python scripts/validate_sportsdata_historical.py --dates "2025-JAN-15,2025-FEB-01,2025-MAR-10"

Cost: 5 API calls (uses 1s rate limit)
"""

import os
import sys
import re
import unicodedata
import argparse
import sqlite3
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.sportsdata_client import get_client


# ---------------------------------------------------------------------------
# Name normalization (same logic as crosswalk builder)
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Normalize player name for fuzzy matching."""
    if not name:
        return ""
    nfd = unicodedata.normalize("NFD", name)
    ascii_name = nfd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"['\-\.]", "", ascii_name).lower().strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------

# Stats to compare (SportsDataIO field → player_game_logs column)
STAT_MAP = {
    "Points":       "pts",
    "Rebounds":     "reb",
    "Assists":      "ast",
    "FieldGoalsAttempted": "fga",
    "FreeThrowsAttempted": "fta",
}

# Default sample dates: spread across 2024-25 season
DEFAULT_DATES = [
    "2024-NOV-06",   # Early season
    "2024-DEC-15",   # Mid December
    "2025-JAN-15",   # Mid January
    "2025-FEB-01",   # Around All-Star break
    "2025-MAR-10",   # Late season
]


def _load_db_stats_for_date(conn: sqlite3.Connection, date_str: str) -> dict:
    """
    Load player stats from player_game_logs for a given date.
    date_str is ISO format: YYYY-MM-DD (converted from SportsDataIO YYYY-MMM-DD)
    Returns: dict keyed by normalized_name → row dict
    """
    # Convert YYYY-MMM-DD → YYYY-MM-DD
    try:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%b-%d")
        iso_date = dt.strftime("%Y-%m-%d")
    except ValueError:
        iso_date = date_str  # Already in ISO format

    cursor = conn.execute("""
        SELECT player_name, pts, reb, ast, fga, fta, minutes
        FROM player_game_logs
        WHERE game_date = ?
    """, (iso_date,))
    rows = cursor.fetchall()
    result = {}
    for row in rows:
        name, pts, reb, ast, fga, fta, minutes = row
        key = _normalize_name(name)
        result[key] = {
            "name": name,
            "pts": pts or 0,
            "reb": reb or 0,
            "ast": ast or 0,
            "fga": fga or 0,
            "fta": fta or 0,
            "minutes": minutes or 0,
        }
    return result


def validate_historical(dates: list, verbose: bool = False):
    print("\n" + "=" * 65)
    print("  SPORTSDATA.IO HISTORICAL DATA VALIDATOR")
    print("=" * 65)

    if not config.USE_SPORTSDATA:
        print("❌  SPORTSDATA_API_KEY not set — cannot validate.")
        sys.exit(1)

    client = get_client()
    conn = sqlite3.connect(config.DB_PATH)

    # Accumulate diffs across all dates
    all_diffs = defaultdict(list)   # stat_name → list of abs differences
    outliers = []                    # (date, player, stat, sd_val, db_val, diff)
    total_players_compared = 0
    total_players_not_matched = 0

    for date_str in dates:
        print(f"\n  📅  {date_str}")

        # Fetch SportsDataIO data
        sd_stats = client.get_player_game_stats(date_str)
        if not sd_stats:
            print(f"     ⚠️  No data returned from SportsDataIO for {date_str}")
            continue

        # Convert date for DB lookup
        try:
            from datetime import datetime
            dt = datetime.strptime(date_str, "%Y-%b-%d")
            iso_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            iso_date = date_str

        # Load our DB stats
        db_stats = _load_db_stats_for_date(conn, iso_date)
        if not db_stats:
            print(f"     ℹ️  No records in player_game_logs for {iso_date} — skipping")
            continue

        print(f"     SportsDataIO: {len(sd_stats)} player-games | DB: {len(db_stats)} player-games")

        date_matched = 0
        date_not_matched = 0

        for sd_player in sd_stats:
            first = sd_player.get("Name", "") or ""
            # SportsDataIO returns "Name" as "FirstName LastName"
            if not first:
                first_n = sd_player.get("FirstName", "") or ""
                last_n  = sd_player.get("LastName", "") or ""
                full    = f"{first_n} {last_n}".strip()
            else:
                full = first

            key = _normalize_name(full)
            db_row = db_stats.get(key)

            if not db_row:
                date_not_matched += 1
                continue

            # Skip DNP players (0 minutes in either source)
            sd_min = sd_player.get("Minutes") or 0
            if sd_min == 0 or db_row["minutes"] == 0:
                continue

            date_matched += 1
            total_players_compared += 1

            # Compare each stat
            for sd_field, db_col in STAT_MAP.items():
                sd_val = sd_player.get(sd_field) or 0
                db_val = db_row.get(db_col) or 0

                diff = abs(sd_val - db_val)
                all_diffs[db_col].append(diff)

                if diff > 2:
                    outliers.append((date_str, full, db_col, sd_val, db_val, diff))

                if verbose:
                    flag = " ⚠️" if diff > 2 else ""
                    print(f"     {full:<25} {db_col:<4}  SD:{sd_val:5.1f}  DB:{db_val:5.1f}  diff:{diff:4.1f}{flag}")

        total_players_not_matched += date_not_matched
        print(f"     Matched: {date_matched} | Not matched: {date_not_matched}")

    conn.close()

    # -----------------------------------------------
    # Results Summary
    # -----------------------------------------------
    print("\n" + "=" * 65)
    print("  ACCURACY REPORT")
    print("=" * 65)

    if total_players_compared == 0:
        print("  ⚠️  No player-games compared. Check dates or DB coverage.")
        return

    print(f"  Total player-games compared: {total_players_compared}")
    print(f"  Players not matched by name: {total_players_not_matched}\n")

    stat_grades = []
    for stat, diffs in all_diffs.items():
        if not diffs:
            continue
        mad = sum(diffs) / len(diffs)
        n_outliers = sum(1 for d in diffs if d > 2)
        outlier_pct = n_outliers / len(diffs) * 100

        if mad < 0.5:
            grade = "A+ (near-perfect)"
        elif mad < 1.0:
            grade = "A  (excellent)"
        elif mad < 2.0:
            grade = "B  (good)"
        elif mad < 3.5:
            grade = "C  (acceptable)"
        else:
            grade = "D  (poor — investigate)"

        stat_grades.append((stat, mad, outlier_pct, grade))
        print(f"  {stat.upper():<5}  MAD: {mad:.2f}  Outliers(>2): {outlier_pct:.1f}%  Grade: {grade}")

    # Overall confidence score
    if stat_grades:
        avg_mad = sum(g[1] for g in stat_grades) / len(stat_grades)
        if avg_mad < 1.0:
            confidence = "HIGH (95%+ data accuracy)"
        elif avg_mad < 2.0:
            confidence = "MEDIUM (likely minor discrepancies)"
        else:
            confidence = "LOW (investigate before using for backtesting)"
        print(f"\n  Overall confidence: {confidence}")
        print(f"  Average MAD across stats: {avg_mad:.2f}")

    # Show worst outliers
    if outliers:
        print(f"\n  Top outliers (diff > 2): showing worst {min(10, len(outliers))}")
        outliers_sorted = sorted(outliers, key=lambda x: -x[5])
        for date, player, stat, sd_val, db_val, diff in outliers_sorted[:10]:
            print(f"    {date}  {player:<25} {stat:<4}  SD:{sd_val:.0f}  DB:{db_val:.0f}  diff:{diff:.0f}")

    print("=" * 65 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Validate SportsDataIO historical data vs ludi.db")
    parser.add_argument("--verbose", action="store_true", help="Show per-player stat comparisons")
    parser.add_argument("--dates", type=str, default="",
                        help="Comma-separated dates in YYYY-MMM-DD format (default: 5 sample dates)")
    args = parser.parse_args()

    if args.dates:
        dates = [d.strip() for d in args.dates.split(",") if d.strip()]
    else:
        dates = DEFAULT_DATES

    validate_historical(dates=dates, verbose=args.verbose)


if __name__ == "__main__":
    main()
