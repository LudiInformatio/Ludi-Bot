#!/usr/bin/env python3

import sys
import os
import sqlite3
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from module_e import LudiCalibrator

def test_tyrese_maxey_realistic():
    """Test Tyrese Maxey with realistic data from database"""
    calib = LudiCalibrator()
    
    # Try to get real Maxey data from database
    try:
        conn = sqlite3.connect(calib.db_path)
        cursor = conn.cursor()
        
        # Get Maxey's recent averages
        cursor.execute("""
            SELECT AVG(pts) as avg_pts, AVG(ast) as avg_ast, AVG(tov) as avg_tov,
                   AVG(fg3m) as avg_3pm, AVG(min) as avg_min, AVG(fga) as avg_fga,
                   AVG(fg3a) as avg_3pa, AVG(fta) as avg_fta, AVG(reb) as avg_reb,
                   AVG(stl) as avg_stl, AVG(blk) as avg_blk, AVG(oreb) as avg_oreb, AVG(dreb) as avg_dreb
            FROM player_game_logs 
            WHERE player_name = 'Tyrese Maxey' 
            AND game_date >= date('now', '-10 days')
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            print(f"=== REAL MAXY DATA (last 10 days) ===")
            print(f"PTS: {row[0]:.1f}, AST: {row[1]:.1f}, TOV: {row[2]:.1f}")
            print(f"3PM: {row[3]:.1f}, MIN: {row[4]:.1f}")
            
            # Use real data
            base_pts = row[0] or 27.5
            base_ast = row[1] or 4.0  
            base_tov = row[2] or 2.0
        else:
            print("No recent Maxey data found, using estimates")
            base_pts = 27.5
            base_ast = 4.0
            base_tov = 2.0
            
    except Exception as e:
        print(f"Database error: {e}")
        base_pts = 27.5
        base_ast = 4.0
        base_tov = 2.0
    
    # Create realistic test player
    test_player = {
        'name': 'Tyrese Maxey',
        'PLAYER_NAME': 'Tyrese Maxey',
        'team': 'PHI',
        'opponent': 'TOR',  # This is key - TOR vs PHI matchup
        'position': 'G',
        # Use realistic baselines
        'base_pts': base_pts,
        'base_ast': base_ast,
        'base_tov': base_tov,
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
        'notes': ''
    }
    
    # Test against different opponents to see when the bug appears
    opponents = ['TOR', 'BOS', 'NYK', 'CHI']
    
    for opponent in opponents:
        test_player['opponent'] = opponent
        yak_report = {'status': 'ACTIVE', 'injury': None}
        
        try:
            result = calib.calibrate_player(test_player.copy(), yak_report, use_synergy=True)
            
            pts = result.get('proj_pts', 0)
            multiplier = pts / base_pts if base_pts > 0 else 0
            
            def_style = calib.DEFENSIVE_STYLES.get(opponent, 'NEUTRAL')
            
            print(f"\n=== vs {opponent} ({def_style}) ===")
            print(f"PTS: {pts:.1f} (multiplier: {multiplier:.3f})")
            print(f"Notes: {result.get('notes', 'N/A')[:100]}...")
            
            if multiplier > 1.5:
                print(f"🔴 CRITICAL BUG: Excessive multiplier {multiplier:.3f} vs {opponent}")
                return result
                
        except Exception as e:
            print(f"Error vs {opponent}: {e}")
    
    return None

def investigate_specific_multiplier():
    """Check if any modifier could be causing 1.95x multiplier"""
    calib = LudiCalibrator()
    
    print("=== INVESTIGATING MULTIPLIER SOURCES ===")
    
    # Check all possible multipliers that could apply to Maxey vs TOR
    base_pts = 27.5
    
    modifiers = []
    
    # 1. ELITE_SCORER vs BLITZ (doesn't exist, only vs PERIMETER)
    # modifiers.append(('ELITE_SCORER vs BLITZ', 1.0))  # No modifier
    
    # 2. ISO_SCORER vs BLITZ 
    modifiers.append(('ISO_SCORER vs BLITZ', 0.92))
    
    # 3. P&R_HANDLER vs BLITZ (only affects AST/TOV, not PTS)
    # modifiers.append(('P&R_HANDLER vs BLITZ', 1.0))  # No PTS modifier
    
    # 4. Team offense style (PHI = HALF_COURT)
    # HALF_COURT vs BLITZ: no specific modifier
    modifiers.append(('HALF_COURT vs BLITZ', 1.0))
    
    # 5. Elite FT% > 85% boost
    modifiers.append(('Elite FT% > 85%', 1.05))
    
    # 6. High shot quality boost
    modifiers.append(('High Shot Quality > 0.55', 1.04))
    
    # 7. PPP efficiency boost (could be up to 1.12)
    modifiers.append(('PPP Efficiency', 1.12))
    
    # 8. Game total boost (> 238)
    modifiers.append(('Game Total > 238', 1.03))
    
    total_multiplier = 1.0
    print(f"Base PTS: {base_pts}")
    
    for name, mod in modifiers:
        if mod != 1.0:
            total_multiplier *= mod
            print(f"{name}: ×{mod:.3f} (running total: ×{total_multiplier:.3f})")
    
    final_pts = base_pts * total_multiplier
    print(f"\nExpected PTS: {final_pts:.1f}")
    print(f"Expected Multiplier: {total_multiplier:.3f}")
    
    # What multiplier would give 53.7?
    bug_multiplier = 53.7 / base_pts
    print(f"\nBug Multiplier Needed: {bug_multiplier:.3f}")
    print(f"Difference: {bug_multiplier / total_multiplier:.2f}x higher than expected")
    
    # Check if any single modifier could be inverted
    for name, mod in modifiers:
        if mod != 1.0:
            inverted = 2.0 - mod  # If 0.92 became 1.08 (inverted around 1.0)
            if inverted > 1.5:
                print(f"Possible inverted {name}: {mod} → {inverted}")

if __name__ == "__main__":
    investigate_specific_multiplier()
    print("\n" + "="*60 + "\n")
    result = test_tyrese_maxey_realistic()
    
    if result:
        print("\n🔴 BUG FOUND AND REPRODUCED!")
    else:
        print("\n✅ No bug found in current test scenarios")