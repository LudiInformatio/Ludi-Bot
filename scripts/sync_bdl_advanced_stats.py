"""
Sync BDL V2 per-game advanced stats to player_game_advanced, player_game_hustle,
and player_game_tracking.

Usage:
  python scripts/sync_bdl_advanced_stats.py              # yesterday (default)
  python scripts/sync_bdl_advanced_stats.py --date 2026-02-21
  python scripts/sync_bdl_advanced_stats.py --backfill   # all dates missing BDL advanced data
  python scripts/sync_bdl_advanced_stats.py --dry-run    # no DB writes
"""

import argparse
import os
import sqlite3
import sys
from datetime import date, timedelta
from typing import Dict, List, Optional

# Add project root to sys.path so config and utils are importable from scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from utils.bdl_client import _get_client  # private singleton -- do NOT use get_client()
from utils.mappings import normalize_bdl_abbr  # F3: normalize GS→GSW, NO→NOP, etc. at write time


# ---------------------------------------------------------------------------
# BDL field name -> DB column name mappings
# ---------------------------------------------------------------------------

ADVANCED_FIELD_MAP = {
    "offensive_rating":                "off_rating",
    "defensive_rating":                "def_rating",
    "net_rating":                      "net_rating",
    "pace":                            "pace",
    "pie":                             "pie",
    "usage_percentage":                "usg_pct",
    "true_shooting_percentage":        "ts_pct",
    "effective_field_goal_percentage": "efg_pct",
    "assist_percentage":               "ast_pct",
    "offensive_rebound_percentage":    "oreb_pct",
    "defensive_rebound_percentage":    "dreb_pct",
    "estimated_offensive_rating":      "estimated_off_rating",
    "estimated_defensive_rating":      "estimated_def_rating",
    "estimated_net_rating":            "estimated_net_rating",
    "points_paint":                    "points_paint",
    "points_fast_break":               "points_fast_break",
    "points_second_chance":            "points_second_chance",
    "points_off_turnovers":            "points_off_turnovers",
    "pct_pts_paint":                   "pct_pts_paint",
    "pct_pts_fast_break":              "pct_pts_fast_break",
    "pct_pts_free_throw":              "pct_pts_free_throw",
    "pct_pts_midrange_2pt":            "pct_pts_midrange_2pt",
}

HUSTLE_FIELD_MAP = {
    "box_outs":                    "box_outs",
    "deflections":                 "deflections",
    "charges_drawn":               "charges_drawn",
    "contested_shots":             "contested_shots",
    "contested_shots_2pt":         "contested_2pt_shots",
    "contested_shots_3pt":         "contested_3pt_shots",
    "loose_balls_recovered_total": "loose_balls_recovered",
    "screen_assists":              "screen_assists",
}

TRACKING_FIELD_MAP = {
    "speed":    "speed",
    "distance": "distance",
    "touches":  "touches",
    "passes":   "passes",
}


# ---------------------------------------------------------------------------
# Player name normalisation
# ---------------------------------------------------------------------------

def _normalize(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace. Handles Jokic/Jokic."""
    if not name:
        return ""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return " ".join(ascii_only.lower().split())


# ---------------------------------------------------------------------------
# Player lookup table (built once, shared across all dates in a run)
# ---------------------------------------------------------------------------

def build_player_lookup(conn: sqlite3.Connection) -> Dict[str, str]:
    """
    Build {normalized_name: player_id} using two tiers:
      Tier 2 (loaded first):  players.name -> player_id  (fallback)
      Tier 1 (overwrites):    player_canonical_ids        (authoritative)
    """
    lookup: Dict[str, str] = {}
    c = conn.cursor()

    # Tier 2 fallback: players table
    try:
        c.execute("SELECT player_id, name FROM players WHERE name IS NOT NULL")
        for pid, name in c.fetchall():
            norm = _normalize(name)
            if norm:
                lookup[norm] = pid
    except Exception as exc:
        print(f"[WARN] Could not load players table for lookup: {exc}")

    # Tier 1: player_canonical_ids -- overwrites Tier 2 on collision
    try:
        c.execute(
            "SELECT canonical_id, full_name, normalized_name "
            "FROM player_canonical_ids"
        )
        for cid, full_name, norm_name in c.fetchall():
            if norm_name:
                lookup[norm_name] = cid
            if full_name:
                lookup[_normalize(full_name)] = cid
    except Exception as exc:
        print(f"[WARN] Could not load player_canonical_ids for lookup: {exc}")

    return lookup


def resolve_player_id(first: str, last: str, lookup: Dict[str, str]) -> Optional[str]:
    """Resolve BDL first+last to canonical player_id. Returns None on miss."""
    full_norm = _normalize(f"{first} {last}")
    if full_norm in lookup:
        return lookup[full_norm]
    # Try reversed ordering for edge cases
    rev_norm = _normalize(f"{last} {first}")
    if rev_norm in lookup:
        return lookup[rev_norm]
    return None


# ---------------------------------------------------------------------------
# Backfill date discovery
# ---------------------------------------------------------------------------

def get_backfill_dates(conn: sqlite3.Connection) -> List[str]:
    """
    Distinct game_dates in player_game_logs that have no bdl_source=1 row in
    player_game_advanced. Ordered most recent first.
    """
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT pgl.game_date
        FROM player_game_logs pgl
        WHERE pgl.game_date IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM player_game_advanced pga
              WHERE pga.game_date = pgl.game_date
                AND pga.bdl_source = 1
          )
        ORDER BY pgl.game_date DESC
    """)
    return [row[0] for row in c.fetchall()]


# ---------------------------------------------------------------------------
# DB write helper: player_game_advanced (UPSERT)
# ---------------------------------------------------------------------------

def upsert_advanced(
    conn: sqlite3.Connection,
    player_id: str,
    player_name: str,
    team_abbrev: str,
    game_date: str,
    record: Dict,
    dry_run: bool,
) -> bool:
    """UPSERT rating + scoring split data to player_game_advanced."""
    v = {db_col: record.get(bdl_key) for bdl_key, db_col in ADVANCED_FIELD_MAP.items()}

    if dry_run:
        return True

    try:
        conn.execute(
            """
            INSERT INTO player_game_advanced
              (player_id, player_name, team_abbrev, game_date,
               off_rating, def_rating, net_rating, pace, pie, usg_pct,
               ts_pct, efg_pct, ast_pct, oreb_pct, dreb_pct,
               points_paint, points_fast_break, points_second_chance, points_off_turnovers,
               estimated_off_rating, estimated_def_rating, estimated_net_rating,
               pct_pts_paint, pct_pts_fast_break, pct_pts_free_throw, pct_pts_midrange_2pt,
               bdl_source, synced_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,CURRENT_TIMESTAMP)
            ON CONFLICT(player_id, game_date) DO UPDATE SET
              off_rating           = excluded.off_rating,
              def_rating           = excluded.def_rating,
              net_rating           = excluded.net_rating,
              pace                 = excluded.pace,
              pie                  = excluded.pie,
              usg_pct              = excluded.usg_pct,
              ts_pct               = excluded.ts_pct,
              efg_pct              = excluded.efg_pct,
              ast_pct              = excluded.ast_pct,
              oreb_pct             = excluded.oreb_pct,
              dreb_pct             = excluded.dreb_pct,
              points_paint         = excluded.points_paint,
              points_fast_break    = excluded.points_fast_break,
              points_second_chance = excluded.points_second_chance,
              points_off_turnovers = excluded.points_off_turnovers,
              estimated_off_rating = excluded.estimated_off_rating,
              estimated_def_rating = excluded.estimated_def_rating,
              estimated_net_rating = excluded.estimated_net_rating,
              pct_pts_paint        = excluded.pct_pts_paint,
              pct_pts_fast_break   = excluded.pct_pts_fast_break,
              pct_pts_free_throw   = excluded.pct_pts_free_throw,
              pct_pts_midrange_2pt = excluded.pct_pts_midrange_2pt,
              team_abbrev          = excluded.team_abbrev,
              player_name          = excluded.player_name,
              bdl_source           = 1,
              synced_at            = CURRENT_TIMESTAMP
            """,
            (
                player_id, player_name, team_abbrev, game_date,
                v["off_rating"], v["def_rating"], v["net_rating"],
                v["pace"], v["pie"], v["usg_pct"],
                v["ts_pct"], v["efg_pct"], v["ast_pct"],
                v["oreb_pct"], v["dreb_pct"],
                v["points_paint"], v["points_fast_break"],
                v["points_second_chance"], v["points_off_turnovers"],
                v["estimated_off_rating"], v["estimated_def_rating"],
                v["estimated_net_rating"],
                v["pct_pts_paint"], v["pct_pts_fast_break"],
                v["pct_pts_free_throw"], v["pct_pts_midrange_2pt"],
            ),
        )
        return True
    except Exception as exc:
        print(f"  [ERROR] advanced upsert {player_name} {game_date}: {exc}")
        return False


# ---------------------------------------------------------------------------
# DB write helper: player_game_hustle (COALESCE)
# ---------------------------------------------------------------------------

def coalesce_hustle(
    conn: sqlite3.Connection,
    player_id: str,
    player_name: str,
    team_abbrev: str,
    game_date: str,
    record: Dict,
    dry_run: bool,
) -> bool:
    """
    COALESCE write hustle data to player_game_hustle.
    Ghost Protocol rows are never overwritten -- COALESCE fills NULLs only.
    """
    v = {db_col: record.get(bdl_key) for bdl_key, db_col in HUSTLE_FIELD_MAP.items()}

    # Skip if BDL returned no hustle fields for this player/game
    if all(val is None for val in v.values()):
        return False

    if dry_run:
        return True

    try:
        conn.execute(
            """
            INSERT INTO player_game_hustle
              (player_id, player_name, team_abbrev, game_date,
               box_outs, deflections, charges_drawn, contested_shots,
               contested_2pt_shots, contested_3pt_shots,
               loose_balls_recovered, screen_assists,
               bdl_source, synced_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1,CURRENT_TIMESTAMP)
            ON CONFLICT(player_id, game_date) DO UPDATE SET
              box_outs              = COALESCE(box_outs,              excluded.box_outs),
              deflections           = COALESCE(deflections,           excluded.deflections),
              charges_drawn         = COALESCE(charges_drawn,         excluded.charges_drawn),
              contested_shots       = COALESCE(contested_shots,       excluded.contested_shots),
              contested_2pt_shots   = COALESCE(contested_2pt_shots,   excluded.contested_2pt_shots),
              contested_3pt_shots   = COALESCE(contested_3pt_shots,   excluded.contested_3pt_shots),
              loose_balls_recovered = COALESCE(loose_balls_recovered, excluded.loose_balls_recovered),
              screen_assists        = COALESCE(screen_assists,        excluded.screen_assists),
              bdl_source            = COALESCE(bdl_source,            1)
            """,
            (
                player_id, player_name, team_abbrev, game_date,
                v["box_outs"], v["deflections"], v["charges_drawn"],
                v["contested_shots"], v["contested_2pt_shots"],
                v["contested_3pt_shots"], v["loose_balls_recovered"],
                v["screen_assists"],
            ),
        )
        return True
    except Exception as exc:
        print(f"  [ERROR] hustle coalesce {player_name} {game_date}: {exc}")
        return False


# ---------------------------------------------------------------------------
# DB write helper: player_game_tracking (COALESCE)
# ---------------------------------------------------------------------------

def coalesce_tracking(
    conn: sqlite3.Connection,
    player_id: str,
    player_name: str,
    team_abbrev: str,
    game_date: str,
    record: Dict,
    dry_run: bool,
) -> bool:
    """
    COALESCE-fill speed/distance/touches/passes in existing player_game_tracking rows.
    Ghost Protocol owns this table (uses nba_player_id PK). BDL only updates existing
    rows by player_name + game_date — it never inserts new rows to avoid PK conflicts.
    """
    v = {db_col: record.get(bdl_key) for bdl_key, db_col in TRACKING_FIELD_MAP.items()}

    if all(val is None for val in v.values()):
        return False

    if dry_run:
        return True

    try:
        cur = conn.execute(
            """
            UPDATE player_game_tracking
            SET speed      = COALESCE(speed,      ?),
                distance   = COALESCE(distance,   ?),
                touches    = COALESCE(touches,    ?),
                passes     = COALESCE(passes,     ?),
                bdl_source = COALESCE(bdl_source, 1)
            WHERE player_name = ? AND game_date = ?
            """,
            (
                v["speed"], v["distance"], v["touches"], v["passes"],
                player_name, game_date,
            ),
        )
        return cur.rowcount > 0  # True only if a Ghost Protocol row existed
    except Exception as exc:
        print(f"  [ERROR] tracking coalesce {player_name} {game_date}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Core: sync a single date
# ---------------------------------------------------------------------------

def sync_date(
    conn: sqlite3.Connection,
    game_date: str,
    lookup: Dict[str, str],
    dry_run: bool,
    verbose: bool = False,
) -> Dict[str, int]:
    """
    Fetch BDL advanced stats for one game date and write to all three tables.
    Commits the entire date as a single transaction for performance and safety.
    """
    counters: Dict[str, int] = {
        "fetched": 0, "written_advanced": 0, "written_hustle": 0,
        "written_tracking": 0, "no_match": 0, "errors": 0,
    }

    client = _get_client()

    try:
        records = client.get_advanced_stats(dates=[game_date])
    except Exception as exc:
        print(f"[ERROR] BDL API call failed for {game_date}: {exc}")
        counters["errors"] += 1
        return counters

    if not records:
        print(f"[WARN] BDL returned 0 records for {game_date}")
        return counters

    counters["fetched"] = len(records)

    for record in records:
        player_info  = record.get("player") or {}
        team_info    = record.get("team") or {}

        bdl_first    = (player_info.get("first_name") or "").strip()
        bdl_last     = (player_info.get("last_name") or "").strip()
        full_name    = f"{bdl_first} {bdl_last}".strip()
        # F3: normalize BDL abbreviations (GS→GSW, NO→NOP, NY→NYK, PHO→PHX, SA→SAS)
        team_abbrev  = normalize_bdl_abbr((team_info.get("abbreviation") or "").strip())
        # record["date"] is the game date from BDL; fall back to the requested date
        rec_date     = record.get("date") or game_date

        player_id = resolve_player_id(bdl_first, bdl_last, lookup)
        if not player_id:
            counters["no_match"] += 1
            if verbose:
                print(f"  [NO_MATCH] {full_name!r} ({game_date})")
            continue

        # 1. Advanced -- always UPSERT (replaces any stale Ghost Protocol values)
        if upsert_advanced(conn, player_id, full_name, team_abbrev, rec_date, record, dry_run):
            counters["written_advanced"] += 1
        else:
            counters["errors"] += 1

        # 2. Hustle -- COALESCE (never clobber Ghost Protocol data)
        if coalesce_hustle(conn, player_id, full_name, team_abbrev, rec_date, record, dry_run):
            counters["written_hustle"] += 1

        # 3. Tracking -- COALESCE (speed/distance/touches/passes only)
        if coalesce_tracking(conn, player_id, full_name, team_abbrev, rec_date, record, dry_run):
            counters["written_tracking"] += 1

    # Commit entire date as one unit; rollback if commit fails
    if not dry_run:
        try:
            conn.commit()
        except Exception as exc:
            print(f"[ERROR] Commit failed for {game_date}: {exc}")
            conn.rollback()
            counters["errors"] += 1

    return counters


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync BDL V2 advanced stats to 3 tables.")
    parser.add_argument("--date", type=str, default=None, help="Date YYYY-MM-DD. Default: yesterday.")
    parser.add_argument("--backfill", action="store_true", help="Sync all dates missing BDL data.")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="No DB writes.")
    parser.add_argument("--verbose", action="store_true", help="Print unmatched players.")
    args = parser.parse_args()

    # Graceful degradation: missing key must not fail the workflow
    bdl_key = getattr(config, "BALLDONTLIE_KEY", None) or os.getenv("BALLDONTLIE_KEY")
    if not bdl_key:
        print("[sync_bdl_advanced_stats] BALLDONTLIE_KEY not set -- skipping.")
        sys.exit(0)

    db_path = getattr(config, "DB_PATH", "ludi.db")
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 30000")

    print("[sync_bdl_advanced_stats] Building player lookup...")
    lookup = build_player_lookup(conn)
    print(f"  Lookup: {len(lookup)} name entries")

    # Determine which dates to process
    if args.backfill:
        dates = get_backfill_dates(conn)
        if not dates:
            print("[sync_bdl_advanced_stats] No missing dates -- already up to date.")
            conn.close()
            return
        print(f"[sync_bdl_advanced_stats] Backfill: {len(dates)} dates to process")
    else:
        if args.date:
            dates = [args.date]
        else:
            yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
            dates = [yesterday]

    if args.dry_run:
        print("[sync_bdl_advanced_stats] DRY RUN -- no DB writes")

    totals = {"fetched": 0, "written_advanced": 0, "written_hustle": 0, "written_tracking": 0, "no_match": 0, "errors": 0}

    for game_date in dates:
        print(f"[sync_bdl_advanced_stats] {game_date}...", end=" ", flush=True)
        c = sync_date(conn, game_date, lookup, args.dry_run, args.verbose)
        fet = c["fetched"]; adv = c["written_advanced"]; hust = c["written_hustle"]
        trk = c["written_tracking"]; nm = c["no_match"]; err = c["errors"]
        print(f"fetched={fet}  adv={adv}  hustle={hust}  track={trk}  no_match={nm}  err={err}")
        for k in totals:
            totals[k] += c[k]

    conn.close()

    print("")
    print("[sync_bdl_advanced_stats] COMPLETE")
    print("  Dates processed : " + str(len(dates)))
    print("  Total fetched   : " + str(totals["fetched"]))
    print("  Advanced written: " + str(totals["written_advanced"]))
    print("  Hustle written  : " + str(totals["written_hustle"]))
    print("  Tracking written: " + str(totals["written_tracking"]))
    print("  No match        : " + str(totals["no_match"]))
    print("  Errors          : " + str(totals["errors"]))

    if totals["errors"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
