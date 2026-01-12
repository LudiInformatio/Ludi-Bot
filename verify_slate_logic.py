#!/usr/bin/env python
"""
verify_slate_logic.py - The "Narrative" Stress Test

Purpose:
Run the full Ludi Pipeline for a single targeted game to verify:
1. Archetype/Matchup Logic (The "Story")
2. Referee Impact (The "Zebra Factor")
3. Scenario Forks (The "What If")

Usage:
python3 verify_slate_logic.py --game "LAL" 
"""

import argparse
import sys
from module_a import Gatekeeper
from module_g import LudiRefEngine
from module_e import LudiCalibrator
from module_d import LudiYak
from module_x_scenario import ScenarioBuilder

class SlateVerifier:
    def __init__(self):
        print("\n" + "="*60)
        print("🕵️  SLATE LOGIC VERIFIER")
        print("    Validating: Archetypes + Refs + Scenarios")
        print("="*60)
        
        self.gate = Gatekeeper()
        self.refs = LudiRefEngine()
        self.calib = LudiCalibrator()
        self.yak = LudiYak()
        self.scen = ScenarioBuilder()

    def run_check(self, target_team_abbr):
        # 1. Fetch Game Data
        print(f"\n[1] Fetching Data for Team: {target_team_abbr}...")
        self.gate.fetch_live_slate()
        
        # Fuzzy match game
        target = None
        target_clean = self.refs._resolve_team_abbr(target_team_abbr) or target_team_abbr.upper()
        
        for gid, data in self.gate.games.items():
            home_abbr = self.refs._resolve_team_abbr(data['home'])
            away_abbr = self.refs._resolve_team_abbr(data['away'])
            
            if target_clean in [home_abbr, away_abbr]:
                target = data
                target['game_id'] = gid
                break
        
        if not target:
            print(f"❌ Game for {target_team_abbr} not found on live slate.")
            print(f"   Available Games: {list(self.gate.games.keys())}")
            return

        print(f"   ✅ Found: {target['matchup']}")

        # 2. Referee Check
        print(f"\n[2] Checking The Zebras (Module G)...")
        # Build Ref DB
        ref_assignments = self.refs.build_ref_database()
        
        # Resolve Home Team Abbr for lookup
        home_team_full = target['home']
        home_abbr = self.refs._resolve_team_abbr(home_team_full)
        
        print(f"   Looking up refs for Home Team: {home_abbr}...")
        
        if home_abbr in ref_assignments:
            crew = ref_assignments[home_abbr]
            print(f"   🦓 Assigned Crew: {', '.join(crew)}")
            ref_impact = self.refs.get_game_impact(home_abbr)
            print(f"   ⚖️  Crew Impact Factor: {ref_impact:.3f}")
            target['ref_impact'] = ref_impact
            
            if ref_impact > 1.02:
                print("      -> PRO-OVER / WHISTLE HAPPY")
            elif ref_impact < 0.98:
                print("      -> PRO-UNDER / LET THEM PLAY")
            else:
                print("      -> NEUTRAL")
        else:
            print(f"   ⚠️  No refs found for {home_abbr}. Using Neutral (1.0).")
            print(f"       (Assignments found for: {list(ref_assignments.keys())})")
            target['ref_impact'] = 1.0

        # 3. Roster & Archetype Check
        print(f"\n[3] Analyzing Rosters (Module E)...")
        
        home_team = target['home']
        away_team = target['away']
        
        # Create "Test Subjects" to verify logic flows
        # We simulate stats for a Star and a Big to see classification
        players = [
            {
                'name': f"{home_team} Star", 'PLAYER_NAME': f"{home_team} Star", 
                'team': home_team, 'TEAM_ABBREVIATION': home_team, 
                'PLAYER_ID': 101,
                'opponent': away_team,
                'base_pts': 28.5, 'base_ast': 9.2, 'base_usg': 0.35, 'base_tpm': 3.1, 'base_reb': 5.0,
                'base_stl': 1.2, 'base_blk': 0.4, 'base_min': 36.0,
                'status': 'Active' 
            },
            {
                'name': f"{away_team} Big", 'PLAYER_NAME': f"{away_team} Big",
                'team': away_team, 'TEAM_ABBREVIATION': away_team,
                'PLAYER_ID': 102,
                'opponent': home_team,
                'base_pts': 18.0, 'base_ast': 5.5, 'base_usg': 0.22, 'base_tpm': 0.5, 'base_reb': 11.0,
                'base_stl': 0.8, 'base_blk': 1.2, 'base_oreb': 2.5, 'base_min': 34.0,
                'status': 'Active'
            }
        ]
        
        target['players'] = players

        for p in players:
            # Calibration (Archetypes)
            yak_report = {'status': p['status'], 'note': 'Simulated'}
            calibrated = self.calib.calibrate_player(p, yak_report)
            
            arch = calibrated.get('archetype', 'None')
            sec = calibrated.get('secondary_archetype', '')
            note = calibrated.get('notes', '')
            
            print(f"     🏷️  {p['name']}:")
            print(f"         Primary:   {arch}")
            if sec:
                print(f"         Secondary: {sec}")
            print(f"         Notes:     {note}")

        # 4. Scenario Check
        print(f"\n[4] Generating Scenarios (Module X)...")
        # Force one player to GTD to test fork
        target['players'][0]['status'] = 'GTD' # Set Star to GTD
        
        scenarios = self.scen.generate_scenarios([target])
        
        print(f"   Generated {len(scenarios)} Scenarios:")
        for sc in scenarios:
            print(f"   - {sc['scenario_name']}")
            if "WITHOUT" in sc['scenario_name']:
                print("     (Usage Vacuum Logic Active)")

        print("\n" + "="*60)
        print("✅ VERIFICATION COMPLETE")
        print("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=str, required=True, help="Target Team Abbr (e.g. LAL, CLE)")
    args = parser.parse_args()
    
    verifier = SlateVerifier()
    verifier.run_check(args.game)
