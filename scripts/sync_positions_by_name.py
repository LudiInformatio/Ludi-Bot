#!/usr/bin/env python3
"""
Sync Player Positions from Tank01 API (Name-Based Matching)

Purpose: Populate the `position` column in the players table using name matching
         to work around Tank01 composite ID vs NBA ID mismatch.

Usage:
    python scripts/sync_positions_by_name.py

Output:
    - Updates players.position in ludi.db
    - Prints summary of position assignments

Author: Ludi Informatio
Date: February 2, 2026
"""

import os
import sys
import json
import requests
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import config
import sqlite3

class PositionSyncerByName:
    def __init__(self):
        self.api_key = config.TANK01_KEY
        self.base_url = "https://tank01-fantasy-stats.p.rapidapi.com"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "tank01-fantasy-stats.p.rapidapi.com"
        }

        # NBA team abbreviations (30 teams)
        self.teams = [
            'ATL', 'BOS', 'BRK', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW',
            'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOP', 'NYK',
            'OKC', 'ORL', 'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS'
        ]

        self.stats = {
            'total_players_api': 0,
            'total_players_db': 0,
            'positions_updated': 0,
            'positions_unchanged': 0,
            'positions_missing_api': 0,
            'players_not_found_db': 0,
            'by_position': {}
        }

        # Store position data from API
        self.player_positions = {}  # name -> position

    def fetch_team_roster(self, team_abv: str) -> list:
        """
        Fetch roster for a single team from Tank01.

        Args:
            team_abv: Team abbreviation (e.g., 'LAL')

        Returns:
            List of player dicts with position data
        """
        url = f"{self.base_url}/getNBATeamRoster"
        params = {
            'teamAbv': team_abv,
            'getStats': 'false'
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            roster = data.get('body', {}).get('roster', [])

            return roster

        except requests.exceptions.RequestException as e:
            print(f"      ❌ Error fetching {team_abv} roster: {e}")
            return []

    def fetch_all_positions(self) -> dict:
        """
        Fetch positions for all 30 NBA teams and build name -> position mapping.

        Returns:
            Dict mapping player_name -> normalized_position
        """
        print("=" * 80)
        print("FETCHING ROSTERS FROM TANK01 API")
        print("=" * 80)

        positions = {}

        for i, team in enumerate(self.teams, 1):
            print(f"  [{i:2d}/30] Fetching {team}...", end=' ')
            roster = self.fetch_team_roster(team)

            if roster:
                print(f"✅ {len(roster)} players")

                for player in roster:
                    name = player.get('longName', '').strip()
                    raw_pos = player.get('pos', '')

                    if name and raw_pos:
                        self.stats['total_players_api'] += 1
                        normalized_pos = self.normalize_position(raw_pos)
                        positions[name] = normalized_pos

            else:
                print("⚠️  No data")

        print(f"\n✅ Fetched {len(positions)} player positions from API")
        print()
        return positions

    def normalize_position(self, pos: str) -> str:
        """
        Normalize position strings from Tank01.

        Args:
            pos: Raw position string from Tank01

        Returns:
            Normalized position (G, F, C, G-F, F-C)
        """
        if not pos or pos == 'UNK':
            return 'UNK'

        pos = pos.upper().strip()

        # Map specific positions to generic
        position_map = {
            'PG': 'G',
            'SG': 'G',
            'SF': 'F',
            'PF': 'F',
            'C': 'C',
            'G': 'G',
            'F': 'F',
            'G-F': 'G-F',
            'F-G': 'G-F',
            'F-C': 'F-C',
            'C-F': 'F-C'
        }

        return position_map.get(pos, pos)

    def update_database_positions(self, positions: dict):
        """
        Update player positions in database using name-based matching.

        Args:
            positions: Dict of player_name -> normalized_position
        """
        print("=" * 80)
        print("UPDATING DATABASE (Name-Based Matching)")
        print("=" * 80)

        conn = sqlite3.connect('ludi.db')
        c = conn.cursor()

        # Get all active players from database
        c.execute('SELECT name, position FROM players WHERE is_active = 1')
        db_players = c.fetchall()

        self.stats['total_players_db'] = len(db_players)
        print(f"Database players (active): {self.stats['total_players_db']}\n")

        for db_name, current_pos in db_players:
            # Try exact match first
            new_pos = positions.get(db_name)

            if not new_pos:
                # Try fuzzy match (common issue: "Jr." vs "Jr")
                for api_name, pos in positions.items():
                    if self.names_match(db_name, api_name):
                        new_pos = pos
                        break

            if not new_pos:
                # Player not found in API data
                self.stats['players_not_found_db'] += 1
                if current_pos == 'UNK':
                    print(f"  ⚠️  {db_name}: Not found in API")
                continue

            if new_pos == 'UNK':
                self.stats['positions_missing_api'] += 1
                continue

            # Update if position changed
            if current_pos != new_pos:
                c.execute('''
                    UPDATE players
                    SET position = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE name = ?
                ''', (new_pos, db_name))

                self.stats['positions_updated'] += 1
                self.stats['by_position'][new_pos] = self.stats['by_position'].get(new_pos, 0) + 1
                print(f"  ✅ {db_name}: {current_pos} → {new_pos}")
            else:
                self.stats['positions_unchanged'] += 1

        conn.commit()
        conn.close()

        print(f"\n✅ Database updated!")

    def names_match(self, name1: str, name2: str) -> bool:
        """
        Check if two names match (handling Jr/Jr. variations).

        Args:
            name1: First name
            name2: Second name

        Returns:
            True if names match
        """
        # Normalize both names
        n1 = name1.replace('.', '').replace('  ', ' ').strip().lower()
        n2 = name2.replace('.', '').replace('  ', ' ').strip().lower()

        return n1 == n2

    def print_summary(self):
        """Print summary statistics."""
        print("\n" + "=" * 80)
        print("POSITION SYNC SUMMARY")
        print("=" * 80)
        print(f"API Players Fetched: {self.stats['total_players_api']}")
        print(f"Database Players (Active): {self.stats['total_players_db']}")
        print(f"Positions Updated: {self.stats['positions_updated']}")
        print(f"Positions Unchanged: {self.stats['positions_unchanged']}")
        print(f"Players Not Found in API: {self.stats['players_not_found_db']}")
        print(f"Positions Missing from API: {self.stats['positions_missing_api']}")

        if self.stats['by_position']:
            print("\nUpdated Position Distribution:")
            for pos in sorted(self.stats['by_position'].keys()):
                count = self.stats['by_position'][pos]
                print(f"  {pos:5s}: {count:3d} players")

        # Calculate final coverage
        updated_count = self.stats['positions_updated']
        total_db = self.stats['total_players_db']
        coverage_pct = (updated_count / total_db * 100) if total_db > 0 else 0

        print(f"\nPosition Coverage: {updated_count}/{total_db} ({coverage_pct:.1f}%)")
        print("=" * 80)

    def run(self):
        """Execute the full position sync process."""
        print("\n" + "=" * 80)
        print("PLAYER POSITION SYNC (Tank01 → Database) - NAME MATCHING")
        print("=" * 80)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Step 1: Fetch positions from API
        positions = self.fetch_all_positions()

        if not positions:
            print("❌ No positions fetched from API. Exiting.")
            return

        # Step 2: Update database
        self.update_database_positions(positions)

        # Step 3: Print summary
        self.print_summary()

        print("\n✅ Position sync complete!")


def main():
    syncer = PositionSyncerByName()
    syncer.run()


if __name__ == '__main__':
    main()
