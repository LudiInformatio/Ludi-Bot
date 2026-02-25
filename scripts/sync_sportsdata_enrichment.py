"""
SportsDataIO Box Score Enrichment Script
Enriches player_game_logs with: started, fantasy_pts_dk, fantasy_pts_fd,
home_or_away, double_doubles, triple_doubles.
Also fills plus_minus as Tier 1 (SportsDataIO provides PlusMinus directly).

Default: last 3 dates with started IS NULL (3 API calls/day, 100/day limit).
Backfill: --backfill --limit 90

Usage:
    python scripts/sync_sportsdata_enrichment.py                # 3-day rolling
    python scripts/sync_sportsdata_enrichment.py --date 2026-02-21
    python scripts/sync_sportsdata_enrichment.py --backfill --limit 90
    python scripts/sync_sportsdata_enrichment.py --dry-run

Cost: 1 API call per date (Discovery Lab Fantasy free tier: 100/day).
Note: Only enriches 2024-25 season box scores (current season requires paid tier).
"""

import os
import sys
import re
import unicodedata
import argparse
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config

# All-Star break 2026 — no games on these dates
ALL_STAR_DATES = {'2026-02-13', '2026-02-14', '2026-02-15', '2026-02-16', '2026-02-17'}


# ---------------------------------------------------------------------------
# Name normalization (same as build_sportsdata_crosswalk.py)
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Normalize player name for fuzzy matching. Handles accents, apostrophes, hyphens."""
    if not name:
        return ""
    nfd = unicodedata.normalize("NFD", name)
    ascii_name = nfd.encode("ascii", "ignore").decode("ascii")
    clean = re.sub(r"['\-\.]", "", ascii_name).lower().strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _iso_to_sd_format(iso_date: str) -> str:
    """Convert '2026-02-22' → '2026-FEB-22' (SportsDataIO format)."""
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    return dt.strftime("%Y-%b-%d").upper()


def _get_dates_to_enrich(conn: sqlite3.Connection, limit: int = 3) -> list:
    """
    Return the last N dates that have game logs but no enrichment (started IS NULL).
    Skips All-Star break dates automatically.
    """
    cursor = conn.execute("""
        SELECT DISTINCT game_date
        FROM player_game_logs
        WHERE started IS NULL
          AND game_date NOT BETWEEN '2026-02-13' AND '2026-02-17'
        ORDER BY game_date DESC
        LIMIT ?
    """, (limit,))
    return [row[0] for row in cursor.fetchall()]


def _get_backfill_dates(conn: sqlite3.Connection, limit: int = 90) -> list:
    """
    Return all dates (newest-first) that have game logs but no enrichment.
    Skips All-Star break dates.
    """
    cursor = conn.execute("""
        SELECT DISTINCT game_date
        FROM player_game_logs
        WHERE started IS NULL
          AND game_date NOT BETWEEN '2026-02-13' AND '2026-02-17'
        ORDER BY game_date DESC
        LIMIT ?
    """, (limit,))
    return [row[0] for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Core enrichment logic
# ---------------------------------------------------------------------------

def _enrich_date(conn: sqlite3.Connection, date_iso: str, dry_run: bool) -> dict:
    """
    Fetch SportsDataIO stats for one date and update player_game_logs.
    Returns stats: fetched, matched, updated, no_match
    """
    from utils.sportsdata_client import get_client

    client = get_client()
    sd_date = _iso_to_sd_format(date_iso)

    sd_players = client.get_player_game_stats(sd_date)

    if not sd_players:
        print(f"     ⚠️  No data returned from SportsDataIO for {sd_date}")
        return {"fetched": 0, "matched": 0, "updated": 0, "no_match": 0}

    print(f"     SportsDataIO: {len(sd_players)} player-games fetched")

    # Build lookup: normalized_name → original player_name (for WHERE clause)
    cursor = conn.execute("""
        SELECT player_name
        FROM player_game_logs
        WHERE game_date = ?
    """, (date_iso,))
    db_rows = {_normalize_name(row[0]): row[0] for row in cursor.fetchall()}

    matched = 0
    no_match = 0
    updated = 0

    updates = []
    for sd_player in sd_players:
        # Get player name (SportsDataIO returns "Name" as "FirstName LastName")
        full_name = sd_player.get("Name", "") or ""
        if not full_name:
            first = sd_player.get("FirstName", "") or ""
            last = sd_player.get("LastName", "") or ""
            full_name = f"{first} {last}".strip()

        norm = _normalize_name(full_name)
        if not norm:
            continue

        # Skip DNP players (0 minutes)
        if not (sd_player.get("Minutes") or 0):
            continue

        original_name = db_rows.get(norm)
        if not original_name:
            no_match += 1
            continue

        matched += 1

        started = sd_player.get("Started")
        dk_pts = sd_player.get("FantasyPointsDraftKings")
        fd_pts = sd_player.get("FantasyPointsFanDuel")
        home_away = sd_player.get("HomeOrAway")
        dd = sd_player.get("DoubleDoubles")
        td = sd_player.get("TripleDoubles")
        pm = sd_player.get("PlusMinus")

        updates.append((
            started, dk_pts, fd_pts, home_away, dd, td,
            pm,  # COALESCE — only fills if plus_minus is NULL
            date_iso, original_name  # WHERE game_date=? AND player_name=?
        ))

    if not dry_run and updates:
        conn.executemany("""
            UPDATE player_game_logs
            SET started        = ?,
                fantasy_pts_dk = ?,
                fantasy_pts_fd = ?,
                home_or_away   = ?,
                double_doubles = ?,
                triple_doubles = ?,
                plus_minus     = COALESCE(plus_minus, ?)
            WHERE game_date = ?
              AND player_name = ?
        """, updates)
        conn.commit()
        updated = len(updates)

    elif dry_run:
        updated = len(updates)  # Would-be updates

    return {
        "fetched": len(sd_players),
        "matched": matched,
        "updated": updated,
        "no_match": no_match,
    }


# ---------------------------------------------------------------------------
# Position sync from SportsDataIO
# ---------------------------------------------------------------------------

def sync_positions_from_sportsdata(conn: sqlite3.Connection, dry_run: bool = False) -> dict:
    """
    Pull fine-grained player positions (PG/SG/SF/PF/C) from SportsDataIO /Players
    and write them into player_canonical_ids.position.

    Only upgrades positions — never overwrites a fine-grained position with a coarser one.
    Upgrade hierarchy: UNK/'' < G/F/C < PG/SG/SF/PF

    Returns: dict with fetched/updated/skipped/no_match counts
    Cost: 1 API call (uses 1h cache — no extra cost if already called today)
    """
    from utils.sportsdata_client import get_client

    client = get_client()
    players = client.get_players()

    if not players:
        print("  ⚠️  SportsDataIO /Players returned empty — skipping position sync")
        return {'fetched': 0, 'updated': 0, 'skipped': 0, 'no_match': 0}

    # Load canonical lookup: normalized_name → current_position
    canonical_pos = {
        row[0]: (row[1] or '')
        for row in conn.execute(
            "SELECT normalized_name, position FROM player_canonical_ids WHERE is_active = 1"
        ).fetchall()
    }

    # Position upgrade ranks — higher = more specific. Never overwrite with lower/equal rank.
    _RANK = {
        '': 0, 'UNK': 0,
        'G': 1, 'F': 1, 'C': 2, 'G-F': 1, 'F-G': 1, 'C-F': 2,
        'PG': 3, 'SG': 3, 'SF': 3, 'PF': 3,
    }

    updated = 0
    skipped = 0
    no_match = 0

    for player in players:
        first = player.get('FirstName', '') or ''
        last = player.get('LastName', '') or ''
        full_name = f"{first} {last}".strip()
        sd_pos = (player.get('Position') or '').strip()

        if not full_name or not sd_pos:
            continue

        norm = _normalize_name(full_name)
        if norm not in canonical_pos:
            no_match += 1
            continue

        current = canonical_pos[norm]
        if _RANK.get(sd_pos, 0) <= _RANK.get(current, 0):
            skipped += 1
            continue  # already fine-grained or equal — don't touch

        if not dry_run:
            conn.execute(
                "UPDATE player_canonical_ids SET position = ? WHERE normalized_name = ?",
                (sd_pos, norm)
            )
        updated += 1

    if not dry_run:
        conn.commit()

    return {'fetched': len(players), 'updated': updated, 'skipped': skipped, 'no_match': no_match}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Enrich player_game_logs with SportsDataIO box score data"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Specific date to enrich (ISO format: YYYY-MM-DD)"
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Backfill all dates with unenriched game logs (newest-first)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=90,
        help="Max dates to process in --backfill mode (default: 90)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be updated without writing to DB"
    )
    parser.add_argument(
        "--sync-positions",
        action="store_true",
        help="Sync fine-grained player positions (PG/SG/SF/PF/C) from SportsDataIO into "
             "player_canonical_ids.position. Uses cached /Players call — no extra API cost."
    )
    args = parser.parse_args()

    # Feature flag check
    if not config.USE_SPORTSDATA:
        print("❌  SPORTSDATA_API_KEY not set — skipping enrichment")
        sys.exit(0)  # Exit 0 so workflow step doesn't fail the pipeline

    print("\n" + "=" * 60)
    print("  SPORTSDATA.IO BOX SCORE ENRICHMENT")
    print("=" * 60)
    if args.dry_run:
        print("  ⚠️  DRY RUN MODE — no DB writes will be made")

    conn = sqlite3.connect(config.DB_PATH)

    # Position sync mode — runs independently of box score enrichment
    if args.sync_positions:
        print("\n" + "=" * 60)
        print("  POSITION SYNC — SportsDataIO → player_canonical_ids")
        print("=" * 60)
        if args.dry_run:
            print("  ⚠️  DRY RUN — no writes")
        stats = sync_positions_from_sportsdata(conn, dry_run=args.dry_run)
        print(f"  Fetched: {stats['fetched']} players")
        verb = "Would update" if args.dry_run else "Updated"
        print(f"  {verb}: {stats['updated']} positions (G→PG/SG, F→SF/PF, UNK→any)")
        print(f"  Skipped: {stats['skipped']} (already fine-grained)")
        print(f"  No match: {stats['no_match']} (not in canonical_ids)")
        conn.close()
        return

    # Determine which dates to process
    if args.date:
        # Single specific date
        dates = [args.date]
        mode_label = f"single date ({args.date})"
    elif args.backfill:
        dates = _get_backfill_dates(conn, limit=args.limit)
        mode_label = f"backfill (limit {args.limit})"
    else:
        # Default: last 3 unenriched dates
        dates = _get_dates_to_enrich(conn, limit=3)
        mode_label = "3-day rolling (default)"

    print(f"  Run mode: {mode_label}")
    print(f"  Dates to process: {len(dates)}\n")

    if not dates:
        print("  ✅  No dates need enrichment — all game logs have started data")
        conn.close()
        return

    total_updated = 0
    total_no_match = 0
    dates_ok = 0
    api_calls = 0

    for date_iso in dates:
        if date_iso in ALL_STAR_DATES:
            print(f"\n  📅  {date_iso} — SKIPPED (All-Star break)")
            continue

        print(f"\n  📅  {date_iso}")
        try:
            stats = _enrich_date(conn, date_iso, dry_run=args.dry_run)
            api_calls += 1
            total_updated += stats["updated"]
            total_no_match += stats["no_match"]
            dates_ok += 1

            verb = "Would update" if args.dry_run else "Updated"
            print(f"     Matched: {stats['matched']} | {verb}: {stats['updated']} | "
                  f"No match: {stats['no_match']}")

        except Exception as e:
            print(f"     ❌  Error processing {date_iso}: {e}")
            continue

    conn.close()

    print("\n" + "=" * 60)
    print("  SUMMARY")
    print(f"  Dates processed: {dates_ok} / {len(dates)}")
    print(f"  Total rows {'would update' if args.dry_run else 'updated'}: {total_updated}")
    print(f"  Players not matched by name: {total_no_match}")
    print(f"  API calls used: {api_calls} (budget: {config.SPORTSDATA_TIER} tier, 100/day)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
