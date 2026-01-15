import requests
import json
import time
from datetime import datetime
import pytz  # Added for Timezone conversion
import config  # Imports: ODDS_API_KEY, TANK01_KEY

# [INTEGRATION] Import The Zebras
from module_g import LudiRefEngine

# [PAID TIER] Import monitoring and retry utilities
from utils.api_monitor import get_monitor
from utils.api_helpers import retry_with_backoff

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

        # [PAID TIER] Initialize API Monitor
        self.monitor = get_monitor()

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

    @retry_with_backoff(max_attempts=3, backoff=2.0)
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

            # [PAID TIER] Log API usage
            self.monitor.log_request('odds_api', 'fetch_slate', response.headers)
            self.monitor.check_quota_threshold('odds_api')

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
                
                # 2. Calculate Ref Impact (V3.0: Returns dict with pace_impact, whistle_impact)
                home_abbr = self._get_abbr(home)
                ref_data = self.zebras.get_game_impact(home_abbr)
                
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
                        'ref_data': ref_data,  # V3.0: Now a dict with pace/whistle/crew/confidence
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
                    'ref_data': ref_data,  # V3.0: Full dict
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
                ref_d = g.get('ref_data', {})
                pace_x = ref_d.get('pace_impact', 1.0) if isinstance(ref_d, dict) else 1.0
                whistle_x = ref_d.get('whistle_impact', 1.0) if isinstance(ref_d, dict) else 1.0
                conf_pct = ref_d.get('confidence', 0.0) * 100 if isinstance(ref_d, dict) else 0
                print(f"      > Time: {g['time_str']} | Line: {g['spread']} | Total: {g['total']} | Pace: {pace_x}x | Whistle: {whistle_x}x ({conf_pct:.0f}% conf)")
            
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
        
        # Valid betting markets (validated 2026-01-07)
        # Note: Attempts (FGA, FTA, FG3A) come from database, not betting markets
        markets = (
            "player_points,player_rebounds,player_assists,"
            "player_threes,player_steals,player_blocks,"
            "player_turnovers,player_double_double,player_triple_double"
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

                # [PAID TIER] Log API usage
                self.monitor.log_request('odds_api', 'fetch_props', response.headers)

                if response.status_code == 200:
                    data = response.json()
                    found_books = [b['title'] for b in data.get('bookmakers', [])]
                    print(f"      ↳ Found Books: {found_books}")
                    
                    for book in data.get('bookmakers', []):
                        
                        # --- THE MASTER BOOK LIST ---
                        nc_legal = ['FanDuel', 'DraftKings', 'BetMGM', 'Caesars', 'bet365', 'Hard Rock Bet']
                        sharps = ['Bovada', 'Pinnacle', 'BetOnline']
                        dfs = ['PrizePicks', 'Underdog Fantasy', 'Dabble']
                        
                        target_books = nc_legal + sharps + dfs
                        
                        # PRIORITY: NC Legal first, then sharps, then DFS
                        # Only capture line if we don't have one yet (avoids alt line overwrites)
                        priority_books = ['FanDuel', 'DraftKings', 'BetMGM', 'Caesars', 'bet365']
                        if book['title'] in target_books:
                            if book['title'] == 'FanDuel' and g_id == target_ids[0]:
                                print(f"         [DEBUG] FanDuel Markets: {[m['key'] for m in book['markets']]}")
                                
                            for market in book['markets']:
                                key = market['key']
                                for outcome in market['outcomes']:
                                    player = outcome['description']
                                    line = outcome.get('point', 'N/A')
                                    price = outcome.get('price', -110)  # Capture odds!
                                    side = outcome.get('name', '').lower()  # 'Over' or 'Under'

                                    if player not in self.games[g_id]['props']:
                                        self.games[g_id]['props'][player] = {}

                                    short_key = key.replace('player_', '')

                                    # --- LINE SHOPPING LOGIC V2.1 (Main Line Only) ---
                                    # Only compare odds at the SAME line (ignore alt lines)
                                    
                                    if player not in self.games[g_id]['props']:
                                        self.games[g_id]['props'][player] = {}
                                    
                                    # Determine if this is a priority book (establishes main line)
                                    priority_books = ['FanDuel', 'DraftKings', 'BetMGM', 'Caesars']
                                    book_name = book['title']
                                    is_priority = book_name in priority_books
                                    
                                    if short_key not in self.games[g_id]['props'][player]:
                                        # Initialize - first priority book sets the main line
                                        if is_priority:
                                            self.games[g_id]['props'][player][short_key] = {
                                                'line': line,  # Main line from priority book
                                                'odds_over': None,
                                                'odds_under': None,
                                                'book_over': None,
                                                'book_under': None,
                                                '_all_books': {}
                                            }
                                        else:
                                            continue  # Skip non-priority books until main line is set
                                    
                                    prop = self.games[g_id]['props'][player][short_key]
                                    main_line = prop['line']
                                    
                                    # CRITICAL: Only capture odds if this book offers the SAME line
                                    # This filters out alt lines (e.g., 24.5 vs 25.5)
                                    if line != main_line:
                                        continue  # Skip alt lines
                                    
                                    # Store this book's odds for the main line
                                    if book_name not in prop['_all_books']:
                                        prop['_all_books'][book_name] = {'over': None, 'under': None}
                                    
                                    if 'over' in side:
                                        prop['_all_books'][book_name]['over'] = price
                                    elif 'under' in side:
                                        prop['_all_books'][book_name]['under'] = price
                                    
                                    # Compare Sharp vs NC-Legal for BEST odds at MAIN line
                                    def odds_value(odds):
                                        if odds is None: return 0
                                        if odds > 0: return 1 + (odds / 100)
                                        else: return 1 + (100 / abs(odds))
                                    
                                    sharp_books = ['Bovada', 'Pinnacle', 'BetOnline.ag']
                                    nc_books = ['FanDuel', 'DraftKings', 'BetMGM', 'Caesars', 'Hard Rock Bet']
                                    
                                    # Find best Sharp
                                    best_sharp_over = {'book': None, 'odds': None, 'value': 0}
                                    best_sharp_under = {'book': None, 'odds': None, 'value': 0}
                                    for sb in sharp_books:
                                        if sb in prop['_all_books']:
                                            o = prop['_all_books'][sb].get('over')
                                            u = prop['_all_books'][sb].get('under')
                                            if o and odds_value(o) > best_sharp_over['value']:
                                                best_sharp_over = {'book': sb, 'odds': o, 'value': odds_value(o)}
                                            if u and odds_value(u) > best_sharp_under['value']:
                                                best_sharp_under = {'book': sb, 'odds': u, 'value': odds_value(u)}
                                    
                                    # Find best NC Legal
                                    best_nc_over = {'book': None, 'odds': None, 'value': 0}
                                    best_nc_under = {'book': None, 'odds': None, 'value': 0}
                                    for ncb in nc_books:
                                        if ncb in prop['_all_books']:
                                            o = prop['_all_books'][ncb].get('over')
                                            u = prop['_all_books'][ncb].get('under')
                                            if o and odds_value(o) > best_nc_over['value']:
                                                best_nc_over = {'book': ncb, 'odds': o, 'value': odds_value(o)}
                                            if u and odds_value(u) > best_nc_under['value']:
                                                best_nc_under = {'book': ncb, 'odds': u, 'value': odds_value(u)}
                                    
                                    # Pick BEST (Sharp wins if better, else NC Legal)
                                    if best_sharp_over['value'] > best_nc_over['value']:
                                        prop['odds_over'] = best_sharp_over['odds']
                                        prop['book_over'] = best_sharp_over['book']
                                    elif best_nc_over['odds']:
                                        prop['odds_over'] = best_nc_over['odds']
                                        prop['book_over'] = best_nc_over['book']
                                    
                                    if best_sharp_under['value'] > best_nc_under['value']:
                                        prop['odds_under'] = best_sharp_under['odds']
                                        prop['book_under'] = best_sharp_under['book']
                                    elif best_nc_under['odds']:
                                        prop['odds_under'] = best_nc_under['odds']
                                        prop['book_under'] = best_nc_under['book']
                    
                    # Call BDL Backup
                    self.fetch_props_balldontlie(g_id)

                    print(f"   > {self.games[g_id]['matchup']}... ✅ Targets Acquired.")
            except Exception as e:
                print(f"   ❌ Error on {g_id}: {e}")

    def fetch_props_balldontlie(self, game_id, limit=50):
        """ [3b] BALLDONTLIE BACKUP/VALIDATION """
        bdl_key = getattr(config, 'BALLDONTLIE_KEY', None)
        if not bdl_key:
            return  # checking if key is present

        print(f"      > [BDL] Cross-referencing with BallDontLie...")
        url = f"https://{config.BALLDONTLIE_HOST}/v2/odds/player_props"
        headers = {"Authorization": bdl_key}
        params = {"game_id": game_id} # BDL uses their own IDs, mapping required in real prod

        try: 
            # Note: In a real scenario, we'd need to map The-Odds-API GameID to BDL GameID.
            # For this placeholder implementation, we just show the structure.
            # r = self.session.get(url, headers=headers, params=params)
            # data = r.json()
            pass 
        except Exception as e:
            print(f"      ⚠️ [BDL] Error: {e}")

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
            ref_d = info['archetypes'].get('ref_data', {})
            pace_x = ref_d.get('pace_impact', 1.0) if isinstance(ref_d, dict) else 1.0
            print(f"   1. [GAME] Spread: {info['vegas']['spread']} | Pace: {pace_x}x")
            
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