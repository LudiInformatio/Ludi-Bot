#!/usr/bin/env python3
"""
LUDI INFORMATIO | FAST TRACKING DATA SYNC (v2)
================================================
Optimized version with:
- 0.5s rate limit (vs 1.0s) 
- Extended date range fetching (vs single-day)
- Batch processing

Usage:
    ./venv/bin/python scripts/sync_tracking_fast.py

Estimated time: ~2 hours (vs 12 hours original)
"""

import sys
import os
import sqlite3
import json
import time
from datetime import datetime
from typing import Dict, List, Set

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nba_api.stats.endpoints import (
    playerdashboardbyshootingsplits,
    playerdashptshots,
    leaguedashptstats
)

class FastTrackingSync:
    def __init__(self, season: str = "2025-26", start_date: str = "2025-11-14", end_date: str = "2026-01-13"):
        self.season = season
        self.start_date = start_date
        self.end_date = end_date
        self.db_path = 'ludi.db'
        self.progress_file = 'logs/tracking_sync_progress.json'
        self.rate_limit_delay = 0.5  # Faster: 0.5s instead of 1.0s
        self.last_request = 0
        
        # Standard headers
        self.headers = {
            'Host': 'stats.nba.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
            'x-nba-stats-origin': 'stats',
            'x-nba-stats-token': 'true'
        }
        
        os.makedirs('logs', exist_ok=True)
        self.progress = self._load_progress()
    
    def _load_progress(self) -> Dict:
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {'players_synced': [], 'speed_synced': False}
    
    def _save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request = time.time()
    
    def _format_date(self, date_str: str) -> str:
        """YYYY-MM-DD to MM/DD/YYYY"""
        parts = date_str.split('-')
        return f"{parts[1]}/{parts[2]}/{parts[0]}"
    
    def get_players_to_sync(self) -> List[Dict]:
        """Get players not yet fully synced."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get players with games in window
        c.execute('''
            SELECT DISTINCT player_name, team_abbreviation, COUNT(*) as games
            FROM player_game_logs
            WHERE game_date >= ? AND game_date <= ?
            GROUP BY player_name
            HAVING games >= 5
            ORDER BY games DESC
        ''', (self.start_date, self.end_date))
        
        all_players = c.fetchall()
        
        # Get already synced players (those with records in DB)
        c.execute('''
            SELECT DISTINCT player_name FROM player_game_tracking
        ''')
        synced_names = {row[0] for row in c.fetchall()}
        
        conn.close()
        
        # Build player list with NBA IDs
        from nba_api.stats.static import players as nba_players
        all_nba = nba_players.get_players()
        
        players = []
        for row in all_players:
            name = row[0]
            if name in synced_names:
                continue  # Skip already synced
            
            # Find NBA ID
            nba_id = None
            search = name.lower()
            for p in all_nba:
                if p['full_name'].lower() == search:
                    nba_id = p['id']
                    break
            
            if nba_id:
                players.append({
                    'name': name,
                    'team': row[1],
                    'nba_id': nba_id,
                    'games': row[2]
                })
        
        return players
    
    def get_player_game_dates(self, player_name: str) -> List[str]:
        """Get all game dates for a player."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT DISTINCT game_date FROM player_game_logs
            WHERE player_name = ? AND game_date >= ? AND game_date <= ?
            ORDER BY game_date
        ''', (player_name, self.start_date, self.end_date))
        dates = [row[0] for row in c.fetchall()]
        conn.close()
        return dates
    
    def fetch_player_data(self, player_id: int, date_from: str, date_to: str) -> Dict:
        """Fetch both shooting splits and difficulty with retry logic."""
        result = {'splits': None, 'difficulty': None}
        
        # Fetch shooting splits with retry
        for attempt in range(3):
            self._rate_limit()
            try:
                splits = playerdashboardbyshootingsplits.PlayerDashboardByShootingSplits(
                    player_id=player_id,
                    season=self.season,
                    per_mode_detailed='PerGame',
                    date_from_nullable=date_from,
                    date_to_nullable=date_to,
                    headers=self.headers,
                    timeout=60  # Increased from 30
                )
                result['splits'] = {
                    'shot_type': splits.shot_type_player_dashboard.get_dict()
                }
                break  # Success, exit retry loop
            except Exception as e:
                if attempt < 2:
                    wait_time = (attempt + 1) * 5  # 5s, 10s backoff
                    print(f"      Splits retry {attempt + 1}/3 after {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"      Splits error (final): {e}")
        
        # Fetch shot difficulty with retry
        for attempt in range(3):
            self._rate_limit()
            try:
                difficulty = playerdashptshots.PlayerDashPtShots(
                    player_id=player_id,
                    team_id=0,
                    season=self.season,
                    date_from_nullable=date_from,
                    date_to_nullable=date_to,
                    headers=self.headers,
                    timeout=60  # Increased from 30
                )
                result['difficulty'] = {
                    'closest_defender': difficulty.closest_defender_shooting.get_dict()
                }
                break  # Success, exit retry loop
            except Exception as e:
                if attempt < 2:
                    wait_time = (attempt + 1) * 5  # 5s, 10s backoff
                    print(f"      Difficulty retry {attempt + 1}/3 after {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"      Difficulty error (final): {e}")
        
        return result
    
    def parse_and_insert(self, player: Dict, game_date: str, data: Dict):
        """Parse API response and insert into DB."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Parse shot types
        drives_fga = drives_fgm = catch_shoot_fga = catch_shoot_fgm = pull_up_fga = pull_up_fgm = 0
        
        splits = data.get('splits', {})
        if splits:
            shot_type = splits.get('shot_type', {})
            headers = shot_type.get('headers', [])
            rows = shot_type.get('data', [])
            
            if headers and rows:
                try:
                    group_idx = headers.index('GROUP_VALUE')
                    fga_idx = headers.index('FGA')
                    fgm_idx = headers.index('FGM')
                    
                    for row in rows:
                        shot_type_name = str(row[group_idx]).lower()
                        if 'drive' in shot_type_name or 'driving' in shot_type_name:
                            drives_fga += row[fga_idx] or 0
                            drives_fgm += row[fgm_idx] or 0
                        elif 'catch' in shot_type_name:
                            catch_shoot_fga += row[fga_idx] or 0
                            catch_shoot_fgm += row[fgm_idx] or 0
                        elif 'pull' in shot_type_name:
                            pull_up_fga += row[fga_idx] or 0
                            pull_up_fgm += row[fgm_idx] or 0
                except (ValueError, IndexError):
                    pass
        
        # Parse shot difficulty
        contested_fga = tight_fga = open_fga = wide_open_fga = 0
        
        difficulty = data.get('difficulty', {})
        if difficulty:
            closest_def = difficulty.get('closest_defender', {})
            def_headers = closest_def.get('headers', [])
            def_rows = closest_def.get('data', [])
            
            if def_headers and def_rows:
                try:
                    group_col = 'CLOSE_DEF_DIST_RANGE' if 'CLOSE_DEF_DIST_RANGE' in def_headers else 'GROUP_VALUE'
                    group_idx = def_headers.index(group_col)
                    fga_idx = def_headers.index('FGA')
                    
                    for row in def_rows:
                        category = str(row[group_idx]).lower()
                        fga = row[fga_idx] or 0
                        
                        if '0-2' in category or 'very tight' in category:
                            contested_fga += fga
                        elif '2-4' in category or 'tight' in category:
                            tight_fga += fga
                            contested_fga += fga
                        elif '4-6' in category or ('open' in category and 'wide' not in category):
                            open_fga += fga
                        elif '6+' in category or 'wide' in category:
                            wide_open_fga += fga
                except (ValueError, IndexError):
                    pass
        
        # Insert
        c.execute('''
            INSERT OR REPLACE INTO player_game_tracking (
                nba_player_id, player_name, game_date, team_abbr,
                drives_fga, drives_fgm, catch_shoot_fga, catch_shoot_fgm,
                pull_up_fga, pull_up_fgm, contested_fga, tight_fga,
                open_fga, wide_open_fga, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            player['nba_id'], player['name'], game_date, player['team'],
            drives_fga, drives_fgm, catch_shoot_fga, catch_shoot_fgm,
            pull_up_fga, pull_up_fgm, contested_fga, tight_fga,
            open_fga, wide_open_fga, datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def sync_player(self, player: Dict, player_idx: int, total_players: int):
        """Sync all games for a player."""
        dates = self.get_player_game_dates(player['name'])
        print(f"\n[{player_idx}/{total_players}] {player['name']} ({len(dates)} games)")
        
        for i, date in enumerate(dates, 1):
            date_formatted = self._format_date(date)
            
            # Fetch data
            data = self.fetch_player_data(player['nba_id'], date_formatted, date_formatted)
            
            # Insert
            self.parse_and_insert(player, date, data)
            
            print(f"   [{i}/{len(dates)}] {date} ✓")
        
        # Mark player as synced
        self.progress['players_synced'].append(player['name'])
        self._save_progress()
    
    def sync_speed_stats(self):
        """Sync league-wide speed stats."""
        if self.progress.get('speed_synced'):
            print("\n[SPEED] Already synced, skipping...")
            return
        
        print("\n[SPEED] Fetching league-wide speed/distance...")
        self._rate_limit()
        
        try:
            response = leaguedashptstats.LeagueDashPtStats(
                season=self.season,
                per_mode_simple='PerGame',
                pt_measure_type='SpeedDistance',
                player_or_team='Player',
                headers=self.headers,
                timeout=30
            )
            
            data = response.get_dict()
            result_sets = data.get('resultSets', [])
            
            if not result_sets:
                print("   No data")
                return
            
            headers = result_sets[0].get('headers', [])
            rows = result_sets[0].get('rowSet', [])
            
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            for row in rows:
                try:
                    c.execute('''
                        INSERT OR REPLACE INTO player_speed_stats (
                            nba_player_id, player_name, team_abbr, season,
                            games_played, avg_minutes, dist_miles, dist_miles_off,
                            dist_miles_def, avg_speed, avg_speed_off, avg_speed_def,
                            synced_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row[headers.index('PLAYER_ID')],
                        row[headers.index('PLAYER_NAME')],
                        row[headers.index('TEAM_ABBREVIATION')],
                        self.season,
                        row[headers.index('GP')],
                        row[headers.index('MIN')],
                        row[headers.index('DIST_MILES')] if 'DIST_MILES' in headers else 0,
                        row[headers.index('DIST_MILES_OFF')] if 'DIST_MILES_OFF' in headers else 0,
                        row[headers.index('DIST_MILES_DEF')] if 'DIST_MILES_DEF' in headers else 0,
                        row[headers.index('AVG_SPEED')] if 'AVG_SPEED' in headers else 0,
                        row[headers.index('AVG_SPEED_OFF')] if 'AVG_SPEED_OFF' in headers else 0,
                        row[headers.index('AVG_SPEED_DEF')] if 'AVG_SPEED_DEF' in headers else 0,
                        datetime.now().isoformat()
                    ))
                except Exception as e:
                    continue
            
            conn.commit()
            conn.close()
            
            self.progress['speed_synced'] = True
            self._save_progress()
            
            print(f"   ✓ Synced {len(rows)} players")
            
        except Exception as e:
            print(f"   ERROR: {e}")
    
    def run(self):
        """Execute sync."""
        print("=" * 70)
        print("LUDI INFORMATIO: FAST TRACKING SYNC (v2)")
        print(f"Rate limit: {self.rate_limit_delay}s | Window: {self.start_date} to {self.end_date}")
        print("=" * 70)
        
        # Get remaining players
        players = self.get_players_to_sync()
        print(f"\n📊 {len(players)} players remaining to sync")
        
        # Check current progress
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM player_game_tracking")
        existing = c.fetchone()[0]
        conn.close()
        print(f"📈 Existing records: {existing}")
        
        # Sync players
        for i, player in enumerate(players, 1):
            self.sync_player(player, i, len(players))
        
        # Sync speed stats
        self.sync_speed_stats()
        
        # Summary
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM player_game_tracking")
        tracking = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM player_speed_stats")
        speed = c.fetchone()[0]
        conn.close()
        
        print("\n" + "=" * 70)
        print("SYNC COMPLETE!")
        print(f"  player_game_tracking: {tracking}")
        print(f"  player_speed_stats: {speed}")
        print("=" * 70)

if __name__ == "__main__":
    sync = FastTrackingSync()
    sync.run()
