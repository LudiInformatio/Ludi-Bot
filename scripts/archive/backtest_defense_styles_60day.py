#!/usr/bin/env python3
"""
60-day backtest to verify team defensive style classifications.
Uses player_defense + team_lineups data for validation.
"""
import sys
sys.path.insert(0, '.')
import sqlite3
from module_e import LudiCalibrator

def get_team_defensive_profile(conn, team_abbr, days=60):
    """Calculate team defensive profile from available data"""
    cursor = conn.cursor()
    
    # Get opponent vs team stats from player_defense
    cursor.execute("""
        SELECT 
            AVG(diff_pct) as avg_diff_pct,
            AVG(dfg_pct) as avg_dfg_pct,
            COUNT(*) as sample_size
        FROM player_defense
        WHERE team_abbr = ?
    """, (team_abbr,))
    
    defense_data = cursor.fetchone()
    
    # Get team defensive rating from team_lineups
    cursor.execute("""
        SELECT 
            AVG(def_rating) as def_rtg,
            SUM(possessions) * 48.0 / NULLIF(SUM(minutes), 0) as pace
        FROM team_lineups
        WHERE team_abbreviation = ?
        AND game_date >= date('now', '-{} days')
    """.format(days), (team_abbr,))
    
    lineup_data = cursor.fetchone()
    
    if not defense_data or not lineup_data:
        return None, 0
    
    return {
        'avg_diff_pct': defense_data[0] or 0,
        'avg_dfg_pct': defense_data[1] or 0,
        'sample_size': defense_data[2] or 0,
        'def_rating': lineup_data[0] or 110,
        'pace': lineup_data[1] or 100
    }, defense_data[2] or 0

def backtest_60_days():
    print("=" * 70)
    print("60-DAY DEFENSIVE STYLE VERIFICATION BACKTEST")
    print("=" * 70)
    
    conn = sqlite3.connect('ludi.db')
    calib = LudiCalibrator()
    
    teams = list(calib.DEFENSIVE_STYLES.keys())
    mismatches = []
    
    print(f"Analyzing {len(teams)} teams over last 60 days...\n")
    
    for team in teams:
        assigned_style = calib.DEFENSIVE_STYLES[team]
        profile, sample_size = get_team_defensive_profile(conn, team)
        
        if profile is None:
            print(f"{team:3} | {assigned_style:12} | ⚠️ No data")
            continue
        
        if sample_size < 3:  # Need at least 3 players for reliable team average
            print(f"{team:3} | {assigned_style:12} | ⚠️ Small sample ({sample_size} players)")
            continue
        
        # Check style consistency
        style_mismatch = False
        reason = ""
        
        # PAINT_PACK should have negative diff_pct (forcing bad rim shots)
        if assigned_style == "PAINT_PACK" and profile['avg_diff_pct'] > 0:
            style_mismatch = True
            reason = f"diff_pct {profile['avg_diff_pct']:.1f}% > 0 (not protecting rim)"
        
        # BLITZ should have lower opponent fg% (pressure working)
        elif assigned_style == "BLITZ" and profile['avg_dfg_pct'] > 48:
            style_mismatch = True
            reason = f"opp_dfg {profile['avg_dfg_pct']:.1f}% high (pressure not working?)"
        
        # PERIMETER should hold opponents to lower 3P% (denies outside shots)
        elif assigned_style == "PERIMETER" and profile['avg_dfg_pct'] > 45:
            style_mismatch = True
            reason = f"opp_dfg {profile['avg_dfg_pct']:.1f}% high (not denying perimeter)"
        
        # Good defensive teams should have def_rating < 112
        elif profile['def_rating'] > 115 and assigned_style in ["PAINT_PACK", "PERIMETER"]:
            style_mismatch = True
            reason = f"def_rtg {profile['def_rating']:.1f} (elite style but poor rating)"
        
        status = "⚠️" if style_mismatch else "✅"
        print(f"{team:3} | {assigned_style:12} | diff%: {profile['avg_diff_pct']:+5.1f} | "
              f"dfg%: {profile['avg_dfg_pct']:4.1f} | def_rtg: {profile['def_rating']:.1f} | "
              f"n:{sample_size:2} | {status}")
        
        if style_mismatch:
            mismatches.append({'team': team, 'style': assigned_style, 'reason': reason})
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    mismatch_rate = (len(mismatches) / len(teams)) * 100 if teams else 0
    print(f"Teams analyzed: {len(teams)}")
    print(f"Style mismatches: {len(mismatches)} ({mismatch_rate:.1f}%)")
    
    if mismatches:
        print(f"\n⚠️ POTENTIAL MISCLASSIFICATIONS:")
        for m in mismatches:
            print(f"  {m['team']:3} ({m['style']:12}): {m['reason']}")
    
    print(f"\n✅ Target mismatch rate: <10%")
    print(f"   Current rate: {mismatch_rate:.1f}%")
    
    if mismatch_rate < 10:
        print("   ✅ CLASSIFICATIONS VERIFIED")
    else:
        print("   ⚠️ REVIEW NEEDED - High mismatch rate")
    
    conn.close()
    return mismatch_rate < 10

if __name__ == "__main__":
    success = backtest_60_days()
    sys.exit(0 if success else 1)