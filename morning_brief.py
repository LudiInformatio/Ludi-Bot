import logging
import datetime
from module_a import Gatekeeper
from module_c import LudiOracle
from module_d import LudiYak
from module_e import LudiCalibrator
from module_f import LudiReporter
from module_g import LudiRefEngine
from module_h_historian import LudiHistorian
from module_x_scenario import ScenarioBuilder
from utils.render_full_report import create_briefing_card
from utils.telegram_notifier import send_photo, send_message
import main # Import to reuse helper methods if possible, or just copy critical logic

# Configure Logging
logging.basicConfig(level=logging.INFO, format="[MORNING-BRIEF] %(message)s")

import argparse

class MorningBriefEngine:
    def __init__(self, target_teams=None, mode="morning"):
        print("\n" + "="*50)
        print(f"   🌅 LUDI {mode.upper()} BRIEF ENGINE")
        print("   Status: Production | Visual: V1.0")
        print("="*50)
        
        self.target_teams = target_teams
        self.mode = mode
        
        # Orchestrator helper (The Central Brain)
        self.orch = main.LudiOrchestrator(send_telegram=False) 
        
        # Alias modules from the Orchestrator to ensure shared state
        self.gate = self.orch.gate
        self.yak = self.orch.yak
        self.sim = self.orch.sim
        self.calib = self.orch.calib
        self.zebras = self.orch.zebras
        self.scenario_builder = self.orch.scenario_builder
        self.reporter = self.orch.reporter

    def run(self):
        """
        Main Execution Flow:
        1. Fetch Slate & Refs
        2. Filter for Target Games
        3. Fetch Props
        4. Run Sims
        5. Filter Top 5 Plays
        6. Generate Visual Card
        7. Send to Telegram
        """
        # 1. Fetch Slate & Refs
        self.gate.fetch_live_slate()
        
        # --- FILTER TARGETS ---
        if self.target_teams:
            # Normalize to uppercase
            targets = [t.upper() for t in self.target_teams]
            print(f"🎯 TARGETING SPECIFIC TEAMS: {targets}")
            
            filtered = {}
            for gid, gdata in self.gate.games.items():
                h = self.gate._get_abbr(gdata['home'])
                a = self.gate._get_abbr(gdata['away'])
                
                # Check if EITHER team is in our target list
                if h in targets or a in targets:
                    filtered[gid] = gdata
                    
            self.gate.games = filtered
            
        if not self.gate.games:
            print("❌ No matching games found on today's slate. Aborting.")
            return

        print(f"✅ Processing {len(self.gate.games)} games.")
        print("🦓 Updating Referee Database...")
        self.zebras.build_ref_database()
        
        # 2. Fetch Props
        print("📊 Fetching Market Data...")
        self.gate.fetch_comprehensive_props(limit_games=len(self.gate.games))
        
        all_bets = []

        # 3. Build & Run Scenarios
        for game_id, game_data in self.gate.games.items():
            if not game_data.get('props'): continue
            
            print(f"   > Analyzing {game_data['matchup']}...")
            
            # Reusing Orchestrator Logic for Roster Building
            h_abbr = self.gate._get_abbr(game_data['home'])
            a_abbr = self.gate._get_abbr(game_data['away'])
            
            h_roster = self.orch.get_active_roster(h_abbr)
            a_roster = self.orch.get_active_roster(a_abbr)
            print(f"      ↳ Roster: {len(h_roster)} {h_abbr}, {len(a_roster)} {a_abbr}")
            
            props = self.orch.fetch_props_for_game(game_id)
            print(f"      ↳ Props Available: {len(props)} players")
            
            h_matched = self.orch.match_props_to_roster(props, h_roster)
            a_matched = self.orch.match_props_to_roster(props, a_roster)
            print(f"      ↳ Matched: {len(h_matched)} {h_abbr}, {len(a_matched)} {a_abbr}")
            
            if not h_matched and not a_matched: 
                print("      ⚠️  Skipping: No player props matched to roster.")
                continue

            # Apply Injury Filters (The Yak)
            final_h, final_a = [], []
            for p in h_matched:
                status = self.yak.get_player_status(p['PLAYER_NAME'], h_abbr)
                p['status'] = status['status']
                if status['status'] not in ['OUT', 'DOUBTFUL']: final_h.append(p)
            
            for p in a_matched:
                status = self.yak.get_player_status(p['PLAYER_NAME'], a_abbr)
                p['status'] = status['status']
                if status['status'] not in ['OUT', 'DOUBTFUL']: final_a.append(p)

            print(f"      ↳ Players: {len(final_h)} Home, {len(final_a)} Away")

            # Build Scenario
            base_scenario = self.orch.build_simulation_scenario(game_data, final_h, final_a)
            
            # Run Simulation
            try:
                # Running just the base scenario for the Morning Brief (Speed)
                sim_results = self.sim.run_simulation_batch([base_scenario])
                
                # Analyze Results (Module F Logic locally)
                processed = self.orch.build_reporter_input(sim_results, game_data, self.orch.fetch_props_for_game(game_id))
                
                # Accumulate for Final Report
                if processed:
                    all_bets.extend(processed)
                                
            except Exception as e:
                print(f"⚠️  Analysis failed for {game_id}: {e}")

        # 4. Generate Final Report & Visuals (Delegated to Module F)
        if not all_bets:
            print("⚠️  No data processed. Aborting.")
            return

        print(f"\n💎 Generating Report for {len(all_bets)} games...")
        
        # Determine Title based on Mode
        if self.mode == "evening":
            report_title = "LUDI EVENING LOCK"
            body = "Updated lines and injury adjustments."
        else:
            report_title = "LUDI MORNING BRIEF"
            body = "Top 5 Quality Plays + SGP Targets"
        
        # Module F handles Bet Logging, Tagging, and Image Generation
        text_report, image_path = self.reporter.generate_report(all_bets, title=report_title)
        
        if image_path:
            print(f"✅ Visual Card Ready: {image_path}")
            # 5. Send to Telegram (Visual Only)
            
            caption = (
                f"**{report_title} | {datetime.date.today().strftime('%b %d')}**\n"
                f"💎 {body}"
            )
            send_photo(image_path, caption=caption)
            print("🚀 Sent to Telegram!")
        else:
            print("❌ Failed to generate visual card.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["morning", "evening"], default="morning", help="Report mode")
    args = parser.parse_args()

    # --- MANUAL WATCHLIST CONFIG ---
    # Jan 13: PHX, MIA, CHI, HOU, SAS, OKC
    # Jan 14: CLE, PHI, NYK, SAC, UTA, CHI (Already in Jan 13 list)
    watchlist = [
        'PHX', 'MIA', 'CHI', 'HOU', 'SAS', 'OKC', # Jan 13
        'CLE', 'PHI', 'NYK', 'SAC', 'UTA'         # Jan 14
    ]
    
    engine = MorningBriefEngine(target_teams=watchlist, mode=args.mode)
    engine.run()
