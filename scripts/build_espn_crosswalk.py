#!/usr/bin/env python3
"""
Build ESPN Athlete ID Crosswalk
================================
Scans all 30 NBA team rosters via ESPN public API and populates
player_canonical_ids.espn_id for all matched players.

ESPN athlete IDs are permanent person-level identifiers — they don't change
when a player switches teams or across seasons.

API: sports.core.api.espn.com/v2/sports/basketball/leagues/nba/teams/{id}/athletes
Auth: None required (public API)
Rate: 0.4s between team calls, 0.1s between athlete ref fetches
Cost: $0 — ESPN public API, no quota

Run manually:
    python scripts/build_espn_crosswalk.py --dry-run   # verify matches
    python scripts/build_espn_crosswalk.py             # live write

Wired into: weekly_validation.yml (runs once/week — rosters change slowly)
"""

import os
import sys
import time
import sqlite3
import unicodedata
import re
import argparse
import requests
from datetime import datetime

# Add project root for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json',
}
TEAM_RATE_LIMIT = 0.4   # seconds between team requests
ATHLETE_RATE_LIMIT = 0.1  # seconds between athlete $ref fetches
TIMEOUT = 15


def normalize_for_lookup(name: str) -> str:
    """
    Normalize a display name to match player_canonical_ids.normalized_name format.
    Matches the logic in _normalize_for_canonical() in sync_injuries.py.
    """
    # NFD decomposition strips accents (Nurkić → Nurkic, Dončić → Doncic)
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower().strip()
    # Strip suffixes: Jr., Sr., II, III, IV, V
    name = re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv|v)$', '', name, flags=re.IGNORECASE)
    return name.strip()


def _get(url: str) -> dict:
    """Fetch JSON from a URL with retry on transient errors."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"      ⚠️  GET failed: {url[:80]} — {e}")
        return {}


def _load_espn_team_ids(conn) -> dict:
    """Load ESPN team IDs from canonical_teams table."""
    try:
        rows = conn.execute(
            "SELECT standard_abbr, espn_id FROM canonical_teams WHERE espn_id IS NOT NULL"
        ).fetchall()
        if rows:
            return {row[0]: row[1] for row in rows}
    except Exception:
        pass
    # Emergency fallback
    return {
        'ATL': 1,  'BOS': 2,  'NOP': 3,  'CHI': 4,  'CLE': 5,
        'DAL': 6,  'DEN': 7,  'DET': 8,  'GSW': 9,  'HOU': 10,
        'IND': 11, 'LAC': 12, 'LAL': 13, 'MIA': 14, 'MIL': 15,
        'MIN': 16, 'BKN': 17, 'NYK': 18, 'ORL': 19, 'PHI': 20,
        'PHX': 21, 'POR': 22, 'SAC': 23, 'SAS': 24, 'OKC': 25,
        'UTA': 26, 'WAS': 27, 'TOR': 28, 'MEM': 29, 'CHA': 30,
    }


def fetch_team_athletes(espn_team_id: int, team_abbr: str) -> list:
    """
    Fetch all active athletes for an ESPN team.
    Returns list of {espn_id, display_name}.
    """
    url = (f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba"
           f"/teams/{espn_team_id}/athletes?limit=100")
    data = _get(url)
    athletes = []

    for item in data.get('items', []):
        ref_url = item.get('$ref', '')
        if not ref_url:
            continue
        athlete_data = _get(ref_url)
        if not athlete_data:
            continue
        espn_id = str(athlete_data.get('id', ''))
        display_name = athlete_data.get('displayName') or athlete_data.get('fullName', '')
        if espn_id and display_name:
            athletes.append({'espn_id': espn_id, 'display_name': display_name})
        time.sleep(ATHLETE_RATE_LIMIT)

    return athletes


def run(dry_run: bool = False, verbose: bool = False):
    conn = sqlite3.connect(DB_PATH)

    # Load source data
    espn_team_ids = _load_espn_team_ids(conn)
    canonical = {
        row[0]: row[1]
        for row in conn.execute(
            "SELECT normalized_name, canonical_id FROM player_canonical_ids WHERE is_active = 1"
        ).fetchall()
    }

    print(f"\n{'[DRY RUN] ' if dry_run else ''}ESPN Athlete ID Crosswalk Builder")
    print(f"Teams to scan: {len(espn_team_ids)} | Canonical players: {len(canonical)}")
    print("=" * 55)

    matched = 0
    already_had_id = 0
    unmatched = []

    for abbr, espn_team_id in sorted(espn_team_ids.items()):
        print(f"\n  Scanning {abbr} (ESPN ID {espn_team_id})...")

        try:
            athletes = fetch_team_athletes(espn_team_id, abbr)
        except Exception as e:
            print(f"    ❌ {abbr} fetch failed: {e}")
            time.sleep(TEAM_RATE_LIMIT)
            continue

        for athlete in athletes:
            norm = normalize_for_lookup(athlete['display_name'])
            if norm in canonical:
                # Check if already has an espn_id
                existing = conn.execute(
                    "SELECT espn_id FROM player_canonical_ids WHERE normalized_name = ?", (norm,)
                ).fetchone()
                if existing and existing[0]:
                    already_had_id += 1
                    if verbose:
                        print(f"    ⏭️  {athlete['display_name']} — already has ESPN ID {existing[0]}")
                    continue

                if not dry_run:
                    conn.execute(
                        "UPDATE player_canonical_ids SET espn_id = ? WHERE normalized_name = ?",
                        (athlete['espn_id'], norm)
                    )
                print(f"    ✅  {athlete['display_name']} → espn_id {athlete['espn_id']}")
                matched += 1
            else:
                unmatched.append(f"{abbr}: {athlete['display_name']}")
                if verbose:
                    print(f"    ⚠️  No canonical match: {athlete['display_name']} ({norm})")

        time.sleep(TEAM_RATE_LIMIT)

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'=' * 55}")
    print(f"{'[DRY RUN] ' if dry_run else ''}Results:")
    print(f"  ✅  New espn_ids written: {matched}")
    print(f"  ⏭️   Already had espn_id: {already_had_id}")
    print(f"  ⚠️   No canonical match:  {len(unmatched)}")
    if unmatched and verbose:
        print(f"\nUnmatched (check for roster changes / G-League players):")
        for name in unmatched[:30]:
            print(f"    {name}")
    print(f"\nDone at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build ESPN athlete ID crosswalk')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show matches without writing to DB')
    parser.add_argument('--verbose', action='store_true',
                        help='Show all athletes including already-matched and unmatched')
    args = parser.parse_args()
    run(dry_run=args.dry_run, verbose=args.verbose)
