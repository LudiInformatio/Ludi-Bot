#!/usr/bin/env python3
"""
Pinnacle Line Capture Script (T5d — Smart Money Layer)

Fetches Pinnacle prop lines from the Odds API (eu region) and writes them
into prop_line_snapshots.  Only UPDATEs existing rows — never INSERTs.
This isolates Pinnacle data from the NC-Legal closing-line CLV pipeline.

Usage:
    python scripts/capture_pinnacle_lines.py [--date YYYY-MM-DD] [--dry-run]
"""

import argparse
import os
import sqlite3
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests

# ---------------------------------------------------------------------------
# Bootstrap — project root on sys.path so we can open ludi.db by name
# ---------------------------------------------------------------------------
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

DB_PATH = project_root / "ludi.db"

# Odds API market key → canonical stat_category stored in prop_line_snapshots
MARKET_TO_STAT = {
    "player_points":    "PTS",
    "player_rebounds":  "REB",
    "player_assists":   "AST",
    "player_threes":    "3PM",
    "player_blocks":    "BLK",
    "player_steals":    "STL",
    "player_turnovers": "TOV",
}

PLAYER_PROP_MARKETS = ",".join(MARKET_TO_STAT.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_accents(s: str) -> str:
    """Remove diacritics for cross-API name matching."""
    if not s:
        return s
    return "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if unicodedata.category(c) != "Mn"
    )


def _odds_api_get(url: str, params: dict) -> Optional[dict]:
    """Single Odds API GET — returns parsed JSON or None on failure."""
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 401:
            remaining = resp.headers.get("x-requests-remaining", "unknown")
            print(f"  [capture_pinnacle] Odds API 401 — quota exhausted or key invalid "
                  f"(remaining: {remaining})")
            return None
        resp.raise_for_status()
        remaining = resp.headers.get("x-requests-remaining", "unknown")
        used      = resp.headers.get("x-requests-used", "unknown")
        print(f"  [capture_pinnacle] Odds API quota: {remaining} remaining, {used} used")
        return resp.json()
    except Exception as e:
        print(f"  [capture_pinnacle] Odds API request failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Fetch — events list then per-event Pinnacle odds
# ---------------------------------------------------------------------------

def fetch_pinnacle_props(game_date: str, api_key: str) -> List[Dict]:
    """
    Return a list of normalized player-prop dicts from Pinnacle for game_date.

    Each item:
        {
            "player_name": str,         # as returned by Odds API (no accents)
            "stat_category": str,       # e.g. "PTS", "REB"
            "pinnacle_line_over": float,
            "pinnacle_line_under": float,
            "pinnacle_odds_over": int,
            "pinnacle_odds_under": int,
        }
    """
    base = "https://api.the-odds-api.com/v4/sports/basketball_nba"

    # Step 1: Get today's events
    events_data = _odds_api_get(f"{base}/events", {"api_key": api_key})
    if not events_data:
        print("  [capture_pinnacle] No events data returned")
        return []

    # Filter to events on game_date (UTC commence_time → date-only comparison is approximate
    # but good enough for a nightly batch that runs at 6:30 PM EDT)
    events = [ev for ev in events_data if game_date in ev.get("commence_time", "")]
    print(f"  [capture_pinnacle] {len(events)} event(s) on {game_date}")

    if not events:
        return []

    all_props: List[Dict] = []

    # Step 2: Per-event Pinnacle props
    for ev in events:
        event_id = ev.get("id")
        away     = ev.get("away_team", "?")
        home     = ev.get("home_team", "?")

        props_data = _odds_api_get(
            f"{base}/events/{event_id}/odds",
            {
                "api_key":     api_key,
                "regions":     "eu",          # Pinnacle lives in eu region
                "bookmakers":  "pinnacle",
                "markets":     PLAYER_PROP_MARKETS,
                "oddsFormat":  "american",
            },
        )

        if not props_data:
            print(f"    {away} @ {home}: no Pinnacle data")
            continue

        count_before = len(all_props)
        # Parse bookmaker → markets → outcomes
        for bookmaker in props_data.get("bookmakers", []):
            if bookmaker.get("key") != "pinnacle":
                continue
            for market in bookmaker.get("markets", []):
                stat_cat = MARKET_TO_STAT.get(market.get("key", ""))
                if not stat_cat:
                    continue

                # Group outcomes by player; each player has one "Over" and one "Under"
                player_slots: Dict[str, Dict] = {}
                for outcome in market.get("outcomes", []):
                    player_name = outcome.get("description", "").strip()
                    side  = outcome.get("name", "").lower()   # "over" or "under"
                    point = outcome.get("point")
                    price = outcome.get("price")

                    if not player_name or point is None or price is None:
                        continue

                    if player_name not in player_slots:
                        player_slots[player_name] = {
                            "player_name":          player_name,
                            "stat_category":        stat_cat,
                            "pinnacle_line_over":   None,
                            "pinnacle_line_under":  None,
                            "pinnacle_odds_over":   None,
                            "pinnacle_odds_under":  None,
                        }

                    slot = player_slots[player_name]
                    if side == "over":
                        slot["pinnacle_line_over"]  = float(point)
                        slot["pinnacle_odds_over"]  = int(price)
                    elif side == "under":
                        slot["pinnacle_line_under"] = float(point)
                        slot["pinnacle_odds_under"] = int(price)

                all_props.extend(player_slots.values())

        added = len(all_props) - count_before
        print(f"    {away} @ {home}: {added} Pinnacle prop slot(s)")

    return all_props


# ---------------------------------------------------------------------------
# Database — UPDATE existing prop_line_snapshots rows only
# ---------------------------------------------------------------------------

def update_pinnacle_rows(
    conn: sqlite3.Connection,
    props: List[Dict],
    game_date: str,
    dry_run: bool,
) -> None:
    """
    Match each prop against prop_line_snapshots by (game_date, player_name, stat_category)
    and UPDATE the 5 Pinnacle columns.

    prop_line_snapshots stores non-accented player names (confirmed by DB inspection).
    Odds API also returns non-accented names. Plain lowercase comparison is sufficient.
    """
    c = conn.cursor()
    captured_at = datetime.now(timezone.utc).isoformat()

    updated   = 0
    not_found = 0

    for prop in props:
        raw_name  = prop.get("player_name", "")
        stat_cat  = prop.get("stat_category", "")

        # prop_line_snapshots.stat_category is stored uppercase (e.g. "PTS")
        # Pinnacle API returns outcome.description with plain ASCII names
        # → normalize both sides: strip accents + lowercase for matching
        name_norm = _strip_accents(raw_name).lower()

        # Lookup matching snapshot rows — use LIKE for accent-safe fuzzy match
        # We do the exact comparison in Python after fetching candidate rows
        c.execute(
            """
            SELECT rowid, player_name
            FROM prop_line_snapshots
            WHERE game_date    = ?
              AND stat_category = ?
            """,
            (game_date, stat_cat),
        )
        rows = c.fetchall()

        matched_rowid = None
        for rowid, db_name in rows:
            if _strip_accents(db_name).lower() == name_norm:
                matched_rowid = rowid
                break

        if matched_rowid is None:
            not_found += 1
            continue

        if dry_run:
            print(
                f"  [DRY-RUN] Would update: {raw_name} {stat_cat} "
                f"| Pinnacle line O/U: "
                f"{prop.get('pinnacle_line_over')}/{prop.get('pinnacle_line_under')} "
                f"| odds: {prop.get('pinnacle_odds_over')}/{prop.get('pinnacle_odds_under')}"
            )
            updated += 1
            continue

        c.execute(
            """
            UPDATE prop_line_snapshots
            SET pinnacle_line_over   = ?,
                pinnacle_line_under  = ?,
                pinnacle_odds_over   = ?,
                pinnacle_odds_under  = ?,
                pinnacle_captured_at = ?
            WHERE rowid = ?
            """,
            (
                prop.get("pinnacle_line_over"),
                prop.get("pinnacle_line_under"),
                prop.get("pinnacle_odds_over"),
                prop.get("pinnacle_odds_under"),
                captured_at,
                matched_rowid,
            ),
        )
        updated += 1

    if not dry_run:
        conn.commit()

    print(
        f"[capture_pinnacle] Updated {updated} rows | "
        f"Not found: {not_found} | Date: {game_date}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Capture Pinnacle lines into prop_line_snapshots")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Game date YYYY-MM-DD (default: today UTC)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print matches but do not execute UPDATE",
    )
    args = parser.parse_args()

    game_date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print("=" * 60)
    print("PINNACLE LINE CAPTURE (T5d) | Smart Money Layer")
    print("=" * 60)
    if args.dry_run:
        print("WARNING: DRY RUN — no database writes")
    print(f"  Date: {game_date}")

    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        print("ERROR: ODDS_API_KEY not set")
        sys.exit(1)

    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    props = fetch_pinnacle_props(game_date, api_key)
    if not props:
        print(f"[capture_pinnacle] Updated 0 rows | Not found: 0 | Date: {game_date}")
        print("  No Pinnacle props fetched — nothing to update")
        return

    with sqlite3.connect(str(DB_PATH)) as conn:
        update_pinnacle_rows(conn, props, game_date, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
