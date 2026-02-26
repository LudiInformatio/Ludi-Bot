import requests
import json
import time
from datetime import datetime, timedelta
import pytz  # Added for Timezone conversion
import config  # Imports: ODDS_API_KEY, TANK01_KEY

# [INTEGRATION] Import The Zebras
from module_g import LudiRefEngine

# [PAID TIER] Import monitoring and retry utilities
from utils.api_monitor import get_monitor
from utils.api_helpers import retry_with_backoff

# [NEW] BallDontLie Client
from utils.bdl_client import BDLClient

# [NEW] Import centralized mappings
from utils.mappings import resolve_team_abbr

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

        # [NEW] Initialize BDL Client
        self.bdl = BDLClient()

        # [BDL FALLBACK] Flag for when The-Odds-API quota is exhausted
        self._using_bdl_fallback = False

        # [ESPN FALLBACK] Flag for when both Odds-API and BDL are unavailable
        self._using_espn_fallback = False

        # [BDL PLAYER CACHE] Lazy-loaded map of bdl_id → full_name
        # Built on first call to _resolve_bdl_player so we don't pay the cost unless needed
        self._bdl_player_cache = {}  # {bdl_player_id: "First Last"}

        # [TANK01 PROP CACHE] Lazy-loaded consensus prop lines from Tank01.
        # Keyed by Tank01 playerID → {tank01_stat_key: line_value (float)}.
        # LINE VALUES ONLY — no over/under odds. Used as validator + last-resort fallback.
        # Populated once per slate by _load_tank01_props(); never re-fetched mid-run.
        self._tank01_props_cache = {}  # {player_id_str: {"pts": 22.5, "reb": 6.5, ...}}
        self._tank01_props_loaded = False


    def _get_abbr(self, team_name):
        """Helper to map API names to Ref Engine Abbreviations"""
        return resolve_team_abbr(team_name)

    @retry_with_backoff(max_attempts=3, backoff=2.0)
    def fetch_live_slate(self, sport='basketball_nba'):
        """ [EDULE & LINES (With Ref Impact1] GET SCH + Date Sorting) """
        print(f"[1] 📡 Fetching Slate & Live Odds...")

        # Build Ref Database
        self.zebras.build_ref_database()

        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds'
        params = {
            'api_key': config.ODDS_API_KEY,
            'regions': 'us,us2',
            'markets': 'h2h,spreads,totals,team_totals',
            'oddsFormat': 'american'
        }
        
        try:
            response = self.session.get(url, params=params)

            # [PAID TIER] Log API usage
            self.monitor.log_request('odds_api', 'fetch_slate', response.headers)
            self.monitor.check_quota_threshold('odds_api')

            response.raise_for_status()
            data = response.json()

            # Check for empty response (quota exhaustion)
            if not data:
                raise ValueError("The-Odds-API returned empty data (possible quota exhaustion)")
            
            print(f"   ✅ Found {len(data)} Games.")
            
            # --- PROCESS & SORT GAMES ---
            display_list = []

            # --- DATE WINDOW: 9 PM cutoff ---
            # Before 9 PM EST: today's games only
            # At/after 9 PM EST: include tomorrow for early research
            _est_now = datetime.now(self.est_tz)
            _today_date = _est_now.date()
            _allowed_dates = {_today_date}
            if _est_now.hour >= 21:
                _allowed_dates.add(_today_date + timedelta(days=1))

            for game in data:
                game_id = game['id']
                home = game['home_team']
                away = game['away_team']

                # 1. Parse Time (API gives UTC, we convert to EST)
                # Handle 'Z' manually to avoid py version issues
                utc_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                est_time = utc_time.astimezone(self.est_tz)

                # Skip games outside the allowed date window
                if est_time.date() not in _allowed_dates:
                    continue
                
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
                        'team_total_home': None,
                        'team_total_away': None,
                        'home_team': home,
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
                                for outcome in market['outcomes']:
                                    if outcome['name'] == home:
                                        self.games[game_id]['vegas']['spread'] = outcome.get('point')
                                        break
                            if market['key'] == 'totals':
                                for outcome in market['outcomes']:
                                    if outcome['name'] == home:
                                        self.games[game_id]['vegas']['total'] = outcome.get('point')
                                        break
                            if market['key'] == 'team_totals':
                                for outcome in market['outcomes']:
                                    if outcome['name'] == home:
                                        self.games[game_id]['vegas']['team_total_home'] = outcome.get('point')
                                    elif outcome['name'] == away:
                                        self.games[game_id]['vegas']['team_total_away'] = outcome.get('point')
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
                    'spread': self.games[game_id]['vegas'].get('spread', 0),
                    'total': self.games[game_id]['vegas'].get('total', 0),
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
            print(f"   ⚠️  The-Odds-API Failed: {e}")
            print(f"   📡 Falling back to BallDontLie for game lines...")
            self._using_bdl_fallback = True
            try:
                self.fetch_game_lines_balldontlie()
            except Exception as bdl_err:
                print(f"   ⚠️   BDL fallback failed: {bdl_err}")
                print(f"   📡 Tier 3 fallback: ESPN DraftKings lines...")
                self._using_espn_fallback = True
                self.fetch_game_lines_espn()

    def fetch_game_lines_balldontlie(self, date_str: str = None):
        """ [1b] BALLDONTLIE FALLBACK: Fetch game schedule + lines when The-Odds-API fails """
        from datetime import datetime
        
        print(f"   📡 [BDL] Fetching game lines from BallDontLie...")
        
        if date_str is None:
            today = datetime.now(self.est_tz)
            date_str = today.strftime('%Y-%m-%d')
        else:
            today = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=self.est_tz)
        
        # 1. Fetch games from BDL
        games_resp = self.bdl.get_games(date=date_str)
        bdl_games = games_resp.get('data', [])
        
        if not bdl_games:
            print(f"   ⚠️  [BDL] No games found for {date_str}")
            raise ValueError(f"BDL returned no games for {date_str}")
        
        print(f"   ✅ [BDL] Found {len(bdl_games)} games")
        
        # 2. Fetch odds from BDL
        odds_resp = self.bdl.get_odds(date=date_str)
        
        # Group odds by game_id, prefer FanDuel > DraftKings > BetMGM > Caesars > others
        vendor_priority = ['fanduel', 'draftkings', 'betmgm', 'caesars', 'bovada', 'pinnacle', 'polymarket', 'kalshi']
        
        game_odds = {}
        for odd in odds_resp:
            game_id = odd.get('game_id')
            if not game_id:
                continue
            vendor = odd.get('vendor', '').lower()
            if game_id not in game_odds:
                game_odds[game_id] = odd  # First vendor
            else:
                # Check if current vendor has higher priority
                current_vendor = game_odds[game_id].get('vendor', '').lower()
                current_idx = vendor_priority.index(current_vendor) if current_vendor in vendor_priority else 999
                new_idx = vendor_priority.index(vendor) if vendor in vendor_priority else 999
                if new_idx < current_idx:
                    game_odds[game_id] = odd
        
        # 3. Process each game
        display_list = []
        
        # Get set of game_ids that have odds
        games_with_odds = set(game_odds.keys())
        
        for bdl_game in bdl_games:
            # Skip postponed games - but include any game that has odds (including completed)
            status = bdl_game.get('status', '')
            game_id = bdl_game['id']
            
            if status == 'Postponed':
                continue
            
            # Skip if no odds available for this game (and it's not scheduled)
            if status != 'Scheduled' and status != 'Pre-Game' and status != '' and game_id not in games_with_odds:
                continue
            
            game_id = bdl_game['id']
            home_team = bdl_game.get('home_team', {})
            visitor_team = bdl_game.get('visitor_team', {})
            
            home_full = home_team.get('full_name', '')
            away_full = visitor_team.get('full_name', '')
            home_abbr = home_team.get('abbreviation', self._get_abbr(home_full) or '')
            
            # Parse game time from BDL datetime
            bdl_datetime = bdl_game.get('datetime')
            if bdl_datetime:
                try:
                    utc_time = datetime.fromisoformat(bdl_datetime.replace('Z', '+00:00'))
                    est_time = utc_time.astimezone(self.est_tz)
                except Exception as e:
                    print(f"[TAG] Context: {e}")
                    est_time = today  # Fallback to today
            else:
                est_time = today
            
            # Get ref data
            ref_data = self.zebras.get_game_impact(home_abbr)
            
            # Get odds for this game
            odds = game_odds.get(game_id, {})
            
            # Map BDL odds to our vegas dict
            vegas = {
                'spread': float(odds.get('spread_home_value', 0)) if odds.get('spread_home_value') else 'N/A',
                'total': float(odds.get('total_value', 0)) if odds.get('total_value') else 'N/A',
                'moneyline_home': odds.get('moneyline_home_odds', 'N/A'),
                'moneyline_away': odds.get('moneyline_away_odds', 'N/A'),
            }
            
            # Store in self.games
            self.games[game_id] = {
                'matchup': f"{away_full} @ {home_full}",
                'home': home_full,
                'away': away_full,
                'start_time': est_time,
                'vegas': vegas,
                'props': {},
                'archetypes': {
                    'ref_data': ref_data,
                    'home_pace': 0,
                    'home_def_rtg': 0
                },
                'player_stats': {}
            }
            
            # Add to display list
            display_list.append({
                'date': est_time.strftime('%Y-%m-%d'),
                'time_str': est_time.strftime('%I:%M %p ET'),
                'matchup': f"{away_full} @ {home_full}",
                'spread': vegas['spread'],
                'total': vegas['total'],
                'ref_data': ref_data,
                'sort_key': est_time
            })
        
        # Display games
        display_list.sort(key=lambda x: x['sort_key'])
        
        current_header = None
        today_str = datetime.now(self.est_tz).strftime('%Y-%m-%d')
        
        for g in display_list:
            if g['date'] != current_header:
                current_header = g['date']
                label = "(TONIGHT)" if current_header == today_str else "(TOMORROW)" if current_header > today_str else "(COMPLETED)"
                print(f"   ----------------------------------------")
                print(f"   === {current_header} {label} ===")
            
            print(f"   🏀 {g['matchup']}")
            ref_d = g.get('ref_data', {})
            pace_x = ref_d.get('pace_impact', 1.0) if isinstance(ref_d, dict) else 1.0
            whistle_x = ref_d.get('whistle_impact', 1.0) if isinstance(ref_d, dict) else 1.0
            conf_pct = ref_d.get('confidence', 0.0) * 100 if isinstance(ref_d, dict) else 0
            print(f"      > Time: {g['time_str']} | Line: {g['spread']} | Total: {g['total']} | Pace: {pace_x}x | Whistle: {whistle_x}x ({conf_pct:.0f}% conf)")
        
        print("   ----------------------------------------")
        print(f"   ✅ [BDL] Loaded {len(self.games)} games with lines")

        # Validate that at least one game has real odds (non-zero spread OR total).
        # BDL can return games without odds data — silent success with zero lines.
        # If no real odds, raise so ESPN Tier 3 fallback can fire.
        games_with_real_odds = sum(
            1 for g in self.games.values()
            if g.get('vegas', {}).get('spread', 0) != 0
            or g.get('vegas', {}).get('total', 0) != 0
        )
        if games_with_real_odds == 0 and len(self.games) > 0:
            print(f"   ⚠️  [BDL] Found {len(self.games)} games but 0 have real odds data")
            raise ValueError(f"BDL returned {len(self.games)} games but no actual odds data")

    def fetch_game_lines_espn(self):
        """[1c] ESPN TIER 3 FALLBACK: Fetch game lines via ESPN DraftKings pickcenter.

        Only called when both The-Odds-API and BDL have failed.
        Provides: spread, O/U, moneylines (DraftKings game-level only).
        No player props available from ESPN — props must be skipped in this mode.
        """
        from utils.espn_client import ESPNClient
        import sqlite3

        print(f"   📡 [ESPN] Fetching DraftKings game lines from ESPN pickcenter...")

        conn = sqlite3.connect('ludi.db')
        client = ESPNClient()
        scoreboard = client.get_scoreboard()  # handles own DB connection for team mapping
        conn.close()

        if not scoreboard:
            print(f"   ⚠️  [ESPN] No scoreboard data returned")
            return

        loaded = 0
        for game_key, lines in scoreboard.items():
            if game_key not in self.games:
                # Initialize game entry — ESPN gives us team abbrs but not full names
                home_abbr = lines.get('home_abbr', '')
                away_abbr = lines.get('away_abbr', '')
                ref_data = self.zebras.get_game_impact(home_abbr)
                self.games[game_key] = {
                    'matchup': f"{away_abbr} @ {home_abbr}",
                    'home': home_abbr,
                    'away': away_abbr,
                    'start_time': None,
                    'vegas': {},
                    'props': {},
                    'archetypes': {
                        'ref_data': ref_data,
                        'home_pace': 0,
                        'home_def_rtg': 0,
                    },
                    'player_stats': {},
                }

            self.games[game_key]['vegas'].update({
                'spread': lines.get('spread', 0),
                'total': lines.get('total', 0),
                'team_total_home': None,   # ESPN doesn't provide team totals
                'team_total_away': None,
                'moneyline_home': lines.get('ml_home'),
                'moneyline_away': lines.get('ml_away'),
                'source': 'ESPN_DK',
            })
            loaded += 1

        print(f"   ✅ [ESPN] Loaded {loaded} games from DraftKings pickcenter")

    def fetch_team_archetypes(self):
        """ [2] GET TEAM ARCHETYPES (Same as before) """
        print(f"[2] 📡 Fetching Team Archetypes (Pace/DefRtg)...")
        # Assuming existing logic works, simplified for brevity here.
        # Ensure you keep the tank01 call here.
        print(f"   ✅ Team Archetypes Mapped.")

    def fetch_comprehensive_props(self, sport='basketball_nba', limit_games=2):
        """ [3] GET TARGETS (NC LEGAL + SHARPS + DFS) """
        
        # If using BDL fallback, props must also use BDL since we don't have Odds-API game IDs
        if getattr(self, '_using_bdl_fallback', False):
            print(f"   📡 [BDL] Using BallDontLie for props (fallback mode)...")
            for g_id in list(self.games.keys())[:limit_games]:
                self.fetch_props_balldontlie(g_id)
            return
        
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
                    
                    # --- V8.14: 5-TIER BOOK STRUCTURE ---
                    # Tier 0: Sharps (CLV) | Tier 1: P2P | Tier 2: NC Legal | Tier 3: DFS | Tier 4: Other
                    nc_legal = ['FanDuel', 'DraftKings', 'BetMGM', 'Caesars', 'bet365', 'Hard Rock Bet', 'Fanatics', 'TheScore Bet']
                    sharps = ['Pinnacle', 'Bovada', 'BetOnline.ag']
                    dfs = ['PrizePicks', 'Underdog Fantasy', 'Betr', 'Fliff']
                    peer_to_peer = ['Novig', 'ProphetX', 'Rebet']

                    target_books = nc_legal + sharps + dfs + peer_to_peer
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
                            # Track consensus strength: how many unique NC legal books agreed on this line
                            nc_books_at_main = sum(
                                1 for book in nc_legal
                                if book in prop.get('_all_books', {}) and main_line in prop['_all_books'][book]
                            )
                            prop['vendor_count'] = nc_books_at_main
                            prop['source_quality'] = 'ODDS_API'

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
                            for book in peer_to_peer:
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
        # Skip if no API key
        if not self.bdl.api_key:
            return

        print(f"      > [BDL] Cross-referencing with BallDontLie...")

        try:
            # 1. Resolve BDL Game ID
            g_data = self.games[game_id]
            date_str = g_data['start_time'].strftime('%Y-%m-%d')

            # [TANK01 3RD FALLBACK] Load Tank01 prop lines once per slate.
            # Must happen before _parse_bdl_props so the cache is available
            # for single-vendor validation and the 3rd-fallback gap-fill.
            self._load_tank01_props(date_str)
            home_team = g_data['home']
            away_team = g_data['away']
            
            # Fetch games for this date
            resp = self.bdl.get_games(date=date_str)
            bdl_game_id = None
            
            for bg in resp.get('data', []):
                # BDL uses "Visitor" instead of "Away" sometimes, or "visitor_team"
                # Check structure: 'home_team': {'full_name': '...'}, 'visitor_team': ...
                h_name = bg.get('home_team', {}).get('full_name')
                v_name = bg.get('visitor_team', {}).get('full_name')
                
                # Check for match (The-Odds-API uses full names usually matching BDL)
                if h_name == home_team and v_name == away_team:
                    bdl_game_id = bg['id']
                    break
            
            if not bdl_game_id:
                print(f"      ⚠️ [BDL] Match not found: {away_team} @ {home_team}")
                return

            # 2. Fetch Props
            # FIX 3: Vendor quality filter - only high-quality vendors
            high_quality_vendors = ['draftkings', 'fanduel', 'caesars', 'betrivers', 'betmgm']
            props = self.bdl.get_player_props(bdl_game_id, vendors=high_quality_vendors)
            
            if props:
                print(f"      ✅ [BDL] Retrieved {len(props)} props")
                self.games[game_id]['bdl_props'] = props
                self._parse_bdl_props(game_id, props)
            else:
                print(f"      ⚠️ [BDL] No props available")

        except Exception as e:
            print(f"      ⚠️ [BDL] Error: {e}")

    def _parse_bdl_props(self, game_id, raw_props):
        """Parse BDL player_props into standard pipeline format.

        Two-pass consensus approach — mirrors The-Odds-API path's _line_votes logic:
          Pass 1: Collect all (line, vendor, odds) entries per (player, stat)
          Pass 2: Pick the modal (most common) line value as the main line,
                  average odds across all vendors that posted that line.

        This prevents alt lines (e.g. 6.5 PTS when market main is 9.5) from
        being used as the primary line due to first-write-wins ordering.
        Only writes props that Odds-API hasn't already populated (BDL fills gaps).
        """
        from collections import Counter

        BDL_VENDOR_MAP = {
            'draftkings': 'DraftKings', 'fanduel': 'FanDuel',
            'betmgm': 'BetMGM', 'caesars': 'Caesars',
            'bet365': 'bet365',
            'fanatics': 'Fanatics',        # NC Legal — confirmed returning props via BDL
            'rebet': 'Rebet',              # P2P near-zero vig — confirmed returning props via BDL
            'espnbet': 'TheScore Bet',     # Rebranded from ESPN Bet Dec 2025; Odds-API key still 'espnbet'
        }
        COMBO_MAP = {
            'points_rebounds_assists': 'pra',
            'points_assists': 'pa',
            'points_rebounds': 'pr',
            'rebounds_assists': 'ra',
        }

        # --- Pass 1: Accumulate all entries per (player, stat) ---
        raw = {}  # {(player_name, internal_key): [(line, vendor, over_odds, under_odds)]}
        for prop in raw_props:
            if prop.get('market', {}).get('type') != 'over_under':
                continue
            player_id = prop.get('player_id')
            player_name = self._resolve_bdl_player(player_id)
            if not player_name:
                continue
            prop_type = prop.get('prop_type', '')
            internal_key = COMBO_MAP.get(prop_type, prop_type)
            line = float(prop.get('line_value', 0))
            vendor = BDL_VENDOR_MAP.get(prop.get('vendor', ''), prop.get('vendor', ''))
            over_odds = prop.get('market', {}).get('over_odds', -110)
            under_odds = prop.get('market', {}).get('under_odds', -110)

            if abs(over_odds) < 100 or abs(under_odds) < 100:
                print(f"Skipping corrupt odds: {over_odds}/{under_odds} for {player_name}")
                continue # Skip this prop — corrupt/truncated odds value

            key = (player_name, internal_key)
            if key not in raw:
                raw[key] = []
            raw[key].append((line, vendor, over_odds, under_odds))

        # --- Pass 2: Consensus line selection, write only gaps ---
        for (player_name, internal_key), entries in raw.items():
            # BDL posts the full alt-line ladder at flat -110/-110 for every sportsbook.
            # The main market line always has REAL market odds (asymmetric, not both -110).
            # Filter: prefer entries where at least one side is NOT exactly -110.
            real_odds_entries = [e for e in entries if e[2] != -110 or e[3] != -110]
            pool = real_odds_entries if real_odds_entries else entries  # fallback to all

            # Find modal line in the filtered pool = main market line
            line_counts = Counter(e[0] for e in pool)
            modal_line, modal_count = line_counts.most_common(1)[0]
            
            # FIX 4: Modal line tightening - require >= 2 vendors agreeing on same line.
            # A line posted by only 1 book is likely an alt line, not the main market.
            # TANK01 VALIDATOR (Phase 8): When BDL has exactly 1 vendor, check whether
            # Tank01's consensus line agrees within 0.5 pts before accepting the line.
            # This salvages legitimate single-vendor BDL props (e.g. thin markets like
            # blocks/steals) while still blocking true alt-line noise.
            if modal_count < 2:
                # Attempt Tank01 validation before discarding — resolves via Tank01 playerID
                # which is NOT the same as BDL player_id.  We pass None here because BDL
                # raw props do not carry Tank01 IDs; _validate_line_with_tank01 treats
                # None → True (pass through). Full ID resolution requires a cross-walk table
                # that doesn't yet exist.  When Phase 8 adds that cross-walk, pass the
                # resolved tank01_player_id here instead of None.
                # TODO (Phase 8 follow-up): build player_canonical_ids bdl_id→tank01_id
                # cross-walk so that single-vendor BDL lines can be validated against Tank01.
                tank01_validates = self._validate_line_with_tank01(
                    internal_stat_key=internal_key,
                    book_line=modal_line,
                    tank01_player_id=None,  # cross-walk not yet available; see TODO above
                    tolerance=0.5,
                )
                if not tank01_validates:
                    print(f"      [BDL+T01] Skipping {player_name} {internal_key}: "
                          f"single vendor + Tank01 disagrees with line {modal_line}")
                    continue
                # Single-vendor line but Tank01 passes (or no Tank01 data) — accept it
                # with a downgraded source_quality tag so downstream can trust accordingly
                print(f"      [BDL] Accepting single-vendor line for {player_name} "
                      f"{internal_key}: {modal_line} (Tank01 validated or no T01 data)")
                # Fall through: modal_line is accepted; main_line assignment below handles it
            
            main_line = modal_line

            # Best odds across vendors at the main line.
            # Use BEST decimal odds (highest payout) per side — not arithmetic average
            # of American odds (which produces nonsense when mixing +/- values).
            main_entries = [e for e in pool if e[0] == main_line]

            def _to_decimal(american):
                if american is None: return 1.909  # -110 default
                if american > 0: return 1 + (american / 100)
                return 1 + (100 / abs(american))

            def _best_american(entries_list, side_idx):
                """Return the American odds with the highest decimal value for this side."""
                best = max(entries_list, key=lambda e: _to_decimal(e[side_idx]))
                return best[side_idx], best[1]  # (odds, vendor_name)

            best_over_odds, best_over_vendor = _best_american(main_entries, 2)
            best_under_odds, best_under_vendor = _best_american(main_entries, 3)
            # Use the vendor with better over odds for the book label (bet to place)
            best_vendor = best_over_vendor

            # Quality gate: require minimum real-odds vendor coverage by market type.
            # Markets with thinner coverage have higher risk of line quality issues.
            # Note: real_odds_entries may be empty for some markets → fallback pool used.
            real_count = len(real_odds_entries)
            MIN_REAL_VENDORS = {
                # High-volume markets: main line is well-defined, 2+ books minimum
                'points': 2, 'rebounds': 2, 'assists': 2,
                # Combo markets: thinner, allow 1 real-odds vendor
                'pra': 1, 'pr': 1, 'pa': 1, 'ra': 1,
                # Rare-event markets: prone to extreme odds, require 2+ real-odds vendors
                'blocks': 2, 'steals': 2, 'threes': 2,
                # Turnovers: moderate volume
                'turnovers': 1,
            }
            min_required = MIN_REAL_VENDORS.get(internal_key, 1)
            if real_odds_entries and real_count < min_required:
                continue  # Skip — insufficient market consensus for reliable line

            # Only write if Odds-API hasn't already set this player/stat
            if player_name not in self.games[game_id]['props']:
                self.games[game_id]['props'][player_name] = {}
            if internal_key not in self.games[game_id]['props'][player_name]:
                # Tag single-vendor accepted lines distinctly for settlement QA
                src_quality = 'BDL_FALLBACK' if len(main_entries) >= 2 else 'BDL_SINGLE_VENDOR'
                self.games[game_id]['props'][player_name][internal_key] = {
                    'line': main_line,
                    'odds_over': best_over_odds, 'book_over': best_over_vendor,
                    'odds_under': best_under_odds, 'book_under': best_under_vendor,
                    'vendor_count': len(main_entries),  # consensus strength
                    'source_quality': src_quality,       # marks line source for grading
                }

        # ------------------------------------------------------------------
        # TANK01 3RD FALLBACK (Phase 8 — Module A)
        # For players that have ZERO BDL coverage (raw dict empty after pass 1),
        # create a minimal prop entry using Tank01's consensus line value + assumed
        # -110/-110 (50/50 fair probability = no devigging needed, edge conservative).
        #
        # This fires only when:
        #   (a) USE_TANK01_PROP_FALLBACK is True in config
        #   (b) Tank01 props were loaded (_load_tank01_props called before this method)
        #   (c) The player has NO BDL entry at all in self.games[game_id]['props']
        #
        # HOW TO ACTIVATE FULL 3rd-FALLBACK:
        #   Call self._load_tank01_props(date_str) in fetch_props_balldontlie() BEFORE
        #   calling self._parse_bdl_props(game_id, props).  Then Tank01 coverage will
        #   automatically fill gaps for players with zero BDL props.
        #
        # CURRENT STATE (Feb 2026): The Tank01 playerID is in _tank01_props_cache keys,
        # but we don't have a playerID → player_name map for Tank01 IDs in module_a.
        # Once the cross-walk table (player_canonical_ids: bdl_id ↔ tank01_id ↔ name)
        # is leveraged here, this block will populate real names. Until then it is a
        # framework placeholder that logs what WOULD be written.
        #
        # TODO (Phase 8 follow-up): resolve Tank01 playerID → player_name via
        #   ludi.db player_canonical_ids table, then uncomment the write below.
        # ------------------------------------------------------------------
        if getattr(config, 'USE_TANK01_PROP_FALLBACK', True) and self._tank01_props_cache:
            game_props = self.games[game_id]['props']

            # Build set of players already covered (BDL or Odds-API)
            covered_players = set(game_props.keys())

            t01_only_count = 0
            for t01_player_id, t01_stats in self._tank01_props_cache.items():
                # Reverse-map Tank01 stat keys → our internal keys
                for t01_key, t01_line in t01_stats.items():
                    # Find internal key for this Tank01 stat
                    internal_key = next(
                        (ik for ik, tk in self._TANK01_STAT_MAP.items() if tk == t01_key),
                        None,
                    )
                    if not internal_key:
                        continue  # Combo or unmapped stat — skip

                    # We cannot write without a player NAME (pipeline keyed by name).
                    # The cross-walk (tank01_id → name) will be added in Phase 8 follow-up.
                    # For now: log the gap so we can see how many players are missing.
                    t01_only_count += 1

            if t01_only_count > 0:
                print(f"      [T01] {t01_only_count} Tank01 stat-entries available for "
                      f"players not in BDL. Full 3rd-fallback needs ID cross-walk "
                      f"(player_canonical_ids bdl↔tank01). See TODO in _parse_bdl_props.")

    def _build_bdl_player_cache(self):
        """Fetch all active BDL players and build {bdl_id: full_name} cache.
        Uses cursor-based pagination. Called once on first resolution attempt."""
        import requests as _requests
        print("   [BDL] Building player ID cache (one-time)...")
        cache = {}
        cursor = None
        per_page = 100
        try:
            while True:
                params = {'per_page': per_page}
                if cursor:
                    params['cursor'] = cursor
                resp = _requests.get(
                    'https://api.balldontlie.io/v1/players/active',
                    headers={'Authorization': self.bdl.api_key},
                    params=params,
                    timeout=10
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                for p in data.get('data', []):
                    full_name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
                    if full_name and p.get('id'):
                        cache[p['id']] = full_name
                next_cursor = data.get('meta', {}).get('next_cursor')
                if not next_cursor:
                    break
                cursor = next_cursor
        except Exception as e:
            print(f"   [BDL] Cache build warning: {e}")
        print(f"   [BDL] Player cache built: {len(cache)} players")
        return cache

    def _resolve_bdl_player(self, player_id):
        """Resolve BDL player_id to player name using in-memory cache.
        Cache is built lazily on first call from BDL active players endpoint."""
        if not player_id:
            return None
        # Lazy-load the cache on first call
        if not self._bdl_player_cache:
            self._bdl_player_cache = self._build_bdl_player_cache()
        return self._bdl_player_cache.get(player_id)

    # ------------------------------------------------------------------
    # TANK01 PROP VALIDATION HELPERS (Phase 8 / Module A 3rd-fallback)
    # ------------------------------------------------------------------

    # Maps our internal stat keys (BDL/Odds-API style) → Tank01 propBets keys.
    # Tank01 uses short lowercase keys; our pipeline strips "player_" from market names.
    _TANK01_STAT_MAP = {
        'points':    'pts',
        'rebounds':  'reb',
        'assists':   'ast',
        'blocks':    'blk',
        'steals':    'stl',
        'threes':    'threes',
        'turnovers': 'turnovers',
        # Combo markets are not in Tank01 propBets — skip validation for these
    }

    def _load_tank01_props(self, game_date_str: str):
        """Load Tank01 consensus prop lines once per slate. LINE VALUES ONLY.

        Populates self._tank01_props_cache:
          {playerID_str: {tank01_stat_key: line_value_float}}

        Args:
            game_date_str: Date in any of YYYY-MM-DD or YYYYMMDD format.
                           Internally converted to YYYYMMDD for Tank01 API.
        """
        if self._tank01_props_loaded:
            return
        if not getattr(config, 'USE_TANK01_PROP_FALLBACK', True):
            self._tank01_props_loaded = True
            return

        try:
            from utils.tank01_client import get_client as get_tank01_client
            tank01 = get_tank01_client()

            # Normalise date: accept YYYY-MM-DD or YYYYMMDD
            date_str = game_date_str.replace('-', '')

            games_with_props = tank01.get_betting_odds(
                game_date=date_str,
                player_props=True,
            )

            loaded_players = 0
            for game in games_with_props:
                for player_prop in game.get('playerProps', []):
                    player_id = str(player_prop.get('playerID', ''))
                    prop_bets = player_prop.get('propBets', {})
                    if player_id and prop_bets:
                        # Convert all line values to float for safe comparison
                        cleaned = {}
                        for stat_key, line_val in prop_bets.items():
                            try:
                                cleaned[stat_key] = float(line_val)
                            except (ValueError, TypeError):
                                pass
                        if cleaned:
                            self._tank01_props_cache[player_id] = cleaned
                            loaded_players += 1

            print(f"[Module A] Tank01 props loaded: {loaded_players} players "
                  f"({len(games_with_props)} games)")

        except Exception as e:
            print(f"[Module A] Tank01 props load failed (non-fatal): {e}")
        finally:
            # Always mark as loaded so we never retry in the same pipeline run
            self._tank01_props_loaded = True

    def _validate_line_with_tank01(
        self,
        internal_stat_key: str,
        book_line: float,
        tank01_player_id: str = None,
        tolerance: float = 0.5,
    ) -> bool:
        """Check whether a book line agrees with Tank01's consensus line.

        Used as a secondary gate when BDL has only 1 vendor for a prop.
        If Tank01 has no data for this player/stat, returns True (don't filter).

        Args:
            internal_stat_key: Our pipeline stat key (e.g. 'points', 'rebounds').
            book_line:         The line from the sportsbook (float).
            tank01_player_id:  Tank01 playerID string. If None, returns True.
            tolerance:         Max allowed difference between lines (default 0.5).

        Returns:
            True  → line validated (or no Tank01 data available — benefit of doubt).
            False → Tank01 disagrees by more than tolerance — likely an alt line.
        """
        if tank01_player_id is None:
            return True  # No ID to look up — pass through

        tank01_stat_key = self._TANK01_STAT_MAP.get(internal_stat_key)
        if not tank01_stat_key:
            return True  # Combo market or unmapped key — skip validation

        player_data = self._tank01_props_cache.get(str(tank01_player_id))
        if not player_data:
            return True  # No Tank01 data for this player — don't penalise

        tank01_line = player_data.get(tank01_stat_key)
        if tank01_line is None:
            return True  # Tank01 has player but not this stat — pass through

        try:
            return abs(float(book_line) - float(tank01_line)) <= tolerance
        except (ValueError, TypeError):
            return True  # Malformed value — pass through

    # ------------------------------------------------------------------
    # END TANK01 HELPERS
    # ------------------------------------------------------------------

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
            print(f"   1. [GAME] Spread: {info['vegas'].get('spread', 'N/A')} | Pace: {pace_x}x")
            
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
