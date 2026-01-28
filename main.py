import sys
import pandas as pd
import time
import logging
import argparse
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

# EST timezone handling
from utils.time_utils import get_est_today
from utils.daily_lock import get_target_config, filter_slate_by_config, apply_filters

# --- IMPORT ARCHITECTURE (MODULES A-H) ---
try:
    import config
    from module_a import Gatekeeper        # The Gatekeeper (Lines)
    from module_b import print_sharp_box_score  # Display function (Stats/Trends)
    from module_c import LudiOracle        # The Simulator (Math)
    from module_d import LudiYak           # The Yak (News)
    from module_e import LudiCalibrator    # The Calibrator (Adjustments)
    from module_f import LudiReporter      # The Reporter (Briefing)
    from module_g import LudiRefEngine     # The Zebras (Referees)
    from module_h_historian import LudiHistorian  # Database/Historical Data
    from module_x_scenario import ScenarioBuilder # The Architect (Scenarios)
    
    # Utilities
    from utils.pm_bot import ProjectManagerBot
    from utils.api_monitor import get_monitor
    from utils.telegram_notifier import send_message
except ImportError as e:
    print(f"CRITICAL ERROR: Missing a Ludi Module. {e}")
    sys.exit(1)

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format="[LUDI-CORE] %(message)s")

class LudiOrchestrator:
    def __init__(self, target_teams=None, send_telegram=False):
        print("\n" + "="*50)
        print("   LUDI INFORMATIO | SYSTEM INITIALIZATION")
        print("   Architecture: Modules A-H (Production v2.0)")
        print("="*50)

        self.target_teams = target_teams # List of team abbrs (e.g. ['CLE', 'SAC'])
        self.send_telegram = send_telegram

        # 1. INITIALIZE ALL SYSTEMS
        self.gate = Gatekeeper()
        self.historian = LudiHistorian()
        self.sim = LudiOracle()
        self.yak = LudiYak()
        self.calib = LudiCalibrator()
        self.reporter = LudiReporter()
        self.zebras = LudiRefEngine()
        self.scenario_builder = ScenarioBuilder()
        
        # Build Ref DB immediately
        self.zebras.build_ref_database()
        
        # Database path
        self.db_path = "ludi.db"

    def get_active_roster(self, team_abbr: str, limit: int = 8) -> List[Dict]:
        """Query database for top N players by minutes, joined with PBP Shot Quality."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = '''
            SELECT pgl.player_id, pgl.player_name, pgl.team_abbreviation, 
                   AVG(pgl.pts), AVG(pgl.reb), AVG(pgl.ast), 
                   AVG(pgl.fga), AVG(pgl.fg3a), AVG(pgl.fta), 
                   AVG(pgl.oreb), AVG(pgl.dreb), AVG(pgl.stl), AVG(pgl.blk), 
                   AVG(pgl.tov), AVG(pgl.minutes), 
                   MAX(psq.shot_quality_avg), MAX(psq.at_rim_frequency), MAX(psq.corner3_frequency)
            FROM player_game_logs pgl
            LEFT JOIN player_season_quality psq ON pgl.player_id = psq.player_id AND psq.season = '2025-26'
            WHERE pgl.team_abbreviation = ? AND pgl.game_date >= date('now', '-30 days')
            GROUP BY pgl.player_id, pgl.player_name, pgl.team_abbreviation
            HAVING COUNT(pgl.player_id) >= 3
            ORDER BY AVG(pgl.minutes) DESC LIMIT ?
        '''
        cursor.execute(query, (team_abbr, limit))
        rows = cursor.fetchall()
        conn.close()

        roster = []
        for row in rows:
            fga, fta, tov, mins = row[6] or 0, row[8] or 0, row[13] or 0, row[14] or 0
            base_usg = round(((fga + 0.44*fta + tov)/mins)/2.1, 3) if mins > 0 else 0
            
            # Extract PBP Stats
            shot_quality = row[15] if row[15] is not None else 0.53  # League avg fallback
            at_rim_freq = row[16] if row[16] is not None else 0.0
            corner3_freq = row[17] if row[17] is not None else 0.0

            roster.append({
                'player_id': row[0], 'PLAYER_NAME': row[1], 'TEAM_ABBREVIATION': row[2],
                'PTS': round(row[3] or 0, 1), 'REB': round(row[4] or 0, 1), 'AST': round(row[5] or 0, 1),
                'FGA': round(fga, 1), 'FG3A': round(row[7] or 0, 1), 'FTA': round(fta, 1),
                'OREB': round(row[9] or 0, 1), 'DREB': round(row[10] or 0, 1),
                'STL': round(row[11] or 0, 1), 'BLK': round(row[12] or 0, 1), 'TOV': round(tov, 1),
                'MIN': round(mins, 1), 'base_usg': base_usg, 'base_min': round(mins, 1),
                'pbp_shot_quality': round(shot_quality, 3),
                'pbp_rim_freq': round(at_rim_freq, 3),
                'pbp_corner3_freq': round(corner3_freq, 3)
            })
        return roster

    def fetch_props_for_game(self, game_id: str) -> Dict[str, Dict]:
        return self.gate.games.get(game_id, {}).get('props', {})

    def match_props_to_roster(self, props_data: Dict, roster: List[Dict]) -> List[Dict]:
        matched = []
        for p in roster:
            if p['PLAYER_NAME'] in props_data:
                pc = p.copy()
                pc['sportsbook_props'] = props_data[p['PLAYER_NAME']]
                matched.append(pc)
        return matched

    def build_simulation_scenario(self, game_data: Dict, home_roster: List[Dict], away_roster: List[Dict]) -> Dict:
        # Get referee data (now a dict with pace_impact, whistle_impact, crew, confidence)
        ref_data = game_data.get('archetypes', {}).get('ref_data', {
            'pace_impact': 1.0, 'whistle_impact': 1.0, 'crew': [], 'confidence': 0.0
        })
        return {
            'scenario_name': game_data.get('matchup', 'UNKNOWN').replace(' @ ', '_vs_').replace(' ', '_'),
            'ref_data': ref_data,  # Pass full dict for pace AND whistle impact
            'pace_factor': 1.0, 'def_factor': 1.0, 'days_rest': 1,
            'players': home_roster + away_roster
        }

    def build_reporter_input(self, sim_results: List[Dict], game_data: Dict, props_data: Dict) -> List[Dict]:
        STAT_MAPPING = {
            'PTS': 'proj_pts', 'REB': 'proj_reb', 'AST': 'proj_ast',
            'FG3M': 'proj_3pm', 'OREB': 'proj_oreb', 'MIN': 'proj_min',
            'FGA': 'proj_fga', 'FTA': 'proj_fta'
        }
        home, away = self.gate._get_abbr(game_data.get('home')), self.gate._get_abbr(game_data.get('away'))
        spread = game_data.get('vegas', {}).get('spread', 0)
        total = game_data.get('vegas', {}).get('total', 0)
        
        players = []
        for sim in sim_results:
            p_name = sim.get('PLAYER_NAME')
            if p_name not in props_data: continue
            
            p_dict = {
                'name': p_name, 'team': sim.get('TEAM'), 'opponent': away if sim.get('TEAM') == home else home,
                'status': sim.get('status', 'Active'), 'scenario': sim.get('SCENARIO', 'BASE'),
                'decision_note': sim.get('decision_note', ''),  # Captured from Yak
                'notes': '', 'odds': {'spread': spread, 'total': total},
                'base_pts': sim.get('PTS', 0), 'base_reb': sim.get('REB', 0), 
                'base_ast': sim.get('AST', 0), 'base_3pm': sim.get('FG3M', 0),
                'base_min': sim.get('MIN', 0), 'base_usg': sim.get('base_usg', 0)
            }
            
            # Map stats
            for c_key, f_key in STAT_MAPPING.items(): p_dict[f_key] = sim.get(c_key, 0)
            
            # Format props
            props_fmt = {}
            for k, v in props_data[p_name].items():
                try: 
                    # Handle both new format (dict with odds) and old format (line only)
                    if isinstance(v, dict):
                        # Module A v9.3+ format (with line shopping)
                        line = float(v.get('line', 0))
                        
                        # Fix: Handle explicit None values (key exists but value is None)
                        val_over = v.get('odds_over')
                        val_under = v.get('odds_under')
                        
                        o_over = val_over if val_over is not None else -110
                        o_under = val_under if val_under is not None else -110
                        
                        # NEW: Extract bookmaker sources (Line Shopping V2.0)
                        book_over = v.get('book_over', 'consensus')
                        book_under = v.get('book_under', 'consensus')
                    else:
                        # Legacy fallback
                        line = float(v)
                        o_over = -110
                        o_under = -110
                        book_over = 'legacy'
                        book_under = 'legacy'

                    mk = {'points': 'pts', 'rebounds': 'reb', 'assists': 'ast', 'threes': '3pm', 'offensive_rebounds': 'oreb'}.get(k, k)
                    props_fmt[mk] = {
                        'line': line, 
                        'odds_over': o_over, 
                        'odds_under': o_under,
                        'book_over': book_over,
                        'book_under': book_under
                    }
                except: continue
            
            if props_fmt:
                p_dict['sportsbook_props'] = props_fmt
                
                # NEW: Calculate hit rates from simulation distributions
                # This is the CORRECT probability from 5000 Monte Carlo runs
                if '_distributions' in sim:
                    lines_for_calc = {k: v.get('line') for k, v in props_fmt.items() if isinstance(v, dict)}
                    hit_rates = self.sim.calculate_hit_rates(sim, lines_for_calc)
                    p_dict['sim_hit_rates'] = hit_rates  # e.g. {'pts': 0.62, 'reb': 0.55}
                
                yak = {'status': sim.get('status', 'ACTIVE'), 'note': sim.get('injury_note', '')}
                players.append(self.calib.calibrate_player(p_dict, yak))

        return [{
            'game_id': game_data.get('matchup', 'UNKNOWN').replace(' @ ', '_vs_'),
            'matchup': game_data.get('matchup', 'UNKNOWN'),
            'game_date': get_est_today(),
            'home_team': home, 'away_team': away, 'opponent': '',
            'spread': abs(spread) if spread != 'N/A' else 0,
            'ref_data': game_data.get('archetypes', {}).get('ref_data', {'pace_impact': 1.0, 'whistle_impact': 1.0, 'crew': [], 'confidence': 0.0}),
            'players': players
        }]

    def run_daily_cycle(self):
        print("\n" + "="*50)
        print("   >>> STARTING DAILY SIMULATION CYCLE <<<")
        print("   Mode: Production v2.0")
        print("="*50)

        # STEP 0: LOAD DAILY LOCK CONFIG
        lock_config = get_target_config()
        if lock_config:
            mode = lock_config.get('mode', 'LIVE')
            print(f"   📋 Daily Lock: {lock_config.get('lock_date')} | Mode: {mode}")

        # STEP 1: FETCH SLATE
        self.gate.fetch_live_slate()

        # --- APPLY GAME LIMIT (for testing) ---
        limit_games = os.getenv('LIMIT_GAMES')
        if limit_games:
            limit_games = int(limit_games)
            games_list = list(self.gate.games.items())
            if len(games_list) > limit_games:
                print(f"🧪 TEST MODE: Limiting to {limit_games} game(s) (found {len(games_list)})")
                # Keep only the first N games
                limited_games = dict(games_list[:limit_games])
                self.gate.games = limited_games

        # --- APPLY DAILY LOCK FILTERING (if TESTING mode) ---
        if lock_config:
            # Convert games dict to list for filtering
            games_list = [{'game_id': gid, **gdata} for gid, gdata in self.gate.games.items()]
            
            # Apply matchup filtering
            games_list = filter_slate_by_config(games_list, lock_config)
            
            # Apply spread/total filters
            games_list = apply_filters(games_list, lock_config)
            
            # Convert back to dict
            self.gate.games = {g['game_id']: g for g in games_list}
        
        # --- LEGACY: CLI TARGET TEAMS FILTER (still supported) ---
        if self.target_teams:
            targets = [t.upper() for t in self.target_teams]
            print(f"   🎯 TARGET FILTER ACTIVE: {targets}")
            
            filtered = {}
            for gid, gdata in self.gate.games.items():
                h = self.gate._get_abbr(gdata.get('home', ''))
                a = self.gate._get_abbr(gdata.get('away', ''))
                if h in targets or a in targets:
                    filtered[gid] = gdata
                    print(f"      ✅ LOCKED: {gdata.get('matchup', gid)}")
            
            self.gate.games = filtered
            print(f"   ✅ Slate reduced to {len(self.gate.games)} games.")

        if not self.gate.games:
            print("❌ No games found. Exiting.")
            return

        # STEP 2: FETCH PROPS
        self.gate.fetch_comprehensive_props(limit_games=len(self.gate.games))
        print("✅ Props loaded.")

        all_scenarios = []
        
        # STEP 3: BUILD SCENARIOS
        print("[step 3] Building Scenarios & Rosters...")
        for game_id, game_data in self.gate.games.items():
            if not game_data.get('props'): continue
            
            h_abbr = self.gate._get_abbr(game_data['home'])
            a_abbr = self.gate._get_abbr(game_data['away'])
            
            print(f"   > Processing {game_data['matchup']}...")
            
            h_roster = self.get_active_roster(h_abbr)
            a_roster = self.get_active_roster(a_abbr)
            h_matched = self.match_props_to_roster(self.fetch_props_for_game(game_id), h_roster)
            a_matched = self.match_props_to_roster(self.fetch_props_for_game(game_id), a_roster)
            
            if not h_matched and not a_matched: continue

            # Yak Filter
            final_h, final_a = [], []
            for p in h_matched:
                status = self.yak.get_player_status(p['PLAYER_NAME'], h_abbr)
                p['status'], p['injury_status'], p['injury_note'] = status['status'], status['status'], status.get('note', '')
                if status['status'] not in ['OUT', 'DOUBTFUL']: final_h.append(p)
            
            for p in a_matched:
                status = self.yak.get_player_status(p['PLAYER_NAME'], a_abbr)
                p['status'], p['injury_status'], p['injury_note'] = status['status'], status['status'], status.get('note', '')
                if status['status'] not in ['OUT', 'DOUBTFUL']: final_a.append(p)

            # Build Base & Fork Scenarios
            base = self.build_simulation_scenario(game_data, final_h, final_a)
            forks = self.scenario_builder.generate_scenarios([base])
            print(f"      ↳ Generated {len(forks)} scenarios")
            
            for sc in forks:
                all_scenarios.append({'scenario': sc, 'game_data': game_data, 'props_data': self.fetch_props_for_game(game_id)})

        # STEP 4: RUN SIMS & RESOLVE SCENARIOS
        print(f"[step 4] Running Monte Carlo Simulations ({len(all_scenarios)} scenarios)...")
        
        # Group scenarios by game to handle forks correctly
        games_batch = {}
        for item in all_scenarios:
            gid = item['game_data']['matchup']
            if gid not in games_batch: games_batch[gid] = []
            games_batch[gid].append(item)
            
        processed_slate = []
        
        for gid, items in games_batch.items():
            try:
                # 1. Run all sims for this game (Base + Forks)
                game_sim_results = []
                for item in items:
                    res = self.sim.run_simulation_batch([item['scenario']])
                    # Propagate scenario name
                    for r in res: r['SCENARIO'] = item['scenario']['scenario_name']
                    game_sim_results.extend(res)
                
                # 2. Resolve Scenarios via Yak (Handle Injuries)
                # This picks the correct scenario for each player based on live status
                final_game_results = self.yak.resolve_scenarios(game_sim_results)
                
                # 3. Build Report
                # Use game/props data from the first item (same for all in batch)
                first = items[0]
                processed_slate.extend(self.build_reporter_input(final_game_results, first['game_data'], first['props_data']))
                
            except Exception as e:
                print(f"⚠️  Sim failed for {gid}: {e}")

        # STEP 5: REPORT
        print("[step 5] Generating Daily Briefing (Module F)...")
        briefing, image_path = self.reporter.generate_report(processed_slate)
        print("\n" + "="*50)
        print("DAILY BRIEFING GENERATED")
        print("="*50)
        print(briefing)
        
        with open("daily_briefing.txt", "w") as f: f.write(briefing)
        print("\n✅ Saved to daily_briefing.txt")
        print(f"✅ Visual Card saved to: {image_path}")
        
        if self.send_telegram:
            print("[step 6] Sending Telegram Briefing...")
            send_message(f"🚨 **LUDI EVENING LOCK** 🚨\n\n{briefing}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="interactive")
    parser.add_argument("--games", nargs='+', help="Target teams (e.g. CLE SAC)")
    parser.add_argument("--send-telegram", action='store_true', help="Send results via Telegram")
    args = parser.parse_args()

    if args.mode == "pm_briefing":
        ProjectManagerBot().generate_briefing(mode="morning")
    elif args.mode == "pm_debrief":
        ProjectManagerBot().generate_briefing(mode="nightly")
    else:
        app = LudiOrchestrator(target_teams=args.games, send_telegram=args.send_telegram)
        app.run_daily_cycle()
