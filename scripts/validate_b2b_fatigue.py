#!/usr/bin/env python3
"""
validate_b2b_fatigue.py
=======================
Week 3 Validation Script

Goal: Validate B2B fatigue penalties against real performance data (Dec 20 - Jan 16).
"""

import sys
import os
import sqlite3
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PATH = 'ludi.db'
START_DATE = '2025-12-20'
END_DATE = '2026-01-16'

def validate_b2b():
    print("=== B2B FATIGUE VALIDATION ===")
    print(f"Window: {START_DATE} to {END_DATE}")
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Identify B2B Games and Players
    query = f"""
    WITH team_games AS (
        SELECT 
            date,
            home_team as team,
            'HOME' as location
        FROM games
        WHERE date BETWEEN '{START_DATE}' AND '{END_DATE}'
        UNION ALL
        SELECT 
            date,
            away_team as team,
            'AWAY' as location
        FROM games
        WHERE date BETWEEN '{START_DATE}' AND '{END_DATE}'
    ),
    b2b_flags AS (
        SELECT 
            t1.date,
            t1.team,
            t1.location,
            CASE WHEN t2.date IS NOT NULL THEN 1 ELSE 0 END as is_b2b
        FROM team_games t1
        LEFT JOIN team_games t2 ON t1.team = t2.team AND t2.date = date(t1.date, '-1 day')
    )
    SELECT 
        pgl.player_name,
        pgl.team_abbreviation,
        pgl.pts,
        bf.is_b2b,
        bf.location
    FROM player_game_logs pgl
    JOIN b2b_flags bf ON pgl.game_date = bf.date AND pgl.team_abbreviation = bf.team
    WHERE pgl.game_date BETWEEN '{START_DATE}' AND '{END_DATE}'
    """
    
    try:
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if df.empty:
            print("❌ No data found for B2B validation.")
            return

        # 2. Analyze Guards vs Others
        # Ideally we join with position, but keeping it simple or inferring?
        # Let's just do aggregate first.
        
        print(f"Total Player-Games: {len(df)}")
        b2b_games = df[df['is_b2b'] == 1]
        rested_games = df[df['is_b2b'] == 0]
        
        print(f"B2B Player-Games: {len(b2b_games)}")
        print(f"Rested Player-Games: {len(rested_games)}")
        
        # Calculate impact
        avg_b2b = b2b_games['pts'].mean()
        avg_rested = rested_games['pts'].mean()
        diff = avg_b2b - avg_rested
        pct_diff = (diff / avg_rested) * 100 if avg_rested else 0
        
        print("\nOVERALL IMPACT:")
        print(f"  Rested Avg PTS: {avg_rested:.2f}")
        print(f"  B2B Avg PTS:    {avg_b2b:.2f}")
        print(f"  Difference:     {diff:.2f} ({pct_diff:.1f}%)")
        
        # Breakdown by Location
        print("\nBY LOCATION (B2B Only):")
        for loc in ['HOME', 'AWAY']:
            loc_b2b = b2b_games[b2b_games['location'] == loc]['pts'].mean()
            loc_rested = rested_games[rested_games['location'] == loc]['pts'].mean()
            if np.isnan(loc_rested): loc_rested = avg_rested # fallback
            
            loc_diff = loc_b2b - loc_rested
            loc_pct = (loc_diff / loc_rested) * 100 if loc_rested else 0
            
            print(f"  {loc} B2B Avg: {loc_b2b:.2f} (Delta: {loc_diff:.2f} | {loc_pct:.1f}%)")
            
        # Target validation
        # Road B2B should be worse than Home B2B
        
        road_drop = b2b_games[b2b_games['location'] == 'AWAY']['pts'].mean() - rested_games['pts'].mean()
        home_drop = b2b_games[b2b_games['location'] == 'HOME']['pts'].mean() - rested_games['pts'].mean()
        
        print("\nVALIDATION CHECK:")
        print(f"  Road Drop: {road_drop:.2f} (Target: ~ -1.0 to -2.0)")
        print(f"  Home Drop: {home_drop:.2f} (Target: ~ -0.5 to -1.0)")
        
        if road_drop < home_drop:
             print("✅ PASS: Road B2B penalty > Home B2B penalty")
        else:
             print("⚠️ FAIL: Road B2B penalty NOT > Home B2B penalty (Variance?)")

    except Exception as e:
        print(f"❌ B2B VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    validate_b2b()
