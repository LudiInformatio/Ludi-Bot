#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from module_e import LudiCalibrator

# Create a test player to debug the modifier issue
def test_tyrese_maxey():
    calib = LudiCalibrator()
    
    # Create test player data based on Tyrese Maxey profile
    test_player = {
        'name': 'Tyrese Maxey',
        'PLAYER_NAME': 'Tyrese Maxey',
        'team': 'PHI',
        'opponent': 'TOR',  # Assume Toronto has BLITZ defense
        'archetype': 'ISO_ASSASSIN',
        'secondary_playtypes': ['ISO_SCORER', 'P&R_HANDLER'],
        'proj_pts': 27.5,  # Base projection
        'proj_ast': 4.0,
        'proj_tov': 2.0,
        'proj_3pm': 2.5,
        'notes': ''
    }
    
    print("=== BEFORE MODIFIERS ===")
    print(f"PTS: {test_player['proj_pts']}")
    print(f"AST: {test_player['proj_ast']}")
    print(f"TOV: {test_player['proj_tov']}")
    print(f"3PM: {test_player['proj_3pm']}")
    
    # Check what defense style Toronto uses
    tor_defense = calib.DEFENSIVE_STYLES.get('TOR', 'NEUTRAL')
    print(f"\nTOR Defense Style: {tor_defense}")
    
    # Test each modifier step by step
    test_copy = test_player.copy()
    
    # Step 1: Apply ISO_ASSASSIN vs BLITZ (if it exists)
    print(f"\n=== STEP 1: ISO_ASSASSIN vs {tor_defense} ===")
    if tor_defense == 'BLITZ':
        # ISO_ASSASSIN vs BLITZ: no direct pts modifier, covered by ISO_SCORER secondary
        print("No ISO_ASSASSIN vs BLITZ modifier found in code")
    elif tor_defense == 'PERIMETER':
        print("ISO_ASSASSIN vs PERIMETER: proj_pts *= 1.08")
        test_copy['proj_pts'] *= 1.08
    
    # Step 2: Apply ISO_SCORER vs BLITZ
    print(f"\n=== STEP 2: ISO_SCORER vs {tor_defense} ===")
    if 'ISO_SCORER' in test_copy['secondary_playtypes']:
        if tor_defense == 'BLITZ':
            print("ISO_SCORER vs BLITZ: proj_pts *= 0.92")
            test_copy['proj_pts'] *= 0.92
            print("ISO_SCORER vs BLITZ: proj_tov *= 1.12") 
            test_copy['proj_tov'] *= 1.12
    
    # Step 3: Apply P&R_HANDLER vs BLITZ  
    print(f"\n=== STEP 3: P&R_HANDLER vs {tor_defense} ===")
    if 'P&R_HANDLER' in test_copy['secondary_playtypes']:
        if tor_defense == 'BLITZ':
            print("P&R_HANDLER vs BLITZ: proj_ast *= 0.90")
            test_copy['proj_ast'] *= 0.90
            print("P&R_HANDLER vs BLITZ: proj_tov *= 1.15")
            test_copy['proj_tov'] *= 1.15
    
    print(f"\n=== EXPECTED FINAL ===")
    print(f"PTS: {test_copy['proj_pts']:.2f}")
    print(f"AST: {test_copy['proj_ast']:.2f}")
    print(f"TOV: {test_copy['proj_tov']:.2f}")
    print(f"3PM: {test_copy['proj_3pm']:.2f}")
    
    # Calculate expected multiplier
    expected_multiplier = test_copy['proj_pts'] / test_player['proj_pts']
    print(f"\nExpected PTS multiplier: {expected_multiplier:.3f}")
    
    print(f"\n=== ACTUAL BUG SCENARIO ===")
    print("If 0.92 became 1.92 (inverted):")
    bug_multiplier = (test_player['proj_pts'] * 1.08 * 1.92) / test_player['proj_pts'] 
    print(f"Buggy PTS multiplier: {bug_multiplier:.3f}")
    print(f"Buggy PTS: {test_player['proj_pts'] * bug_multiplier:.1f}")
    
    return test_copy

if __name__ == "__main__":
    test_tyrese_maxey()