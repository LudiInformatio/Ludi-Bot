#!/usr/bin/env python3
"""
monitor_playtype_distribution.py
================================
Week 3 Validation Script

Goal: Validate secondary playtype distribution (ISO_SCORER, SPOT_UP, etc.)
and flag players with mismatched or missing tags.
"""

import sys
import os
import sqlite3
import pandas as pd
from collections import Counter

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from module_e import LudiCalibrator

def monitor_playtypes():
    print("=== PLAYTYPE DISTRIBUTION MONITOR ===")
    
    calibrator = LudiCalibrator()
    conn = sqlite3.connect('ludi.db')
    cursor = conn.cursor()
    
    # 1. Get Active Players (approx from tracking)
    cursor.execute("""
        SELECT DISTINCT player_name 
        FROM player_game_tracking 
        WHERE game_date >= date('now', '-30 days')
    """)
    players = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    print(f"Analyzing {len(players)} players with recent tracking data...")
    
    playtype_counts = Counter()
    total_tagged = 0
    multi_tag_count = 0
    player_tags = {}
    
    # 2. Classify Each
    for p_name in players:
        # Fetch tracking stats
        tracking = calibrator._get_tracking_stats(p_name)
        if not tracking:
            continue
            
        # Classify
        primary, secondary = calibrator._select_top_playtypes(tracking)
        
        tags = []
        if primary: tags.append(primary)
        if secondary: tags.append(secondary)
        
        player_tags[p_name] = tags
        
        if tags:
            total_tagged += 1
            if len(tags) > 1:
                multi_tag_count += 1
                
        for t in tags:
            playtype_counts[t] += 1
            
    # 3. Report Distribution
    print("\nDISTRIBUTION:")
    total_observations = sum(playtype_counts.values())
    for pt, count in playtype_counts.most_common():
        pct = (count / len(players)) * 100
        print(f"  {pt:<15}: {count:3d} players ({pct:5.1f}%)")
        
    print(f"\nCoverage: {total_tagged}/{len(players)} ({total_tagged/len(players)*100:.1f}%)")
    print(f"Multi-Tag: {multi_tag_count} players")
    
    # 4. Flag Edge Cases
    print("\nEDGE CASES (Sample):")
    # Sample logic: Star players with < 2 tags?
    # Or incompatible tags?
    
    incompatible_pairs = [
        ('SPOT_UP', 'ISO_SCORER'), # Rare combination? Actually possible (Elite Scorer)
        ('RIM_RUNNER', 'SNIPER')   # Impossible
    ]
    
    for p_name, tags in list(player_tags.items())[:20]: # Show first 20 for brevity or filter
        if len(tags) == 0:
            print(f"  ⚠️ {p_name}: No tags")
        elif 'ISO_SCORER' in tags and 'SPOT_UP' in tags:
             print(f"  ℹ️ {p_name}: ISO + SPOT_UP (Elite Scorer?)")

if __name__ == "__main__":
    monitor_playtypes()
