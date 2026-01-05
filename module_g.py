import pandas as pd
import requests
import time
from datetime import datetime
from io import StringIO  # <--- Added for the clean fix

# ==============================================================================
# LUDI INFORMATIO | MODULE G: THE ZEBRAS
# V2.2 - OFFICIATING IMPACT ENGINE (FutureWarning Fixed)
# ==============================================================================

class LudiRefEngine:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE G (ZEBRAS) ONLINE")
        print(f"{'='*40}")
        
        self.daily_assignments = {}
        
        # 1. THE CHEAT SHEET (2025-26 TENDENCIES)
        self.IMPACT_MAP = {
            "Andy Nagy": 1.04,
            "Jacyn Goble": 1.03,
            "Phenizee Ransom": 1.03,
            "John Goble": 1.02,
            "Zach Zarba": 1.02,
            "Ed Malloy": 1.02,
            "Bill Kennedy": 1.01,
            "Josh Tiven": 1.01,
            "Scott Foster": 0.96,
            "Courtney Kirkland": 0.97,
            "James Williams": 0.97,
            "Sean Wright": 0.98,
            "Tony Brothers": 0.99,
            "Marc Davis": 0.99
        }

        # 2. TEAM NAME RESOLVER
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
        crew = self.daily_assignments.get(home_team_abbr, [])
        if not crew: return 1.0 
        
        total_impact = 0.0
        known_refs_count = 0
        
        for ref in crew:
            for key_ref, impact_val in self.IMPACT_MAP.items():
                if key_ref in ref:
                    total_impact += impact_val
                    known_refs_count += 1
                    break
        
        if known_refs_count > 0:
            crew_size = len(crew)
            unknowns = crew_size - known_refs_count
            final_impact = (total_impact + (unknowns * 1.0)) / crew_size
            return round(final_impact, 3)
        
        return 1.0

if __name__ == "__main__":
    zebras = LudiRefEngine()
    assignments = zebras.build_ref_database()
    
    if assignments:
        print("\n--- TEST: First 3 Games ---")
        for team in list(assignments.keys())[:3]:
            print(f"{team}: {zebras.get_game_impact(team)}")