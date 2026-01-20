#!/usr/bin/env python3
"""Test pbpstats API with proper usage"""
import sys
sys.path.insert(0, '/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot')

from pbpstats.client import Client
import time
import os

print("Testing PBP Stats API (Possessions for lineup data)...")
start = time.time()

try:
    # Create cache directory
    cache_dir = "/tmp/pbpstats_cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    # Settings for client
    settings = {
        "dir": cache_dir,
        "Possessions": {"source": "web", "data_provider": "data_nba"},
        "Boxscore": {"source": "web", "data_provider": "data_nba"}
    }
    
    client = Client(settings)
    print(f"✅ Client initialized ({time.time() - start:.2f}s)")
    
    # Try getting games for a date
    print("\nFetching games for Jan 17, 2026...", end=" ", flush=True)
    start = time.time()
    
    season = client.Season("nba", "2025-26", "Regular Season")
    print(f"✅ Season loaded ({time.time() - start:.2f}s)")
    
    # Get games for a specific day
    print("\nFetching day games...", end=" ", flush=True)
    start = time.time()
    day = client.Day("01/17/2026", "nba")
    print(f"✅ Day loaded ({time.time() - start:.2f}s)")
    
    if hasattr(day, 'games') and day.games:
        print(f"\nFound {len(day.games.items)} games:")
        for game in day.games.items[:3]:
            print(f"  - Game ID: {game['game_id']}")
            
        # Try to load possession data for first game
        if day.games.items:
            first_game_id = day.games.items[0]['game_id']
            print(f"\nLoading possessions for {first_game_id}...", end=" ", flush=True)
            start = time.time()
            
            game = client.Game(first_game_id)
            elapsed = time.time() - start
            print(f"✅ Game loaded ({elapsed:.2f}s)")
            
            if hasattr(game, 'possessions') and game.possessions:
                print(f"  Possessions: {len(game.possessions.items)} items")
                
                # Show sample possession with lineup
                if game.possessions.items:
                    sample = game.possessions.items[0]
                    print(f"\n  Sample possession:")
                    print(f"    Start time: {getattr(sample, 'start_time', 'N/A')}")
                    print(f"    Offense team: {getattr(sample, 'offense_team_id', 'N/A')}")
                    if hasattr(sample, 'lineup_ids'):
                        print(f"    Lineup IDs: {sample.lineup_ids[:5]}...")
    else:
        print("⚠️  No games found")
        
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {str(e)[:300]}")
    import traceback
    traceback.print_exc()
