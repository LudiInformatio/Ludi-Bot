#!/usr/bin/env python3
"""
Tank01 Depth Charts Sync

Fetches NBA depth charts and updates local database.
Identifies starters (depth_order=1) vs backups (depth_order>=2).

Usage:
    python scripts/sync_depth_charts.py              # Sync all teams
    python scripts/sync_depth_charts.py --team ATL   # Single team
    python scripts/sync_depth_charts.py --dry-run    # Preview only
    python scripts/sync_depth_charts.py --verbose    # Debug output

Author: Phase 6.1 Implementation
Date: February 2, 2026
"""

import sqlite3
import requests
import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config

class DepthChartSync:
    """
    Syncs Tank01 depth charts to local database.

    Responsibilities:
    1. Fetch depth charts from Tank01 API
    2. Parse depth position strings (e.g., "PG1" → 1)
    3. Sync to depth_charts table
    4. Update is_starter column in players table
    """

    def __init__(self, db_path='ludi.db', verbose=False):
        self.db_path = db_path
        self.api_key = config.TANK01_KEY
        self.base_url = f"https://{config.TANK01_HOST}"
        self.verbose = verbose

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

    def fetch_depth_charts(self):
        """
        Fetch all 30 team depth charts from Tank01.

        Returns:
            {
                "success": bool,
                "teams": int,
                "data": [...],
                "errors": []
            }
        """
        url = f"{self.base_url}/getNBADepthCharts"

        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": config.TANK01_HOST
        }

        self._log(f"🔍 Fetching depth charts from {url}")

        try:
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()

                # Tank01 returns array of teams directly (not under "body" key)
                if isinstance(data, list):
                    teams = data
                elif "body" in data:
                    teams = data["body"]
                else:
                    return {
                        "success": False,
                        "teams": 0,
                        "data": [],
                        "errors": ["Unexpected response structure"]
                    }

                self._log(f"✅ Received {len(teams)} teams")

                return {
                    "success": True,
                    "teams": len(teams),
                    "data": teams,
                    "errors": []
                }
            else:
                return {
                    "success": False,
                    "teams": 0,
                    "data": [],
                    "errors": [f"API returned status {response.status_code}"]
                }

        except Exception as e:
            return {
                "success": False,
                "teams": 0,
                "data": [],
                "errors": [str(e)]
            }

    def _parse_depth_order(self, depth_position):
        """
        Parse depth order from position string.

        Examples:
            "PG1" → 1
            "SG2" → 2
            "C3" → 3

        Args:
            depth_position: String like "PG1", "SG2", etc.

        Returns:
            int: Depth order (1, 2, 3, ...)
        """
        if not depth_position:
            return 999  # Unknown depth

        # Extract number from end of string
        # "PG1" → "1", "SG10" → "10"
        depth_str = ''.join(filter(str.isdigit, depth_position))

        try:
            return int(depth_str) if depth_str else 999
        except ValueError:
            return 999

    def sync_to_database(self, depth_data, dry_run=False, team_filter=None):
        """
        Sync depth chart data to database.

        Args:
            depth_data: Output from fetch_depth_charts()
            dry_run: If True, preview changes without writing
            team_filter: Optional team abbreviation to sync (e.g., "ATL")

        Returns:
            {
                "teams_synced": int,
                "players_updated": int,
                "starters_identified": int,
                "errors": []
            }
        """
        if not depth_data["success"]:
            return {
                "teams_synced": 0,
                "players_updated": 0,
                "starters_identified": 0,
                "errors": depth_data["errors"]
            }

        conn = self._get_conn()
        cursor = conn.cursor()

        teams_synced = 0
        players_updated = 0
        starters_identified = 0
        errors = []
        sync_timestamp = datetime.now().isoformat()

        try:
            # Clear existing depth chart data (fresh sync each time)
            if not dry_run:
                if team_filter:
                    cursor.execute('DELETE FROM depth_charts WHERE team_abbr = ?', (team_filter,))
                    self._log(f"🗑️  Cleared existing depth chart for {team_filter}")
                else:
                    cursor.execute('DELETE FROM depth_charts')
                    self._log("🗑️  Cleared all existing depth charts")

            for team_data in depth_data["data"]:
                team_abbr = team_data.get("teamAbv", "UNK")
                team_id = team_data.get("teamID", "")

                # Apply team filter if specified
                if team_filter and team_abbr != team_filter:
                    continue

                depth_chart = team_data.get("depthChart", {})

                if not depth_chart:
                    errors.append(f"{team_abbr}: No depth chart data")
                    continue

                self._log(f"📊 Processing {team_abbr}...")

                for position, players in depth_chart.items():
                    # Positions should be PG, SG, SF, PF, C
                    if position not in ["PG", "SG", "SF", "PF", "C"]:
                        continue

                    for player in players:
                        player_name = player.get("longName", "")
                        player_id = player.get("playerID", "")
                        depth_position = player.get("depthPosition", "")

                        # Parse depth order (e.g., "PG1" → 1)
                        depth_order = self._parse_depth_order(depth_position)

                        if not player_name:
                            continue

                        # Insert into depth_charts table
                        if dry_run:
                            self._log(f"  [DRY RUN] {team_abbr} {position}{depth_order}: {player_name}")
                        else:
                            try:
                                cursor.execute('''
                                    INSERT INTO depth_charts (
                                        team_abbr, team_id, position,
                                        player_name, player_id, depth_order, synced_at
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    team_abbr, team_id, position,
                                    player_name, player_id, depth_order, sync_timestamp
                                ))

                                players_updated += 1

                                if depth_order == 1:
                                    starters_identified += 1
                                    self._log(f"  ⭐ {position}1: {player_name}")
                                else:
                                    self._log(f"     {position}{depth_order}: {player_name}")

                            except sqlite3.IntegrityError as e:
                                errors.append(f"{team_abbr} {position}{depth_order}: {str(e)}")

                teams_synced += 1

            if not dry_run:
                conn.commit()
                self._log(f"✅ Committed {players_updated} players to database")

        except Exception as e:
            conn.rollback()
            errors.append(f"Database error: {str(e)}")

        finally:
            conn.close()

        return {
            "teams_synced": teams_synced,
            "players_updated": players_updated,
            "starters_identified": starters_identified,
            "errors": errors
        }

    def update_player_starter_status(self):
        """
        Update is_starter column in players table based on depth_charts.

        Logic:
        - If player has depth_order=1 in ANY position → is_starter=1
        - Otherwise → is_starter=0

        Returns:
            int: Count of players updated
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            # First, reset all players to non-starter
            cursor.execute('UPDATE players SET is_starter = 0')

            # Then, mark starters (depth_order=1)
            cursor.execute('''
                UPDATE players
                SET is_starter = 1
                WHERE name IN (
                    SELECT DISTINCT player_name
                    FROM depth_charts
                    WHERE depth_order = 1
                )
            ''')

            updated_count = cursor.rowcount
            conn.commit()

            self._log(f"✅ Updated is_starter for {updated_count} players")

            return updated_count

        except Exception as e:
            conn.rollback()
            self._log(f"❌ Error updating player starter status: {e}")
            return 0

        finally:
            conn.close()

    def get_sync_stats(self):
        """
        Get current depth chart statistics.

        Returns:
            dict: Stats about current depth chart data
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        stats = {}

        try:
            # Total teams
            cursor.execute('SELECT COUNT(DISTINCT team_abbr) FROM depth_charts')
            stats["teams"] = cursor.fetchone()[0]

            # Total players
            cursor.execute('SELECT COUNT(*) FROM depth_charts')
            stats["total_players"] = cursor.fetchone()[0]

            # Starters
            cursor.execute('SELECT COUNT(*) FROM depth_charts WHERE depth_order = 1')
            stats["starters"] = cursor.fetchone()[0]

            # Last sync time
            cursor.execute('SELECT MAX(synced_at) FROM depth_charts')
            stats["last_synced"] = cursor.fetchone()[0]

            # Players marked as starters
            cursor.execute('SELECT COUNT(*) FROM players WHERE is_starter = 1')
            stats["players_marked_starter"] = cursor.fetchone()[0]

        except Exception as e:
            stats["error"] = str(e)

        finally:
            conn.close()

        return stats


def main():
    parser = argparse.ArgumentParser(description="Sync Tank01 depth charts to database")
    parser.add_argument("--team", type=str, help="Sync single team (e.g., ATL)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")
    parser.add_argument("--stats", action="store_true", help="Show current stats only")

    args = parser.parse_args()

    syncer = DepthChartSync(verbose=args.verbose or args.dry_run)

    # Show stats mode
    if args.stats:
        stats = syncer.get_sync_stats()
        print("📊 Depth Chart Statistics")
        print("=" * 50)
        for key, value in stats.items():
            print(f"{key:.<30} {value}")
        return

    # Sync mode
    print("🏀 Tank01 Depth Charts Sync")
    print("=" * 50)

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No changes will be saved")

    if args.team:
        print(f"📍 Target: {args.team} only")
    else:
        print("📍 Target: All 30 teams")

    print()

    # Step 1: Fetch from API
    print("Step 1: Fetching from Tank01 API...")
    depth_data = syncer.fetch_depth_charts()

    if not depth_data["success"]:
        print(f"❌ Failed to fetch depth charts:")
        for error in depth_data["errors"]:
            print(f"   - {error}")
        sys.exit(1)

    print(f"✅ Received {depth_data['teams']} teams\n")

    # Step 2: Sync to database
    print("Step 2: Syncing to database...")
    result = syncer.sync_to_database(depth_data, dry_run=args.dry_run, team_filter=args.team)

    if result["errors"]:
        print(f"⚠️  Encountered {len(result['errors'])} errors:")
        for error in result["errors"][:5]:  # Show first 5
            print(f"   - {error}")

    print()
    print("📊 Sync Results")
    print("=" * 50)
    print(f"Teams synced: {result['teams_synced']}")
    print(f"Players updated: {result['players_updated']}")
    print(f"Starters identified: {result['starters_identified']}")

    if args.dry_run:
        print("\n⚠️  DRY RUN - No changes saved to database")
        return

    # Step 3: Update player starter status
    print("\nStep 3: Updating player starter status...")
    updated = syncer.update_player_starter_status()
    print(f"✅ Updated {updated} players in players table")

    print("\n✅ Sync complete!")


if __name__ == "__main__":
    main()
