#!/usr/bin/env python3
"""
Pre-Game Lineup Sync Script

Fetches starting lineup data from Tank01 depth charts for teams on today's slate,
updates players.is_starter column, and returns starters dict.

Usage:
    python scripts/sync_lineup_starters.py --mode morning
    python scripts/sync_lineup_starters.py --mode evening
    python scripts/sync_lineup_starters.py --mode late_games

Modes:
    morning: Full sync for morning workflow (9:45 AM)
    evening: Refresh for evening lock (6:35 PM)
    late_games: Only sync games where lineup_confirmed=False and tip_time > now + 90 min
"""

import sqlite3
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from utils.tank01_client import get_client
from utils.player_id_resolver import PlayerIDResolver


logging.basicConfig(
    level=logging.INFO,
    format="[LINEUP-SYNC] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


class LineupSync:
    def __init__(self, db_path: str = 'ludi.db', verbose: bool = False):
        self.db_path = db_path
        self.verbose = verbose
        self.tank01 = get_client()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

    def _log(self, msg: str):
        if self.verbose:
            logger.info(msg)
        else:
            print(f"   [LINEUP] {msg}")

    def get_slate_teams(self, conn) -> set:
        """Get unique teams from today's slate games."""
        cursor = conn.cursor()
        today = date.today().strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT DISTINCT home_team, away_team 
            FROM games 
            WHERE date = ?
        """, (today,))
        
        teams = set()
        for row in cursor.fetchall():
            if row[0]:
                teams.add(row[0])
            if row[1]:
                teams.add(row[1])
        
        return teams

    def get_games_needing_lineup_sync(self, conn) -> List[dict]:
        """Get games where lineup_confirmed=False and tip_time > now + 90 min."""
        from utils.game_notes_cache import get_cache_path, load_game_cache
        from datetime import datetime, timedelta
        import json
        
        cursor = conn.cursor()
        today = date.today().strftime('%Y-%m-%d')
        
        cursor.execute("""
            SELECT game_id, home_team, away_team, start_time
            FROM games 
            WHERE date = ?
        """, (today,))
        
        games = []
        now = datetime.now()
        threshold = now + timedelta(minutes=90)
        
        for row in cursor.fetchall():
            game_id, home_team, away_team, start_time = row
            
            cache_path = get_cache_path()
            cache_file = Path(cache_path)
            game_key = f"{home_team}@{away_team}"
            
            if not cache_file.exists():
                continue
            
            try:
                with open(cache_file) as f:
                    cache_data = json.load(f)
                
                game_data = cache_data.get(game_key, {})
                
                if not game_data.get('lineup_confirmed', False):
                    start_dt = datetime.strptime(f"{today} {game_data.get('tip_time_et', '19:00')}", "%Y-%m-%d %H:%M")
                    if start_dt > threshold:
                        games.append({
                            'game_id': game_id,
                            'home_team': home_team,
                            'away_team': away_team,
                            'game_key': game_key
                        })
            except Exception as e:
                self._log(f"Warning: Could not check cache for {game_key}: {e}")
        
        return games

    def sync_lineups_for_slate(self, slate_games: List[dict]) -> Dict[str, List[str]]:
        """
        Main function: Sync starting lineups for teams in slate_games.
        
        Args:
            slate_games: List of game dicts with 'home_team' and 'away_team' keys
            
        Returns:
            Dict mapping team_abbr -> list of starter names
        """
        if not slate_games:
            self._log("No slate games provided, fetching from database")
            conn = self._get_conn()
            try:
                teams = self.get_slate_teams(conn)
            finally:
                conn.close()
            if not teams:
                self._log("No games found in database for today")
                return {}
            slate_games = [{'home_team': t.split('@')[0], 'away_team': t.split('@')[1]} for t in [f"{list(teams)[i]}@{list(teams)[i+1]}" for i in range(0, len(teams)-1, 2)]]

        teams = set()
        for game in slate_games:
            if 'home_team' in game and game['home_team']:
                teams.add(game['home_team'])
            if 'away_team' in game and game['away_team']:
                teams.add(game['away_team'])
        
        if not teams:
            self._log("No teams found in slate_games")
            return {}
        
        self._log(f"Syncing lineups for {len(teams)} teams: {', '.join(sorted(teams))}")
        
        starters_by_team = {}
        
        for team in teams:
            try:
                starters = self._sync_team_lineup(team)
                starters_by_team[team] = starters
            except Exception as e:
                self._log(f"Warning: Failed to sync lineup for {team}: {e}")
                starters_by_team[team] = []
        
        confirmed = sum(1 for s in starters_by_team.values() if s)
        self._log(f"Successfully synced {confirmed}/{len(teams)} teams")
        
        return starters_by_team

    def _sync_team_lineup(self, team_abbr: str) -> List[str]:
        """Sync lineup for a single team from Tank01 depth charts."""
        try:
            depth_data = self.tank01.get_depth_charts()
        except Exception as e:
            self._log(f"Warning: Tank01 depth charts fetch failed for {team_abbr}: {e}")
            return []
        
        team_data = depth_data.get(team_abbr, {})
        depth_chart = team_data.get("depthChart", {})
        
        starters = []
        
        position_order = ["PG", "SG", "SF", "PF", "C"]
        
        for pos in position_order:
            players = depth_chart.get(pos, [])
            if players and len(players) > 0:
                starter = players[0]
                if isinstance(starter, dict):
                    starter_name = starter.get("longName", "")  # Tank01 depth chart key (not "playerName")
                else:
                    starter_name = str(starter)
                if starter_name:
                    starters.append(starter_name)
        
        if starters:
            self._log(f"{team_abbr}: {starters}")
        
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            
            cursor.execute('UPDATE players SET is_starter = 0 WHERE team = ?', (team_abbr,))
            
            for starter_name in starters:
                normalized_name = PlayerIDResolver.normalize_name(starter_name)
                if not normalized_name:
                    continue
                cursor.execute('''
                    UPDATE players SET is_starter = 1 
                    WHERE player_id = (
                        SELECT canonical_id FROM player_canonical_ids
                        WHERE normalized_name = ?
                    ) AND team = ?
                ''', (normalized_name, team_abbr))
            
            conn.commit()
            
        except Exception as e:
            self._log(f"Warning: DB update failed for {team_abbr}: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return starters

    def sync_late_games(self, conn) -> Dict[str, List[str]]:
        """Sync lineups only for games that need updating."""
        games = self.get_games_needing_lineup_sync(conn)
        
        if not games:
            self._log("No games need lineup sync")
            return {}
        
        self._log(f"Syncing {len(games)} late games with unconfirmed lineups")
        
        slate_games = []
        for game in games:
            slate_games.append({
                'home_team': game['home_team'],
                'away_team': game['away_team']
            })
        
        return self.sync_lineups_for_slate(slate_games)


def main():
    parser = argparse.ArgumentParser(description="Sync NBA starting lineups from Tank01")
    parser.add_argument('--mode', choices=['morning', 'evening', 'late_games'], 
                       default='morning', help='Sync mode')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--db-path', default='ludi.db', help='Database path')
    
    args = parser.parse_args()
    
    syncer = LineupSync(db_path=args.db_path, verbose=args.verbose)
    
    if args.mode == 'late_games':
        conn = syncer._get_conn()
        try:
            starters = syncer.sync_late_games(conn)
        finally:
            conn.close()
    else:
        starters = syncer.sync_lineups_for_slate([])
    
    print(f"\n✅ Lineup sync complete: {sum(len(v) for v in starters.values())} starters across {len(starters)} teams")


if __name__ == '__main__':
    main()
