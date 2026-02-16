#!/usr/bin/env python3
"""
60-day backtest to verify team offensive style classifications.
Uses player game logs to approximate team offensive tendencies.
"""
import sys
sys.path.insert(0, '.')
import sqlite3
from datetime import datetime, timedelta
from module_e import LudiCalibrator

def get_team_offensive_profile(conn, team_abbr, days=60):
    """Calculate team offensive profile from player logs"""
    cursor = conn.cursor()
    
    # Get team performance from player game logs
    cursor.execute("""
        SELECT 
            AVG(pts) as avg_pts,
            AVG(ast) as avg_ast,
            AVG(fga) as avg_fga,
            AVG(fg3a) as avg_fg3a,
            AVG(fta) as avg_fta,
            AVG(tov) as avg_tov,
            COUNT(DISTINCT game_date) as games
        FROM player_game_logs
        WHERE team_abbreviation = ?
        AND game_date >= date('now', '-{} days')
        AND minutes >= 10  -- Only rotation players
    """.format(days), (team_abbr,))
    
    result = cursor.fetchone()
    if not result or result[6] < 5:  # Less than 5 games
        return None, 0
    
    avg_pts, avg_ast, avg_fga, avg_fg3a, avg_fta, avg_tov, games = result
    
    # Calculate offensive indicators
    ast_to_tov = avg_ast / avg_tov if avg_tov > 0 else 0
    three_pt_rate = avg_fg3a / avg_fga if avg_fga > 0 else 0
    ft_rate = avg_fta / avg_fga if avg_fga > 0 else 0
    
    return {
        'avg_pts': avg_pts,
        'avg_ast': avg_ast,
        'avg_fga': avg_fga,
        'avg_fg3a': avg_fg3a,
        'avg_fta': avg_fta,
        'avg_tov': avg_tov,
        'games': games,
        'ast_to_tov': ast_to_tov,
        'three_pt_rate': three_pt_rate,
        'ft_rate': ft_rate
    }, games

def backtest_60_days():
    print("=" * 70)
    print("60-DAY TEAM STYLE VERIFICATION BACKTEST")
    print("=" * 70)
    
    conn = sqlite3.connect('ludi.db')
    calib = LudiCalibrator()
    
    teams = list(calib.OFFENSIVE_STYLES.keys())
    mismatches = []
    anomalies = []
    
    print(f"Analyzing {len(teams)} teams over last 60 days...\n")
    
    for team in teams:
        assigned_style = calib.OFFENSIVE_STYLES[team]
        profile, games = get_team_offensive_profile(conn, team)
        
        if profile is None:
            anomalies.append(f"{team}: No player data available")
            continue
            
        if games < 5:
            anomalies.append(f"{team}: Only {games} games (insufficient data)")
            continue
        
        # Check if profile matches assigned style
        style_mismatch = False
        reason = ""
        
        if assigned_style == "PACE_PUSH" and profile['three_pt_rate'] < 0.30:
            style_mismatch = True
            reason = f"3PA rate {profile['three_pt_rate']:.2f} < 0.30 (should shoot more 3s)"
        elif assigned_style == "HALF_COURT" and profile['ft_rate'] > 0.30:
            style_mismatch = True
            reason = f"FTA rate {profile['ft_rate']:.2f} > 0.30 (should get fewer FTA)"
        elif assigned_style == "MOTION" and profile['ast_to_tov'] < 1.5:
            style_mismatch = True
            reason = f"AST/TOV {profile['ast_to_tov']:.2f} < 1.5 (Motion should have higher ratio)"
        elif assigned_style == "ISO_HEAVY" and profile['ast_to_tov'] > 2.5:
            style_mismatch = True
            reason = f"AST/TOV {profile['ast_to_tov']:.2f} > 2.5 (ISO should have lower ratio)"
        
        print(f"{team:3} | {assigned_style:12} | AST/TOV: {profile['ast_to_tov']:4.2f} | 3PA%: {profile['three_pt_rate']:4.2f} | FTA%: {profile['ft_rate']:4.2f} | G: {games:2}", end="")
        
        if style_mismatch:
            print(f" | ⚠️  {reason}")
            mismatches.append({
                'team': team,
                'assigned': assigned_style,
                'profile': profile,
                'reason': reason
            })
        else:
            print(f" | ✅")
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_teams = len([t for t in teams if not any(a.startswith(t + ":") for a in anomalies)])
    mismatch_count = len(mismatches)
    mismatch_rate = (mismatch_count / total_teams) * 100 if total_teams > 0 else 0
    
    print(f"Teams analyzed: {total_teams}")
    print(f"Style mismatches: {mismatch_count} ({mismatch_rate:.1f}%)")
    print(f"Anomalies (no data): {len(anomalies)}")
    
    if mismatches:
        print(f"\n⚠️  TEAMS WITH POTENTIAL MISCLASSIFICATIONS:")
        for m in mismatches:
            print(f"  {m['team']:3} ({m['assigned']:12}): {m['reason']}")
    
    if anomalies:
        print(f"\n📊 DATA ANOMALIES:")
        for a in anomalies:
            print(f"  {a}")
    
    print(f"\n✅ Target mismatch rate: <10%")
    print(f"   Current mismatch rate: {mismatch_rate:.1f}%")
    
    if mismatch_rate < 10:
        print("   ✅ CLASSIFICATIONS VERIFIED")
    else:
        print("   ⚠️  REVIEW NEEDED - High mismatch rate")
    
    conn.close()
    return mismatch_rate < 10

if __name__ == "__main__":
    success = backtest_60_days()
    sys.exit(0 if success else 1)