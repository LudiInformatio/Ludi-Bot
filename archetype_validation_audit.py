#!/usr/bin/env python3
"""
archetype_validation_audit.py - Ludi Informatio Archetype Verification Suite
This script validates the "Team/Player Types" by analyzing the 40,000+ hydrated records
from the Ghost Protocol backfill.

Goal: Prove that tagged archetypes (e.g., SLASHER) actually perform differently in 
target matchups (e.g., vs HACKERS) compared to their neutral baseline.
"""
import sqlite3
import pandas as pd
import numpy as np
from module_e import LudiCalibrator

# Initialize Calibrator (to use its archetype logic and team styles)
calib = LudiCalibrator()

def run_archetype_audit():
    print("========================================")
    print(" LUDI INFORMATIO | ARCHETYPE VALIDATION ")
    print("   >>> AUDITING 60-DAY GHOST BACKFILL   ")
    print("========================================\n")

    conn = sqlite3.connect('ludi.db')
    
    # 1. LOAD DATA
    # We join player logs with game results to get matchup context
    query = '''
        SELECT 
            p.player_name, p.team_abbreviation as team, p.game_date, 
            p.pts, p.reb, p.ast, p.fg3m, p.fg3a, p.fta, p.fga, p.minutes,
            g.home_team, g.away_team
        FROM player_game_logs p
        JOIN games g ON p.game_id = g.game_id
        WHERE p.game_date >= '2025-11-14'
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Determine Opponent
    df['opponent'] = df.apply(lambda x: x['away_team'] if x['team'] == x['home_team'] else x['home_team'], axis=1)
    # Map Opponent Style
    df['def_style'] = df['opponent'].map(calib.DEFENSIVE_STYLES).fillna('NEUTRAL')

    # 2. DYNAMICALLY ASSIGN ARCHETYPES
    # We use a simplified version of the logic in module_e for historical profiling
    print("📊 Assigning archetypes based on backfill baselines...")
    
    # Calculate player season averages for assignment
    baselines = df.groupby('player_name').agg({
        'pts': 'mean', 'reb': 'mean', 'ast': 'mean', 
        'fg3m': 'mean', 'fta': 'mean', 'fga': 'mean', 'minutes': 'mean'
    }).reset_index()

    player_types = {}
    for _, p in baselines.iterrows():
        # Create a mock packet for _assign_archetype
        # (Assuming Usg is approx (fga + 0.44*fta)/minutes/2.1)
        usg = 0.20
        if p['minutes'] > 0:
            usg = ((p['fga'] + 0.44*p['fta']) / p['minutes']) / 2.1
            
        packet = {
            'name': p['player_name'],
            'base_pts': p['pts'], 'base_reb': p['reb'], 'base_ast': p['ast'],
            'base_3pm': p['fg3m'], 'base_usg': usg, 'base_stl': 0, 'base_blk': 0
        }
        archetype, _ = calib._assign_archetype(packet)
        player_types[p['player_name']] = archetype

    df['archetype'] = df['player_name'].map(player_types)

    # 3. RUN MATCHUP AUDITS
    audit_configs = [
        {
            'name': 'SLASHER vs HACKERS (FT Rate Audit)',
            'archetype': 'SLASHER',
            'def_style': 'HACKERS',
            'target_stat': 'fta',
            'expected_boost': 1.20
        },
        {
            'name': 'STRETCH_BIG vs PAINT_PACK (3PA Audit)',
            'archetype': 'STRETCH_BIG',
            'def_style': 'PAINT_PACK',
            'target_stat': 'fg3a',
            'expected_boost': 1.15
        },
        {
            'name': 'HELIOCENTRIC vs BLITZ (Assist Audit)',
            'archetype': 'HELIOCENTRIC',
            'def_style': 'BLITZ',
            'target_stat': 'ast',
            'expected_boost': 1.18
        }
    ]

    for audit in audit_configs:
        print(f"\n🔍 Testing: {audit['name']}")
        
        # Get baseline for these players
        players_in_pool = baselines[baselines['player_name'].map(player_types) == audit['archetype']]['player_name']
        if players_in_pool.empty:
            print("   ⚠️ No players found for this archetype.")
            continue
            
        # Target Matchups
        target_df = df[(df['archetype'] == audit['archetype']) & (df['def_style'] == audit['def_style'])]
        # Neutral Matchups
        neutral_df = df[(df['archetype'] == audit['archetype']) & (df['def_style'] == 'NEUTRAL')]

        if len(target_df) < 5:
            print(f"   ⚠️ Insufficient sample size ({len(target_df)} games).")
            continue

        target_avg = target_df[audit['target_stat']].mean()
        neutral_avg = neutral_df[audit['target_stat']].mean()
        
        actual_boost = target_avg / neutral_avg if neutral_avg > 0 else 1.0
        
        print(f"   Baseline ({audit['target_stat']}): {neutral_avg:.2f}")
        print(f"   Target Matchup Avg: {target_avg:.2f}")
        print(f"   Actual Multiplier: {actual_boost:.3f}x")
        print(f"   Model Multiplier:  {audit['expected_boost']:.3f}x")
        
        if abs(actual_boost - audit['expected_boost']) < 0.10:
            print("   ✅ VERIFIED: Data matches model assumption.")
        elif actual_boost > 1.05:
            print("   🟡 VALID: Directional boost confirmed, but weaker than expected.")
        else:
            print("   ❌ DISPROVED: No statistical edge found for this type matchup.")

    print("\n" + "="*40)
    print(" AUDIT COMPLETE ")
    print("="*40)

if __name__ == "__main__":
    run_archetype_audit()
