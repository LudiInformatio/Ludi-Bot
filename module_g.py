import pandas as pd
import requests
import sqlite3
import time
from datetime import datetime
from io import StringIO
import sys
import os

# ==============================================================================
# LUDI INFORMATIO | MODULE G: THE ZEBRAS
# V3.0 - DATABASE-DRIVEN OFFICIATING IMPACT ENGINE (Jan 15, 2026)
# ==============================================================================

DB_PATH = "ludi.db"

class LudiRefEngine:
    def __init__(self, db_path=DB_PATH):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE G (ZEBRAS) V3.0 ONLINE")
        print(f"{'='*40}")
        
        self.db_path = db_path
        self.daily_assignments = {}
        
        # League average baseline (used for unknown refs)
        self.LEAGUE_AVG_FOULS = 21.5
        
        # Team name resolver (still needed for scraping assignments)
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
            "Utah": "UTA", "Washington": "WAS"
        }
        
        # Ensure today's games exist before any referee operations
        self._ensure_todays_games()
        
        # Check database connectivity and referee count
        self._verify_database()

    def _ensure_todays_games(self):
        """Auto-populate today's games if missing (before any referee operations)"""
        print("   [ZEBRAS] 🔍 Checking today's games in database...")
        
        if not self._check_todays_games_exist():
            print("   [ZEBRAS] 📡 No games found - auto-populating today's slate...")
            self._populate_todays_games()
            print("   [ZEBRAS] ✅ Games populated successfully")
        else:
            print("   [ZEBRAS] ✅ Today's games already exist")

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
            print(f"   [ZEBRAS] ⚠️ Error checking games: {e}")
            return False

    def _populate_todays_games(self):
        """Populate today's games using The-Odds API (mirrors populate_todays_games.py logic)"""
        try:
            # Import config to access API key
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
            
            # Team mapping (copied from populate_todays_games.py)
            TEAM_MAP = {
                "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
                "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
                "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
                "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
                "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
                "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN",
                "New Orleans Pelicans": "NOP", "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC",
                "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX",
                "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
                "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS"
            }
            
            def resolve_team(name):
                return TEAM_MAP.get(name, name[:3].upper())
            
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
                    home_team = resolve_team(game['home_team'])
                    away_team = resolve_team(game['away_team'])
                    
                    # Construct ludi_game_id format: YYYYMMDD_AWAY@HOME
                    ludi_game_id = f"{est_time.strftime('%Y%m%d')}_{away_team}@{home_team}"
                    
                    games_to_insert.append((ludi_game_id, game_date, home_team, away_team))
            
            # Insert into database
            if games_to_insert:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for g in games_to_insert:
                    g_id, g_date, home, away = g
                    print(f"   [ZEBRAS] 🏀 {away} @ {home}")
                    
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
                print(f"   [ZEBRAS] ✅ Inserted {len(games_to_insert)} games")
            else:
                print("   [ZEBRAS] ⚠️ No games found for today")
                
        except Exception as e:
            print(f"   [ZEBRAS] ❌ Error populating games: {e}")

    def _verify_database(self):
        """Verify referee_profiles table exists and has data."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM referee_profiles")
            count = c.fetchone()[0]
            conn.close()
            print(f"   [ZEBRAS] 📊 Database: {count} referees loaded")
        except Exception as e:
            print(f"   [ZEBRAS] ⚠️ Database error: {e}")
            print(f"   [ZEBRAS] 💡 Run: python scripts/scrape_referee_roster.py")

    def _get_referee_profile(self, ref_name):
        """
        Query database for referee profile by name.
        Uses fuzzy matching (LIKE) to handle name variations.
        
        Returns:
            dict with pace_impact, whistle_impact, style, or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Try exact match first
            c.execute("""
                SELECT referee_name, avg_fouls_per_game, avg_pace_impact, style
                FROM referee_profiles
                WHERE referee_name = ?
            """, (ref_name,))
            result = c.fetchone()
            
            # If no exact match, try fuzzy match (last name)
            if not result and ' ' in ref_name:
                last_name = ref_name.split()[-1]
                c.execute("""
                    SELECT referee_name, avg_fouls_per_game, avg_pace_impact, style
                    FROM referee_profiles
                    WHERE referee_name LIKE ?
                """, (f'%{last_name}%',))
                result = c.fetchone()
            
            conn.close()
            
            if result:
                avg_fouls = result[1]
                pace_impact = result[2]
                style = result[3]
                
                # Calculate whistle_impact from fouls/game relative to league avg
                # Higher fouls = more FTA opportunities
                whistle_impact = round(avg_fouls / self.LEAGUE_AVG_FOULS, 3)
                
                return {
                    'name': result[0],
                    'pace_impact': pace_impact,
                    'whistle_impact': whistle_impact,
                    'style': style
                }
            return None
            
        except Exception as e:
            print(f"   [ZEBRAS] DB Error: {e}")
            return None

    def build_ref_database(self):
        """
        Scrapes the official NBA Referee Assignments page.
        """
        url = "https://official.nba.com/referee-assignments/"
        print("   [ZEBRAS] 🦓 Scraping Official NBA Assignments...", end=" ")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        try:
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                print(f"❌ Failed (Status {r.status_code}). Using Neutral Pace.")
                return {}

            # Parse Tables with StringIO fix applied
            dfs = pd.read_html(StringIO(r.text))
            
            if not dfs:
                print("⚠️ No tables found on page.")
                return {}

            df = dfs[0]
            df.columns = [c.upper() for c in df.columns]
            
            count = 0
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
                                    crew.append(raw_ref)
                        
                        if home_abbr:
                            self.daily_assignments[home_abbr] = crew
                            count += 1
            
            print(f"✅ Success. Found assignments for {count} games.")
            return self.daily_assignments

        except Exception as e:
            print(f"❌ Error scraping refs: {e}")
            return {}

    def _resolve_team_abbr(self, raw_name):
        clean_name = raw_name.replace('.', '').strip()
        
        if clean_name in self.TEAM_MAP:
            return self.TEAM_MAP[clean_name]
            
        for key, abbr in self.TEAM_MAP.items():
            if key in clean_name: 
                return abbr
            
        if len(clean_name) == 3 and clean_name.isupper():
            return clean_name
            
        return None

    def get_game_impact(self, home_team_abbr):
        """
        Calculate referee impact for a game, now returning a dict with
        separate pace and whistle impact factors.
        
        Returns:
            dict: {
                'pace_impact': float,      # Multiplier for game pace
                'whistle_impact': float,   # Multiplier for FTA projections
                'crew': list,              # List of referee names
                'confidence': float        # 0.0-1.0, how many refs we have data for
            }
        """
        crew = self.daily_assignments.get(home_team_abbr, [])
        
        # Default neutral response
        neutral_response = {
            'pace_impact': 1.0,
            'whistle_impact': 1.0,
            'crew': crew,
            'confidence': 0.0
        }
        
        if not crew:
            return neutral_response
        
        pace_factors = []
        whistle_factors = []
        known_count = 0
        
        for ref in crew:
            profile = self._get_referee_profile(ref)
            if profile:
                pace_factors.append(profile['pace_impact'])
                whistle_factors.append(profile['whistle_impact'])
                known_count += 1
            else:
                # Unknown ref, use neutral
                pace_factors.append(1.0)
                whistle_factors.append(1.0)
        
        # Calculate crew averages
        avg_pace = sum(pace_factors) / len(pace_factors)
        avg_whistle = sum(whistle_factors) / len(whistle_factors)
        confidence = known_count / len(crew)
        
        return {
            'pace_impact': round(avg_pace, 3),
            'whistle_impact': round(avg_whistle, 3),
            'crew': crew,
            'confidence': round(confidence, 2)
        }


if __name__ == "__main__":
    zebras = LudiRefEngine()
    assignments = zebras.build_ref_database()
    
    if assignments:
        print("\n--- TEST: First 3 Games (New V3.0 Output) ---")
        for team in list(assignments.keys())[:3]:
            impact = zebras.get_game_impact(team)
            print(f"\n🏀 {team}:")
            print(f"   Crew: {impact['crew']}")
            print(f"   Pace Impact: {impact['pace_impact']}x")
            print(f"   Whistle Impact: {impact['whistle_impact']}x")
            print(f"   Confidence: {impact['confidence'] * 100:.0f}%")