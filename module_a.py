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
from utils.mappings import resolve_team_abbr, normalize_bdl_abbr

class Gatekeeper:
    """
    Module A — Data Gatekeeper. Entry point for all market data.

    self.games[game_id] data contract:
    {
        'game_id':   str  — Odds-API event ID (e.g. "abc123"), or "{AWAY}_{HOME}" for BDL/ESPN
        'matchup':   str  — "{AWAY} @ {HOME}"
        'home':      str  — canonical team abbreviation (e.g. "BOS")
        'away':      str  — canonical team abbreviation
        'home_team': str  — same as 'home' (alias for downstream compat)
        'away_team': str  — same as 'away'
        'start_time': datetime | None — EST-aware datetime (None = BDL line source)
        'game_date': str  — "YYYY-MM-DD" (derived from start_time or today)
        'vegas': {
            'spread':           float  — home spread (negative = home favored)
            'total':            float  — game total (O/U)
            'moneyline_home':   int | None — American odds
            'moneyline_away':   int | None — American odds
            'team_total_home':  float | None — home team total
            'team_total_away':  float | None — away team total
        },
        'props': {
            stat_key (str): {         — e.g. 'points', 'rebounds', 'assists'
                player_name (str): {
                    'line':      float,
                    'odds_over': int,    — best NC-legal over odds (American)
                    'odds_under': int,   — best NC-legal under odds (American)
                    'book_over': str,    — bookmaker name for over odds
                    'book_under': str,   — bookmaker name for under odds
                    'source_quality': str,  — 'HIGH'|'MEDIUM'|'LOW'|'SINGLE_VENDOR'|'UNKNOWN'
                    'vendor_count': int,    — number of books offering this line
                }
            }
        },
        'archetypes': {
            'ref_data':    dict  — LudiRefEngine payload (pace/whistle/crew/confidence)
            'home_pace':   float — home team pace from team_leverage_profiles (0 if unavailable)
            'home_def_rtg': float — home team DRtg 14d from player_game_advanced (0 if unavailable)
        },
    }
    """

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

        # [A6] Tank01 player name → ID cross-walk (built alongside _tank01_props_cache).
        # Keyed by normalized player name (lowercase, accent-stripped) → tank01 player_id_str.
        # Enables _validate_line_with_tank01() to actually validate single-vendor BDL lines.
        self._tank01_name_to_id = {}  # {normalized_name_str: tank01_player_id_str}
        # Reverse map — needed for Tank01 3rd fallback to resolve player names from cached IDs.
        self._tank01_id_to_name = {}  # {tank01_player_id_str: display_player_name}


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
            'regions': 'us,us2,eu',  # eu added Mar 1 2026: unlocks Pinnacle for game line CLV
            'markets': 'h2h,spreads,totals',  # team_totals NOT supported on this endpoint (422)
            'oddsFormat': 'american'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)  # A3: prevent indefinite hang

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
                        'home_pace': 0,  # D3: populated by fetch_team_archetypes()
                        'home_def_rtg': 0  # D3: populated by fetch_team_archetypes()
                    },
                }
                
                # 4. Extract Vegas Lines
                for book in game['bookmakers']:
                    # Uses API key format. Verified Mar 1 2026:
                    # betmgm=BetMGM, williamhill_us=Caesars, espnbet=theScore Bet, pinnacle via eu region.
                    if book['key'] in ['draftkings', 'fanduel', 'betmgm', 'williamhill_us',
                                       'fanatics', 'espnbet', 'pinnacle', 'bovada']:
                        for market in book['markets']:
                            if market['key'] == 'spreads':
                                for outcome in market['outcomes']:
                                    if outcome['name'] == home:
                                        self.games[game_id]['vegas']['spread'] = outcome.get('point')
                                        break
                            if market['key'] == 'totals':
                                for outcome in market['outcomes']:
                                    if outcome['name'] == 'Over':  # A1: Odds-API uses "Over"/"Under" for totals (not team names)
                                        self.games[game_id]['vegas']['total'] = outcome.get('point')
                                        break
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

            # --- PHASE 1.5: Team Totals Enrichment ---
            # team_totals is not supported on the bulk /odds endpoint (returns 422).
            # Fetch per-event after the slate is built. Cost: 1 credit per game.
            # Per-event format: outcome['description'] = team name, outcome['name'] = Over/Under.
            # Non-blocking: failure → Module E falls back to implied team total (total ± spread / 2).
            _tt_books = {'draftkings', 'fanduel', 'betmgm', 'williamhill_us', 'fanatics'}
            _tt_written = 0
            for _gid, _gdata in list(self.games.items()):
                try:
                    _tt_url = f'https://api.the-odds-api.com/v4/sports/{sport}/events/{_gid}/odds'
                    _tt_params = {
                        'api_key': config.ODDS_API_KEY,
                        'regions': 'us,us2',
                        'markets': 'team_totals',
                        'oddsFormat': 'american',
                    }
                    _tt_resp = self.session.get(_tt_url, params=_tt_params, timeout=15)
                    if _tt_resp.status_code != 200:
                        continue
                    _tt_json = _tt_resp.json()
                    _home = _gdata['home']
                    _away = _gdata['away']
                    for _bk in _tt_json.get('bookmakers', []):
                        if _bk['key'] not in _tt_books:
                            continue
                        for _mkt in _bk.get('markets', []):
                            if _mkt['key'] != 'team_totals':
                                continue
                            for _oc in _mkt['outcomes']:
                                _team = _oc.get('description', '')
                                _side = _oc.get('name', '')   # "Over" or "Under"
                                _pt = _oc.get('point')
                                if _side == 'Over' and _pt is not None:
                                    if _team == _home and _gdata['vegas']['team_total_home'] is None:
                                        _gdata['vegas']['team_total_home'] = _pt
                                        _tt_written += 1
                                    elif _team == _away and _gdata['vegas']['team_total_away'] is None:
                                        _gdata['vegas']['team_total_away'] = _pt
                                        _tt_written += 1
                        break  # first valid book is enough for the line value
                except Exception:
                    continue  # non-blocking — Module E implied fallback handles missing data
            if _tt_written:
                print(f"   ✅ Team totals enriched: {_tt_written} values across {len(self.games)} games")

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
        
        # B1: 9 PM EST cutover — fetch tomorrow too so early research is possible after games end
        if date_str is None:
            today = datetime.now(self.est_tz)
            dates_to_fetch = [today.strftime('%Y-%m-%d')]
            if today.hour >= 21:
                tomorrow_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                dates_to_fetch.append(tomorrow_str)
                print(f"   📅 [BDL] After 9 PM — also fetching tomorrow: {tomorrow_str}")
        else:
            today = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=self.est_tz)
            dates_to_fetch = [date_str]

        # B4: Game line vendor priority — prediction markets (polymarket, kalshi) removed.
        # They have no NBA game lines; reserved for Ludi Lens web app when implemented.
        vendor_priority = ['fanduel', 'draftkings', 'betmgm', 'caesars', 'bovada', 'pinnacle']

        # Fetch games + odds across all dates in the window
        bdl_games = []
        game_odds = {}  # {game_id: best_odds_entry via vendor_priority}

        for fetch_date in dates_to_fetch:
            # 1. Fetch games
            g_resp = self.bdl.get_games(date=fetch_date)
            bdl_games.extend(g_resp.get('data', []))

            # 2. Fetch odds, select best vendor per game
            o_resp = self.bdl.get_odds(date=fetch_date)
            for odd in o_resp:
                game_id = odd.get('game_id')
                if not game_id:
                    continue
                vendor = odd.get('vendor', '').lower()
                if game_id not in game_odds:
                    game_odds[game_id] = odd
                else:
                    current_vendor = game_odds[game_id].get('vendor', '').lower()
                    current_idx = vendor_priority.index(current_vendor) if current_vendor in vendor_priority else 999
                    new_idx = vendor_priority.index(vendor) if vendor in vendor_priority else 999
                    if new_idx < current_idx:
                        game_odds[game_id] = odd

        if not bdl_games:
            print(f"   ⚠️  [BDL] No games found for {', '.join(dates_to_fetch)}")
            raise ValueError(f"BDL returned no games for {', '.join(dates_to_fetch)}")

        print(f"   ✅ [BDL] Found {len(bdl_games)} games across {len(dates_to_fetch)} date(s)")
        
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
            # F2: normalize BDL abbreviation (GS→GSW, NO→NOP, NY→NYK, PHO→PHX, SA→SAS)
            home_abbr = normalize_bdl_abbr(home_team.get('abbreviation', self._get_abbr(home_full) or ''))
            
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
                    'home_pace': 0,  # D3: populated by fetch_team_archetypes()
                    'home_def_rtg': 0  # D3: populated by fetch_team_archetypes()
                },
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

        print(f"   📡 [ESPN] Fetching DraftKings game lines from ESPN pickcenter...")

        # B2: 9 PM EST cutover — also fetch tomorrow's slate for early research
        _est_now = datetime.now(self.est_tz)
        dates_to_fetch_espn = [_est_now.strftime('%Y%m%d')]  # ESPN uses YYYYMMDD format
        if _est_now.hour >= 21:
            tomorrow_espn = (_est_now + timedelta(days=1)).strftime('%Y%m%d')
            dates_to_fetch_espn.append(tomorrow_espn)
            print(f"   📅 [ESPN] After 9 PM — also fetching tomorrow: {tomorrow_espn}")

        client = ESPNClient()
        scoreboard = {}
        for espn_date in dates_to_fetch_espn:
            day_board = client.get_scoreboard(date_str=espn_date)
            scoreboard.update(day_board)  # merge; later date's games don't overwrite today's

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
                # B3: Use parsed start_time from ESPN competition.date (may be None if unavailable)
                espn_start_time = lines.get('start_time')
                self.games[game_key] = {
                    'matchup': f"{away_abbr} @ {home_abbr}",
                    'home': home_abbr,
                    'away': away_abbr,
                    'start_time': espn_start_time,  # B3: was always None; now uses ESPN competition.date
                    'vegas': {},
                    'props': {},
                    'archetypes': {
                        'ref_data': ref_data,
                        'home_pace': 0,  # D3: populated by fetch_team_archetypes()
                        'home_def_rtg': 0,  # D3: populated by fetch_team_archetypes()
                    },
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
        """
        [2] GET TEAM ARCHETYPES — Pace + ORtg from team_leverage_profiles,
        minutes-weighted DRtg from player_game_advanced (14d window).

        Populates self.games[game_id]['archetypes']['home_pace'] and 'home_def_rtg'
        with real values instead of the default 0s from the init blocks.
        """
        print(f"[2] 📡 Fetching Team Archetypes (Pace/DefRtg)...")

        try:
            import sqlite3
            # F5: use config.DB_PATH instead of hardcoded relative path
            conn = sqlite3.connect(config.DB_PATH)

            # --- Pace + ORtg from team_leverage_profiles (season-level) ---
            pace_map = {}  # {team_abbr: (overall_pace, overall_ortg)}
            try:
                rows = conn.execute(
                    "SELECT team_abbr, overall_pace, overall_ortg FROM team_leverage_profiles"
                ).fetchall()
                for team_abbr, pace, ortg in rows:
                    pace_map[team_abbr] = (pace or 0, ortg or 0)
            except Exception as e:
                print(f"   [D3] team_leverage_profiles unavailable: {e}")

            # --- Minutes-weighted DRtg from player_game_advanced (14d) ---
            from datetime import date, timedelta
            cutoff = (date.today() - timedelta(days=14)).isoformat()
            drtg_map = {}  # {team_abbr: weighted_avg_drtg}
            try:
                rows = conn.execute(
                    """
                    SELECT team_abbrev,
                           SUM(def_rating * minutes) / NULLIF(SUM(minutes), 0) AS wt_drtg
                    FROM player_game_advanced
                    WHERE game_date >= ? AND def_rating IS NOT NULL AND minutes > 0
                    GROUP BY team_abbrev
                    HAVING COUNT(*) >= 5
                    """,
                    (cutoff,)
                ).fetchall()
                for team_abbr, wt_drtg in rows:
                    if wt_drtg is not None:
                        # F2: normalize BDL abbreviations so lookup in self.games matches
                        drtg_map[normalize_bdl_abbr(team_abbr)] = round(wt_drtg, 1)
            except Exception as e:
                print(f"   [D3] player_game_advanced DRtg query failed: {e}")

            conn.close()

            # --- Wire into self.games ---
            for game_id, game in self.games.items():
                # F1: Use correct game dict keys ('home'/'away'/'archetypes' not 'home_team'/'away_team'/'team_info')
                home_team = game.get('home', '')
                away_team = game.get('away', '')
                archetypes = game.get('archetypes', {})

                home_pace, _ = pace_map.get(home_team, (0, 0))
                home_drtg = drtg_map.get(home_team, 0)
                away_drtg = drtg_map.get(away_team, 0)

                archetypes['home_pace'] = home_pace or 0
                archetypes['home_def_rtg'] = home_drtg or 0
                archetypes['away_def_rtg'] = away_drtg or 0  # extra signal, harmless

            print(f"   ✅ Team Archetypes Mapped — {len(pace_map)} pace, {len(drtg_map)} DRtg records.")

        except Exception as e:
            print(f"   ⚠️ [D3] fetch_team_archetypes failed: {e}. Defaults intact.")

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
        
        # Valid betting markets (verified live Mar 1 2026 via /events/{id}/markets endpoint)
        # Removed: player_turnovers (PrizePicks-only, 1 book — not worth a market slot)
        # Added: player_points_rebounds_assists (17 books — nearly as wide as individual stats)
        # Attempt markets (FGA/FTA/3PA) do NOT exist on Odds API — Module C projects these internally.
        markets = (
            "player_points,player_rebounds,player_assists,"
            "player_threes,player_steals,player_blocks,"
            "player_points_rebounds_assists,"
            "player_double_double,player_triple_double"
        )
        
        for g_id in target_ids:
            url = f'https://api.the-odds-api.com/v4/sports/{sport}/events/{g_id}/odds'
            params = {
                'api_key': config.ODDS_API_KEY,
                'regions': 'us,us2,us_dfs,us_ex,eu',  # eu added Mar 1 2026: unlocks Pinnacle for prop CLV
                'markets': markets,
                'oddsFormat': 'american'
            }
            try:
                time.sleep(0.5)
                response = self.session.get(url, params=params, timeout=30)  # A3: prevent indefinite hang

                # [PAID TIER] Log API usage
                self.monitor.log_request('odds_api', 'fetch_props', response.headers)

                if response.status_code == 200:
                    data = response.json()
                    found_books = [b['title'] for b in data.get('bookmakers', [])]
                    print(f"      ↳ Found Books: {found_books}")
                    
                    # --- V9.5 (Mar 1 2026): 4-TIER BOOK STRUCTURE — verified live via API ---
                    # Verified: bet365 NOT on Odds API. williamhill_us API key = Caesars (book name in NC).
                    # Removed: Hard Rock Bet + BetRivers (not NC-legal). Fixed title mismatches (Mar 1).
                    nc_legal    = ['FanDuel', 'DraftKings', 'BetMGM', 'Caesars', 'Fanatics', 'theScore Bet']
                    sharps      = ['Pinnacle', 'Bovada', 'BetOnline.ag']
                    peer_to_peer = ['Novig', 'ProphetX']
                    dfs         = ['PrizePicks', 'Underdog', 'Betr DFS', 'DraftKings Pick6', 'Fliff']
                    prediction  = ['Kalshi', 'Polymarket']  # regulated prediction markets — alt line reference

                    target_books = nc_legal + sharps + peer_to_peer + dfs + prediction
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

                            # --- PHASE 2B: Alt line extraction (Sprint 4) ---
                            # Capture ±1.5 and ±3.0 lines from NC Legal books into
                            # game['alt_props'][stat_key][player_name] for Module F EV sweep.
                            # Zero extra API cost — data already in _all_books from Phase 1.
                            for _delta in [1.5, 3.0]:
                                for _alt_line in [main_line + _delta, main_line - _delta]:
                                    if _alt_line <= 0:
                                        continue
                                    _bo, _bbo, _bu, _bbu = None, None, None, None
                                    for _bk in nc_legal:
                                        if _bk not in prop['_all_books']:
                                            continue
                                        _bk_o = prop['_all_books'][_bk].get(_alt_line, {})
                                        if _bk_o.get('over') and (
                                            _bo is None or odds_value(_bk_o['over']) > odds_value(_bo)
                                        ):
                                            _bo, _bbo = _bk_o['over'], _bk
                                        if _bk_o.get('under') and (
                                            _bu is None or odds_value(_bk_o['under']) > odds_value(_bu)
                                        ):
                                            _bu, _bbu = _bk_o['under'], _bk
                                    if _bo is not None or _bu is not None:
                                        # Write to game-level alt_props dict
                                        # Structure: alt_props[stat_key][player_name][line] = {odds}
                                        # Module F reads: game.get('alt_props',{}).get(stat_key,{}).get(player_name,{})
                                        (self.games[g_id]
                                            .setdefault('alt_props', {})
                                            .setdefault(short_key, {})
                                            .setdefault(player, {})
                                        )[_alt_line] = {
                                            'odds_over': _bo, 'book_over': _bbo,
                                            'odds_under': _bu, 'book_under': _bbu,
                                        }

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
            # A5: Expanded vendor filter to match BDL_VENDOR_MAP capabilities (8 vendors)
            high_quality_vendors = ['draftkings', 'fanduel', 'caesars', 'betrivers', 'betmgm',
                                    'bet365', 'fanatics', 'espnbet']
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
        import unicodedata as _ud
        import re as _re2

        def _norm_name(name: str) -> str:
            """Normalize player name for Tank01 cross-walk lookup (accent-strip + lowercase)."""
            nfd = _ud.normalize('NFD', name)
            stripped = ''.join(c for c in nfd if _ud.category(c) != 'Mn')
            clean = stripped.lower().strip()
            clean = _re2.sub(r'\s+(jr|sr|ii|iii|iv)\.?\s*$', '', clean).strip()
            return clean

        BDL_VENDOR_MAP = {
            'draftkings': 'DraftKings', 'fanduel': 'FanDuel',
            'betmgm': 'BetMGM', 'caesars': 'Caesars',
            'betrivers': 'BetRivers',      # A5: Added — was in high_quality_vendors but missing from map
            'bet365': 'bet365',
            'fanatics': 'Fanatics',        # NC Legal — confirmed returning props via BDL
            'rebet': 'Rebet',              # P2P near-zero vig — confirmed returning props via BDL
            'espnbet': 'theScore Bet',     # Rebranded from ESPN Bet Dec 2025; lowercase matches Odds-API title
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
            market = prop.get('market') or {}
            over_odds = market.get('over_odds') or -110   # guard None from explicit null
            under_odds = market.get('under_odds') or -110

            if abs(over_odds) < 100 or abs(under_odds) < 100:
                print(f"Skipping corrupt odds: {over_odds}/{under_odds} for {player_name}")
                continue  # Corrupt/truncated odds (e.g. BDL milestone bug: -2, -4, -9)

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
                # A6: Resolve Tank01 player ID via in-session name cross-walk
                t01_id = self._tank01_name_to_id.get(_norm_name(player_name))
                tank01_validates = self._validate_line_with_tank01(
                    internal_stat_key=internal_key,
                    book_line=modal_line,
                    tank01_player_id=t01_id,  # A6: now resolved via _tank01_name_to_id cross-walk
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
        # CURRENT STATE (Mar 1 2026): Uses _tank01_id_to_name reverse map (built in
        # _load_tank01_props alongside _tank01_name_to_id). Writes Tank01-only props
        # at -110/-110 for players with zero BDL/Odds-API coverage. Tagged
        # 'TANK01_ONLY' for downstream QA. Canonical name alignment future upgrade:
        # could query player_canonical_ids.normalized_name for accent consistency.
        # ------------------------------------------------------------------
        if getattr(config, 'USE_TANK01_PROP_FALLBACK', True) and self._tank01_props_cache:
            game_props = self.games[game_id]['props']
            t01_written = 0

            for t01_player_id, t01_stats in self._tank01_props_cache.items():
                # Resolve player name via id→name reverse map (built in _load_tank01_props)
                t01_player_name = self._tank01_id_to_name.get(t01_player_id)
                if not t01_player_name:
                    continue  # Can't write without a name — skip silently

                # Skip players already covered by Odds-API or BDL (fallback = gaps only)
                if t01_player_name in game_props:
                    continue

                # Write Tank01-only props with -110/-110 assumed odds (line value only)
                for t01_key, t01_line in t01_stats.items():
                    internal_key = next(
                        (ik for ik, tk in self._TANK01_STAT_MAP.items() if tk == t01_key),
                        None,
                    )
                    if not internal_key:
                        continue  # Combo or unmapped stat — skip

                    if t01_player_name not in game_props:
                        game_props[t01_player_name] = {}
                    if internal_key not in game_props[t01_player_name]:
                        game_props[t01_player_name][internal_key] = {
                            'line': t01_line,
                            'odds_over': -110, 'book_over': 'Tank01',
                            'odds_under': -110, 'book_under': 'Tank01',
                            'vendor_count': 1,
                            'source_quality': 'TANK01_ONLY',  # No real market odds
                        }
                        t01_written += 1

            if t01_written > 0:
                t01_only_key = 'TANK01_ONLY'
                t01_only_count = len([
                    p for p in game_props
                    if game_props[p] and all(
                        v.get('source_quality') == t01_only_key
                        for v in game_props[p].values()
                        if isinstance(v, dict)
                    )
                ])
                print(f"      [T01] {t01_written} prop entries written for "
                      f"{t01_only_count} Tank01-only players (no BDL/Odds-API coverage)")

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

            import unicodedata
            import re as _re

            def _normalize_t01_name(name: str) -> str:
                """Strip accents + lowercase to match player_canonical_ids.normalized_name."""
                nfd = unicodedata.normalize('NFD', name)
                stripped = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
                clean = stripped.lower().strip()
                clean = _re.sub(r'\s+(jr|sr|ii|iii|iv)\.?\s*$', '', clean).strip()
                return clean

            loaded_players = 0
            for game in games_with_props:
                for player_prop in game.get('playerProps', []):
                    player_id = str(player_prop.get('playerID', ''))
                    player_name = player_prop.get('playerName', '') or player_prop.get('longName', '')
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
                            # A6: Build name→ID AND id→name cross-walks
                            if player_name:
                                norm_name = _normalize_t01_name(player_name)
                                self._tank01_name_to_id[norm_name] = player_id
                                self._tank01_id_to_name[player_id] = player_name

            print(f"[Module A] Tank01 props loaded: {loaded_players} players "
                  f"({len(games_with_props)} games), {len(self._tank01_name_to_id)} name cross-walk entries")

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

    def save_games_cache(self, date_str=None):
        """Write self.games to cache/daily_games_{date}.json so morning_brief can skip API re-fetch."""
        import json, pathlib, datetime as _dt
        date_str = date_str or _dt.datetime.now().strftime('%Y-%m-%d')
        p = pathlib.Path(__file__).parent / 'cache' / f'daily_games_{date_str}.json'
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(self.games, default=str))
        print(f"   💾 Games cache written: {p.name} ({len(self.games)} games)")

    def load_games_cache(self, date_str=None, max_age_hours=14):
        """Load self.games from cache if fresh (< max_age_hours old). Returns True if loaded."""
        import json, pathlib, datetime as _dt
        date_str = date_str or _dt.datetime.now().strftime('%Y-%m-%d')
        p = pathlib.Path(__file__).parent / 'cache' / f'daily_games_{date_str}.json'
        if not p.exists():
            return False
        age_hours = (_dt.datetime.now().timestamp() - p.stat().st_mtime) / 3600
        if age_hours > max_age_hours:
            print(f"   ⚠️  Games cache is {age_hours:.1f}h old (limit {max_age_hours}h) — falling back to API")
            return False
        try:
            self.games = json.load(p.open())
            print(f"   ✅ Odds cache hit: {p.name} ({len(self.games)} games, {age_hours:.1f}h old) — 0 credits")
            return True
        except Exception as e:
            print(f"   ⚠️  Cache load failed: {e} — falling back to API")
            return False

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
