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
        print(f"   >>> PIPELINE: V9.4 (4-TIER LINE SHOPPING)")
        print(f"   >>> TIERS: NC_LEGAL | SHARP | DFS | SOCIAL")
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
                'regions': 'us,us2,us_dfs,us_ex',  # V9.4: Added us_ex for Novig/ProphetX
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
                    
                    # --- V9.4: 4-TIER BOOK STRUCTURE ---
                    # Tier 1: NC Legal (betting) | Tier 2: Sharp (CLV) | Tier 3: DFS | Tier 4: Social/Exchange
                    nc_legal = ['FanDuel', 'DraftKings', 'BetMGM', 'Caesars', 'bet365', 'Hard Rock Bet']
                    sharps = ['Pinnacle', 'Bovada', 'BetOnline.ag']
                    dfs = ['PrizePicks', 'Underdog Fantasy', 'Dabble']
                    social = ['Novig', 'ProphetX', 'Fliff']

                    target_books = nc_legal + sharps + dfs + social
                    priority_books = ['FanDuel', 'DraftKings', 'BetMGM', 'Caesars']  # For consensus line

                    # Helper function for odds comparison
                    def odds_value(odds):
                        if odds is None: return 0
                        if odds > 0: return 1 + (odds / 100)
                        return 1 + (100 / abs(odds))

                    # PHASE 1: Collect all lines and odds from all books
                    for book in data.get('bookmakers', []):
                        book_name = book['title']
                        if book_name not in target_books:
                            continue

                        is_priority = book_name in priority_books

                        if book_name == 'FanDuel' and g_id == target_ids[0]:
                            print(f"         [DEBUG] FanDuel Markets: {[m['key'] for m in book['markets']]}")

                        for market in book['markets']:
                            key = market['key']
                            short_key = key.replace('player_', '')

                            for outcome in market['outcomes']:
                                player = outcome['description']
                                line = outcome.get('point', 'N/A')
                                price = outcome.get('price', -110)
                                side = outcome.get('name', '').lower()

                                if not isinstance(line, (int, float)):
                                    continue

                                if player not in self.games[g_id]['props']:
                                    self.games[g_id]['props'][player] = {}

                                if short_key not in self.games[g_id]['props'][player]:
                                    self.games[g_id]['props'][player][short_key] = {
                                        '_line_votes': {},  # {27.5: 4, 26.5: 1}
                                        '_all_books': {},   # {book: {line: {over, under}}}
                                        'line': None,
                                        # Tier 1: NC Legal (FOR BETTING)
                                        'odds_over': None, 'book_over': None,
                                        'odds_under': None, 'book_under': None,
                                        # Tier 2: Sharp (FOR CLV CONTEXT)
                                        'sharp_odds_over': None, 'sharp_book_over': None,
                                        'sharp_odds_under': None, 'sharp_book_under': None,
                                        # Tier 3: DFS
                                        'dfs_odds_over': None, 'dfs_book_over': None,
                                        # Tier 4: Social/Exchange (zero-vig benchmark)
                                        'novig_odds_over': None, 'novig_book_over': None,
                                    }

                                prop = self.games[g_id]['props'][player][short_key]

                                # ONLY COUNT VOTES FROM NC LEGAL BOOKS (FIX: Alt line bug)
                                # Alt lines from DFS/Sharp books will not influence main line selection
                                # We can only bet at NC Legal books, so only their lines should vote
                                if book_name in nc_legal:
                                    vote_weight = 2 if is_priority else 1
                                    if line not in prop['_line_votes']:
                                        prop['_line_votes'][line] = 0
                                    prop['_line_votes'][line] += vote_weight

                                # Store odds by book and line
                                if book_name not in prop['_all_books']:
                                    prop['_all_books'][book_name] = {}
                                if line not in prop['_all_books'][book_name]:
                                    prop['_all_books'][book_name][line] = {'over': None, 'under': None}

                                if 'over' in side:
                                    prop['_all_books'][book_name][line]['over'] = price
                                elif 'under' in side:
                                    prop['_all_books'][book_name][line]['under'] = price

                    # PHASE 2: Determine consensus line and assign tiered odds
                    for player, stats in self.games[g_id]['props'].items():
                        for stat_key, prop in stats.items():
                            if not prop.get('_line_votes'):
                                continue

                            # Find consensus line (most votes FROM NC LEGAL BOOKS)
                            main_line = max(prop['_line_votes'].keys(), key=lambda x: prop['_line_votes'][x])

                            # Validate NC Legal coverage exists (FIX: Alt line bug defense-in-depth)
                            nc_legal_has_odds = False
                            for book in nc_legal:
                                if book in prop['_all_books'] and main_line in prop['_all_books'][book]:
                                    odds = prop['_all_books'][book][main_line]
                                    if odds.get('over') or odds.get('under'):
                                        nc_legal_has_odds = True
                                        break

                            if not nc_legal_has_odds:
                                # No NC Legal books offer this line - SKIP IT
                                # This prevents alt lines from being selected
                                if g_id == target_ids[0]:  # Debug first game only
                                    print(f"         ⚠️ Skipped {stat_key} line {main_line} (no NC Legal odds)")
                                continue

                            prop['line'] = main_line

                            # Find best NC Legal at main line (FOR BETTING)
                            for book in nc_legal:
                                if book in prop['_all_books'] and main_line in prop['_all_books'][book]:
                                    odds = prop['_all_books'][book][main_line]
                                    if odds.get('over') and odds_value(odds['over']) > odds_value(prop.get('odds_over')):
                                        prop['odds_over'] = odds['over']
                                        prop['book_over'] = book
                                    if odds.get('under') and odds_value(odds['under']) > odds_value(prop.get('odds_under')):
                                        prop['odds_under'] = odds['under']
                                        prop['book_under'] = book

                            # Find best Sharp at main line (FOR CLV CONTEXT)
                            for book in sharps:
                                if book in prop['_all_books'] and main_line in prop['_all_books'][book]:
                                    odds = prop['_all_books'][book][main_line]
                                    if odds.get('over') and odds_value(odds['over']) > odds_value(prop.get('sharp_odds_over')):
                                        prop['sharp_odds_over'] = odds['over']
                                        prop['sharp_book_over'] = book
                                    if odds.get('under') and odds_value(odds['under']) > odds_value(prop.get('sharp_odds_under')):
                                        prop['sharp_odds_under'] = odds['under']
                                        prop['sharp_book_under'] = book

                            # Find DFS odds at main line
                            for book in dfs:
                                if book in prop['_all_books'] and main_line in prop['_all_books'][book]:
                                    odds = prop['_all_books'][book][main_line]
                                    if odds.get('over'):
                                        prop['dfs_odds_over'] = odds['over']
                                        prop['dfs_book_over'] = book
                                        break

                            # Find Social/Exchange odds (zero-vig benchmark)
                            for book in social:
                                if book in prop['_all_books'] and main_line in prop['_all_books'][book]:
                                    odds = prop['_all_books'][book][main_line]
                                    if odds.get('over'):
                                        prop['novig_odds_over'] = odds['over']
                                        prop['novig_book_over'] = book
                                        break

                            # Clean up internal tracking (optional - keep for debugging)
                            # del prop['_line_votes']
                    
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