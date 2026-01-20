#!/usr/bin/env python3
"""
Sync Player Positions from Tank01 API

Purpose: Populate the `position` column in the players table with accurate position data
         from Tank01's roster endpoint.

Usage:
    python scripts/sync_player_positions.py

Output:
    - Updates players.position in ludi.db
    - Prints summary of position assignments
    - Creates log file in logs/position_sync/

Author: Ludi Informatio
Date: January 20, 2026
"""

import os
import sys
import json
import requests
import sqlite3
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from config import TANK01_KEY
except ImportError:
    print("⚠️  Warning: Could not import TANK01_KEY from config. Using environment variable.")
    TANK01_KEY = os.getenv('TANK01_KEY')

class PositionSyncer:
    def __init__(self):
        self.api_key = TANK01_KEY
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
            'total_players': 0,
            'positions_updated': 0,
            'positions_unchanged': 0,
            'positions_missing': 0,
            'by_position': {}
        }
    
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
            'getStats': 'false'  # We only need roster data, not stats
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
    
    def fetch_all_rosters(self) -> dict:
        """
        Fetch rosters for all 30 NBA teams.
        
        Returns:
            Dict mapping team_abv -> list of players
        """
        print("=" * 80)
        print("FETCHING ROSTERS FROM TANK01 API")
        print("=" * 80)
        
        rosters = {}
        
        for i, team in enumerate(self.teams, 1):
            print(f"  [{i:2d}/30] Fetching {team}...", end=' ')
            roster = self.fetch_team_roster(team)
            
            if roster:
                rosters[team] = roster
                print(f"✅ {len(roster)} players")
            else:
                print("⚠️  No data")
        
        print()
        return rosters
    
    def normalize_position(self, pos: str) -> str:
        """
        Normalize position strings from Tank01.
        
        Tank01 positions can be:
        - Single: 'G', 'F', 'C'
        - Combo: 'G-F', 'F-G', 'F-C', 'C-F'
        - Multiple: 'PG', 'SG', 'SF', 'PF', 'C'
        
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
            'F-G': 'G-F',  # Normalize to G-F
            'F-C': 'F-C',
            'C-F': 'F-C'   # Normalize to F-C
        }
        
        return position_map.get(pos, pos)
    
    def update_player_position(self, player_id: str, name: str, position: str, team: str) -> bool:
        """
        Update a single player's position in the database.
        
        Args:
            player_id: Player ID
            name: Player name
            position: Normalized position
            team: Team abbreviation
        
        Returns:
            True if updated, False if unchanged
        """
        conn = sqlite3.connect('ludi.db')
        c = conn.cursor()
        
        # Check current position
        c.execute('SELECT position FROM players WHERE player_id = ?', (player_id,))
        row = c.fetchone()
        
        if not row:
            # Player doesn't exist - skip (shouldn't happen if roster is synced)
            conn.close()
            return False
        
        current_pos = row[0]
        
        # Update if position changed or was unknown
        if current_pos != position:
            c.execute('''
                UPDATE players
                SET position = ?, updated_at = CURRENT_TIMESTAMP
                WHERE player_id = ?
            ''', (position, player_id))
            
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
    
    def sync_positions(self, rosters: dict):
        """
        Sync positions from Tank01 rosters to database.
        
        Args:
            rosters: Dict of team_abv -> player list
        """
        print("=" * 80)
        print("SYNCING POSITIONS TO DATABASE")
        print("=" * 80)
        
        for team_abv, roster in rosters.items():
            print(f"\n  {team_abv}:")
            
            for player in roster:
                player_id = str(player.get('playerID', ''))
                name = player.get('longName', '')
                raw_pos = player.get('pos', 'UNK')
                
                if not player_id or not name:
                    continue
                
                self.stats['total_players'] += 1
                
                # Normalize position
                position = self.normalize_position(raw_pos)
                
                if position == 'UNK':
                    self.stats['positions_missing'] += 1
                    print(f"    ⚠️  {name}: No position data")
                    continue
                
                # Update database
                updated = self.update_player_position(player_id, name, position, team_abv)
                
                if updated:
                    self.stats['positions_updated'] += 1
                    print(f"    ✅ {name}: {raw_pos} → {position}")
                    
                    # Track position distribution
                    self.stats['by_position'][position] = self.stats['by_position'].get(position, 0) + 1
                else:
                    self.stats['positions_unchanged'] += 1
    
    def print_summary(self):
        """Print summary statistics."""
        print("\n" + "=" * 80)
        print("POSITION SYNC SUMMARY")
        print("=" * 80)
        print(f"Total Players Processed: {self.stats['total_players']}")
        print(f"Positions Updated: {self.stats['positions_updated']}")
        print(f"Positions Unchanged: {self.stats['positions_unchanged']}")
        print(f"Positions Missing: {self.stats['positions_missing']}")
        
        print("\nPosition Distribution:")
        for pos in sorted(self.stats['by_position'].keys()):
            count = self.stats['by_position'][pos]
            pct = count / self.stats['total_players'] * 100 if self.stats['total_players'] > 0 else 0
            print(f"  {pos:5s}: {count:3d} players ({pct:.1f}%)")
        
        print("\n" + "=" * 80)
    
    def save_log(self):
        """Save sync log to file."""
        log_dir = 'logs/position_sync'
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        log_path = f"{log_dir}/{timestamp}_position_sync.json"
        
        log_data = {
            'timestamp': timestamp,
            'stats': self.stats
        }
        
        with open(log_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        print(f"📄 Log saved to: {log_path}")
    
    def run(self):
        """Execute the full position sync process."""
        print("\n" + "=" * 80)
        print("PLAYER POSITION SYNC (Tank01 → Database)")
        print("=" * 80)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Step 1: Fetch rosters
        rosters = self.fetch_all_rosters()
        
        if not rosters:
            print("❌ No rosters fetched. Exiting.")
            return
        
        # Step 2: Sync positions
        self.sync_positions(rosters)
        
        # Step 3: Print summary
        self.print_summary()
        
        # Step 4: Save log
        self.save_log()
        
        print("\n✅ Position sync complete!")


def main():
    syncer = PositionSyncer()
    syncer.run()


if __name__ == '__main__':
    main()
