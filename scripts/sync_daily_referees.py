#!/usr/bin/env python3
"""
Daily Referee Assignment Sync - "Day Forward" Intelligence System

Captures referee crews from official.nba.com/referee-assignments/ and:
1. Populates games.referee_crew for today's slate
2. Auto-registers new referees to referee_profiles
3. Enables learning engines (learn_daily_trends.py, analyze_star_bias.py)

Designed for GitHub Actions automation (9:30 AM ET daily).
"""

import argparse
import sqlite3
import pandas as pd
import requests
from datetime import datetime
from typing import Dict, List, Tuple
from io import StringIO
import sys
import os

class DailyRefereeSync:
    """Daily capture system for referee intelligence."""
    
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        
        # Copy TEAM_MAP from module_g.py (lines 26-55)
        self.TEAM_MAP = {
            "Atlanta": "ATL", "Boston": "BOS", "Brooklyn": "BKN", "Charlotte": "CHA",
            "Chicago": "CHI", "Cleveland": "CLE", "Dallas": "DAL", "Denver": "DEN",
            "Detroit": "DET", "Golden State": "GSW", "Houston": "HOU", "Indiana": "IND",
            "L.A. Clippers": "LAC", "LA Clippers": "LAC", "Clippers": "LAC",
            "L.A. Lakers": "LAL", "LA Lakers": "LAL", "Lakers": "LAL", "Los Angeles Lakers": "LAL",
            "Memphis": "MEM", "Miami": "MIA", "Milwaukee": "MIL", "Minnesota": "MIN",
            "New Orleans": "NOP", "New York": "NYK", "Knicks": "NYK",
            "Oklahoma City": "OKC", "Orlando": "ORL", "Philadelphia": "PHI", "Phoenix": "PHX",
            "Portland": "POR", "Sacramento": "SAC", "San Antonio": "SAS", "Toronto": "TOR",
            "Utah": "UTA", "Washington": "WAS",
            "Atlanta Hawks": "ATL",
            "Boston Celtics": "BOS",
            "Brooklyn Nets": "BKN",
            "Charlotte Hornets": "CHA",
            "Chicago Bulls": "CHI",
            "Cleveland Cavaliers": "CLE",
            "Dallas Mavericks": "DAL",
            "Denver Nuggets": "DEN",
            "Detroit Pistons": "DET",
            "Golden State Warriors": "GSW",
            "Houston Rockets": "HOU",
            "Indiana Pacers": "IND",
            "Los Angeles Clippers": "LAC",
            "Los Angeles Lakers": "LAL",
            "Memphis Grizzlies": "MEM",
            "Miami Heat": "MIA",
            "Milwaukee Bucks": "MIL",
            "Minnesota Timberwolves": "MIN",
            "New Orleans Pelicans": "NOP",
            "New York Knicks": "NYK",
            "Oklahoma City Thunder": "OKC",
            "Orlando Magic": "ORL",
            "Philadelphia 76ers": "PHI",
            "Phoenix Suns": "PHX",
            "Portland Trail Blazers": "POR",
            "Sacramento Kings": "SAC",
            "San Antonio Spurs": "SAS",
            "Toronto Raptors": "TOR",
            "Utah Jazz": "UTA",
            "Washington Wizards": "WAS"
        }
        
        # Ensure today's games exist before any referee operations
        self._ensure_todays_games()
    
    def _ensure_todays_games(self):
        """Auto-populate today's games if missing (before any referee operations)"""
        print("   🔍 Checking today's games in database...")
        
        if not self._check_todays_games_exist():
            print("   📡 No games found - auto-populating today's slate...")
            self._populate_todays_games()
            print("   ✅ Games populated successfully")
        else:
            print("   ✅ Today's games already exist")

    def _check_todays_games_exist(self) -> bool:
        """Check if any games exist for today's date"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) FROM games WHERE date = ?", (today,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
            
        except Exception as e:
            print(f"   ⚠️ Error checking games: {e}")
            return False

    def _populate_todays_games(self):
        """Populate today's games using The-Odds API (mirrors populate_todays_games.py logic)"""
        try:
            # Import config to access API key
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath('scripts/sync_daily_referees.py'))))
            import config
            
            # Fetch schedule from The-Odds API
            url = 'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
            params = {
                'api_key': config.ODDS_API_KEY,
                'regions': 'us',
                'markets': 'h2h',  # We just need event info
                'oddsFormat': 'american'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Get today's date in EST
            import pytz
            EST_TZ = pytz.timezone('US/Eastern')
            today_str = datetime.now(EST_TZ).strftime('%Y-%m-%d')
            
            games_to_insert = []
            for game in data:
                # Convert UTC start time to EST date string
                utc_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                est_time = utc_time.astimezone(EST_TZ)
                game_date = est_time.strftime('%Y-%m-%d')
                
                if game_date == today_str:
                    game_id = game['id']  # Use API ID as unique identifier
                    home_team = self._resolve_team_abbr(game['home_team'])
                    away_team = self._resolve_team_abbr(game['away_team'])
                    
                    if home_team and away_team:
                        # Construct ludi_game_id format: YYYYMMDD_AWAY@HOME
                        ludi_game_id = f"{est_time.strftime('%Y%m%d')}_{away_team}@{home_team}"
                        
                        games_to_insert.append((ludi_game_id, game_date, home_team, away_team))
            
            # Insert into database
            if games_to_insert:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for g in games_to_insert:
                    g_id, g_date, home, away = g
                    print(f"   🏀 {away} @ {home}")
                    
                    cursor.execute("""
                        INSERT INTO games (game_id, date, home_team, away_team)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(game_id) DO UPDATE SET
                            date=excluded.date,
                            home_team=excluded.home_team,
                            away_team=excluded.away_team
                    """, (g_id, g_date, home, away))
                
                conn.commit()
                conn.close()
                print(f"   ✅ Inserted {len(games_to_insert)} games")
            else:
                print("   ⚠️ No games found for today")
                
        except Exception as e:
            print(f"   ❌ Error populating games: {e}")
    
    def scrape_assignments(self) -> Dict[str, List[str]]:
        """
        Scrape today's referee assignments from NBA official site.
        
        Reuses logic from module_g.build_ref_database()
        
        Returns:
            dict: {team_abbr: [ref1, ref2, ref3]}
        """
        url = "https://official.nba.com/referee-assignments/"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                print(f"❌ Failed (Status {r.status_code}).")
                return {}

            # Parse Tables with StringIO fix applied
            dfs = pd.read_html(StringIO(r.text))
            
            if not dfs:
                print("⚠️ No tables found on page.")
                return {}

            df = dfs[0]
            df.columns = [c.upper() for c in df.columns]
            
            assignments = {}
            for _, row in df.iterrows():
                game_str = str(row.get('GAME', ''))
                
                if '@' in game_str:
                    parts = game_str.split('@')
                    if len(parts) > 1:
                        raw_home = parts[1].strip()
                        
                        if '(' in raw_home:
                            raw_home = raw_home.split('(')[0].strip()
                            
                        home_abbr = self._resolve_team_abbr(raw_home)
                        
                        crew = []
                        for col in df.columns:
                            if 'CHIEF' in col or 'REFEREE' in col or 'UMPIRE' in col:
                                if pd.notna(row[col]):
                                    raw_ref = str(row[col]).split('(')[0].strip()
                                    if raw_ref:
                                        crew.append(raw_ref)
                        
                        if home_abbr and crew:
                            assignments[home_abbr] = crew
            
            return assignments
            
        except Exception as e:
            print(f"❌ Scrape failed: {e}")
            return {}
    
    def _resolve_team_abbr(self, raw_name: str) -> str:
        """
        Standardize team names to 3-letter abbreviations.
        
        Copy from module_g.py lines 169-182
        """
        clean_name = raw_name.replace('.', '').strip()
        
        if clean_name in self.TEAM_MAP:
            return self.TEAM_MAP[clean_name]
            
        for key, abbr in self.TEAM_MAP.items():
            if key in clean_name: 
                return abbr
            
        if len(clean_name) == 3 and clean_name.isupper():
            return clean_name
            
        return None
    
    def get_todays_games(self) -> List[Tuple[int, str, str]]:
        """
        Query today's games from database.
        
        Returns:
            list: [(game_id, home_team, away_team), ...] 
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        # Fallback to test date if needed during dev (can remove later)
        # today = '2026-01-14' # Uncomment to test with last known date if wanted
        
        cursor.execute("""
            SELECT game_id, home_team, away_team
            FROM games
            WHERE date = ?
        """, (today,))
        
        games = cursor.fetchall()
        conn.close()
        
        return games
    
    def update_game_crew(self, game_id: str, crew_list: List[str], dry_run=False):
        """
        Populate games.referee_crew column.
        
        Args:
            game_id: Database game_id
            crew_list: List of referee names
            dry_run: If True, print but don't execute
        """
        crew_string = ', '.join(crew_list)
        
        if dry_run:
            print(f"   [DRY RUN] Would update game {game_id}: {crew_string}")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE games 
            SET referee_crew = ? 
            WHERE game_id = ?
        """, (crew_string, game_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Updated game {game_id}: {crew_string}")
    
    def register_new_referee(self, ref_name: str, dry_run=False):
        """
        Auto-register new referee if not in database.
        
        Uses neutral baseline:
        - avg_fouls_per_game: 21.5 (league average)
        - avg_pace_impact: 1.0 (neutral)
        - style: 'NEUTRAL'
        - data_source: 'daily_capture'
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if ref exists
        cursor.execute("""
            SELECT referee_id FROM referee_profiles 
            WHERE referee_name = ?
        """, (ref_name,))
        
        if cursor.fetchone():
            conn.close()
            return  # Already exists
        
        if dry_run:
            print(f"   [DRY RUN] Would register new ref: {ref_name}")
            conn.close()
            return
        
        # Insert with neutral baseline
        cursor.execute("""
            INSERT INTO referee_profiles (
                referee_name, 
                avg_fouls_per_game, 
                avg_pace_impact, 
                style, 
                data_source,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (ref_name, 21.5, 1.0, 'NEUTRAL', 'daily_capture', datetime.now()))
        
        conn.commit()
        conn.close()
        
        print(f"🆕 Registered new referee: {ref_name}")
    
    def run(self, dry_run=False):
        """
        Main orchestration: scrape, match, update.
        """
        print("🦓 Daily Referee Sync - Day Forward Intelligence")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"🧪 Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print()
        
        # Step 1: Scrape assignments
        print("📡 Scraping official.nba.com/referee-assignments/...")
        assignments = self.scrape_assignments()
        print(f"✅ Found assignments for {len(assignments)} teams\n")
        
        # Step 2: Get today's games
        print("🔍 Querying today's games from database...")
        games = self.get_todays_games()
        print(f"✅ Found {len(games)} games scheduled today ({datetime.now().strftime('%Y-%m-%d')})\n")
        
        # Step 3: Match and update
        print("🔗 Matching crews to games...")
        matched = 0
        
        for game_id, home_team, away_team in games:
            crew = assignments.get(home_team)
            
            if crew:
                self.update_game_crew(game_id, crew, dry_run)
                
                # Auto-register new refs
                for ref in crew:
                    self.register_new_referee(ref, dry_run)
                
                matched += 1
            else:
                print(f"⚠️  No crew found for {home_team} (game {game_id})")
        
        print()
        print(f"✅ Summary: {matched}/{len(games)} games updated")
        
        if not dry_run:
            print("🎯 Referee learning engines can now run!")


def main():
    parser = argparse.ArgumentParser(
        description='Daily Referee Assignment Sync - Day Forward Intelligence'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Test mode - print actions without database writes'
    )
    parser.add_argument(
        '--db-path',
        default='ludi.db',
        help='Path to database (default: ludi.db)'
    )
    
    args = parser.parse_args()
    
    syncer = DailyRefereeSync(db_path=args.db_path)
    syncer.run(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
