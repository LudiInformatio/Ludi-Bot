# LUDI INFORMATIO | ROSTER VALIDATOR UTILITY
# ----------------------------------------
# Purpose: Validate current NBA rosters against Tank01 API
# Detects: Trades, signings, waivers, two-way contracts
# Storage: Dual format (JSON reports + SQLite history)

import sqlite3
import requests
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import config
from utils.api_monitor import get_monitor

class RosterValidator:
    """
    Validates current roster data against Tank01 API.
    Detects trades, signings, waivers since last database update.

    Follows the singleton pattern to maintain a single instance and prevent
    duplicate API calls across modules.

    Usage:
        from utils.roster_validator import get_roster_validator
        validator = get_roster_validator()
        results = validator.validate_and_update(dry_run=True)
    """

    def __init__(self, db_path='ludi.db', logs_dir='logs/rosters'):
        """
        Initialize roster validator with database and JSON log directory.

        Args:
            db_path: Path to SQLite database (default: 'ludi.db')
            logs_dir: Directory for JSON validation reports (default: 'logs/rosters')
        """
        self.db_path = db_path
        self.logs_dir = logs_dir
        self.TANK_KEY = config.TANK01_KEY
        self.TANK_HOST = "tank01-fantasy-stats.p.rapidapi.com"
        self.monitor = get_monitor()

        # Create logs directory if it doesn't exist
        os.makedirs(logs_dir, exist_ok=True)

        print(f"✅ RosterValidator initialized (DB: {db_path}, Logs: {logs_dir})")

    def _get_conn(self) -> sqlite3.Connection:
        """Create a new database connection."""
        return sqlite3.connect(self.db_path)

    def fetch_all_nba_teams(self) -> List[Dict]:
        """
        Fetch all 30 NBA teams from Tank01 API.

        Returns:
            List of team dicts with teamAbv, teamCity, teamName, etc.
        """
        url = f"https://{self.TANK_HOST}/getNBATeams"
        headers = {
            "X-RapidAPI-Key": self.TANK_KEY,
            "X-RapidAPI-Host": self.TANK_HOST
        }

        try:
            r = requests.get(url, headers=headers, timeout=10)
            self.monitor.log_request('tank01', 'teams', r.headers)

            if r.status_code != 200:
                print(f"   ⚠️ Tank01 teams API returned status {r.status_code}")
                return []

            data = r.json()
            teams = data.get('body', [])

            print(f"   ✅ Fetched {len(teams)} NBA teams from Tank01")
            return teams

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)[:100]}"
            print(f"   ❌ Error fetching teams: {error_msg}")
            self.monitor.log_failed_request('tank01', 'teams', error_msg)
            return []

    def fetch_team_roster(self, team_abv: str) -> List[Dict]:
        """
        Fetch current roster for a specific team from Tank01 API.

        Args:
            team_abv: Team abbreviation (e.g., 'LAL', 'BOS', 'WAS')

        Returns:
            List of player dicts with playerID, longName, pos, etc.
        """
        url = f"https://{self.TANK_HOST}/getNBATeamRoster"
        params = {"teamAbv": team_abv}
        headers = {
            "X-RapidAPI-Key": self.TANK_KEY,
            "X-RapidAPI-Host": self.TANK_HOST
        }

        try:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            self.monitor.log_request('tank01', 'roster', r.headers)

            if r.status_code != 200:
                print(f"   ⚠️ Tank01 roster API returned status {r.status_code} for {team_abv}")
                return []

            data = r.json()
            roster = data.get('body', {}).get('roster', [])

            # Small delay to respect rate limits
            time.sleep(0.1)

            return roster

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)[:100]}"
            print(f"   ❌ Error fetching {team_abv} roster: {error_msg}")
            self.monitor.log_failed_request('tank01', 'roster', error_msg)
            return []

    def get_current_database_rosters(self) -> Dict[str, List[Dict]]:
        """
        Load current rosters from database grouped by team.

        Returns:
            Dict mapping team_abv to list of player dicts
            {
                'LAL': [{'player_id': '...', 'name': '...', 'team': 'LAL'}, ...],
                'BOS': [...],
                ...
            }
        """
        conn = self._get_conn()
        c = conn.cursor()

        c.execute('''
            SELECT player_id, name, team, position, status, base_ppg, usg_pct
            FROM players
            WHERE is_active = 1 OR is_active IS NULL
            ORDER BY team, name
        ''')

        rows = c.fetchall()
        conn.close()

        # Group by team
        rosters = {}
        for row in rows:
            team = row[2]  # team column
            player = {
                'player_id': row[0],
                'name': row[1],
                'team': row[2],
                'position': row[3],
                'status': row[4],
                'base_ppg': row[5],
                'usg_pct': row[6]
            }

            if team not in rosters:
                rosters[team] = []
            rosters[team].append(player)

        return rosters

    def compare_rosters(self, tank01_rosters: Dict[str, List[Dict]], db_rosters: Dict[str, List[Dict]]) -> Dict:
        """
        Compare Tank01 vs database rosters to detect changes.

        NOTE: Uses player NAME for matching (not player_id) because Tank01 and nba_api
        use different ID systems. Names are normalized (lowercase, stripped) for comparison.

        Args:
            tank01_rosters: Current rosters from Tank01 API (keyed by team_abv)
            db_rosters: Current rosters from database (keyed by team_abv)

        Returns:
            {
                'trades': [{'player_id': ..., 'name': ..., 'old_team': ..., 'new_team': ...}, ...],
                'signings': [{'player_id': ..., 'name': ..., 'team': ...}, ...],
                'waivers': [{'player_id': ..., 'name': ..., 'last_team': ...}, ...],
                'unchanged': [...]  # Validation count
            }
        """
        changes = {
            'trades': [],
            'signings': [],
            'waivers': [],
            'unchanged': []
        }

        def normalize_name(name):
            """Normalize player name for comparison (lowercase, stripped, no Jr./Sr./III)."""
            if not name:
                return ''
            name = name.lower().strip()
            # Remove common suffixes
            for suffix in [' jr.', ' sr.', ' iii', ' ii', ' iv']:
                name = name.replace(suffix, '')
            return name

        # Create lookup of all Tank01 players by NORMALIZED NAME
        tank01_players = {}
        for team_abv, roster in tank01_rosters.items():
            for player in roster:
                player_name = player.get('longName', '')
                if player_name:
                    normalized_name = normalize_name(player_name)
                    tank01_players[normalized_name] = {
                        'player_id': str(player.get('playerID', '')),
                        'name': player_name,
                        'team': team_abv,
                        'position': player.get('pos', 'UNK')
                    }

        # Create lookup of all database players by NORMALIZED NAME
        db_players = {}
        for team_abv, roster in db_rosters.items():
            for player in roster:
                player_name = player['name']
                if player_name:
                    normalized_name = normalize_name(player_name)
                    db_players[normalized_name] = player

        # DETECT TRADES: Player in both, but team changed
        for normalized_name, tank01_player in tank01_players.items():
            if normalized_name in db_players:
                db_player = db_players[normalized_name]
                if tank01_player['team'] != db_player['team']:
                    changes['trades'].append({
                        'player_id': db_player['player_id'],  # Use database ID
                        'name': tank01_player['name'],  # Use Tank01 name (more current)
                        'old_team': db_player['team'],
                        'new_team': tank01_player['team']
                    })
                else:
                    changes['unchanged'].append(normalized_name)

        # DETECT SIGNINGS: Player in Tank01, not in database
        for normalized_name, tank01_player in tank01_players.items():
            if normalized_name not in db_players:
                changes['signings'].append({
                    'player_id': tank01_player['player_id'],
                    'name': tank01_player['name'],
                    'team': tank01_player['team'],
                    'position': tank01_player['position']
                })

        # DETECT WAIVERS: Player in database, not in Tank01
        for normalized_name, db_player in db_players.items():
            if normalized_name not in tank01_players:
                changes['waivers'].append({
                    'player_id': db_player['player_id'],
                    'name': db_player['name'],
                    'last_team': db_player['team']
                })

        return changes

    def apply_roster_updates(self, changes: Dict, tank01_rosters: Dict[str, List[Dict]]) -> int:
        """
        Apply detected changes to database.

        Args:
            changes: Dict from compare_rosters() with trades/signings/waivers
            tank01_rosters: Current Tank01 roster data for lookups

        Returns:
            int: Total number of changes applied
        """
        from database import LudiHistorian

        historian = LudiHistorian(db_path=self.db_path)
        total_changes = 0

        # Apply TRADES
        for trade in changes['trades']:
            # Update player's team
            historian.update_player_census_v2({
                'id': trade['player_id'],
                'name': trade['name'],
                'team': trade['new_team'],
                'pos': 'UNK'  # Will be updated if available
            })

            # Log to history
            historian.log_roster_change(
                player_id=trade['player_id'],
                player_name=trade['name'],
                old_team=trade['old_team'],
                new_team=trade['new_team'],
                change_type='TRADE',
                notes=f"Detected via Tank01 API on {datetime.now().strftime('%Y-%m-%d')}"
            )

            total_changes += 1
            print(f"      TRADE: {trade['name']} ({trade['old_team']} → {trade['new_team']})")

        # Apply SIGNINGS
        for signing in changes['signings']:
            # Add new player
            historian.update_player_census_v2({
                'id': signing['player_id'],
                'name': signing['name'],
                'team': signing['team'],
                'pos': signing.get('position', 'UNK')
            })

            # Log to history
            historian.log_roster_change(
                player_id=signing['player_id'],
                player_name=signing['name'],
                old_team=None,
                new_team=signing['team'],
                change_type='SIGNING',
                notes=f"New player detected via Tank01 API on {datetime.now().strftime('%Y-%m-%d')}"
            )

            total_changes += 1
            print(f"      SIGNING: {signing['name']} → {signing['team']}")

        # Apply WAIVERS (mark as inactive)
        for waiver in changes['waivers']:
            # Mark player as inactive
            conn = self._get_conn()
            c = conn.cursor()
            c.execute('''
                UPDATE players
                SET is_active = 0, roster_updated_at = CURRENT_TIMESTAMP
                WHERE player_id = ?
            ''', (waiver['player_id'],))
            conn.commit()
            conn.close()

            # Log to history
            historian.log_roster_change(
                player_id=waiver['player_id'],
                player_name=waiver['name'],
                old_team=waiver['last_team'],
                new_team=None,
                change_type='WAIVED',
                notes=f"Player no longer on any roster (Tank01 API {datetime.now().strftime('%Y-%m-%d')})"
            )

            total_changes += 1
            print(f"      WAIVED: {waiver['name']} (last team: {waiver['last_team']})")

        return total_changes

    def generate_validation_report(self, changes: Dict, db_player_count: int, tank01_player_count: int) -> str:
        """
        Generate human-readable validation report.

        Args:
            changes: Dict from compare_rosters()
            db_player_count: Total players in database before update
            tank01_player_count: Total players in Tank01 rosters

        Returns:
            str: Formatted console report
        """
        report_lines = [
            "",
            "=" * 50,
            "   >>> ROSTER VALIDATION REPORT <<<",
            "=" * 50,
            "",
            f"DATABASE STATE (Before):",
            f"  - Total Players: {db_player_count}",
            "",
            f"TANK01 STATE (Current):",
            f"  - Total Players: {tank01_player_count}",
            f"  - Fetched: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "CHANGES DETECTED:",
            ""
        ]

        # Trades section
        if changes['trades']:
            report_lines.append(f"[TRADES] {len(changes['trades'])} players changed teams")
            for trade in changes['trades']:
                report_lines.append(f"  • {trade['name']}: {trade['old_team']} → {trade['new_team']}")
            report_lines.append("")
        else:
            report_lines.append("[TRADES] 0 players changed teams")
            report_lines.append("")

        # Signings section
        if changes['signings']:
            report_lines.append(f"[SIGNINGS] {len(changes['signings'])} new players")
            for signing in changes['signings']:
                report_lines.append(f"  • {signing['name']} ({signing['team']})")
            report_lines.append("")
        else:
            report_lines.append("[SIGNINGS] 0 new players")
            report_lines.append("")

        # Waivers section
        if changes['waivers']:
            report_lines.append(f"[WAIVERS] {len(changes['waivers'])} players removed from rosters")
            for waiver in changes['waivers']:
                report_lines.append(f"  • {waiver['name']} (last team: {waiver['last_team']})")
            report_lines.append("")
        else:
            report_lines.append("[WAIVERS] 0 players removed")
            report_lines.append("")

        # Summary
        total_changes = len(changes['trades']) + len(changes['signings']) + len(changes['waivers'])
        report_lines.extend([
            "SUMMARY:",
            f"  ✅ {total_changes} total changes detected",
            f"  📊 API Usage: 31 requests (3.1% of daily quota)",
            f"  💰 Estimated Cost: $0.0103",
            "",
            "=" * 50
        ])

        return "\n".join(report_lines)

    def validate_and_update(self, dry_run=False) -> Dict:
        """
        Main orchestration method - validates rosters and optionally applies updates.

        Args:
            dry_run: If True, preview changes without applying to database

        Returns:
            {
                'changes': {...},
                'report': "...",
                'report_file': "/path/to/report.json"
            }
        """
        print("\n" + "=" * 50)
        print("   >>> ROSTER VALIDATION CYCLE <<<")
        print("=" * 50)

        # 1. Fetch all team rosters from Tank01 (31 API calls)
        print("\n   [1/5] Fetching NBA teams...")
        teams = self.fetch_all_nba_teams()

        if not teams:
            print("   ❌ Failed to fetch teams. Aborting validation.")
            return {
                'changes': {'trades': [], 'signings': [], 'waivers': [], 'unchanged': []},
                'report': "Failed to fetch teams from Tank01 API",
                'report_file': None
            }

        print(f"   [2/5] Fetching rosters for {len(teams)} teams...")
        tank01_rosters = {}
        for i, team in enumerate(teams, 1):
            team_abv = team.get('teamAbv', '')
            if team_abv:
                print(f"         ({i}/{len(teams)}) {team_abv}...", end=" ")
                roster = self.fetch_team_roster(team_abv)
                tank01_rosters[team_abv] = roster
                print(f"{len(roster)} players")

        # 2. Load database rosters
        print("\n   [3/5] Loading database rosters...")
        db_rosters = self.get_current_database_rosters()
        db_player_count = sum(len(roster) for roster in db_rosters.values())
        tank01_player_count = sum(len(roster) for roster in tank01_rosters.values())

        print(f"         Database: {db_player_count} players across {len(db_rosters)} teams")
        print(f"         Tank01: {tank01_player_count} players across {len(tank01_rosters)} teams")

        # 3. Compare and detect changes
        print("\n   [4/5] Comparing rosters...")
        changes = self.compare_rosters(tank01_rosters, db_rosters)

        # 4. Apply updates (or preview if dry_run)
        print(f"\n   [5/5] {'Previewing' if dry_run else 'Applying'} changes...")
        if not dry_run:
            count = self.apply_roster_updates(changes, tank01_rosters)
            print(f"\n   ✅ {count} roster updates applied to database")
        else:
            total_changes = len(changes['trades']) + len(changes['signings']) + len(changes['waivers'])
            print(f"\n   🔍 DRY RUN: {total_changes} changes detected (not applied)")

        # 5. Generate report
        report = self.generate_validation_report(changes, db_player_count, tank01_player_count)

        # 6. Save to JSON
        report_data = {
            'validation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'dry_run': dry_run,
            'database_snapshot': {
                'total_players': db_player_count,
                'teams': len(db_rosters)
            },
            'tank01_snapshot': {
                'total_players': tank01_player_count,
                'teams': len(tank01_rosters)
            },
            'changes': changes,
            'summary': {
                'total_changes': len(changes['trades']) + len(changes['signings']) + len(changes['waivers']),
                'trades': len(changes['trades']),
                'signings': len(changes['signings']),
                'waivers': len(changes['waivers']),
                'api_calls': 31,
                'cost': '$0.0103'
            }
        }

        report_file = os.path.join(
            self.logs_dir,
            f"{datetime.now().strftime('%Y-%m-%d')}_roster_validation.json"
        )

        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)

        print(f"\n   📄 Detailed report saved: {report_file}")

        return {
            'changes': changes,
            'report': report,
            'report_file': report_file
        }


# ============================================================================
# SINGLETON PATTERN
# ============================================================================

_roster_validator_instance = None


def get_roster_validator() -> RosterValidator:
    """
    Get or create the singleton RosterValidator instance.

    Returns:
        RosterValidator: The singleton instance
    """
    global _roster_validator_instance
    if _roster_validator_instance is None:
        _roster_validator_instance = RosterValidator()
    return _roster_validator_instance


# ============================================================================
# MODULE TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("   ROSTER VALIDATOR MODULE TEST")
    print("=" * 60)

    validator = get_roster_validator()

    # Test dry-run
    results = validator.validate_and_update(dry_run=True)

    print(results['report'])
    print(f"\n✅ Test complete. Review report at: {results['report_file']}")
