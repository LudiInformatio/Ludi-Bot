import sys
import pandas as pd
import time
import logging
import argparse
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

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
    
    # Utilities
    from utils.pm_bot import ProjectManagerBot
    from utils.api_monitor import get_monitor
except ImportError as e:
    print(f"CRITICAL ERROR: Missing a Ludi Module. {e}")
    sys.exit(1)

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format="[LUDI-CORE] %(message)s")

class LudiOrchestrator:
    def __init__(self):
        print("\n" + "="*50)
        print("   LUDI INFORMATIO | SYSTEM INITIALIZATION")
        print("   Architecture: Modules A-H (Production v2.0)")
        print("="*50)

        # 1. INITIALIZE ALL SYSTEMS
        self.gate = Gatekeeper()
        self.historian = LudiHistorian()
        self.sim = LudiOracle()
        self.yak = LudiYak()
        self.calib = LudiCalibrator()
        self.reporter = LudiReporter()
        self.zebras = LudiRefEngine()
        
        # Build Ref DB immediately
        self.zebras.build_ref_database()
        
        # Database path
        self.db_path = "ludi.db"

    def get_active_roster(self, team_abbr: str, limit: int = 8) -> List[Dict]:
        """
        Query database for top N players by minutes played in last 20 days.
        Returns list of player dicts with season averages.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = '''
            SELECT
                player_id,
                player_name,
                team_abbreviation,
                AVG(pts) as avg_pts,
                AVG(reb) as avg_reb,
                AVG(ast) as avg_ast,
                AVG(fga) as avg_fga,
                AVG(fg3a) as avg_fg3a,
                AVG(fta) as avg_fta,
                AVG(oreb) as avg_oreb,
                AVG(dreb) as avg_dreb,
                AVG(stl) as avg_stl,
                AVG(blk) as avg_blk,
                AVG(tov) as avg_tov,
                AVG(minutes) as avg_min,
                AVG(fg_pct) as fg_pct,
                AVG(fg3_pct) as fg3_pct,
                AVG(ft_pct) as ft_pct,
                COUNT(*) as games_played
            FROM player_game_logs
            WHERE team_abbreviation = ?
            AND game_date >= date('now', '-30 days')
            GROUP BY player_id, player_name, team_abbreviation
            HAVING COUNT(*) >= 3
            ORDER BY AVG(minutes) DESC
            LIMIT ?
        '''

        cursor.execute(query, (team_abbr, limit))
        rows = cursor.fetchall()
        conn.close()

        roster = []
        for row in rows:
            roster.append({
                'player_id': row[0],
                'PLAYER_NAME': row[1],
                'TEAM_ABBREVIATION': row[2],
                'PTS': round(row[3], 1) if row[3] else 0,
                'REB': round(row[4], 1) if row[4] else 0,
                'AST': round(row[5], 1) if row[5] else 0,
                'FGA': round(row[6], 1) if row[6] else 0,
                'FG3A': round(row[7], 1) if row[7] else 0,
                'FTA': round(row[8], 1) if row[8] else 0,
                'OREB': round(row[9], 1) if row[9] else 0,
                'DREB': round(row[10], 1) if row[10] else 0,
                'STL': round(row[11], 1) if row[11] else 0,
                'BLK': round(row[12], 1) if row[12] else 0,
                'TOV': round(row[13], 1) if row[13] else 0,
                'MIN': round(row[14], 1) if row[14] else 0,
                'FG_PCT': round(row[15], 3) if row[15] else 0.450,
                'FG3_PCT': round(row[16], 3) if row[16] else 0.350,
                'FT_PCT': round(row[17], 3) if row[17] else 0.750,
                'games_played': row[18]
            })

        return roster

    def fetch_props_for_game(self, game_id: str) -> Dict[str, Dict]:
        if game_id not in self.gate.games:
            return {}
        return self.gate.games[game_id].get('props', {})

    def match_props_to_roster(self, props_data: Dict, roster: List[Dict]) -> List[Dict]:
        matched_roster = []
        for player in roster:
            player_name = player['PLAYER_NAME']
            if player_name in props_data:
                player_copy = player.copy()
                player_copy['sportsbook_props'] = props_data[player_name]
                matched_roster.append(player_copy)
        return matched_roster

    def build_simulation_scenario(self, game_data: Dict, home_roster: List[Dict], away_roster: List[Dict]) -> Dict:
        matchup = game_data.get('matchup', 'UNKNOWN')
        ref_impact = game_data.get('archetypes', {}).get('ref_impact', 1.0)
        
        # Combine rosters
        all_players = home_roster + away_roster
        
        # Create scenario name
        scenario_name = matchup.replace(' @ ', '_vs_').replace(' ', '_')
        
        return {
            'scenario_name': scenario_name,
            'ref_impact': ref_impact,
            'pace_factor': 1.0,
            'def_factor': 1.0,
            'days_rest': 1,
            'players': all_players
        }

    def build_reporter_input(self, sim_results: List[Dict], game_data: Dict, props_data: Dict) -> List[Dict]:
        STAT_MAPPING = {
            'PTS': 'proj_pts', 'REB': 'proj_reb', 'AST': 'proj_ast',
            'FG3M': 'proj_3pm', 'OREB': 'proj_oreb', 'MIN': 'proj_min'
        }
        
        players = []
        for sim in sim_results:
            player_name = sim.get('PLAYER_NAME')
            team = sim.get('TEAM')
            
            player_dict = {
                'name': player_name,
                'team': team,
                'status': 'Active',
                'scenario': sim.get('SCENARIO', 'BASE')
            }
            
            for c_key, f_key in STAT_MAPPING.items():
                player_dict[f_key] = sim.get(c_key, 0)
                
            if player_name in props_data:
                props_formatted = {}
                for stat_key, line_value in props_data[player_name].items():
                    if line_value == 'N/A' or line_value is None: continue
                    try:
                        line_float = float(line_value)
                    except: continue
                    
                    mapped_key = {
                        'points': 'pts', 'rebounds': 'reb', 'assists': 'ast',
                        'threes': '3pm', 'offensive_rebounds': 'oreb'
                    }.get(stat_key, stat_key)
                    
                    props_formatted[mapped_key] = {
                        'line': line_float,
                        'odds_over': -110,
                        'odds_under': -110
                    }
                
                if props_formatted:
                    player_dict['sportsbook_props'] = props_formatted
                    players.append(player_dict)

        spread = game_data.get('vegas', {}).get('spread', 0)
        if spread == 'N/A': spread = 0
        ref_impact = game_data.get('archetypes', {}).get('ref_impact', 1.0)
        
        return [{
            'game_id': game_data.get('matchup', 'UNKNOWN').replace(' @ ', '_vs_'),
            'game_date': datetime.now().strftime('%Y-%m-%d'),
            'home_team': self.gate._get_abbr(game_data.get('home')),
            'away_team': self.gate._get_abbr(game_data.get('away')),
            'opponent': '', # Filled by reporter logic if needed
            'spread': abs(spread) if spread else 0,
            'ref_impact': ref_impact,
            'players': players
        }]

    def run_daily_cycle(self):
        print("\n" + "="*50)
        print("   >>> STARTING DAILY SIMULATION CYCLE <<<")
        print("   Mode: Production v2.0")
        print("="*50)

        # STEP 1: FETCH SLATE
        print("[step 1] Fetching Live Games (Module A)...")
        self.gate.fetch_live_slate()
        if not self.gate.games:
            print("❌ No games found. Exiting.")
            return

        print(f"✅ Found {len(self.gate.games)} games.")

        # STEP 2: FETCH PROPS
        print("[step 2] Fetching Player Props (Module A)...")
        # In production we might want comprehensive, for now use generic fetch
        self.gate.fetch_comprehensive_props(limit_games=15)
        print("✅ Props loaded.")

        all_scenarios = []
        
        # STEP 3: BUILD SCENARIOS
        print("[step 3] Building Scenarios & Rosters...")
        for game_id, game_data in self.gate.games.items():
            if not game_data.get('props'): continue
            
            home_team = self.gate._get_abbr(game_data['home'])
            away_team = self.gate._get_abbr(game_data['away'])
            
            if not home_team or not away_team: continue
            
            print(f"   > Processing {game_data['matchup']}...")
            
            # Get Rosters
            home_roster = self.get_active_roster(home_team)
            away_roster = self.get_active_roster(away_team)
            
            # Match Props
            props_data = self.fetch_props_for_game(game_id)
            home_matched = self.match_props_to_roster(props_data, home_roster)
            away_matched = self.match_props_to_roster(props_data, away_roster)
            
            if not home_matched and not away_matched:
                continue

            # Check Injuries (Yak)
            # TODO: Integrate Module D calls here to update status
            
            # Build Scenario
            scenario = self.build_simulation_scenario(game_data, home_matched, away_matched)
            all_scenarios.append({
                'scenario': scenario,
                'game_data': game_data,
                'props_data': props_data
            })

        if not all_scenarios:
            print("❌ No valid scenarios generated.")
            return

        # STEP 4: RUN SIMULATIONS
        print(f"[step 4] Running Monte Carlo Simulations ({len(all_scenarios)} games)...")
        processed_slate = []
        
        for item in all_scenarios:
            try:
                sim_results = self.sim.run_simulation_batch([item['scenario']])
                reporter_input = self.build_reporter_input(sim_results, item['game_data'], item['props_data'])
                processed_slate.extend(reporter_input)
            except Exception as e:
                print(f"⚠️  Sim failed for {item.get('game_data', {}).get('matchup')}: {e}")

        # STEP 5: GENERATE REPORT
        print("[step 5] Generating Daily Briefing (Module F)...")
        briefing = self.reporter.generate_report(processed_slate)

        print("\n" + "="*50)
        print("DAILY BRIEFING GENERATED")
        print("="*50)
        print(briefing)
        
        with open("daily_briefing.txt", "w") as f:
            f.write(briefing)
        print("\n✅ Saved to daily_briefing.txt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ludi Informatio Manager")
    parser.add_argument("--mode", type=str, default="interactive", 
                        choices=["interactive", "briefing", "debrief", "pm_briefing", "pm_debrief"],
                        help="Operation mode")
    
    args = parser.parse_args()

    if args.mode == "pm_briefing":
        bot = ProjectManagerBot()
        bot.generate_briefing(mode="morning")
    
    elif args.mode == "pm_debrief":
        bot = ProjectManagerBot()
        bot.generate_briefing(mode="nightly")

    elif args.mode == "interactive":
        app = LudiOrchestrator()
        app.run_daily_cycle()
        
    else:
        print(f"Mode {args.mode} not yet implemented.")