#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from module_e import LudiCalibrator

def test_full_calibrate():
    """Test the full calibrate method to find the bug source"""
    calib = LudiCalibrator()
    
    # Create test player data based on Tyrese Maxey profile
    test_player = {
        'name': 'Tyrese Maxey',
        'PLAYER_NAME': 'Tyrese Maxey', 
        'team': 'PHI',
        'opponent': 'TOR',  # Assume Toronto has BLITZ defense
        'position': 'G',
        # Base stats that get converted to proj stats
        'base_pts': 27.5,
        'base_ast': 4.0,
        'base_tov': 2.0,
        'base_3pm': 2.5,
        'base_min': 35.0,
        'base_fga': 18.0,
        'base_3pa': 7.0,
        'base_fta': 6.0,
        'base_reb': 3.0,
        'base_stl': 1.0,
        'base_blk': 0.2,
        'base_oreb': 0.5,
        'base_dreb': 2.5,
        'base_fg_pct': 0.46,
        'base_ft_pct': 0.89,
        # Required fields
        'notes': ''
    }
    
    # Mock yak report
    yak_report = {
        'status': 'ACTIVE',
        'injury': None
    }
    
    print("=== BEFORE CALIBRATION ===")
    print(f"Base PTS: {test_player['base_pts']}")
    print(f"Base AST: {test_player['base_ast']}")
    print(f"Base TOV: {test_player['base_tov']}")
    print(f"Base 3PM: {test_player['base_3pm']}")
    
    # Check what defense style Toronto uses
    tor_defense = calib.DEFENSIVE_STYLES.get('TOR', 'NEUTRAL')
    print(f"\nTOR Defense Style: {tor_defense}")
    
    # Run the full calibration
    try:
        calibrated = calib.calibrate_player(test_player, yak_report, use_synergy=False)
        
        print(f"\n=== AFTER CALIBRATION (use_synergy=False) ===")
        print(f"PTS: {calibrated.get('proj_pts', 'N/A')}")
        print(f"AST: {calibrated.get('proj_ast', 'N/A')}")
        print(f"TOV: {calibrated.get('proj_tov', 'N/A')}")
        print(f"3PM: {calibrated.get('proj_3pm', 'N/A')}")
        print(f"Archetype: {calibrated.get('archetype', 'N/A')}")
        print(f"Secondary Playtypes: {calibrated.get('secondary_playtypes', 'N/A')}")
        print(f"Notes: {calibrated.get('notes', 'N/A')}")
        
        # Calculate multiplier
        if 'proj_pts' in calibrated:
            multiplier = calibrated['proj_pts'] / test_player['base_pts']
            print(f"\nPTS Multiplier: {multiplier:.3f}")
            
            if multiplier > 1.5:
                print(f"🔴 CRITICAL: Found excessive multiplier! {multiplier:.3f}")
                return calibrated
        
    except Exception as e:
        print(f"ERROR in calibration: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Now test with Synergy enabled (this might be the source)
    try:
        calibrated_with_synergy = calib.calibrate_player(test_player, yak_report, use_synergy=True)
        
        print(f"\n=== AFTER CALIBRATION (use_synergy=True) ===")
        print(f"PTS: {calibrated_with_synergy.get('proj_pts', 'N/A')}")
        print(f"AST: {calibrated_with_synergy.get('proj_ast', 'N/A')}")
        print(f"TOV: {calibrated_with_synergy.get('proj_tov', 'N/A')}")
        print(f"3PM: {calibrated_with_synergy.get('proj_3pm', 'N/A')}")
        print(f"Notes: {calibrated_with_synergy.get('notes', 'N/A')}")
        
        # Calculate multiplier
        if 'proj_pts' in calibrated_with_synergy:
            multiplier = calibrated_with_synergy['proj_pts'] / test_player['base_pts']
            print(f"\nPTS Multiplier: {multiplier:.3f}")
            
            if multiplier > 1.5:
                print(f"🔴 CRITICAL: Found excessive multiplier with synergy! {multiplier:.3f}")
                return calibrated_with_synergy
                
    except Exception as e:
        print(f"ERROR in calibration with synergy: {e}")
        import traceback
        traceback.print_exc()
        
    return None

def check_boost_stat_implementation():
    """Check the _boost_stat implementation for bugs"""
    calib = LudiCalibrator()
    
    # Test the _boost_stat method directly
    test_dict = {'proj_pts': 27.5}
    print("=== Testing _boost_stat method ===")
    print(f"Before: {test_dict}")
    
    # Test correct usage
    calib._boost_stat(test_dict, 'proj_pts', 0.92)
    print(f"After 0.92 multiplier: {test_dict}")
    
    # Test if there's any weird rounding or accumulation
    calib._boost_stat(test_dict, 'proj_pts', 1.08)
    print(f"After additional 1.08 multiplier: {test_dict}")
    
    # Test the suspicious case: what if 0.92 becomes 1.92?
    test_bug = {'proj_pts': 27.5}
    calib._boost_stat(test_bug, 'proj_pts', 1.92)
    print(f"After 1.92 multiplier (BUG): {test_bug}")

if __name__ == "__main__":
    check_boost_stat_implementation()
    print("\n" + "="*50 + "\n")
    result = test_full_calibrate()
    
    if result:
        print("\n🔴 BUG REPRODUCED!")
        print("Investigate the calibration method that produced these values.")
    else:
        print("\n✅ No excessive multipliers found in basic test.")