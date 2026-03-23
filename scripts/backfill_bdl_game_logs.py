#!/usr/bin/env python3
"""
Backfill player_game_logs from BDL /v1/stats endpoint.

Fetches per-game box score stats for historical seasons and UPSERTs into
player_game_logs. Uses the BDL v1 /stats endpoint with date-based queries
and full pagination via _get_all_pages().

Usage:
  python scripts/backfill_bdl_game_logs.py --season 2024 --backfill          # all missing 2024-25 dates
  python scripts/backfill_bdl_game_logs.py --season 2024 --date 2024-12-25   # single date
  python scripts/backfill_bdl_game_logs.py --season 2024 --backfill --dry-run
  python scripts/backfill_bdl_game_logs.py --season 2024 --backfill --max-dates 10
"""

import argparse
import logging
import os
import sqlite3
import sys
from datetime import datetime
from typing import Dict, List, Optional, Set

# Add project root to sys.path so config and utils are importable from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from database import LudiHistorian
from utils.bdl_client import BDLClient
from utils.mappings import normalize_bdl_abbr

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


# ---------------------------------------------------------------------------
# Season helpers
# ---------------------------------------------------------------------------

def _season_date_range(season: int) -> tuple:
    """Return (start_date, end_date) for a BDL season year.
    season=2024 means the 2024-25 NBA season (Oct 2024 - Sep 2025).
    """
    return (f"{season}-10-01", f"{season + 1}-09-30")


def _derive_season_id(game_date: str) -> str:
    """Derive Ludi season_id string from a game date."""
    if game_date >= "2025-10-01":
        return "2025-26"
    elif game_date >= "2024-10-01":
        return "2024-25"
    elif game_date >= "2023-10-01":
        return "2023-24"
    elif game_date >= "2022-10-01":
        return "2022-23"
    else:
        return "2021-22"


# ---------------------------------------------------------------------------
# Minutes parsing — BDL v1 /stats returns plain integer string (not MM:SS)
# ---------------------------------------------------------------------------

def _parse_minutes(raw) -> int:
    """Parse BDL minutes field to integer. Handles plain int string and MM:SS fallback."""
    if not raw:
        return 0
    if isinstance(raw, (int, float)):
        return int(raw)
    raw_str = str(raw).strip()
    if ":" in raw_str:
        # Fallback for MM:SS format (unlikely but defensive)
        return int(raw_str.split(":")[0])
    try:
        return int(float(raw_str))
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Player lookup (NO is_active filter — historical players need resolution)
# ---------------------------------------------------------------------------

def build_player_lookup(conn: sqlite3.Connection) -> Dict[str, str]:
    """Build {lowercased_name: canonical_id} using two tiers.
    Tier 2 (fallback): players table
    Tier 1 (authoritative, overwrites): player_canonical_ids (full table)
    """
    lookup: Dict[str, str] = {}
    c = conn.cursor()

    # Tier 2 fallback: players table
    try:
        c.execute("SELECT player_id, name FROM players WHERE name IS NOT NULL")
        for row in c.fetchall():
            pid, name = row
            if name:
                lookup[name.lower()] = str(pid)
    except Exception as exc:
        logger.warning(f"Could not load players table for lookup: {exc}")

    # Tier 1: player_canonical_ids — full table, no is_active filter
    try:
        c.execute(
            "SELECT canonical_id, full_name, normalized_name "
            "FROM player_canonical_ids"
        )
        for row in c.fetchall():
            canonical_id, full_name, normalized_name = row
            if full_name:
                lookup[full_name.lower()] = str(canonical_id)
            if normalized_name:
                lookup[normalized_name.lower()] = str(canonical_id)
    except Exception as exc:
        logger.warning(f"Could not load player_canonical_ids for lookup: {exc}")

    return lookup


# ---------------------------------------------------------------------------
# Date discovery
# ---------------------------------------------------------------------------

def get_existing_dates(conn: sqlite3.Connection, season_start: str, season_end: str) -> Set[str]:
    """Get all dates that already have player_game_logs rows in the season range."""
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT game_date FROM player_game_logs
        WHERE game_date >= ? AND game_date < ?
    """, (season_start, season_end))
    return {row[0] for row in c.fetchall()}


def get_bdl_game_dates(client: BDLClient, season: int) -> List[str]:
    """Fetch all game dates for a season from BDL /v1/games endpoint."""
    print(f"[BDL-BACKFILL] Fetching game dates from BDL for season {season}...")
    all_games = client._get_all_pages(
        f"{client.BASE_URL_V1}/games",
        {"seasons[]": season, "per_page": 100}
    )
    # Extract unique dates, sorted
    dates = set()
    for game in all_games:
        game_date = (game.get("date") or "")[:10]  # YYYY-MM-DD
        if game_date:
            dates.add(game_date)
    return sorted(dates)


# ---------------------------------------------------------------------------
# UPSERT SQL
# ---------------------------------------------------------------------------

UPSERT_SQL = """
INSERT INTO player_game_logs (
    game_id, game_date, season_id, player_id, player_name,
    team_abbreviation, team_name, pts, ast, reb, minutes,
    stl, blk, tov, fgm, fga, fg3m, fg3a, ftm, fta,
    oreb, dreb, pf, plus_minus, fg_pct, fg3_pct, ft_pct, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(player_id, game_date) DO UPDATE SET
    team_abbreviation = excluded.team_abbreviation,
    game_id = CASE WHEN player_game_logs.game_id LIKE 'bdl_%' THEN excluded.game_id ELSE player_game_logs.game_id END,
    season_id = excluded.season_id,
    pts = excluded.pts,
    ast = excluded.ast,
    reb = excluded.reb,
    minutes = excluded.minutes,
    stl = excluded.stl,
    blk = excluded.blk,
    tov = excluded.tov,
    fgm = excluded.fgm,
    fga = excluded.fga,
    fg3m = excluded.fg3m,
    fg3a = excluded.fg3a,
    ftm = excluded.ftm,
    fta = excluded.fta,
    oreb = excluded.oreb,
    dreb = excluded.dreb,
    pf = excluded.pf,
    plus_minus = COALESCE(player_game_logs.plus_minus, excluded.plus_minus),
    fg_pct = excluded.fg_pct,
    fg3_pct = excluded.fg3_pct,
    ft_pct = excluded.ft_pct
"""


# ---------------------------------------------------------------------------
# Core: process a single date
# ---------------------------------------------------------------------------

def process_date(
    conn: sqlite3.Connection,
    client: BDLClient,
    game_date: str,
    player_lookup: Dict[str, str],
    ludi: LudiHistorian,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Fetch BDL stats for one date and UPSERT into player_game_logs."""
    counters = {"fetched": 0, "inserted": 0, "no_match": 0, "errors": 0}

    try:
        stats = client._get_all_pages(
            f"{client.BASE_URL_V1}/stats",
            {"dates[]": game_date, "per_page": 100}
        )
    except Exception as exc:
        logger.error(f"BDL API call failed for {game_date}: {exc}")
        counters["errors"] += 1
        return counters

    if not stats:
        return counters

    counters["fetched"] = len(stats)
    season_id = _derive_season_id(game_date)
    now_ts = datetime.utcnow().isoformat()
    rows_to_insert = []

    for stat in stats:
        player_info = stat.get("player") or {}
        team_info = stat.get("team") or {}
        game_info = stat.get("game") or {}

        first_name = (player_info.get("first_name") or "").strip()
        last_name = (player_info.get("last_name") or "").strip()
        player_name = f"{first_name} {last_name}".strip()
        if not player_name:
            continue

        # Resolve canonical player ID: lookup dict first, then firewall
        canonical_id = player_lookup.get(player_name.lower())
        if not canonical_id:
            bdl_player_id = str(player_info.get("id", ""))
            canonical_id = ludi.resolve_player_id_for_insert(bdl_player_id, player_name)
        if not canonical_id:
            counters["no_match"] += 1
            continue

        # Normalize team abbreviation (GS->GSW, NO->NOP, etc.)
        team_abbr = normalize_bdl_abbr((team_info.get("abbreviation") or "").strip())
        team_name = (team_info.get("full_name") or "").strip()

        # Build game_id from BDL game ID
        bdl_game_id = game_info.get("id", "")
        game_id = f"bdl_{bdl_game_id}" if bdl_game_id else f"bdl_{game_date}"

        # Parse stats
        minutes = _parse_minutes(stat.get("min"))
        pts = stat.get("pts") or 0
        ast = stat.get("ast") or 0
        reb = stat.get("reb") or 0
        stl = stat.get("stl") or 0
        blk = stat.get("blk") or 0
        tov = stat.get("turnover") or 0  # BDL uses "turnover" not "tov"
        fgm = stat.get("fgm") or 0
        fga = stat.get("fga") or 0
        fg3m = stat.get("fg3m") or 0
        fg3a = stat.get("fg3a") or 0
        ftm = stat.get("ftm") or 0
        fta = stat.get("fta") or 0
        oreb = stat.get("oreb") or 0
        dreb = stat.get("dreb") or 0
        pf = stat.get("pf") or 0
        plus_minus = stat.get("plus_minus")  # Can be None
        fg_pct = stat.get("fg_pct") or 0.0
        fg3_pct = stat.get("fg3_pct") or 0.0
        ft_pct = stat.get("ft_pct") or 0.0

        rows_to_insert.append((
            game_id, game_date, season_id, canonical_id, player_name,
            team_abbr, team_name, pts, ast, reb, minutes,
            stl, blk, tov, fgm, fga, fg3m, fg3a, ftm, fta,
            oreb, dreb, pf, plus_minus, fg_pct, fg3_pct, ft_pct, now_ts
        ))

    # UPSERT all rows for this date
    if not dry_run and rows_to_insert:
        try:
            conn.executemany(UPSERT_SQL, rows_to_insert)
            conn.commit()
            counters["inserted"] = len(rows_to_insert)
        except Exception as exc:
            logger.error(f"DB write failed for {game_date}: {exc}")
            conn.rollback()
            counters["errors"] += 1
    elif dry_run:
        counters["inserted"] = len(rows_to_insert)

    return counters


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill player_game_logs from BDL /v1/stats endpoint."
    )
    parser.add_argument("--season", type=int, required=True,
                        help="BDL season start year (e.g. 2024 for 2024-25)")
    parser.add_argument("--date", type=str, default=None,
                        help="Process a single date (YYYY-MM-DD)")
    parser.add_argument("--backfill", action="store_true",
                        help="Find and backfill all missing dates for the season")
    parser.add_argument("--max-dates", dest="max_dates", type=int, default=None,
                        help="Limit number of dates to process")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="No DB writes — preview only")
    parser.add_argument("--verbose", action="store_true",
                        help="Extra logging")
    args = parser.parse_args()

    if not args.date and not args.backfill:
        parser.error("Must specify --date or --backfill")

    # Check BDL key
    bdl_key = os.getenv("BALLDONTLIE_KEY")
    if not bdl_key:
        print("[BDL-BACKFILL] BALLDONTLIE_KEY not set -- skipping.")
        sys.exit(0)

    # Season range
    season_start, season_end = _season_date_range(args.season)
    season_label = f"{args.season}-{str(args.season + 1)[-2:]}"

    # DB connection
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ludi.db"
    )
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row

    # BDL client + firewall
    client = BDLClient(api_key=bdl_key)
    ludi = LudiHistorian(db_path=db_path)

    # Build player lookup
    print("[BDL-BACKFILL] Building player lookup...")
    player_lookup = build_player_lookup(conn)
    print(f"[BDL-BACKFILL] Lookup: {len(player_lookup)} name entries")

    # Determine dates to process
    if args.date:
        dates = [args.date]
    else:
        # --backfill: get all BDL game dates, filter out those already in DB
        bdl_dates = get_bdl_game_dates(client, args.season)
        print(f"[BDL-BACKFILL] Found {len(bdl_dates)} game dates for season {args.season}")

        existing = get_existing_dates(conn, season_start, season_end)
        dates = [d for d in bdl_dates if d not in existing]
        print(f"[BDL-BACKFILL] {len(dates)} dates missing from player_game_logs")

        if not dates:
            print("[BDL-BACKFILL] All dates already present -- nothing to backfill.")
            conn.close()
            return

    # Apply max-dates limit
    if args.max_dates and len(dates) > args.max_dates:
        dates = dates[:args.max_dates]
        print(f"[BDL-BACKFILL] Limited to {args.max_dates} dates")

    mode = "dry_run" if args.dry_run else "backfill" if args.backfill else "single"
    print(f"[BDL-BACKFILL] Season: {season_label} | Mode: {mode} | dry_run={args.dry_run}")

    if args.dry_run:
        print("[BDL-BACKFILL] DRY RUN -- no DB writes")

    # Process each date
    totals = {"fetched": 0, "inserted": 0, "no_match": 0, "errors": 0}

    for i, game_date in enumerate(dates, 1):
        print(f"[BDL-BACKFILL] Processing date {i}/{len(dates)}: {game_date} ...", end=" ", flush=True)
        c = process_date(conn, client, game_date, player_lookup, ludi, args.dry_run)
        print(f"{c['fetched']} records, {c['inserted']} inserted, {c['no_match']} no_match")
        for k in totals:
            totals[k] += c[k]

    conn.close()

    print("")
    print(f"[BDL-BACKFILL] COMPLETE: {len(dates)} dates processed, "
          f"{totals['inserted']} rows inserted, {totals['no_match']} no_match")
    if totals["errors"] > 0:
        print(f"[BDL-BACKFILL] ERRORS: {totals['errors']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
