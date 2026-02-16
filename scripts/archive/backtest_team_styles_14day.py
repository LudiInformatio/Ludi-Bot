#!/usr/bin/env python3
"""
14-day recent trends backtest.
Identifies teams that changed style in last 2 weeks.
"""
import sys
sys.path.insert(0, '.')
import sqlite3
from datetime import datetime, timedelta
from module_e import LudiCalibrator

def get_pace_trend(conn, team_abbr, recent_days=14, prior_days=46):
    """Compare recent pace vs prior pace using team_lineups"""
    cursor = conn.cursor()
    
    # Recent period (last N days) - from team_lineups
    cursor.execute("""
        SELECT SUM(possessions) * 48.0 / NULLIF(SUM(minutes), 0)
        FROM team_lineups
        WHERE game_date >= date('now', '-{} days')
        AND team_abbreviation = ?
    """.format(recent_days), (team_abbr,))
    
    recent_pace = cursor.fetchone()[0] or 0
    
    # Prior period (days N to N+prior_days)
    cursor.execute("""
        SELECT SUM(possessions) * 48.0 / NULLIF(SUM(minutes), 0)
        FROM team_lineups
        WHERE game_date >= date('now', '-{} days')
        AND game_date < date('now', '-{} days')
        AND team_abbreviation = ?
    """.format(recent_days + prior_days, recent_days), (team_abbr,))
    
    prior_pace = cursor.fetchone()[0] or 0
    
    return recent_pace, prior_pace

def get_offensive_rating_trend(conn, team_abbr, recent_days=14, prior_days=46):
    """Compare recent ORtg vs prior ORtg using team_lineups"""
    cursor = conn.cursor()
    
    # Recent period
    cursor.execute("""
        SELECT AVG(off_rating)
        FROM team_lineups
        WHERE game_date >= date('now', '-{} days')
        AND team_abbreviation = ?
    """.format(recent_days), (team_abbr,))
    
    recent_ortg = cursor.fetchone()[0] or 0
    
    # Prior period
    cursor.execute("""
        SELECT AVG(off_rating)
        FROM team_lineups
        WHERE game_date >= date('now', '-{} days')
        AND game_date < date('now', '-{} days')
        AND team_abbreviation = ?
    """.format(recent_days + prior_days, recent_days), (team_abbr,))
    
    prior_ortg = cursor.fetchone()[0] or 0
    
    return recent_ortg, prior_ortg

def analyze_recent_trends():
    print("=" * 70)
    print("14-DAY RECENT TRENDS ANALYSIS")
    print("=" * 70)
    
    conn = sqlite3.connect('ludi.db')
    calib = LudiCalibrator()
    
    teams = list(calib.OFFENSIVE_STYLES.keys())
    teams_to_watch = []
    
    print(f"Analyzing pace/ORtg trends for {len(teams)} teams...\n")
    
    for team in teams:
        assigned_style = calib.OFFENSIVE_STYLES[team]
        
        recent_pace, prior_pace = get_pace_trend(conn, team)
        recent_ortg, prior_ortg = get_offensive_rating_trend(conn, team)
        
        # Skip if insufficient data
        if recent_pace == 0 or prior_pace == 0:
            continue
        
        # Calculate changes
        pace_change = ((recent_pace - prior_pace) / prior_pace) * 100 if prior_pace > 0 else 0
        ortg_change = ((recent_ortg - prior_ortg) / prior_ortg) * 100 if prior_ortg > 0 else 0
        
        # Flag significant changes (>5%)
        significant_change = False
        change_type = ""
        
        if abs(pace_change) > 5:
            significant_change = True
            change_type += f"Pace {pace_change:+.1f}% "
        
        if abs(ortg_change) > 5:
            significant_change = True
            change_type += f"ORtg {ortg_change:+.1f}%"
        
        if not change_type:
            change_type = "Stable"
        
        print(f"{team:3} | {assigned_style:12} | {change_type:20} | "
              f"Pace: {prior_pace:5.1f}→{recent_pace:5.1f} | "
              f"ORtg: {prior_ortg:5.1f}→{recent_ortg:5.1f}", end="")
        
        if significant_change:
            print(" | ⚠️")
            teams_to_watch.append({
                'team': team,
                'style': assigned_style,
                'changes': change_type,
                'recent_pace': recent_pace,
                'prior_pace': prior_pace,
                'pace_change': pace_change,
                'recent_ortg': recent_ortg,
                'prior_ortg': prior_ortg,
                'ortg_change': ortg_change
            })
        else:
            print(" | ✅")
    
    print("\n" + "=" * 70)
    print("TEAMS WITH SIGNIFICANT RECENT CHANGES")
    print("=" * 70)
    
    if teams_to_watch:
        print(f"Found {len(teams_to_watch)} teams with >5% pace/ORtg changes:\n")
        
        for team_data in teams_to_watch:
            team = team_data['team']
            style = team_data['style']
            
            print(f"🏀 {team} ({style})")
            print(f"   Changes: {team_data['changes']}")
            print(f"   Pace: {team_data['prior_pace']:.1f} → {team_data['recent_pace']:.1f} "
                  f"({team_data['pace_change']:+.1f}%)")
            print(f"   ORtg: {team_data['prior_ortg']:.1f} → {team_data['recent_ortg']:.1f} "
                  f"({team_data['ortg_change']:+.1f}%)")
            
            # Suggest potential style reclassification
            if team_data['pace_change'] > 7 and style != "PACE_PUSH":
                print(f"   💡 Consider: PACE_PUSH (speeding up)")
            elif team_data['pace_change'] < -7 and style != "HALF_COURT":
                print(f"   💡 Consider: HALF_COURT (slowing down)")
            
            print()
    else:
        print("✅ No significant style changes in last 14 days")
        print("   All teams maintaining their offensive identity")
    
    print("=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    
    conn.close()
    return teams_to_watch

if __name__ == "__main__":
    teams_to_watch = analyze_recent_trends()