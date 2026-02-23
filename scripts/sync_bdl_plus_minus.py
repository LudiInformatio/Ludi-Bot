"""
sync_bdl_plus_minus.py -- BDL Box Score Plus/Minus Tier 2 Fill

Fills player_game_logs.plus_minus WHERE NULL using BDL box score data.
Never overwrites Tank01 (Tier 1) or SportsDataIO (Tier 1) values.
BDL is Tier 2: additive-only, COALESCE pattern enforced via WHERE plus_minus IS NULL.

Why this script exists:
  Tank01 box scores are our Tier 1 source for game logs, but plus_minus is
  frequently NULL (7,565+ rows as of Feb 22, 2026). BDL box scores reliably
  include plus_minus as a direct field on each player stat dict.

Usage:
    python scripts/sync_bdl_plus_minus.py                    # yesterday
    python scripts/sync_bdl_plus_minus.py --date 2026-02-21  # specific date
    python scripts/sync_bdl_plus_minus.py --backfill         # all NULL dates
    python scripts/sync_bdl_plus_minus.py --dry-run          # preview only

Cost: ~15 BDL calls per date (1 per game, up to 15 games/night), 600 req/min limit.
      BDL box_scores endpoint: 1 API call per invocation per date.
"""

import argparse
import os
import re
import sqlite3
import sys
import unicodedata
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

# Allow imports from project root regardless of CWD
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import config
from utils.bdl_client import _get_client


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DB_PATH = config.DB_PATH  # "ludi.db"
DIVIDER = "=" * 60


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """
    Normalize a player name for fuzzy matching across APIs.

    Handles:
    - Unicode accents (Doncic -> Doncic, Jokic -> Jokic)
    - Apostrophes, hyphens, periods removed (Day'Ron -> dayron)
    - Suffixes stripped (Jr., Sr., III, II, IV)
    - Lowercased and whitespace collapsed

    Examples:
        "Stephen Curry"   -> "stephen curry"
        "Nikola Jokic"    -> "nikola jokic"
        "Gary Payton II"  -> "gary payton"
        "Day'Ron Sharpe"  -> "dayron sharpe"
        "E.J. Liddell"    -> "ej liddell"
    """
    if not name:
        return ""
    # Strip accents via Unicode NFD decomposition
    nfd = unicodedata.normalize("NFD", name)
    ascii_name = nfd.encode("ascii", "ignore").decode("ascii")
    # Lowercase
    clean = ascii_name.lower().strip()
    # Remove suffixes before punctuation removal (order matters for "jr." etc.)
    for suffix in [" jr.", " jr", " sr.", " sr", " iii", " ii", " iv", " v"]:
        if clean.endswith(suffix):
            clean = clean[: -len(suffix)]
    # Remove apostrophes, hyphens, periods (handles Day'Ron, E.J.)
    clean = re.sub(r"['\-\.]", "", clean)
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_db_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Open WAL-mode SQLite connection with busy timeout."""
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_null_rows(conn: sqlite3.Connection, game_date: str) -> Dict[str, dict]:
    """
    Build a lookup of normalized_player_name -> row for rows that have
    NULL plus_minus on the given date.

    Returns:
        Dict keyed by normalized name, value = {'player_name': str, 'rowid': int}
        Only includes rows where plus_minus IS NULL (candidates for BDL fill).
    """
    cur = conn.execute(
        """
        SELECT rowid, player_name
        FROM   player_game_logs
        WHERE  game_date = ?
          AND  plus_minus IS NULL
        """,
        (game_date,),
    )
    result: Dict[str, dict] = {}
    for row in cur.fetchall():
        normalized = _normalize_name(row["player_name"] or "")
        if normalized:
            # If two players normalize to the same key, keep first encountered.
            # Duplicate normalized names would indicate a data integrity issue.
            result.setdefault(
                normalized,
                {"player_name": row["player_name"], "rowid": row["rowid"]},
            )
    return result


def _fetch_dates_with_null_plus_minus(conn: sqlite3.Connection) -> List[str]:
    """
    Return all distinct game_dates that have at least one NULL plus_minus row.
    Ordered most-recent-first so recent data is filled first.
    """
    cur = conn.execute(
        """
        SELECT DISTINCT game_date
        FROM   player_game_logs
        WHERE  plus_minus IS NULL
        ORDER  BY game_date DESC
        """
    )
    return [row[0] for row in cur.fetchall()]


def _update_plus_minus(
    conn: sqlite3.Connection,
    rowid: int,
    value: int,
    dry_run: bool,
) -> bool:
    """
    Update plus_minus for a single row by rowid.

    The WHERE plus_minus IS NULL clause is the Tier 2 safety guard -- even if
    Tank01 wrote a value between when we read the NULL lookup and now, this
    UPDATE will silently skip the row (rowcount == 0) rather than overwrite it.

    Returns True if the row was updated (or would be updated in dry-run mode).
    """
    if dry_run:
        return True  # Treat as success for counting purposes
    try:
        cur = conn.execute(
            """
            UPDATE player_game_logs
            SET    plus_minus = ?
            WHERE  rowid = ?
              AND  plus_minus IS NULL
            """,
            (value, rowid),
        )
        return cur.rowcount > 0
    except Exception as e:
        print(f"    [DB ERROR] rowid={rowid}: {e}")
        return False


# ---------------------------------------------------------------------------
# BDL box score parsing
# ---------------------------------------------------------------------------

def _extract_players_from_game(game: dict) -> List[Tuple[str, Optional[int]]]:
    """
    Extract (full_name, plus_minus) tuples from a BDL box score game dict.

    BDL box score structure (confirmed from API docs and live testing Feb 22, 2026):

      game = {
          'home_team': {
              'team': {'abbreviation': 'GSW'},
              'players': [
                  {
                      'player': {'id': 123, 'first_name': 'Stephen', 'last_name': 'Curry'},
                      'min': '32:15',
                      'pts': 28,
                      'plus_minus': 12,   # Direct field on player_entry, NOT in 'player' subdict
                      ...
                  }
              ]
          },
          'visitor_team': {... same shape ...}
      }

    Returns list of (full_name, plus_minus) for ALL players (home + away).
    plus_minus will be None if the field is absent or the player did not play.
    """
    results: List[Tuple[str, Optional[int]]] = []

    for side_key in ("home_team", "visitor_team"):
        side = game.get(side_key)
        if not isinstance(side, dict):
            continue
        players = side.get("players", [])
        if not isinstance(players, list):
            continue

        for player_entry in players:
            if not isinstance(player_entry, dict):
                continue

            # Name lives in the nested 'player' subdict
            player_info = player_entry.get("player") or {}
            first = (player_info.get("first_name") or "").strip()
            last = (player_info.get("last_name") or "").strip()
            if not first and not last:
                continue
            full_name = f"{first} {last}".strip()

            # plus_minus is a DIRECT field on player_entry (not inside player_info)
            raw_pm = player_entry.get("plus_minus")
            if raw_pm is None:
                results.append((full_name, None))
                continue

            # Cast to int -- BDL may return int, float, or empty string for DNP
            try:
                pm_int = int(raw_pm)
                results.append((full_name, pm_int))
            except (ValueError, TypeError):
                results.append((full_name, None))

    return results


# ---------------------------------------------------------------------------
# Core processing for a single date
# ---------------------------------------------------------------------------

def _process_date(
    client,
    conn: sqlite3.Connection,
    game_date: str,
    dry_run: bool,
    verbose: bool,
) -> Tuple[int, int, int, int, int]:
    """
    Fetch BDL box scores for game_date and fill NULL plus_minus values.

    Returns:
        (games_fetched, players_with_pm, updated, already_had_value, no_match)

        games_fetched     - Number of game dicts returned by BDL
        players_with_pm   - BDL players who had a non-None plus_minus value
        updated           - Rows we updated (or would update in dry-run)
        already_had_value - BDL players found in DB but plus_minus already non-NULL
        no_match          - BDL players not found in our DB at all for this date
    """
    # Fetch box scores from BDL
    try:
        games = client.get_box_scores(date=game_date)
    except Exception as e:
        print(f"  [BDL ERROR] Failed to fetch box scores for {game_date}: {e}")
        return 0, 0, 0, 0, 0

    if not games:
        print(f"  [WARN] No BDL box scores returned for {game_date}")
        return 0, 0, 0, 0, 0

    if verbose:
        print(f"  BDL returned {len(games)} game(s) for {game_date}")

    # Build DB lookup: normalized_name -> row_info for NULL rows only
    null_lookup = _fetch_null_rows(conn, game_date)

    # Build set of ALL normalized names on this date (to detect already-filled rows)
    all_rows_cur = conn.execute(
        "SELECT player_name FROM player_game_logs WHERE game_date = ?",
        (game_date,),
    )
    all_names_on_date = {
        _normalize_name(r["player_name"] or "") for r in all_rows_cur.fetchall()
    }

    games_fetched = len(games)
    players_with_pm = 0
    updated = 0
    already_had_value = 0
    no_match = 0

    for game in games:
        player_entries = _extract_players_from_game(game)

        for full_name, pm_value in player_entries:
            if pm_value is None:
                # No plus_minus data (DNP or incomplete game data) -- skip
                continue

            players_with_pm += 1
            norm_name = _normalize_name(full_name)

            if norm_name in null_lookup:
                # Row exists in DB with NULL plus_minus -- fill it (Tier 2 write)
                row_info = null_lookup[norm_name]
                success = _update_plus_minus(
                    conn, row_info["rowid"], pm_value, dry_run
                )
                if success:
                    updated += 1
                    if verbose:
                        flag = "[DRY RUN] " if dry_run else ""
                        print(
                            f"    {flag}Updated: {row_info['player_name']} "
                            f"-> plus_minus={pm_value:+d}"
                        )
                    # Remove from lookup to prevent double-counting if BDL returns
                    # the same player in multiple game entries (should not happen)
                    del null_lookup[norm_name]

            elif norm_name in all_names_on_date:
                # Row exists but plus_minus is already non-NULL.
                # Tank01 or another Tier 1 source already filled it -- skip.
                already_had_value += 1
                if verbose:
                    print(f"    [SKIP] {full_name} already has plus_minus value")

            else:
                # BDL player not found in our DB for this date.
                # Common for G-League callups or players outside our player pool.
                no_match += 1
                if verbose:
                    print(f"    [NO MATCH] {full_name} (normalized: '{norm_name}')")

    # Commit once per date -- all updates for this date are atomic
    if not dry_run:
        try:
            conn.commit()
        except Exception as e:
            print(f"  [DB ERROR] Commit failed for {game_date}: {e}")

    return games_fetched, players_with_pm, updated, already_had_value, no_match


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "BDL Tier 2 fill: backfill NULL plus_minus in player_game_logs. "
            "Never overwrites Tank01 (Tier 1) data."
        )
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        help="Specific date to process (default: yesterday)",
    )
    group.add_argument(
        "--backfill",
        action="store_true",
        help="Process all dates with NULL plus_minus (most-recent-first)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be updated without writing to DB",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print per-player detail",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    # Guard: BDL API key is required; exit 0 (not 1) so CI doesn't fail
    if not config.BALLDONTLIE_KEY:
        print("BALLDONTLIE_KEY not set in environment or .env -- cannot fetch BDL box scores.")
        print("Set BALLDONTLIE_KEY and retry. Exiting.")
        sys.exit(0)

    client = _get_client()
    dry_run = args.dry_run
    verbose = args.verbose

    print(DIVIDER)
    print("  BDL PLUS/MINUS TIER 2 FILL")
    print(DIVIDER)

    if dry_run:
        print("  [DRY RUN MODE -- no writes to database]")

    # Open DB connection
    try:
        conn = _get_db_conn(DB_PATH)
    except Exception as e:
        print(f"  [FATAL] Cannot open database at '{DB_PATH}': {e}")
        sys.exit(1)

    # Determine which dates to process
    if args.backfill:
        dates = _fetch_dates_with_null_plus_minus(conn)
        mode_label = f"backfill ({len(dates)} dates with NULL plus_minus)"
        if not dates:
            print("  No dates with NULL plus_minus found. Nothing to do.")
            conn.close()
            return
    elif args.date:
        dates = [args.date]
        mode_label = f"specific date ({args.date})"
    else:
        # Default: yesterday -- most recently completed NBA games
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        dates = [yesterday]
        mode_label = f"yesterday ({yesterday})"

    print(f"  Mode: {mode_label}")
    print()

    # Process each date and accumulate totals
    total_updated = 0
    total_skipped = 0
    total_no_match = 0
    total_players_with_pm = 0

    for game_date in dates:
        print(f"  {game_date}")
        games_fetched, players_with_pm, updated, already_had_value, no_match = (
            _process_date(client, conn, game_date, dry_run, verbose)
        )
        print(f"     BDL games fetched:        {games_fetched}")
        print(f"     Players with plus_minus:  {players_with_pm}")
        if dry_run:
            print(f"     Would update (was NULL):  {updated}")
        else:
            print(f"     Updated (was NULL):       {updated}")
        print(f"     Already had value (skip): {already_had_value}")
        print(f"     No match in DB:           {no_match}")
        if no_match > 0 and updated == 0:
            print(f"     ℹ️  Expected if Module H hasn't ingested {game_date} yet.")
        print()

        total_updated += updated
        total_skipped += already_had_value
        total_no_match += no_match
        total_players_with_pm += players_with_pm

    conn.close()

    # Final summary block
    prefix = "DRY RUN " if dry_run else ""
    print(f"  {prefix}SUMMARY")
    if dry_run:
        print(f"  Total would update:          {total_updated} rows")
    else:
        print(f"  Total updated:               {total_updated} rows")
    print(f"  Total skipped (had value):   {total_skipped}")
    print(f"  Total no match:              {total_no_match}")
    print(DIVIDER)


if __name__ == "__main__":
    main()
