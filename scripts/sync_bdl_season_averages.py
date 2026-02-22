#!/usr/bin/env python3
"""
BDL Season Averages Sync Script

Fetches all Ball Don't Lie season average categories (player stats) and
team standings, writing them to ludi.db. Replaces Ghost Protocol Synergy
scraping for ISO/transition/handoff/cut PPP data.

Categories synced (18 total):
  - general:       base, advanced, usage, scoring, defense, misc
  - tracking:      drives, passing, speeddistance
  - hustle:        (no stat_type -- single endpoint)
  - shotdashboard: overall, pullups, catch_and_shoot
  - playtype:      isolation, transition, handoff, cut, misc

Standings written to team_standings_bdl (30 teams).

Usage:
    python scripts/sync_bdl_season_averages.py                    # all categories
    python scripts/sync_bdl_season_averages.py --category playtype
    python scripts/sync_bdl_season_averages.py --category hustle
    python scripts/sync_bdl_season_averages.py --season 2024
    python scripts/sync_bdl_season_averages.py --dry-run

Author: Ludi Informatio
Date: February 22, 2026
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import unicodedata
from typing import Dict, List, Optional, Tuple

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from utils.bdl_client import BDLClient

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CURRENT_SEASON = 2025  # BDL uses start year (2025 = 2024-25 season)

# (category, stat_type) tuples -- stat_type=None for hustle (single endpoint)
CATEGORIES: List[Tuple[str, Optional[str]]] = [
    ("general",       "base"),
    ("general",       "advanced"),
    ("general",       "usage"),
    ("general",       "scoring"),
    ("general",       "defense"),
    ("general",       "misc"),
    ("tracking",      "drives"),
    ("tracking",      "passing"),
    ("tracking",      "speeddistance"),
    ("hustle",        None),               # No stat_type -- single endpoint
    ("shotdashboard", "overall"),
    ("shotdashboard", "pullups"),
    ("shotdashboard", "catch_and_shoot"),
    ("playtype",      "isolation"),
    ("playtype",      "transition"),
    ("playtype",      "handoff"),
    ("playtype",      "cut"),
    ("playtype",      "misc"),
]

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db_connection(db_path: str = "ludi.db") -> sqlite3.Connection:
    """Open a WAL-mode SQLite connection with a 30-second busy timeout."""
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------

def _extract_denorm_fields(record: Dict, category: str, stat_type: Optional[str]) -> Dict:
    """
    Pull the denormalized columns out of a raw BDL record.

    BDL nests most stats under record["stats"] (a sub-dict).
    The full record is also stored as stats_json so nothing is truly lost --
    these columns allow fast SQL queries without JSON parsing.
    """
    # BDL returns playtype/tracking/hustle stats nested under "stats" key
    stats = record.get("stats") or record  # fall back to top-level if no nesting
    return {
        # playtype records carry PPP / possession share / eFG
        "ppp":            stats.get("ppp"),
        "poss_pct":       stats.get("poss_pct"),
        # playtype + shotdashboard both expose efg_pct
        "efg_pct":        stats.get("efg_pct"),
        # tracking/drives
        "drives":         stats.get("drives"),
        # tracking/speeddistance
        "avg_speed":      stats.get("avg_speed"),
        "dist_miles":     stats.get("dist_miles"),
        # hustle
        "deflections":    stats.get("deflections"),
        "box_outs":       stats.get("box_outs"),
        "screen_assists": stats.get("screen_assists"),
    }


def _build_stats_json(record: Dict) -> str:
    """
    Serialize the full record to JSON after removing nested 'player' and
    'team' keys (those are stored in dedicated columns).
    """
    payload = {k: v for k, v in record.items() if k not in ("player", "team")}
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_category(
    client: BDLClient,
    category: str,
    stat_type: Optional[str],
    season: int,
    verbose: bool = False,
) -> List[Dict]:
    """
    Fetch all pages for a given (category, stat_type) combination.

    Uses _get_all_pages() directly so we handle cursor-based pagination for
    endpoints that return 400-500+ players (100 per page default).

    hustle category has no stat_type -- the 'type' param is omitted entirely.
    """
    url = f"{client.BASE_URL_V1}/season_averages/{category}"
    params: Dict = {
        "season":      season,
        "season_type": "regular",
        "per_page":    100,
    }
    # Only add 'type' when a stat_type is specified (hustle omits it)
    if stat_type is not None:
        params["type"] = stat_type

    label = f"{category} / {stat_type or '(none)'}"
    if verbose:
        print(f"    Fetching {label} from {url} ...")

    try:
        records = client._get_all_pages(url, params)
        if verbose:
            print(f"    -> {len(records)} records returned")
        return records
    except Exception as exc:
        print(f"  [WARNING] Failed to fetch {label}: {exc}")
        return []


def fetch_standings(client: BDLClient, season: int, verbose: bool = False) -> List[Dict]:
    """Fetch team standings for the given season."""
    if verbose:
        print("    Fetching standings ...")
    try:
        records = client.get_standings(season=season)
        if verbose:
            print(f"    -> {len(records)} team records returned")
        return records
    except Exception as exc:
        print(f"  [WARNING] Failed to fetch standings: {exc}")
        return []


# ---------------------------------------------------------------------------
# DB writes -- player season averages
# ---------------------------------------------------------------------------

def upsert_player_averages(
    conn: sqlite3.Connection,
    records: List[Dict],
    category: str,
    stat_type: Optional[str],
    season: int,
    dry_run: bool = False,
) -> int:
    """
    Upsert records into player_season_averages_bdl.

    UNIQUE constraint: (player_id, season, category, stat_type)

    SQLite treats two NULL values as distinct in a UNIQUE index, so multiple
    hustle rows per player could theoretically slip through on INSERT. We
    avoid this by always using ON CONFLICT DO UPDATE -- the first insert
    creates the row; subsequent calls simply update it in place because SQLite
    matches (player_id, season, 'hustle', NULL) exactly via the constraint.
    """
    if not records:
        return 0

    sql = """
        INSERT INTO player_season_averages_bdl
            (player_id, player_name, team_abbrev, season,
             category, stat_type, stats_json,
             ppp, poss_pct, efg_pct,
             drives, avg_speed, dist_miles,
             deflections, box_outs, screen_assists,
             updated_at)
        VALUES
            (?, ?, ?, ?,
             ?, ?, ?,
             ?, ?, ?,
             ?, ?, ?,
             ?, ?, ?,
             CURRENT_TIMESTAMP)
        ON CONFLICT(player_id, season, category, stat_type) DO UPDATE SET
            player_name    = excluded.player_name,
            team_abbrev    = excluded.team_abbrev,
            stats_json     = excluded.stats_json,
            ppp            = excluded.ppp,
            poss_pct       = excluded.poss_pct,
            efg_pct        = excluded.efg_pct,
            drives         = excluded.drives,
            avg_speed      = excluded.avg_speed,
            dist_miles     = excluded.dist_miles,
            deflections    = excluded.deflections,
            box_outs       = excluded.box_outs,
            screen_assists = excluded.screen_assists,
            updated_at     = CURRENT_TIMESTAMP
    """

    upserted = 0
    cursor = conn.cursor()

    for record in records:
        try:
            # --- Extract player identity ---
            player_node = record.get("player") or {}
            player_id   = player_node.get("id")
            if not player_id:
                # Some endpoints embed player_id at top level (no nesting)
                player_id = record.get("player_id")
            if not player_id:
                continue  # Cannot identify player -- skip

            first  = player_node.get("first_name", "")
            last   = player_node.get("last_name", "")
            player_name = (f"{first} {last}").strip() or record.get("player_name", "Unknown")

            # --- Extract team abbreviation ---
            team_node   = record.get("team") or {}
            team_abbrev = team_node.get("abbreviation") or record.get("team_abbreviation", "")

            # --- Build JSON payload (all stat fields, no nested objects) ---
            stats_json = _build_stats_json(record)

            # --- Denormalised quick-access columns ---
            denorm = _extract_denorm_fields(record, category, stat_type)

            row = (
                player_id, player_name, team_abbrev, season,
                category, stat_type, stats_json,
                denorm["ppp"],         denorm["poss_pct"],    denorm["efg_pct"],
                denorm["drives"],      denorm["avg_speed"],   denorm["dist_miles"],
                denorm["deflections"], denorm["box_outs"],    denorm["screen_assists"],
            )

            if not dry_run:
                cursor.execute(sql, row)
            upserted += 1

        except Exception as exc:
            # Never crash on a single bad record
            print(f"  [WARNING] Skipping record in {category}/{stat_type}: {exc}")
            continue

    if not dry_run:
        conn.commit()

    return upserted


# ---------------------------------------------------------------------------
# DB writes -- standings
# ---------------------------------------------------------------------------

def upsert_standings(
    conn: sqlite3.Connection,
    records: List[Dict],
    season: int,
    dry_run: bool = False,
) -> int:
    """
    Upsert team standings into team_standings_bdl.

    BDL standings response structure varies slightly by API version.
    The response may use:
      - Top-level wins/losses OR nested under conference.record
      - "home_record"/"road_record" strings ("W-L") OR separate fields
      - conference/division as plain strings OR dicts with name+rank

    We handle all known shapes with .get() and safe fallbacks.
    """
    if not records:
        return 0

    sql = """
        INSERT OR REPLACE INTO team_standings_bdl
            (team_id, team_name, team_abbrev,
             wins, losses, win_pct,
             conference, conference_rank,
             division, division_rank,
             home_wins, home_losses,
             away_wins, away_losses,
             last_ten_wins, streak,
             season, updated_at)
        VALUES
            (?, ?, ?,
             ?, ?, ?,
             ?, ?,
             ?, ?,
             ?, ?,
             ?, ?,
             ?, ?,
             ?, CURRENT_TIMESTAMP)
    """

    written = 0
    cursor  = conn.cursor()

    for record in records:
        try:
            team_id     = record.get("id")
            team_name   = record.get("full_name") or record.get("name", "Unknown")
            team_abbrev = record.get("abbreviation", "")

            # --- Wins / losses (top-level first, nested fallback) ---
            wins   = _safe_int(record.get("wins"))
            losses = _safe_int(record.get("losses"))

            # --- Conference (string or dict) ---
            conf_raw = record.get("conference", {})
            if isinstance(conf_raw, dict):
                conference      = conf_raw.get("name", "")
                conference_rank = _safe_int(conf_raw.get("rank"))
                # Some BDL responses nest wins/losses here only
                conf_record = conf_raw.get("record", {})
                if wins is None and isinstance(conf_record, dict):
                    wins   = _safe_int(conf_record.get("wins"))
                    losses = _safe_int(conf_record.get("losses"))
            else:
                conference      = str(conf_raw) if conf_raw else ""
                conference_rank = _safe_int(record.get("conference_rank"))

            win_pct = round(wins / max((wins or 0) + (losses or 0), 1), 4) \
                      if wins is not None else None

            # --- Division (string or dict) ---
            div_raw = record.get("division", {})
            if isinstance(div_raw, dict):
                division      = div_raw.get("name", "")
                division_rank = _safe_int(div_raw.get("rank"))
            else:
                division      = str(div_raw) if div_raw else ""
                division_rank = _safe_int(record.get("division_rank"))

            # --- Home / away records ("W-L" string or separate fields) ---
            home_wins, home_losses = _parse_record_string(
                record.get("home_record") or record.get("home", "")
            )
            away_wins, away_losses = _parse_record_string(
                record.get("road_record") or record.get("road") or record.get("away", "")
            )
            # Explicit field fallback
            if home_wins is None:
                home_wins   = _safe_int(record.get("home_wins"))
                home_losses = _safe_int(record.get("home_losses"))
            if away_wins is None:
                away_wins   = _safe_int(record.get("away_wins"))
                away_losses = _safe_int(record.get("away_losses"))

            # --- Last-ten record ---
            last_ten_wins, _ = _parse_record_string(
                record.get("last_ten") or record.get("last_ten_record", "")
            )

            # --- Streak ("W3" / "L2" string, or dict) ---
            streak = record.get("streak", "")
            if isinstance(streak, dict):
                # Shape: {"result": "L", "length": 2}
                streak = f"{streak.get('result','')}{streak.get('length','')}"

            row = (
                team_id, team_name, team_abbrev,
                wins, losses, win_pct,
                conference, conference_rank,
                division, division_rank,
                home_wins, home_losses,
                away_wins, away_losses,
                last_ten_wins, str(streak),
                season,
            )

            if not dry_run:
                cursor.execute(sql, row)
            written += 1

        except Exception as exc:
            abbrev = record.get("abbreviation", "?")
            print(f"  [WARNING] Skipping standings row for {abbrev}: {exc}")
            continue

    if not dry_run:
        conn.commit()

    return written


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

def _safe_int(val) -> Optional[int]:
    """Convert val to int, returning None on failure."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _parse_record_string(record_str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse a 'W-L' string into (wins, losses).
    Returns (None, None) if empty or malformed.

    Examples:
        '10-17' -> (10, 17)
        ''      -> (None, None)
    """
    if not record_str or not isinstance(record_str, str):
        return None, None
    parts = record_str.split("-")
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


# ---------------------------------------------------------------------------
# Main sync orchestration
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """NFD normalization: strips accents, apostrophes, hyphens, lowercases."""
    if not name:
        return ""
    nfd = unicodedata.normalize("NFD", name)
    ascii_n = nfd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"['\.\-]", "", ascii_n).lower().strip()
    return re.sub(r"\s+", " ", clean)


def _resolve_canonical_ids(conn: sqlite3.Connection) -> int:
    """
    Populate canonical_id in player_season_averages_bdl using player_canonical_ids.
    Matches on normalized player_name → normalized_name in canonical_ids table.
    Returns number of rows updated.
    """
    # Build lookup: normalized_name → canonical_id
    lookup = {}
    rows = conn.execute(
        "SELECT canonical_id, normalized_name FROM player_canonical_ids WHERE normalized_name IS NOT NULL"
    ).fetchall()
    for cid, norm in rows:
        if norm:
            lookup[norm] = cid

    # Get all unresolved player names
    unresolved = conn.execute(
        "SELECT DISTINCT player_name FROM player_season_averages_bdl WHERE canonical_id IS NULL"
    ).fetchall()

    updated = 0
    for (player_name,) in unresolved:
        norm = _normalize_name(player_name)
        canonical_id = lookup.get(norm)
        if canonical_id:
            conn.execute(
                "UPDATE player_season_averages_bdl SET canonical_id = ? WHERE player_name = ? AND canonical_id IS NULL",
                (canonical_id, player_name),
            )
            updated += 1

    conn.commit()
    return updated


def run_sync(
    season: int,
    category_filter: Optional[str],
    dry_run: bool,
    verbose: bool,
) -> None:
    """Iterate all categories, fetch from BDL, upsert to DB, print summary."""

    # Guard: require API key
    api_key = os.getenv("BALLDONTLIE_KEY")
    if not api_key:
        print("BALLDONTLIE_KEY not set in environment -- exiting.")
        sys.exit(0)

    season_label = f"{season}-{str(season + 1)[-2:]}"
    print()
    print("=" * 60)
    print(f"  BDL SEASON AVERAGES SYNC ({season_label} Regular Season)")
    if dry_run:
        print("  *** DRY RUN -- no DB writes ***")
    print("=" * 60)
    print()

    client = BDLClient(api_key=api_key)

    # Apply --category filter
    categories_to_run = [
        (cat, st) for cat, st in CATEGORIES
        if category_filter is None or cat == category_filter
    ]

    if not categories_to_run:
        print(f"  No categories matched filter: '{category_filter}'")
        valid = sorted(set(c for c, _ in CATEGORIES))
        print(f"  Valid categories: {valid}")
        sys.exit(1)

    total_categories  = len(categories_to_run)
    synced_categories = 0
    total_rows        = 0
    error_count       = 0

    # Open DB connection (None in dry-run mode)
    conn = get_db_connection() if not dry_run else None

    for idx, (category, stat_type) in enumerate(categories_to_run, start=1):
        st_label = stat_type if stat_type else "(none)"
        prefix   = f"  [{idx:2d}/{total_categories}] {category:<14} / {st_label:<18}"

        records = fetch_category(client, category, stat_type, season, verbose=verbose)

        if not records:
            print(f"{prefix}-> 0 records (skipped or empty)")
            error_count += 1
            continue

        if not dry_run:
            upserted = upsert_player_averages(
                conn, records, category, stat_type, season, dry_run=False
            )
        else:
            # Dry-run: count records that have a resolvable player ID
            upserted = sum(
                1 for r in records
                if (r.get("player") or {}).get("id") or r.get("player_id")
            )

        print(f"{prefix}-> {len(records):4d} fetched, {upserted:4d} upserted")
        total_rows        += upserted
        synced_categories += 1

    print()

    # Standings
    standings_written  = 0
    standings_records  = fetch_standings(client, season, verbose=verbose)
    if standings_records:
        if not dry_run:
            standings_written = upsert_standings(conn, standings_records, season)
        else:
            standings_written = len(standings_records)
        print(f"  Standings: {standings_written} teams written to team_standings_bdl")
    else:
        print("  Standings: no data returned (skipped)")

    # Resolve canonical_ids after all upserts
    canonical_updated = 0
    if conn and not dry_run:
        canonical_updated = _resolve_canonical_ids(conn)
        null_after = conn.execute(
            "SELECT COUNT(*) FROM player_season_averages_bdl WHERE canonical_id IS NULL"
        ).fetchone()[0]
        print(f"  canonical_id resolution: {canonical_updated} new matches, {null_after} still unresolved")

    if conn:
        conn.close()

    # Summary
    print()
    print("  SUMMARY")
    print(f"  Categories synced  : {synced_categories}/{total_categories}")
    print(f"  Total rows upserted: {total_rows:,}")
    print(f"  Standings rows     : {standings_written}")
    print(f"  canonical_id fills : {canonical_updated}")
    print(f"  Errors             : {error_count}")
    if dry_run:
        print("  (DRY RUN -- no data written to database)")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync BDL season averages (all categories) and standings to ludi.db"
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help=(
            "Sync only this category "
            "(general|tracking|hustle|shotdashboard|playtype)"
        ),
    )
    parser.add_argument(
        "--season",
        type=int,
        default=CURRENT_SEASON,
        help=f"BDL season start year (default: {CURRENT_SEASON} = 2024-25)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch data but do not write to database",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-request debug output",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_sync(
        season=args.season,
        category_filter=args.category,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )
