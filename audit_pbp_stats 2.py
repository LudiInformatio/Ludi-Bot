#!/usr/bin/env python3
"""
PBP Stats Comprehensive Data Explorer
Fetches samples from ALL key endpoints to audit data quality and structure.
"""
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pbp_stats_client import (
    get_totals, 
    get_wowy_stats, 
    get_game_stats, 
    get_shots, 
    get_on_off,
    get_team_leverage_summary
)

OUTPUT_FILE = "pbp_stats_audit.json"
TEST_TEAM_ID = "1610612747" # Lakers
TEST_PLAYER_ID = "2544"     # LeBron
CURRENT_SEASON = "2025-26"

def run_audit():
    print(f"🕵️  Starting PBP Stats Audit for Season {CURRENT_SEASON}...")
    audit_data = {}

    # 1. PLAYER TOTALS (Offense & Defense)
    print("1. Fetching Player Totals...")
    totals = get_totals("Player", TEST_TEAM_ID, CURRENT_SEASON)
    if totals:
        rows = totals.get('multi_row_table_data', [])
        print(f"   ✅ Got {len(rows)} players")
        # Save first row as sample
        if rows: audit_data['player_totals_sample'] = rows[0]

    # 2. WOWY (LeBron On/Off)
    print("2. Fetching WOWY (LeBron On/Off)...")
    wowy = get_wowy_stats(TEST_TEAM_ID, [TEST_PLAYER_ID], CURRENT_SEASON)
    if wowy:
        rows = wowy.get('multi_row_table_data', [])
        print(f"   ✅ Got {len(rows)} lineup configs")
        if rows: audit_data['wowy_sample'] = rows[0]

    # 3. ON/OFF DETAILED (LeBron)
    print("3. Fetching Detailed On/Off Stats...")
    on_off = get_on_off(TEST_TEAM_ID, TEST_PLAYER_ID, "player", CURRENT_SEASON)
    if on_off:
        rows = on_off.get('multi_row_table_data', [])
        print(f"   ✅ Got {len(rows)} on/off splits")
        if rows: audit_data['on_off_sample'] = rows[0]

    # 4. SHOT QUALITY (LeBron)
    print("4. Fetching Shot Quality (LeBron)...")
    shots = get_shots(TEST_PLAYER_ID, "Player", CURRENT_SEASON)
    if shots:
        rows = shots.get('multi_row_table_data', [])
        print(f"   ✅ Got {len(rows)} shots")
        if rows: audit_data['shot_quality_sample'] = rows[0]

    # 5. TEAM LEVERAGE
    print("5. Fetching Team Leverage Stats...")
    leverage = get_team_leverage_summary(CURRENT_SEASON, "High")
    if leverage:
        rows = leverage.get('multi_row_table_data', [])
        print(f"   ✅ Got {len(rows)} teams (High Leverage)")
        if rows: audit_data['leverage_sample'] = rows[0]

    # 6. LINEUP STATS
    print("6. Fetching Lineup Stats (Lakers)...")
    lineups = get_totals("Lineup", TEST_TEAM_ID, CURRENT_SEASON)
    if lineups:
        rows = lineups.get('multi_row_table_data', [])
        print(f"   ✅ Got {len(rows)} lineups")
        if rows: audit_data['lineup_sample'] = rows[0]

    # Save Audit to File
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(audit_data, f, indent=4)
    
    print(f"\n✅ Audit Complete. Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_audit()
