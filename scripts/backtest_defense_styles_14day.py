#!/usr/bin/env python3
"""
14-day recent trends backtest for defensive styles.
Identifies teams with changing defensive schemes.
"""
import sys
sys.path.insert(0, '.')
import sqlite3
from module_e import LudiCalibrator

def get_defensive_trend(conn, team_abbr, recent_days=14, prior_days=46):
    """Compare recent vs prior defensive rating and tendencies"""
    cursor = conn.cursor()
    
    # Recent period - from team_lineups (NOT games.pace)
    cursor.execute("""
        SELECT 
            AVG(def_rating) as def_rtg,
            SUM(possessions) * 48.0 / NULLIF(SUM(minutes), 0) as pace
        FROM team_lineups
        WHERE team_abbreviation = ?
        AND game_date >= date('now', '-{} days')
    """.format(recent_days), (team_abbr,))
    
    recent = cursor.fetchone()
    recent_def_rtg = recent[0] or 0
    recent_pace = recent[1] or 0
    
    # Prior period
    cursor.execute("""
        SELECT 
            AVG(def_rating) as def_rtg,
            SUM(possessions) * 48.0 / NULLIF(SUM(minutes), 0) as pace
        FROM team_lineups
        WHERE team_abbreviation = ?
        AND game_date >= date('now', '-{} days')
        AND game_date < date('now', '-{} days')
    """.format(recent_days + prior_days, recent_days), (team_abbr,))
    
    prior = cursor.fetchone()
    prior_def_rtg = prior[0] or 0
    prior_pace = prior[1] or 0
    
    return {
        'recent_def_rtg': recent_def_rtg,
        'prior_def_rtg': prior_def_rtg,
        'recent_pace': recent_pace,
        'prior_pace': prior_pace
    }

def analyze_defensive_trends():
    print("=" * 70)
    print("14-DAY DEFENSIVE TRENDS ANALYSIS")
    print("=" * 70)
    
    conn = sqlite3.connect('ludi.db')
    calib = LudiCalibrator()
    
    teams = list(calib.DEFENSIVE_STYLES.keys())
    teams_to_watch = []
    
    print(f"Analyzing defensive trends for {len(teams)} teams...\n")
    
    for team in teams:
        assigned_style = calib.DEFENSIVE_STYLES[team]
        trend = get_defensive_trend(conn, team)
        
        if not trend['prior_def_rtg'] or not trend['recent_def_rtg']:
            continue
        
        # Calculate changes
        def_rtg_change = trend['recent_def_rtg'] - trend['prior_def_rtg']
        
        # Significant change = >5 points defensive rating
        significant_change = abs(def_rtg_change) > 5
        
        change_type = "Stable"
        if def_rtg_change < -5:
            change_type = f"Improving ({def_rtg_change:+.1f})"
        elif def_rtg_change > 5:
            change_type = f"Declining ({def_rtg_change:+.1f})"
        
        status = "⚠️" if significant_change else "✅"
        print(f"{team:3} | {assigned_style:12} | {change_type:20} | "
              f"DefRtg: {trend['prior_def_rtg']:.1f}→{trend['recent_def_rtg']:.1f} | {status}")
        
        if significant_change:
            teams_to_watch.append({
                'team': team,
                'style': assigned_style,
                'change': def_rtg_change,
                'recent': trend['recent_def_rtg'],
                'prior': trend['prior_def_rtg']
            })
    
    print("\n" + "=" * 70)
    print("TEAMS WITH SIGNIFICANT DEFENSIVE CHANGES")
    print("=" * 70)
    
    if teams_to_watch:
        for t in teams_to_watch:
            direction = "IMPROVING 📈" if t['change'] < 0 else "DECLINING 📉"
            print(f"🏀 {t['team']} ({t['style']}): {direction}")
            print(f"   DefRtg: {t['prior']:.1f} → {t['recent']:.1f} ({t['change']:+.1f})")
            
            # Suggest reclassification if needed
            if t['change'] < -7 and t['style'] not in ["PAINT_PACK", "PERIMETER"]:
                print(f"   💡 Consider upgrade to elite defense classification")
            elif t['change'] > 7 and t['style'] in ["PAINT_PACK", "PERIMETER"]:
                print(f"   💡 Consider downgrade - elite status may be outdated")
            print()
    else:
        print("✅ No significant defensive changes in last 14 days")
        print("   All teams maintaining their defensive identity")
    
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    
    conn.close()
    return teams_to_watch

if __name__ == "__main__":
    teams_to_watch = analyze_defensive_trends()