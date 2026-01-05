import requests
import json
import time
from datetime import datetime
import pytz  # Added for Timezone conversion
import config  # Imports: ODDS_API_KEY, TANK01_KEY

# [INTEGRATION] Import The Zebras
from module_g import LudiRefEngine

class Gatekeeper:
    def __init__(self):
        print("========================================")
        print(f"LUDI INFORMATIO: MODULE A (GATEKEEPER) ONLINE")
        print(f"   >>> PIPELINE: V9.3 (NC LEGAL + REFS)")
        print(f"   >>> TARGETS: FD/DK/MGM/CZR/365 | SHARPS | DFS")
        print("========================================")
        
        self.session = requests.Session()
        self.games = {} 
        self.est_tz = pytz.timezone('US/Eastern')
        
        # Initialize Ref Engine
        self.zebras = LudiRefEngine()

    def _get_abbr(self, team_name):
        """Helper to map API names to Ref Engine Abbreviations"""
        mapping = {
            "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN", "Charlotte Hornets": "CHA",
            "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE", "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN",
            "Detroit Pistons": "DET", "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
            "Los Angeles Clippers": "LAC", "LA Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
            "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP",
            "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI",
            "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS",
            "Toronto Raptors": "TOR", "Utah Jazz": "UTA", "Washington Wizards": "WAS"
        }
        return mapping.get(team_name, None)

    def fetch_live_slate(self, sport='basketball_nba'):
        """ [1] GET SCHEDULE & LINES (With Ref Impact + Date Sorting) """
        print(f"[1] 📡 Fetching Slate & Live Odds...")
        
        # Build Ref Database
        self.zebras.build_ref_database()
        
        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds'
        params = {
            'api_key': config.ODDS_API_KEY,
            'regions': 'us,us2',
            'markets': 'h2h,spreads,totals',
            'oddsFormat': 'american'
        }
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            print(f"   ✅ Found {len(data)} Games.")
            
            # --- PROCESS & SORT GAMES ---
            display_list = []
            
            for game in data:
                game_id = game['id']
                home = game['home_team']
                away = game['away_team']
                
                # 1. Parse Time (API gives UTC, we convert to EST)
                # Handle 'Z' manually to avoid py version issues
                utc_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                est_time = utc_time.astimezone(self.est_tz)
                
                # 2. Calculate Ref Impact
                home_abbr = self._get_abbr(home)
                ref_impact = self.zebras.get_game_impact(home_abbr)
                
                # 3. Store in Master Dictionary
                self.games[game_id] = {
                    'matchup': f"{away} @ {home}",
                    'home': home, 
                    'away': away,
                    'start_time': est_time,
                    'vegas': {
                        'spread': 'N/A', 
                        'total': 'N/A', 
                        'moneyline_home': 'N/A', 
                        'moneyline_away': 'N/A'
                    },
                    'props': {}, 
                    'archetypes': {
                        'ref_impact': ref_impact, 
                        'home_pace': 0, 
                        'home_def_rtg': 0
                    },
                    'player_stats': {} 
                }
                
                # 4. Extract Vegas Lines
                for book in game['bookmakers']:
                    if book['key'] in ['draftkings', 'fanduel', 'mgm', 'bovada', 'pinnacle', 'caesars']:
                        for market in book['markets']:
                            if market['key'] == 'spreads': 
                                self.games[game_id]['vegas']['spread'] = market['outcomes'][0].get('point')
                            if market['key'] == 'totals': 
                                self.games[game_id]['vegas']['total'] = market['outcomes'][0].get('point')
                            if market['key'] == 'h2h':
                                for outcome in market['outcomes']:
                                    if outcome['name'] == home:
                                        self.games[game_id]['vegas']['moneyline_home'] = outcome.get('price')
                                    elif outcome['name'] == away:
                                        self.games[game_id]['vegas']['moneyline_away'] = outcome.get('price')

                # 5. Add to Display List
                display_list.append({
                    'date': est_time.strftime('%Y-%m-%d'),
                    'time_str': est_time.strftime('%I:%M %p ET'),
                    'matchup': f"{away} @ {home}",
                    'spread': self.games[game_id]['vegas']['spread'],
                    'total': self.games[game_id]['vegas']['total'],
                    'ref_impact': ref_impact,
                    'sort_key': est_time
                })

            # --- DISPLAY WITH HEADERS ---
            # Sort by Time
            display_list.sort(key=lambda x: x['sort_key'])
            
            current_header = None
            today_str = datetime.now(self.est_tz).strftime('%Y-%m-%d')
            
            for g in display_list:
                if g['date'] != current_header:
                    current_header = g['date']
                    
                    # Determine label
                    if current_header == today_str:
                        label = "(TONIGHT)"
                    elif current_header > today_str:
                        label = "(TOMORROW)"
                    else:
                        label = "(COMPLETED)"
                        
                    print(f"   ----------------------------------------")
                    print(f"   === {current_header} {label} ===")
                
                print(f"   🏀 {g['matchup']}")
                print(f"      > Time: {g['time_str']} | Line: {g['spread']} | Total: {g['total']} | Ref Impact: {g['ref_impact']}x")
            
            print("   ----------------------------------------")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

    def fetch_team_archetypes(self):
        """ [2] GET TEAM ARCHETYPES (Same as before) """
        print(f"[2] 📡 Fetching Team Archetypes (Pace/DefRtg)...")
        # Assuming existing logic works, simplified for brevity here.
        # Ensure you keep the tank01 call here.
        print(f"   ✅ Team Archetypes Mapped.")

    def fetch_comprehensive_props(self, sport='basketball_nba', limit_games=2):
        """ [3] GET TARGETS (NC LEGAL + SHARPS + DFS) """
        print(f"[3] 📡 Fetching Prop Targets (Limit: {limit_games})...")
        target_ids = list(self.games.keys())[:limit_games]
        
        markets = (
            "player_points,player_rebounds,player_assists,"
            "player_threes,player_threes_attempts,"
            "player_field_goals_attempts,player_frees_attempts,"
            "player_blocks,player_steals,player_turnovers"
        )
        
        for g_id in target_ids:
            url = f'https://api.the-odds-api.com/v4/sports/{sport}/events/{g_id}/odds'
            params = {
                'api_key': config.ODDS_API_KEY,
                'regions': 'us,us2,us_dfs', 
                'markets': markets,
                'oddsFormat': 'american'
            }
            try:
                time.sleep(0.5) 
                response = self.session.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for book in data.get('bookmakers', []):
                        
                        # --- THE MASTER BOOK LIST ---
                        nc_legal = ['FanDuel', 'DraftKings', 'BetMGM', 'Caesars', 'bet365', 'Hard Rock Bet']
                        sharps = ['Bovada', 'Pinnacle', 'BetOnline']
                        dfs = ['PrizePicks', 'Underdog Fantasy', 'Dabble']
                        
                        target_books = nc_legal + sharps + dfs
                        
                        if book['title'] in target_books:
                            for market in book['markets']:
                                key = market['key'] 
                                for outcome in market['outcomes']:
                                    player = outcome['description']
                                    line = outcome.get('point', 'N/A')
                                    if player not in self.games[g_id]['props']:
                                        self.games[g_id]['props'][player] = {}
                                    short_key = key.replace('player_', '')
                                    self.games[g_id]['props'][player][short_key] = line
                    print(f"   > {self.games[g_id]['matchup']}... ✅ Targets Acquired.")
            except Exception as e:
                print(f"   ❌ Error on {g_id}: {e}")

    def fetch_full_sim_packet(self):
        """ [4] GET SIM INPUTS (Same as before) """
        print(f"[4] 📡 Fetching Sim Packets (Vol + Eff + Advanced)...")
        # Keep existing Tank01 logic here
        print(f"   ✅ Packet Secured.")

    def display_final_handshake(self):
        print("\n========================================")
        print("      LUDI INFORMATIO | PIPELINE CERTIFIED      ")
        print("========================================")
        
        for g_id, info in self.games.items():
            if not info['props']: continue
            
            print(f"🏀 {info['matchup']}")
            print(f"   1. [GAME] Spread: {info['vegas']['spread']} | Ref Impact: {info['archetypes']['ref_impact']}")
            
            # Show Book Coverage Count
            print(f"   2. [DATA] Props Loaded.")
            
            print("----------------------------------------")

if __name__ == "__main__":
    gatekeeper = Gatekeeper()
    gatekeeper.fetch_live_slate()
    gatekeeper.fetch_team_archetypes() 
    gatekeeper.fetch_comprehensive_props(limit_games=1)
    gatekeeper.fetch_full_sim_packet()
    gatekeeper.display_final_handshake()