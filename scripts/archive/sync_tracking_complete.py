#!/usr/bin/env python3
"""
LUDI INFORMATIO | COMPLETE TRACKING DATA SYNC
==============================================
Syncs all tracking stats for 60-day window:
- Shot types (drives, catch & shoot, pull-up) per game
- Shot difficulty (contested, open, defender distance) per game  
- Speed/distance (season aggregate)
- Defensive matchups per game

Usage:
    ./venv/bin/python scripts/sync_tracking_complete.py --season 2025-26 --start-date 2025-11-14 --end-date 2026-01-13

Estimated time: ~2.8 hours
"""

import sys
import os
import sqlite3
import json
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.nba_api_client import get_nba_client

class TrackingSyncEngine:
    def __init__(self, season: str, start_date: str, end_date: str):
        self.season = season
        self.start_date = start_date
        self.end_date = end_date
        self.client = get_nba_client()
        self.db_path = 'ludi.db'
        self.progress_file = 'logs/tracking_sync_progress.json'
        
       # Ensure logs directory
        os.makedirs('logs', exist_ok=True)
        
        # Load progress
        self.progress = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """Load sync progress from file."""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            'players_synced': [],
            'games_synced': [],
            'speed_synced': False,
            'started_at': datetime.now().isoformat()
        }
    
    def _save_progress(self):
        """Save current progress."""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def get_target_players(self) -> List[Dict]:
        """Get all players with games in the target window."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT DISTINCT player_name, team_abbreviation, COUNT(*) as games
            FROM player_game_logs
            WHERE game_date >= ? AND game_date <= ?
            GROUP BY player_name
            HAVING games >= 3
            ORDER BY games DESC
        ''', (self.start_date, self.end_date))
        
        players = []
        for row in c.fetchall():
            nba_player_id = self.client.get_player_id(row[0])
            if nba_player_id:
                players.append({
                    'name': row[0],
                    'team': row[1],
                    'nba_id': nba_player_id,
                    'games': row[2]
                })
        
        conn.close()
        return players
    
    def get_player_games(self, player_name: str) -> List[Dict]:
        """Get all games for a player in the target window."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT DISTINCT game_date, game_id
            FROM player_game_logs
            WHERE player_name = ? AND game_date >= ? AND game_date <= ?
            ORDER BY game_date
        ''', (player_name, self.start_date, self.end_date))
        
        games = [{'date': row[0], 'tank_id': row[1]} for row in c.fetchall()]
        conn.close()
        return games
    
    def sync_player_game_tracking(self, player: Dict):
        """Sync shot types and difficulty for all player games."""
        games = self.get_player_games(player['name'])
        
        print(f"\n[{player['name']}] Syncing {len(games)} games...")
        
        for i, game in enumerate(games, 1):
            # Check if already synced
            if f"{player['nba_id']}_{game['date']}" in self.progress.get('players_synced', []):
                print(f"   [{i}/{len(games)}] {game['date']} - skipped (already synced)")
                continue
            
            # Fetch data with single-day date filter
            try:
                splits = self.client.get_player_shooting_splits(
                    player['nba_id'],
                    season=self.season,
                    date_from=self._format_date(game['date']),
                    date_to=self._format_date(game['date'])
                )
                
                difficulty = self.client.get_player_shot_difficulty(
                    player['nba_id'],
                    season=self.season,
                    date_from=self._format_date(game['date']),
                    date_to=self._format_date(game['date'])
                )
                
                # Parse and insert
                self._insert_game_tracking(player, game, splits, difficulty)
                
                # Mark as synced
                self.progress['players_synced'].append(f"{player['nba_id']}_{game['date']}")
                
                print(f"   [{i}/{len(games)}] {game['date']} - ✓")
                
                # Save progress every 10 games
                if i % 10 == 0:
                    self._save_progress()
                    
            except Exception as e:
                print(f"   [{i}/{len(games)}] {game['date']} - ERROR: {e}")
                continue
    
    def _format_date(self, date_str: str) -> str:
        """Convert YYYY-MM-DD to MM/DD/YYYY for nba_api."""
        parts = date_str.split('-')
        return f"{parts[1]}/{parts[2]}/{parts[0]}"
    
    def _insert_game_tracking(self, player: Dict, game: Dict, splits: Dict, difficulty: Dict):
        """Insert parsed tracking data into database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Parse shot types
        shot_type = splits.get('shot_type', {})
        shot_data = shot_type.get('data', [])
        headers = shot_type.get('headers', [])
        
        drives_fga = drives_fgm = 0
        catch_shoot_fga = catch_shoot_fgm = 0
        pull_up_fga = pull_up_fgm = 0
        
        if headers and shot_data:
            try:
                group_idx = headers.index('GROUP_VALUE')
                fga_idx = headers.index('FGA')
                fgm_idx = headers.index('FGM')
                
                for row in shot_data:
                    shot_type_name = str(row[group_idx]).lower()
                    if 'drive' in shot_type_name or 'driving' in shot_type_name:
                        drives_fga += row[fga_idx] or 0
                        drives_fgm += row[fgm_idx] or 0
                    elif 'catch' in shot_type_name:
                        catch_shoot_fga += row[fga_idx] or 0
                        catch_shoot_fgm += row[fgm_idx] or 0
                    elif 'pull' in shot_type_name or 'pullup' in shot_type_name:
                        pull_up_fga += row[fga_idx] or 0
                        pull_up_fgm += row[fgm_idx] or 0
            except (ValueError, IndexError) as e:
                print(f"      Warning: Could not parse shot types: {e}")
        
        # Parse shot difficulty - uses CLOSE_DEF_DIST_RANGE column
        closest_def = difficulty.get('closest_defender', {})
        def_data = closest_def.get('data', [])
        def_headers = closest_def.get('headers', [])
        
        contested_fga = tight_fga = open_fga = wide_open_fga = 0
        avg_def_dist = 0
        
        if def_headers and def_data:
            try:
                # Use CLOSE_DEF_DIST_RANGE for defender distance category
                group_col = 'CLOSE_DEF_DIST_RANGE' if 'CLOSE_DEF_DIST_RANGE' in def_headers else 'GROUP_VALUE'
                group_idx = def_headers.index(group_col)
                fga_idx = def_headers.index('FGA')
                
                for row in def_data:
                    category = str(row[group_idx]).lower()
                    fga = row[fga_idx] or 0
                    
                    # Very Tight (0-2 feet) and Tight (2-4 feet) = contested
                    if '0-2' in category or 'very tight' in category:
                        contested_fga += fga
                    elif '2-4' in category or ('tight' in category and 'very' not in category):
                        tight_fga += fga
                        contested_fga += fga  # Count 2-4 as contested too
                    elif '4-6' in category or 'open' in category:
                        if 'wide' not in category:
                            open_fga += fga
                    elif '6+' in category or '6 ft' in category or 'wide open' in category:
                        wide_open_fga += fga
            except (ValueError, IndexError) as e:
                print(f"      Warning: Could not parse shot difficulty: {e}")
        
        # Insert
        c.execute('''
            INSERT OR REPLACE INTO player_game_tracking (
                nba_player_id, player_name, nba_game_id, game_date, team_abbr,
                drives_fga, drives_fgm, catch_shoot_fga, catch_shoot_fgm,
                pull_up_fga, pull_up_fgm, contested_fga, tight_fga,
                open_fga, wide_open_fga, avg_defender_dist, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            player['nba_id'], player['name'], 'UNKNOWN', game['date'], player['team'],
            drives_fga, drives_fgm, catch_shoot_fga, catch_shoot_fgm,
            pull_up_fga, pull_up_fgm, contested_fga, tight_fga,
            open_fga, wide_open_fga, avg_def_dist,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def sync_speed_stats(self):
        """Sync league-wide speed/distance stats."""
        if self.progress.get('speed_synced'):
            print("\n[SPEED STATS] Already synced, skipping...")
            return
        
        print("\n[SPEED STATS] Fetching league-wide data...")
        
        try:
            # Add method if not exists
            from nba_api.stats.endpoints import leaguedashptstats
            
            response = leaguedashptstats.LeagueDashPtStats(
                season=self.season,
                per_mode_simple='PerGame',
                pt_measure_type='SpeedDistance',
                player_or_team='Player',
                headers=self.client.headers,
                timeout=30
            )
            
            data = response.get_dict()
            result_sets = data.get('resultSets', [])
            
            if not result_sets:
                print("   No data returned")
                return
            
            headers = result_sets[0].get('headers', [])
            rows = result_sets[0].get('rowSet', [])
            
            print(f"   Processing {len(rows)} players...")
            
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            for row in rows:
                try:
                    player_id = row[headers.index('PLAYER_ID')]
                    player_name = row[headers.index('PLAYER_NAME')]
                    team = row[headers.index('TEAM_ABBREVIATION')]
                    games = row[headers.index('GP')]
                    minutes = row[headers.index('MIN')]
                    
                    # Get speed/distance fields (check if columns exist)
                    dist_miles = row[headers.index('DIST_MILES')] if 'DIST_MILES' in headers else 0
                    dist_off = row[headers.index('DIST_MILES_OFF')] if 'DIST_MILES_OFF' in headers else 0
                    dist_def = row[headers.index('DIST_MILES_DEF')] if 'DIST_MILES_DEF' in headers else 0
                    avg_speed = row[headers.index('AVG_SPEED')] if 'AVG_SPEED' in headers else 0
                    avg_speed_off = row[headers.index('AVG_SPEED_OFF')] if 'AVG_SPEED_OFF' in headers else 0
                    avg_speed_def = row[headers.index('AVG_SPEED_DEF')] if 'AVG_SPEED_DEF' in headers else 0
                    
                    c.execute('''
                        INSERT OR REPLACE INTO player_speed_stats (
                            nba_player_id, player_name, team_abbr, season,
                            games_played, avg_minutes, dist_miles, dist_miles_off,
                            dist_miles_def, avg_speed, avg_speed_off, avg_speed_def,
                            synced_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        player_id, player_name, team, self.season,
                        games, minutes, dist_miles, dist_off, dist_def,
                        avg_speed, avg_speed_off, avg_speed_def,
                        datetime.now().isoformat()
                    ))
                except Exception as e:
                    print(f"   Error processing {row[1]}: {e}")
                    continue
            
            conn.commit()
            conn.close()
            
            self.progress['speed_synced'] = True
            self._save_progress()
            
            print(f"   ✓ Synced {len(rows)} players")
            
        except Exception as e:
            print(f"   ERROR: {e}")
    
    def run(self):
        """Execute full sync."""
        print("=" * 70)
        print("LUDI INFORMATIO: COMPLETE TRACKING DATA SYNC")
        print(f"Season: {self.season}")
        print(f"Window: {self.start_date} to {self.end_date}")
        print("=" * 70)
        
        # Get players
        players = self.get_target_players()
        print(f"\n📊 Found {len(players)} players with 3+ games in window")
        
        # Sync per-game tracking
        print("\n" + "=" * 70)
        print("PHASE 1: PER-GAME TRACKING (SHOT TYPES + DIFFICULTY)")
        print("=" * 70)
        
        for i, player in enumerate(players, 1):
            print(f"\n[{i}/{len(players)}] {player['name']} ({player['games']} games)")
            self.sync_player_game_tracking(player)
        
        # Sync speed stats
        print("\n" + "=" * 70)
        print("PHASE 2: SPEED/DISTANCE STATS (LEAGUE-WIDE)")
        print("=" * 70)
        self.sync_speed_stats()
        
        # Summary
        print("\n" + "=" * 70)
        print("SYNC COMPLETE!")
        print("=" * 70)
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM player_game_tracking")
        tracking_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM player_speed_stats")
        speed_count = c.fetchone()[0]
        
        conn.close()
        
        print(f"\nRecords created:")
        print(f"  player_game_tracking: {tracking_count}")
        print(f"  player_speed_stats: {speed_count}")
        print(f"\nProgress file: {self.progress_file}")
        print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description='Sync tracking stats')
    parser.add_argument('--season', default='2025-26', help='NBA season')
    parser.add_argument('--start-date', default='2025-11-14', help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', default='2026-01-13', help='End date (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    engine = TrackingSyncEngine(args.season, args.start_date, args.end_date)
    engine.run()

if __name__ == "__main__":
    main()
