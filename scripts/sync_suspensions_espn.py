"""
sync_suspensions_espn.py — ESPN Suspension Intelligence Sync

Scans all 30 NBA teams via ESPN's public API for active player suspensions.
Writes confirmed suspensions to player_injuries (status='OUT', injury_type='SUSPENSION').

Why ESPN for suspensions:
  - Tank01/BDL do not reliably surface suspension status as a distinct type
  - ESPN API returns INJURY_STATUS_SUSPENSION (type.id=17) with returnDate + editorial context
  - Anti-drug violations, altercation suspensions, and conduct violations all appear here
  - Zero API cost (no auth, no quota)

This script is Phase 8.16 (Suspension Intelligence) delivered via ESPN instead of
the originally planned Perplexity + Claude Haiku approach (which required LLM cost).

Wire into: data_sync.yml after "Sync Injuries" step
Also fire from: injury_refresh.yml (daytime runs) for intraday suspension announcements

Usage:
    python scripts/sync_suspensions_espn.py
    python scripts/sync_suspensions_espn.py --dry-run
    python scripts/sync_suspensions_espn.py --team PHI  # single team
"""

import sqlite3
import requests
import time
import sys
import os
import json
from datetime import datetime, date, timedelta
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ESPN team ID mapping — sourced from canonical_teams DB at runtime.
# Fallback used only if canonical_teams table isn't populated yet (e.g. first-ever init).
_ESPN_TEAM_IDS_FALLBACK = {
    'ATL': 1,  'BOS': 2,  'NOP': 3,  'CHI': 4,  'CLE': 5,
    'DAL': 6,  'DEN': 7,  'DET': 8,  'GSW': 9,  'HOU': 10,
    'IND': 11, 'LAC': 12, 'LAL': 13, 'MIA': 14, 'MIL': 15,
    'MIN': 16, 'BKN': 17, 'NYK': 18, 'ORL': 19, 'PHI': 20,
    'PHX': 21, 'POR': 22, 'SAC': 23, 'SAS': 24, 'OKC': 25,
    'UTA': 26, 'WAS': 27, 'TOR': 28, 'MEM': 29, 'CHA': 30
}


def _load_espn_team_ids(conn) -> dict:
    """Load ESPN team IDs from canonical_teams table. Falls back to hardcoded if unavailable."""
    try:
        rows = conn.execute(
            "SELECT standard_abbr, espn_id FROM canonical_teams WHERE espn_id IS NOT NULL"
        ).fetchall()
        if rows:
            return {row[0]: row[1] for row in rows}
    except Exception:
        pass
    return _ESPN_TEAM_IDS_FALLBACK

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'application/json',
}
TIMEOUT = 10
RATE_LIMIT_SLEEP = 0.4  # seconds between team calls


def _get(url: str) -> dict:
    """Safe GET with timeout and error handling."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"   [ESPN] Request error: {e}")
    return {}


def fetch_team_suspensions(espn_team_id: int, team_abbr: str) -> list:
    """
    Fetch all active suspensions for one team from ESPN core API.
    Returns list of suspension dicts ready for DB insert.
    """
    url = f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/teams/{espn_team_id}/injuries"
    data = _get(url)
    items = data.get('items', [])

    suspensions = []
    for item in items:
        ref = item.get('$ref', '')
        if not ref:
            continue

        injury = _get(ref)
        if not injury:
            continue

        # Filter: only process suspension type (id=17)
        inj_type = injury.get('type', {})
        if inj_type.get('id') not in ('17', 17) and 'SUSPENSION' not in inj_type.get('name', ''):
            continue

        # Get player name via athlete $ref
        athlete_ref = injury.get('athlete', {}).get('$ref', '')
        player_name = None
        if athlete_ref:
            athlete = _get(athlete_ref)
            player_name = athlete.get('displayName') or athlete.get('fullName')

        if not player_name:
            continue

        # Parse return date
        details = injury.get('details', {})
        return_date = details.get('returnDate')  # "YYYY-MM-DD"

        # Calculate days out from today
        days_out = None
        if return_date:
            try:
                rd = datetime.strptime(return_date, '%Y-%m-%d').date()
                days_out = max(0, (rd - date.today()).days)
            except ValueError:
                pass

        # Build description from ESPN editorial content
        short = injury.get('shortComment', '')
        long_comment = injury.get('longComment', '')
        description = short if short else long_comment[:200] if long_comment else 'Suspended'

        # Determine if still active (returnDate in future or today)
        is_active = True
        if return_date:
            try:
                rd = datetime.strptime(return_date, '%Y-%m-%d').date()
                if rd < date.today():
                    is_active = False  # Suspension served, skip
            except ValueError:
                pass

        if not is_active:
            continue

        suspensions.append({
            'player_name': player_name,
            'team_abbreviation': team_abbr,
            'status': 'OUT',
            'injury_type': 'SUSPENSION',
            'return_date': return_date,
            'days_out': days_out,
            'onset_date': None,
            'description': description[:500],
            'source': 'espn_suspension',
            'snapshot_time': datetime.now().isoformat(),
            'is_game_day_report': 0,
        })

    return suspensions


def resolve_stale_espn_suspensions(conn: sqlite3.Connection) -> int:
    """
    Auto-resolve ESPN suspension records where returnDate has passed.
    Called before inserting new data to clean up served suspensions.
    """
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE player_injuries
        SET resolved_at = ?
        WHERE source = 'espn_suspension'
          AND resolved_at IS NULL
          AND return_date IS NOT NULL
          AND return_date < date('now')
    """, (datetime.now().isoformat(),))
    count = cursor.rowcount
    conn.commit()
    return count


def sync_to_db(suspensions: list, conn: sqlite3.Connection, dry_run: bool = False) -> dict:
    """
    Write suspension records to player_injuries.
    Uses INSERT OR REPLACE to upsert — safe to run multiple times.
    """
    cursor = conn.cursor()
    inserted = 0
    skipped = 0

    for s in suspensions:
        # Check if already in DB with same source and unresolved
        cursor.execute("""
            SELECT id FROM player_injuries
            WHERE player_name = ?
              AND source = 'espn_suspension'
              AND resolved_at IS NULL
        """, (s['player_name'],))
        existing = cursor.fetchone()

        if existing:
            # Update snapshot_time to keep it fresh (prevents staleness guard from cleaning it)
            if not dry_run:
                cursor.execute("""
                    UPDATE player_injuries
                    SET snapshot_time = ?, description = ?, return_date = ?, days_out = ?
                    WHERE id = ?
                """, (s['snapshot_time'], s['description'], s['return_date'], s['days_out'], existing[0]))
            skipped += 1
        else:
            if not dry_run:
                cursor.execute("""
                    INSERT INTO player_injuries (
                        player_name, team_abbreviation, status, injury_type,
                        return_date, days_out, onset_date, description, source,
                        snapshot_time, is_game_day_report, resolved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """, (
                    s['player_name'], s['team_abbreviation'], s['status'],
                    s['injury_type'], s['return_date'], s['days_out'],
                    s['onset_date'], s['description'], s['source'],
                    s['snapshot_time'], s['is_game_day_report']
                ))
            inserted += 1

    if not dry_run:
        conn.commit()

    return {'inserted': inserted, 'updated': skipped}


def main():
    parser = argparse.ArgumentParser(description='ESPN Suspension Sync')
    parser.add_argument('--dry-run', action='store_true', help='Print without writing to DB')
    parser.add_argument('--team', type=str, help='Only sync one team abbreviation (e.g. PHI)')
    args = parser.parse_args()

    print("=" * 50)
    print("   ESPN SUSPENSION SYNC")
    print(f"   Mode: {'DRY RUN' if args.dry_run else 'Production'}")
    print("=" * 50)

    db_path = getattr(config, 'DB_PATH', 'ludi.db')
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")

    # Load ESPN team IDs from canonical_teams (single source of truth)
    espn_team_ids = _load_espn_team_ids(conn)
    print(f"   📋 ESPN team map loaded: {len(espn_team_ids)} teams "
          f"({'canonical_teams DB' if len(espn_team_ids) == 30 else 'fallback'})")

    # Step 1: Resolve any ESPN suspensions where returnDate has passed
    resolved = resolve_stale_espn_suspensions(conn)
    if resolved:
        print(f"✅ Auto-resolved {resolved} served suspension(s)")

    # Step 2: Determine which teams to scan
    if args.team:
        team_abbr = args.team.upper()
        if team_abbr not in espn_team_ids:
            print(f"❌ Unknown team: {team_abbr}")
            sys.exit(1)
        teams_to_scan = [(espn_team_ids[team_abbr], team_abbr)]
    else:
        teams_to_scan = [(v, k) for k, v in espn_team_ids.items()]

    print(f"\n📡 Scanning {len(teams_to_scan)} team(s)...")

    all_suspensions = []
    for espn_team_id, team_abbr in teams_to_scan:
        suspensions = fetch_team_suspensions(espn_team_id, team_abbr)
        if suspensions:
            for s in suspensions:
                print(f"   🚫 {s['player_name']} ({team_abbr}) — SUSPENDED | Return: {s['return_date']} | {s['description'][:80]}")
            all_suspensions.extend(suspensions)
        time.sleep(RATE_LIMIT_SLEEP)

    # Step 3: Write to DB
    if all_suspensions:
        result = sync_to_db(all_suspensions, conn, dry_run=args.dry_run)
        print(f"\n✅ Sync complete: {result['inserted']} new, {result['updated']} updated")
    else:
        print("\n✅ No active suspensions found")

    conn.close()

    if all_suspensions:
        print(f"\n📋 Summary ({len(all_suspensions)} active suspension(s)):")
        for s in all_suspensions:
            print(f"   {s['player_name']} ({s['team_abbreviation']}) — return {s['return_date']} ({s['days_out']}d)")


if __name__ == '__main__':
    main()
