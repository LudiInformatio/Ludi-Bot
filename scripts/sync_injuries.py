#!/usr/bin/env python3
"""
Injury Sync Script

Fetches NBA injury data from BDL (primary) and Tank01 (fallback),
syncs to local database with status-change detection.

Usage:
    python scripts/sync_injuries.py              # Sync all injuries
    python scripts/sync_injuries.py --dry-run    # Preview only
    python scripts/sync_injuries.py --verbose    # Debug output

Author: Phase 8.0 Implementation
Date: February 17, 2026
"""

import sqlite3
import argparse
import sys
import os
from datetime import datetime, date
from pathlib import Path
import requests
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.bdl_client import BDLClient
from utils.player_id_resolver import PlayerIDResolver


class InjurySync:
    """
    Syncs NBA injury data to local database.

    Responsibilities:
    1. Fetch injuries from BDL (primary) and Tank01 (fallback)
    2. Status-change detection: only INSERT when status changes
    3. Update players table with current injury status
    4. Handle resolved injuries (set resolved_at)
    """

    STATUS_MAP = {
        'Out': 'OUT',
        'Day-To-Day': 'QUESTIONABLE',
        'Doubtful': 'DOUBTFUL',
        'Questionable': 'QUESTIONABLE',
        'Probable': 'PROBABLE',
    }

    def __init__(self, db_path='ludi.db', verbose=False, dry_run=False):
        self.db_path = db_path
        self.verbose = verbose
        self.dry_run = dry_run
        self.is_game_day_report = os.getenv('IS_GAME_DAY_REPORT', 'false').lower() == 'true'

    def _log(self, message):
        """Print message if verbose mode enabled"""
        if self.verbose:
            print(message)

    def _get_conn(self):
        """Get database connection with WAL mode"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

    def _calculate_days_out(self, return_date_str, onset_date_str):
        """
        Calculate days_out based on return_date or onset_date.

        Args:
            return_date_str: Expected return date (YYYY-MM-DD) or None
            onset_date_str: When injury first appeared in our records or None

        Returns:
            int: Number of days out (positive = still out, negative = returning soon)
        """
        today = date.today()

        if return_date_str:
            try:
                return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
                return (return_date - today).days
            except (ValueError, TypeError):
                pass

        if onset_date_str:
            try:
                onset_date = datetime.strptime(onset_date_str, '%Y-%m-%d').date()
                return (today - onset_date).days
            except (ValueError, TypeError):
                pass

        return 0

    def _parse_injury_type(self, description):
        """
        Parse injury type from description field.

        Takes first few words as injury type.
        Example: "Left ankle sprain" -> "Left ankle"
        """
        if not description:
            return None

        words = description.split()[:3]
        return ' '.join(words) if words else None

    def _get_last_injury_record(self, conn, player_name):
        """Get the most recent injury record for a player"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status, onset_date, resolved_at
            FROM player_injuries
            WHERE player_name = ?
            ORDER BY snapshot_time DESC
            LIMIT 1
        ''', (player_name,))
        row = cursor.fetchone()
        if row:
            return {'status': row[0], 'onset_date': row[1], 'resolved_at': row[2]}
        return None

    def _get_active_players_from_db(self, conn):
        """Get list of all players from database"""
        cursor = conn.cursor()
        cursor.execute('SELECT name, team FROM players')
        return {(row[0], row[1]) for row in cursor.fetchall()}

    def fetch_injuries_bdl(self):
        """
        Fetch injuries from BallDontLie API (primary source).

        Returns:
            {
                "success": bool,
                "injuries": [...],
                "errors": []
            }
        """
        self._log("🔍 Fetching injuries from BDL...")

        try:
            client = BDLClient()
            if not client.api_key:
                return {
                    "success": False,
                    "injuries": [],
                    "errors": ["BDL API key not configured"]
                }

            injuries = client.get_active_injuries()

            if injuries is None:
                return {
                    "success": False,
                    "injuries": [],
                    "errors": ["BDL returned None"]
                }

            self._log(f"✅ BDL returned {len(injuries)} injury records")

            parsed_injuries = []
            for item in injuries:
                player = item.get('player', {})
                if not player:
                    continue

                first_name = player.get('first_name', '')
                last_name = player.get('last_name', '')
                player_name = f"{first_name} {last_name}".strip()

                if not player_name:
                    continue

                # BDL injury endpoint returns team_id only (no team object)
                # Resolve abbreviation from our players table by name
                team_abbreviation = None  # populated later in sync_to_database

                bdl_status = item.get('status', 'Out')
                normalized_status = self.STATUS_MAP.get(bdl_status, 'OUT')

                return_date = item.get('return_date')
                description = item.get('description', '')

                injury_type = self._parse_injury_type(description)

                parsed_injuries.append({
                    'player_name': player_name,
                    'team_abbreviation': team_abbreviation,
                    'status': normalized_status,
                    'return_date': return_date,
                    'description': description,
                    'injury_type': injury_type,
                    'source': 'BDL'
                })

            return {
                "success": True,
                "injuries": parsed_injuries,
                "errors": []
            }

        except Exception as e:
            return {
                "success": False,
                "injuries": [],
                "errors": [str(e)]
            }

    def fetch_injuries_tank01(self):
        """
        Fetch injuries from Tank01 API (fallback source).

        Returns:
            {
                "success": bool,
                "injuries": [...],
                "errors": []
            }
        """
        self._log("🔍 Fetching injuries from Tank01 (fallback)...")

        try:
            url = f"https://{config.TANK01_HOST}/getNBAInjuryList"
            headers = {
                "X-RapidAPI-Key": config.TANK01_KEY,
                "X-RapidAPI-Host": config.TANK01_HOST
            }

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code != 200:
                return {
                    "success": False,
                    "injuries": [],
                    "errors": [f"Tank01 returned status {response.status_code}"]
                }

            data = response.json()

            if 'body' not in data:
                return {
                    "success": False,
                    "injuries": [],
                    "errors": ["Tank01 response missing 'body' key"]
                }

            resolver = PlayerIDResolver()

            parsed_injuries = []
            for item in data['body']:
                # Tank01 getNBAInjuryList has no 'longName' field.
                # Resolve player name from playerID via canonical ID table.
                player_id = item.get('playerID', '')
                player_name = ''
                team_abbreviation = item.get('teamAbv', '')

                if player_id:
                    try:
                        player_info = resolver.get_player_info(player_id)
                        player_name = player_info.get('full_name', '')
                        if not team_abbreviation:
                            team_abbreviation = player_info.get('team', '')
                    except (ValueError, Exception):
                        pass  # name stays empty → skipped below

                if not player_name:
                    continue

                designation = item.get('designation', 'Available')
                normalized_status = self.STATUS_MAP.get(designation, 'ACTIVE')

                if normalized_status == 'ACTIVE':
                    continue

                # injReturnDate is YYYYMMDD; convert to YYYY-MM-DD
                raw_ret = item.get('injReturnDate', '')
                return_date = (
                    f"{raw_ret[:4]}-{raw_ret[4:6]}-{raw_ret[6:]}"
                    if len(raw_ret) == 8 else None
                )

                description = item.get('description', '')
                injury_type = self._parse_injury_type(description)

                parsed_injuries.append({
                    'player_name': player_name,
                    'team_abbreviation': team_abbreviation,
                    'status': normalized_status,
                    'return_date': return_date,
                    'description': description,
                    'injury_type': injury_type,
                    'source': 'Tank01'
                })

            self._log(f"✅ Tank01 returned {len(parsed_injuries)} injury records")

            return {
                "success": True,
                "injuries": parsed_injuries,
                "errors": []
            }

        except Exception as e:
            return {
                "success": False,
                "injuries": [],
                "errors": [str(e)]
            }

    def sync_to_database(self, injury_data):
        """
        Sync injury data to database with status-change detection.

        Args:
            injury_data: Output from fetch_injuries_* methods

        Returns:
            {
                "injuries_synced": int,
                "status_changes": int,
                "resolved": int,
                "errors": []
            }
        """
        if not injury_data["success"]:
            return {
                "injuries_synced": 0,
                "status_changes": 0,
                "resolved": 0,
                "errors": injury_data["errors"]
            }

        conn = self._get_conn()
        cursor = conn.cursor()

        injuries_synced = 0
        status_changes = 0
        resolved_count = 0
        errors = []
        snapshot_time = datetime.now().isoformat()

        active_player_names = {inj['player_name'] for inj in injury_data["injuries"]}
        all_db_players = self._get_active_players_from_db(conn)

        try:
            for injury in injury_data["injuries"]:
                player_name = injury['player_name']
                new_status = injury['status']
                return_date = injury.get('return_date')
                description = injury.get('description', '')
                injury_type = injury.get('injury_type')
                source = injury.get('source', 'Unknown')

                # Resolve team abbreviation from our players table (BDL doesn't return it)
                team_abbreviation = injury.get('team_abbreviation')
                if not team_abbreviation:
                    for pname, team in all_db_players:
                        if pname.lower() == player_name.lower():
                            team_abbreviation = team
                            break
                injury['team_abbreviation'] = team_abbreviation

                last_injury = self._get_last_injury_record(conn, player_name)

                should_insert = False
                onset_date = None

                if last_injury:
                    if last_injury['status'] != new_status:
                        should_insert = True
                        status_changes += 1
                        self._log(f"  🔄 Status change: {player_name}: {last_injury['status']} -> {new_status}")
                else:
                    should_insert = True

                if should_insert and new_status != 'ACTIVE':
                    onset_date = datetime.now().strftime('%Y-%m-%d')

                if should_insert and not self.dry_run:
                    try:
                        cursor.execute('''
                            INSERT INTO player_injuries (
                                player_name, team_abbreviation, status, injury_type,
                                return_date, days_out, onset_date, description, source,
                                snapshot_time, is_game_day_report, resolved_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                        ''', (
                            player_name,
                            injury.get('team_abbreviation'),
                            new_status,
                            injury_type,
                            return_date,
                            self._calculate_days_out(return_date, onset_date),
                            onset_date,
                            description,
                            source,
                            snapshot_time,
                            1 if self.is_game_day_report else 0
                        ))
                        injuries_synced += 1
                    except sqlite3.Error as e:
                        errors.append(f"Insert error for {player_name}: {e}")

                if not self.dry_run:
                    player_team = None
                    for pname, team in all_db_players:
                        if pname.lower() == player_name.lower():
                            player_team = team
                            break

                    cursor.execute('''
                        UPDATE players SET
                            current_injury_status = ?,
                            injury_updated_at = ?,
                            injury_return_date = ?,
                            days_out_current = ?
                        WHERE LOWER(name) = LOWER(?)
                    ''', (
                        new_status,
                        snapshot_time,
                        return_date,
                        self._calculate_days_out(return_date, onset_date),
                        player_name
                    ))

            resolved_cursor = conn.cursor()
            resolved_cursor.execute('''
                SELECT DISTINCT player_name
                FROM player_injuries
                WHERE resolved_at IS NULL
            ''')
            currently_injured = {row[0] for row in resolved_cursor.fetchall()}

            players_no_longer_injured = currently_injured - active_player_names

            for player_name in players_no_longer_injured:
                if not self.dry_run:
                    resolved_cursor.execute('''
                        UPDATE player_injuries
                        SET resolved_at = ?
                        WHERE player_name = ? AND resolved_at IS NULL
                    ''', (snapshot_time, player_name))

                    resolved_cursor.execute('''
                        UPDATE players SET
                            current_injury_status = 'ACTIVE',
                            injury_updated_at = ?,
                            injury_return_date = NULL,
                            days_out_current = 0
                        WHERE LOWER(name) = LOWER(?)
                    ''', (snapshot_time, player_name))

                    if resolved_cursor.rowcount > 0:
                        resolved_count += 1
                        self._log(f"  ✅ Resolved: {player_name}")
                else:
                    resolved_count += 1
                    self._log(f"  [DRY RUN] Would resolve: {player_name}")

            if not self.dry_run:
                conn.commit()

        except Exception as e:
            conn.rollback()
            errors.append(f"Database error: {str(e)}")

        finally:
            conn.close()

        return {
            "injuries_synced": injuries_synced,
            "status_changes": status_changes,
            "resolved": resolved_count,
            "errors": errors
        }


def main():
    parser = argparse.ArgumentParser(description="Sync NBA injuries to database")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")

    args = parser.parse_args()

    syncer = InjurySync(verbose=args.verbose, dry_run=args.dry_run)

    print("🏥 Injury Sync")
    print("=" * 50)

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No changes will be saved")
        print()

    print(f"Game Day Report: {syncer.is_game_day_report}")
    print()

    print("Step 1: Fetching from BDL (primary)...")
    injury_data = syncer.fetch_injuries_bdl()

    if not injury_data["success"]:
        print(f"⚠️  BDL fetch failed: {injury_data['errors']}")
        print()
        print("Step 2: Trying Tank01 (fallback)...")
        injury_data = syncer.fetch_injuries_tank01()

        if not injury_data["success"]:
            print(f"⚠️  Tank01 fetch also failed: {injury_data['errors']}")
            print()
            print("⚠️  WARNING: Both BDL and Tank01 failed. Exiting gracefully.")
            print("   This is not a critical failure - workflow should continue.")
            sys.exit(0)
    else:
        print(f"✅ BDL fetch successful: {len(injury_data['injuries'])} injuries")
        print()

        print("Step 2: Checking Tank01 for additional data...")
        tank01_data = syncer.fetch_injuries_tank01()

        if tank01_data["success"]:
            tank01_names = {inj['player_name'] for inj in tank01_data["injuries"]}
            bdl_names = {inj['player_name'] for inj in injury_data["injuries"]}
            new_from_tank01 = tank01_names - bdl_names

            if new_from_tank01:
                print(f"   Found {len(new_from_tank01)} additional injuries from Tank01")
                for inj in tank01_data["injuries"]:
                    if inj['player_name'] in new_from_tank01:
                        injury_data["injuries"].append(inj)
            else:
                print("   No additional injuries from Tank01")
        print()

    print("Step 3: Syncing to database...")
    result = syncer.sync_to_database(injury_data)

    if result["errors"]:
        print(f"⚠️  Encountered {len(result['errors'])} errors:")
        for error in result["errors"][:5]:
            print(f"   - {error}")

    print()
    print("📊 Sync Results")
    print("=" * 50)
    print(f"Injuries synced: {result['injuries_synced']}")
    print(f"Status changes: {result['status_changes']}")
    print(f"Resolved: {result['resolved']}")

    if args.dry_run:
        print("\n⚠️  DRY RUN - No changes saved to database")

    print()
    print("✅ Sync complete!")


if __name__ == "__main__":
    main()
