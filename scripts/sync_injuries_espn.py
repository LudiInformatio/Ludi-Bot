"""
sync_injuries_espn.py — ESPN Injury Intelligence Sync (Fast Source)

Scans all 30 NBA teams via ESPN's public API for active player injuries.
Writes confirmed OUT/DOUBTFUL/GTD records to player_injuries with source='ESPN'.

Why ESPN for injuries (partial Phase 8.21):
  - BDL and Tank01 can lag 2-6 hours behind official team announcements
  - ESPN updates within 15-30 minutes of team announcements
  - ESPN API is FREE, no auth, no quota — same endpoint as suspension sync
  - Catches same-day rulings (surgery, game-time decisions) before morning brief + evening lock

Scope (partial 8.21 — injury pipeline only):
  - NOT the full Phase 8.21 integration (no ESPN client utility, no crosswalk build,
    no game lines fallback, no longComment corpus). Full 8.21 remains on roadmap.
  - Name → team resolution uses player_canonical_ids.normalized_name (accent-safe)
  - Skips suspension type (type_id=17) — handled by sync_suspensions_espn.py

Wire into:
  - daily_briefing.yml: BEFORE "Run Morning Briefing" step
  - evening_slate_lock.yml: BEFORE "--force" BDL/Tank01 sync
  - injury_refresh.yml: FIRST step in each refresh cycle (ESPN is fastest source)

Usage:
    python scripts/sync_injuries_espn.py
    python scripts/sync_injuries_espn.py --dry-run
    python scripts/sync_injuries_espn.py --team UTA   # single team
"""

import sqlite3
import requests
import unicodedata
import re
import time
import sys
import os
import json
from datetime import datetime, date
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ESPN team ID mapping (same as sync_suspensions_espn.py)
ESPN_TEAM_IDS = {
    'ATL': 1,  'BOS': 2,  'NOP': 3,  'CHI': 4,  'CLE': 5,
    'DAL': 6,  'DEN': 7,  'DET': 8,  'GSW': 9,  'HOU': 10,
    'IND': 11, 'LAC': 12, 'LAL': 13, 'MIA': 14, 'MIL': 15,
    'MIN': 16, 'BKN': 17, 'NYK': 18, 'ORL': 19, 'PHI': 20,
    'PHX': 21, 'POR': 22, 'SAC': 23, 'SAS': 24, 'OKC': 25,
    'UTA': 26, 'WAS': 27, 'TOR': 28, 'MEM': 29, 'CHA': 30
}

# ESPN status → our status mapping
ESPN_STATUS_MAP = {
    'Out': 'OUT',
    'Questionable': 'GTD',
    'Doubtful': 'DOUBTFUL',
    'Day-To-Day': 'GTD',
    'Probable': 'PROBABLE',
}

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
        print(f"   [ESPN-INJ] Request error: {e}")
    return {}


def _normalize_name(name: str) -> str:
    """Normalize player name to match player_canonical_ids.normalized_name format.
    Strips accents (NFD) + lowercase + remove suffixes (Jr., Sr., II, III)."""
    nfd = unicodedata.normalize('NFD', name)
    without_accents = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    clean = without_accents.lower().strip()
    clean = re.sub(r'\s+(jr|sr|ii|iii|iv)\.?\s*$', '', clean).strip()
    return clean


def _load_canonical_lookup(conn: sqlite3.Connection) -> dict:
    """Load normalized_name → (full_name, team) from player_canonical_ids."""
    cursor = conn.cursor()
    cursor.execute('SELECT normalized_name, full_name, team FROM player_canonical_ids WHERE is_active = 1')
    return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}


def fetch_team_injuries(espn_team_id: int, team_abbr: str) -> list:
    """
    Fetch all active injuries for one team from ESPN core API.
    Skips suspensions (type_id=17) — those are handled by sync_suspensions_espn.py.
    Returns list of injury dicts ready for DB processing.
    """
    url = f"https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/teams/{espn_team_id}/injuries"
    data = _get(url)
    items = data.get('items', [])

    injuries = []
    for item in items:
        ref = item.get('$ref', '')
        if not ref:
            continue

        injury = _get(ref)
        if not injury:
            continue

        # Skip suspensions — handled by sync_suspensions_espn.py
        inj_type = injury.get('type', {})
        if inj_type.get('id') in ('17', 17) or 'SUSPENSION' in inj_type.get('name', '').upper():
            continue

        # Map ESPN status to our status
        espn_status = injury.get('status', '')
        our_status = ESPN_STATUS_MAP.get(espn_status)
        if not our_status:
            continue  # Skip statuses we don't track (Active, Probable not worth recording)

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
        return_date = details.get('returnDate')  # "YYYY-MM-DD" or None

        # Calculate days_out
        days_out = None
        if return_date:
            try:
                rd = datetime.strptime(return_date, '%Y-%m-%d').date()
                days_out = (rd - date.today()).days
            except ValueError:
                pass

        # Build description
        short = injury.get('shortComment', '')
        long_comment = injury.get('longComment', '')
        description = short if short else (long_comment[:200] if long_comment else inj_type.get('name', 'Injury'))

        # Parse injury type label
        injury_type = inj_type.get('name', '') or details.get('type', 'Injury')

        injuries.append({
            'player_name': player_name,
            'team_abbreviation': team_abbr,
            'status': our_status,
            'injury_type': injury_type[:100],
            'return_date': return_date,
            'days_out': days_out,
            'onset_date': None,
            'description': description[:500],
            'source': 'ESPN',
            'snapshot_time': datetime.now().isoformat(),
            'is_game_day_report': 0,
        })

    return injuries


def sync_to_db(injuries: list, conn: sqlite3.Connection,
               canonical_lookup: dict, dry_run: bool = False) -> dict:
    """
    Write ESPN injury records to player_injuries.
    - Resolves player names via canonical_lookup (accent-safe)
    - Stores canonical full_name (e.g. 'Jusuf Nurkić' not 'Jusuf Nurkic')
    - Uses UPDATE for existing ESPN records (keeps snapshot fresh)
    - Uses INSERT for new entries not yet in DB
    - Dedup guard: skips identical (player, status, date) already recorded today
    """
    cursor = conn.cursor()
    inserted = 0
    updated = 0
    skipped = 0

    for inj in injuries:
        player_name = inj['player_name']
        team_abbreviation = inj['team_abbreviation']

        # Resolve to canonical full_name + confirm team via canonical_ids
        normalized = _normalize_name(player_name)
        canonical_match = canonical_lookup.get(normalized)
        if canonical_match:
            player_name = canonical_match[0]  # Use canonical full_name (e.g. Jusuf Nurkić)
            if not team_abbreviation:
                team_abbreviation = canonical_match[1]

        # Dedup guard: skip if identical (player, status, date) already exists today
        existing_today = cursor.execute('''
            SELECT id FROM player_injuries
            WHERE player_name = ? AND status = ?
              AND DATE(snapshot_time) = DATE('now')
              AND resolved_at IS NULL
            LIMIT 1
        ''', (player_name, inj['status'])).fetchone()

        if existing_today:
            # Update snapshot to keep it within the 14-day staleness guard
            if not dry_run:
                cursor.execute('''
                    UPDATE player_injuries
                    SET snapshot_time = ?, description = ?, return_date = ?, days_out = ?,
                        team_abbreviation = COALESCE(NULLIF(team_abbreviation,''), ?)
                    WHERE id = ?
                ''', (inj['snapshot_time'], inj['description'], inj['return_date'],
                      inj['days_out'], team_abbreviation, existing_today[0]))
            updated += 1
            continue

        # Check if there's already an ESPN record for this player (any date, unresolved)
        existing_espn = cursor.execute('''
            SELECT id FROM player_injuries
            WHERE player_name = ? AND source = 'ESPN' AND resolved_at IS NULL
            LIMIT 1
        ''', (player_name,)).fetchone()

        if existing_espn:
            if not dry_run:
                cursor.execute('''
                    UPDATE player_injuries
                    SET snapshot_time = ?, status = ?, description = ?,
                        return_date = ?, days_out = ?,
                        team_abbreviation = COALESCE(NULLIF(team_abbreviation,''), ?)
                    WHERE id = ?
                ''', (inj['snapshot_time'], inj['status'], inj['description'],
                      inj['return_date'], inj['days_out'], team_abbreviation, existing_espn[0]))
            updated += 1
        else:
            if not dry_run:
                cursor.execute('''
                    INSERT INTO player_injuries (
                        player_name, team_abbreviation, status, injury_type,
                        return_date, days_out, onset_date, description, source,
                        snapshot_time, is_game_day_report, resolved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                ''', (
                    player_name, team_abbreviation, inj['status'],
                    inj['injury_type'], inj['return_date'], inj['days_out'],
                    inj['onset_date'], inj['description'], inj['source'],
                    inj['snapshot_time'], inj['is_game_day_report']
                ))
            inserted += 1

    if not dry_run:
        conn.commit()

    return {'inserted': inserted, 'updated': updated, 'skipped': skipped}


def resolve_stale_espn_injuries(conn: sqlite3.Connection, active_players: set) -> int:
    """
    Auto-resolve ESPN injury records for players no longer listed as injured.
    Called after processing all teams to clean up recovered players.
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, player_name FROM player_injuries
        WHERE source = 'ESPN' AND resolved_at IS NULL
    ''')
    to_resolve = [(row[0], row[1]) for row in cursor.fetchall()
                  if row[1] not in active_players]

    count = 0
    for row_id, pname in to_resolve:
        cursor.execute('''
            UPDATE player_injuries SET resolved_at = ? WHERE id = ?
        ''', (datetime.now().isoformat(), row_id))
        count += 1

    conn.commit()
    return count


def main():
    parser = argparse.ArgumentParser(description='ESPN Injury Sync (partial Phase 8.21)')
    parser.add_argument('--dry-run', action='store_true', help='Print without writing to DB')
    parser.add_argument('--team', type=str, help='Only sync one team (e.g. UTA)')
    args = parser.parse_args()

    print("=" * 55)
    print("   ESPN INJURY SYNC (Phase 8.21 — Injuries Only)")
    print(f"   Mode: {'DRY RUN' if args.dry_run else 'Production'}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')}")
    print("=" * 55)

    db_path = getattr(config, 'DB_PATH', 'ludi.db')
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")

    # Load canonical name lookup once
    canonical_lookup = _load_canonical_lookup(conn)
    print(f"   📋 Canonical lookup loaded: {len(canonical_lookup)} players")

    # Determine teams to scan
    if args.team:
        team_abbr = args.team.upper()
        if team_abbr not in ESPN_TEAM_IDS:
            print(f"❌ Unknown team: {team_abbr}")
            sys.exit(1)
        teams_to_scan = [(ESPN_TEAM_IDS[team_abbr], team_abbr)]
    else:
        teams_to_scan = [(v, k) for k, v in ESPN_TEAM_IDS.items()]

    print(f"\n📡 Scanning {len(teams_to_scan)} team(s) for injuries...")

    all_injuries = []
    active_injured_players = set()

    for espn_team_id, team_abbr in teams_to_scan:
        team_injuries = fetch_team_injuries(espn_team_id, team_abbr)
        if team_injuries:
            for inj in team_injuries:
                # Resolve canonical name for active set tracking
                normalized = _normalize_name(inj['player_name'])
                canonical_match = canonical_lookup.get(normalized)
                canonical_name = canonical_match[0] if canonical_match else inj['player_name']
                active_injured_players.add(canonical_name)
                print(f"   🏥 {canonical_name} ({team_abbr}) — {inj['status']} | {inj['injury_type'][:40]}")
            all_injuries.extend(team_injuries)
        time.sleep(RATE_LIMIT_SLEEP)

    # Sync to DB
    if all_injuries:
        result = sync_to_db(all_injuries, conn, canonical_lookup, dry_run=args.dry_run)
        print(f"\n✅ Sync complete: {result['inserted']} new, {result['updated']} updated")
    else:
        print("\n✅ No active injuries found via ESPN")

    # Resolve players no longer listed as injured by ESPN.
    # ONLY run when scanning ALL 30 teams — a partial --team scan would incorrectly
    # resolve other teams' injury records since they're not in active_injured_players.
    # This handles both directions: OUT→still OUT (keep), OUT→not listed (resolve/return).
    if not args.dry_run and not args.team:
        resolved = resolve_stale_espn_injuries(conn, active_injured_players)
        if resolved:
            print(f"✅ Auto-resolved {resolved} ESPN injury record(s) — players returned to active")

    conn.close()
    print(f"\n   Total ESPN injuries: {len(all_injuries)}")


if __name__ == '__main__':
    main()
