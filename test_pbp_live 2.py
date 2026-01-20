#!/usr/bin/env python3
"""
PBP Stats Live Connectivity Test
Verifies if the API client can fetch real data with the new headers.
"""
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pbp_stats_client import get_totals, get_wowy_stats, get_game_stats

def test_connectivity():
    print("📡 Testing PBP Stats API Connectivity...\n")
    
    # Test 1: Team Totals (Lakers)
    print("1. Fetching 2025-26 Team Totals (Lakers)...")
    try:
        totals = get_totals("Team", "1610612747", "2025-26")
        if totals:
            res = totals.get('multi_row_table_data', [])
            if res:
                row = res[0]
                print(f"   ✅ Success! {row.get('Name')} | ORtg: {row.get('OffRtg')} | DRtg: {row.get('DefRtg')}")
            else:
                print("   ⚠️  Response valid but empty data list.")
        else:
            print("   ❌ Failed to get data.")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

    # Test 2: WOWY Stats (LeBron James On/Off)
    # LeBron ID: 2544
    print("\n2. Fetching WOWY Stats (LeBron James On/Off)...")
    try:
        # Note: PBP Stats uses specific params for WOWY
        # For this test we check if the function returns *any* valid response
        wowy = get_wowy_stats("1610612747", ["2544"], "2025-26")
        if wowy:
             res = wowy.get('multi_row_table_data', [])
             if res:
                 print(f"   ✅ Success! Returned {len(res)} lineup combinations.")
                 print(f"      Sample: {res[0].get('OnOffRtg')}") 
             else:
                 print("   ⚠️  Response valid but empty data list.")
        else:
            print("   ❌ Failed to get WOWY data.")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_connectivity()
