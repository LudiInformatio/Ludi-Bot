import sys
import pandas as pd
import time
import logging
from datetime import datetime

# ====================================================
# LUDI INFORMATIO | CENTRAL ORCHESTRATOR
# ====================================================

# --- IMPORT ARCHITECTURE (MODULES A-G) ---
# Ensure your files are named module_a.py, module_b.py, etc.
try:
    import config
    from module_a import LudiGatekeeper   # The Gatekeeper (Lines)
    from module_b import LudiEngine       # The Engine (Stats/Trends)
    from module_c import LudiSimulator    # The Simulator (Math)
    from module_d import LudiYak          # The Yak (News)
    from module_e import LudiCalibrator   # The Calibrator (Adjustments)
    from module_f import LudiReporter     # The Reporter (Briefing)
    from module_g import LudiRefEngine    # The Zebras (Referees)
except ImportError as e:
    print(f"CRITICAL ERROR: Missing a Ludi Module. {e}")
    sys.exit(1)

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format="[LUDI-CORE] %(message)s")

class LudiOrchestrator:
    def __init__(self):
        print("\n" + "="*50)
        print("   LUDI INFORMATIO | SYSTEM INITIALIZATION")
        print("   Architecture: Modules A-G (Full Stack)")
        print("="*50)

        # 1. INITIALIZE ALL SYSTEMS
        self.gate = LudiGatekeeper()
        self.engine = LudiEngine()
        self.sim = LudiSimulator()
        self.yak = LudiYak()
        self.calib = LudiCalibrator()
        self.reporter = LudiReporter()
        self.zebras = LudiRefEngine()
        
        # Build Ref DB immediately
        self.zebras.build_ref_database()

    def get_roster_for_game(self, team_abbr):
        """
        Helper: Filters Module B's history DB to find active players for a team.
        """
        if self.engine.history_df.empty:
            return []
            
        # Filter by Team Abbreviation (assuming 'TEAM_ABBREVIATION' exists in NBA API data)
        # We look at the last 15 days to get the current rotation
        recent_date = pd.Timestamp.now() - pd.Timedelta(days=20)
        
        mask = (self.engine.history_df['TEAM_ABBREVIATION'] == team_abbr) & \
               (self.engine.history_df['GAME_DATE'] >= recent_date)
               
        team_df = self.engine.history_df[mask]
        
        # Get unique players who have played recently
        # Return list of (ID, Name)
        roster = team_df[['PLAYER_ID', 'PLAYER_NAME']].drop_duplicates()
        return roster.to_dict('records')

    def run_daily_cycle(self):
        print("\n" + "="*50)
        print("   >>> STARTING DAILY SIMULATION CYCLE <<<")
        print("="*50)

        # -------------------------------------------------
        # STEP 1: FETCH THE SLATE (Module A)
        # -------------------------------------------------
        slate_result = self.gate.fetch_slate()
        if slate_result['status'] != "SUCCESS":
            print("CRITICAL: Gatekeeper failed to retrieve odds.")
            return

        games = slate_result['data']['rosters']['body']
        all_bets = [] # To store valid plays
        streaks = []  # To store heat check data

        print(f"\n[CORE] Processing {len(games)} Games...")

        # -------------------------------------------------
        # STEP 2: ANALYZE EACH GAME
        # -------------------------------------------------
        for game in games:
            home = game['home']
            away = game['away']
            vegas_total = game['odds']['total']
            vegas_spread = game['odds']['spread']

            # A. GET REF IMPACT (Module G)
            # This adjusts the pace. If Scott Foster is reffing, maybe pace slows down.
            ref_factor = self.zebras.get_game_impact(home, away)
            
            # Base Pace (League Avg) * Ref Factor
            game_pace = 99.5 * ref_factor 
            
            game_env = {
                "pace": game_pace,
                "blowout_risk": abs(vegas_spread) > 14.5
            }

            print(f"\n   ðŸ€ MATCHUP: {away} @ {home} (Ref Factor: {ref_factor})")

            # B. SIMULATE PLAYERS (Modules B -> C -> D -> E)
            # We combine Home and Away rosters
            rosters = self.get_roster_for_game(home) + self.get_roster_for_game(away)
            
            for player in rosters:
                pid = player['PLAYER_ID']
                pname = player['PLAYER_NAME']
                
                # 1. ENGINE (Module B): Get Waterfall Trends
                analysis = self.engine.analyze_player(pid, pname)
                if not analysis: continue

                # Check for Streaks (Module F Helper)
                l5_pts = analysis['raw_trends'].get('l5_pts', 0)
                if l5_pts > 25.0: # Simple threshold for Heat Check
                    streaks.append({
                        "player": pname, "stat": "PTS", 
                        "l5": l5_pts, "line": 0 # Placeholder
                    })

                # 2. YAK (Module D): Check News
                # We check the player's team to find specific news
                p_team = home if player in self.get_roster_for_game(home) else away
                news_report = self.yak.get_player_status(pname, p_team)

                # 3. SIMULATOR (Module C): Run Math
                # We assume a generic opponent defense profile for now
                opp_profile = {"rank_pnr_handler": 15, "rank_rebounding": 15}
                
                # Convert Engine analysis to Simulator profile
                sim_profile = {
                    "name": pname,
                    "base_pts": analysis['final_projections']['pts'],
                    "base_reb": analysis['final_projections']['reb'],
                    "base_ast": analysis['final_projections']['ast'],
                    "base_3pm": analysis['final_projections']['3pm']
                }
                
                sim_results = self.sim.simulate_player_props(sim_profile, game_env, opp_profile)

                # 4. CALIBRATOR (Module E): Apply Adjustments
                # This applies the 'Helio-Centric' boost and News filters
                # merging Sim results into the calibration packet
                packet_to_calibrate = {
                    "name": pname,
                    "final_projections": {
                        "pts": sim_results['proj_pts'],
                        "reb": sim_results['proj_reb'],
                        "ast": sim_results['proj_ast'],
                        "3pm": sim_results['proj_3pm']
                    },
                    "impact_stats": analysis['impact_stats']
                }
                
                final_packet = self.calib.calibrate_player(packet_to_calibrate, news_report)

                # -------------------------------------------------
                # STEP 3: FIND THE EDGE (Module F)
                # -------------------------------------------------
                # In a real run, we would match this against specific Prop Lines from Odds API.
                # For this version, we will assume a Standard Line (e.g. Waterfall Avg) to find "Value"
                # OR simply log high-value projections.
                
                # Example: If Final Proj > 20 and no major news
                final_pts = final_packet['final_projections']['pts']
                
                # Create a "Mock" Prop Line for demonstration (usually comes from Module A)
                mock_line = round(analysis['raw_trends'].get('season_pts', 0) * 1.0, 1)
                
                if final_pts > 10.0 and mock_line > 0:
                    edge = self.reporter.calculate_edge(final_pts, mock_line)
                    ev = self.reporter.calculate_ev(self.reporter.estimate_win_probability(edge), -110)
                    units = self.reporter.calculate_kelly(ev)
                    
                    if ev > 2.0: # Only keep positive EV
                        all_bets.append({
                            "type": "PROP",
                            "name": pname,
                            "bet_on": "Over PTS",
                            "line": mock_line,
                            "odds": -110,
                            "model_val": final_pts,
                            "ev": ev,
                            "units": units
                        })

        # -------------------------------------------------
        # STEP 4: GENERATE BRIEFING (Module F)
        # -------------------------------------------------
        print("\n[CORE] Simulation Complete. Generating Report...")
        
        # We pass empty list for 'best_games' for now, focusing on props
        briefing = self.reporter.create_daily_briefing([], all_bets, streaks)
        
        print(briefing)
        
        # OPTIONAL: Save to file
        with open("daily_briefing.txt", "w", encoding="utf-8") as f:
            f.write(briefing)

if __name__ == "__main__":
    app = LudiOrchestrator()
    app.run_daily_cycle()