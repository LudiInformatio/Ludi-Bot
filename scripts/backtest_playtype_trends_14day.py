#!/usr/bin/env python3
"""
14-Day Trend Analysis for Secondary Playtype Matchups.
Identifies recent spikes in specific playtype-defense interactions.
"""
import sys
sys.path.insert(0, '.')

from module_e import LudiCalibrator
import sqlite3
from datetime import datetime, timedelta

def run_14day_trends():
    print("=" * 70)
    print("PHASE 3: 14-DAY PLAYTYPE TRENDS ANALYSIS")
    print("=" * 70)
    
    calib = LudiCalibrator(debug_log=False)
    
    # 1. Get recent games (Last 14 days)
    conn = sqlite3.connect('ludi.db')
    cursor = conn.cursor()
    cutoff_date = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
    days_back_30 = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    days_back_15 = (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d')

    print(f"📅 Analyzing games since {cutoff_date}...")
    
    # Analyze Defense Frequency (Recent 14 vs Previous 15-30)
    def get_defense_counts(start_date, end_date=None):
        query = """
        SELECT DISTINCT game_date, team_abbreviation
        FROM player_game_logs 
        WHERE game_date >= ?
        """
        params = [start_date]
        if end_date:
            query += " AND game_date <= ?"
            params.append(end_date)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        style_counts = {}
        for _, team in rows:
            # Check what DEFENSE this team plays (from module_e static dict)
            # Use 'team' as opponent to see what defenses players are facing
            def_style = calib.DEFENSIVE_STYLES.get(team, "NEUTRAL")
            style_counts[def_style] = style_counts.get(def_style, 0) + 1
            
        return style_counts, len(rows)

    recent_counts, recent_total = get_defense_counts(cutoff_date)
    prev_counts, prev_total = get_defense_counts(days_back_30, days_back_15)
    
    conn.close()

    print(f"📊 Sample Size: {recent_total} recent team-games vs {prev_total} baseline.")
    
    if recent_total == 0:
        print("❌ No recent data found.")
        return

    print("\n🔍 DEFENSIVE STYLE TRENDS (Last 14 Days vs Baseline)")
    print(f"{'DEFENSE STYLE':<15} | {'RECENT %':<10} | {'PREV %':<10} | {'TREND':<10}")
    print("-" * 60)
    
    styles = set(list(recent_counts.keys()) + list(prev_counts.keys()))
    
    for style in sorted(styles):
        rec_pct = (recent_counts.get(style, 0) / recent_total * 100) if recent_total else 0
        prev_pct = (prev_counts.get(style, 0) / prev_total * 100) if prev_total else 0
        diff = rec_pct - prev_pct
        
        trend_arrow = "➡️"
        if diff > 5: trend_arrow = "⬆️ HOT"
        elif diff < -5: trend_arrow = "⬇️ COLD"
        
        print(f"{style:<15} | {rec_pct:5.1f}%     | {prev_pct:5.1f}%     | {trend_arrow} ({diff:+5.1f}%)")

    print("\n🎯 MATCHUP IMPLICATIONS")
    print("-" * 60)
    
    # Hot styles trigger specific matchups
    hot_styles = [s for s in styles if (recent_counts.get(s,0)/recent_total*100) > (prev_counts.get(s,0)/prev_total*100) + 2]
    
    for style in hot_styles:
        if style == "BLITZ":
            print(f"🔥 BLITZ is trending (+{(recent_counts.get('BLITZ',0)/recent_total*100 - prev_counts.get('BLITZ',0)/prev_total*100):.1f}%).")
            print("   -> expect MORE [ISO_SCORER] penalties (TOV tax)")
            print("   -> expect MORE [P&R_HANDLER] blitz taxes")
        elif style == "PAINT_PACK":
            print(f"🔥 PAINT_PACK is trending (+{(recent_counts.get('PAINT_PACK',0)/recent_total*100 - prev_counts.get('PAINT_PACK',0)/prev_total*100):.1f}%).")
            print("   -> expect MORE [SPOT_UP] 3PM boosts")
            print("   -> expect MORE [P&R_ROLL_MAN] scoring boosts")
        elif style == "FUNNEL":
            print(f"🔥 FUNNEL is trending.")
            print("   -> expect MORE [TRANSITION] scoring boosts")

    print("\n✅ Phase 3 Trend Analysis Complete")

if __name__ == "__main__":
    run_14day_trends()
