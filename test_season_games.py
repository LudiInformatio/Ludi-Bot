#!/usr/bin/env python3
"""Test pbpstats - find correct way to get games by date"""
import sys
sys.path.insert(0, '/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot')

from pbpstats.client import Client
import os

cache_dir = "/tmp/pbpstats_cache"
os.makedirs(cache_dir, exist_ok=True)

settings = {
    "dir": cache_dir,
    "Games": {"source": "web", "data_provider": "data_nba"}
}

client = Client(settings)
print("Testing Season.games approach...")

try:
    season = client.Season("nba", "2025-26", "Regular Season")
    print(f"✅ Season loaded")
    
    if hasattr(season, 'games'):
        print(f"  Season has games attribute: {type(season.games)}")
        if hasattr(season.games, 'items'):
            total = len(season.games.items)
            print(f"  Total games: {total}")
            
            # Filter by date
            target_date = "01/17/2026"
            jan17_games = [g for g in season.games.items if g.get('date') == target_date]
            print(f"  Games on {target_date}: {len(jan17_games)}")
            
            if jan17_games:
                print(f"\n  Sample game:")
                sample = jan17_games[0]
                for key in list(sample.keys())[:10]:
                    print(f"    {key}: {sample[key]}")
        else:
            print(f"  games type: {season.games}")
            print(f"  games attrs: {dir(season.games)[:10]}")
    else:
        print(f"  Season attrs: {[a for a in dir(season) if not a.startswith('_')][:15]}")
        
except Exception as e:
    print(f"❌ {type(e).__name__}: {str(e)[:200]}")
    import traceback
    traceback.print_exc()
