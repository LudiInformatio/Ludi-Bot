
import sys
import argparse
import logging
from datetime import datetime
from module_f import LudiReporter
from module_a import Gatekeeper
from module_c import LudiOracle
from utils.telegram_notifier import send_message

# Setup Logging
logging.basicConfig(level=logging.INFO, format="[GAME-NOTES] %(message)s")

def send_specific_game_notes(home_team, away_team):
    print(f"\n🔎 SEARCHING SLATE FOR: {away_team} @ {home_team}")
    
    # 1. Initialize Modules
    gate = Gatekeeper()
    sim = LudiOracle()
    reporter = LudiReporter()
    
    # 2. Fetch Live Slate & Props
    gate.fetch_live_slate()
    gate.fetch_comprehensive_props(limit_games=5) # Ensure we get props for this game
    
    target_game = None
    
    # 3. Find the specific game
    for game_id, game in gate.games.items():
        # Check standard abbreviations
        h = gate._get_abbr(game['home'])
        a = gate._get_abbr(game['away'])
        
        if (h == home_team and a == away_team) or (h == away_team and a == home_team):
            target_game = game
            target_game_id = game_id
            break
            
    if not target_game:
        print(f"❌ Game {away_team} @ {home_team} not found in current slate.")
        # Try to list what WAS found
        print("   Current Slate:")
        for g in gate.games.values():
            print(f"   - {g['matchup']}")
        return

    print(f"✅ FOUND MATCHUP: {target_game['matchup']}")
    print(f"   Referees: {target_game.get('archetypes', {}).get('ref_crew', 'Pending')}")
    
    # 4. Run Simulation for this game ONLY
    # (We reuse the logic from main.py but isolated)
    
    # Get Rosters (using Orchestrator helper logic would be best, but we'll mock the minimal need here)
    # We need to instantiate the Orchestrator to use its helpers properly? 
    # Let's import the class from main to avoid code duplication.
    from main import LudiOrchestrator
    orchestrator = LudiOrchestrator()
    
    # Fetch Rosters
    home_roster = orchestrator.get_active_roster(home_team)
    away_roster = orchestrator.get_active_roster(away_team)
    
    # Match Props
    props_data = orchestrator.fetch_props_for_game(target_game_id)
    home_matched = orchestrator.match_props_to_roster(props_data, home_roster)
    away_matched = orchestrator.match_props_to_roster(props_data, away_roster)
    
    # Build Scenario
    scenario = orchestrator.build_simulation_scenario(target_game, home_matched, away_matched)
    
    # Run Sim
    print(f"🎲 Running Simulations for {scenario['scenario_name']}")
    sim_results = sim.run_simulation_batch([scenario])
    
    # Build Report Input
    processed_slate = orchestrator.build_reporter_input(sim_results, target_game, props_data)
    
    # 5. Generate & Send Report
    # We want a CUSTOM header for this, not the standard briefing.
    
    # Generate the standard blocks first
    standard_report = reporter.generate_report(processed_slate)
    
    # Custom Header
    header = f"📋 **GAME NOTES: {away_team} @ {home_team}**\n"
    header += f"📅 {datetime.now().strftime('%b %d')} | ⏰ 10:00 AM EST Update\n"
    
    # Ref Info (Crucial Requirement)
    refs = target_game.get('archetypes', {}).get('ref_crew', [])
    ref_impact = target_game.get('archetypes', {}).get('ref_impact', 1.0)
    
    if refs and refs != "Unknown":
        header += f"🦓 **Ref Crew:** {', '.join(refs)}\n"
        header += f"⚖️ **Ref Impact:** {ref_impact} (Avg: 1.0)\n"
    else:
        header += f"🦓 **Ref Crew:** Pending/Unknown\n"
        
    header += "──────────────\n"
    
    full_message = header + standard_report
    
    print("\n📨 Sending Game Notes to Telegram...")
    send_message(full_message)
    print("✅ Done.")

if __name__ == "__main__":
    # Default to MIL @ DEN if no args
    h = "DEN"
    a = "MIL"
    
    send_specific_game_notes(h, a)
