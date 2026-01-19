#!/usr/bin/env python3
"""Quick test of PBP Stats API connectivity"""
import sys
sys.path.insert(0, '/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot')

from pbpstats.client import Client
import time

print("Testing PBP Stats API...")
start = time.time()

try:
    # Client requires settings parameter
    settings = {
        'dir': '/tmp/pbpstats'  # Cache directory
    }
    client = Client(settings)
    print(f"✅ Client initialized ({time.time() - start:.2f}s)")
    
    # Try a simple games query with timeout
    print("\nFetching games for 2026-01-17...", end=" ", flush=True)
    start = time.time()
    
    game_settings = {
        'Season': '2025-26',
        'SeasonType': 'Regular Season',
        'Date': '2026-01-17'
    }
    
    response = client.Game.Games(league='nba', settings=game_settings)
    elapsed = time.time() - start
    
    if response and 'resultSets' in response:
        games = response['resultSets'][0].get('rowSet', [])
        print(f"✅ Got {len(games)} games ({elapsed:.2f}s)")
        if games:
            print(f"\nSample game: {games[0][:3]}")
    else:
        print(f"⚠️  Empty response ({elapsed:.2f}s)")
        
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {str(e)[:200]}")
    import traceback
    traceback.print_exc()
