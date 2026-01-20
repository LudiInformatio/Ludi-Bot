#!/usr/bin/env python3
"""
WOWY Lineup Extractor using pbpstats
Extracts lineup performance data (who played with/without whom)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from pbpstats.client import Client
from datetime import datetime
import time

def extract_lineup_data_for_game(game_id, conn):
    """
    Extract lineup stats (WOWY data) for a single game
    Returns: player_id → [lineups_with, lineups_without, net_rating_diff]
    """
    cache_dir = "/tmp/pbpstats_cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    settings = {
        "dir": cache_dir,
        "Possessions": {"source": "web", "data_provider": "data_nba"}
    }
    
    try:
        client = Client(settings)
        game = client.Game(game_id)
        
        if not hasattr(game, 'possessions') or not game.possessions:
            return None
        
        # Get lineup stats
        lineup_stats = game.possessions.lineup_stats
        
        # Build player WOWY matrix
        player_wowy = {}
        
        for lineup in lineup_stats:
            lineup_id = lineup.get('LineupId', lineup.get('lineup_id', ''))
            off_rating = float(lineup.get('OffRtg', lineup.get('off_rating', 0)))
            def_rating = float(lineup.get('DefRtg', lineup.get('def_rating', 0)))
            net_rating = off_rating - def_rating
            possessions = int(lineup.get('Poss', lineup.get('possessions', 0)))
            
            # Parse player IDs from lineup
            player_ids = lineup_id.split('-') if lineup_id else []
            
            for player_id in player_ids:
                if player_id not in player_wowy:
                    player_wowy[player_id] = {
                        'with_lineups': [],
                        'net_ratings': []
                    }
                
                player_wowy[player_id]['with_lineups'].append({
                    'lineup_id': lineup_id,
                    'net_rating': net_rating,
                    'possessions': possessions,
                    'teammates': [pid for pid in player_ids if pid != player_id]
                })
                player_wowy[player_id]['net_ratings'].append(net_rating)
        
        return player_wowy
        
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {str(e)[:100]}")
        return None

def main():
    """Test on a recent game"""
    # Example: Use NBA game ID (10-digit format starting with 002)
    # Format: 002YYSSSGGG where YY=season year, SSS=season type, GGG=game number
    
    # Test with a known game
    test_game_id = "0022500500"  # Example 2025-26 season game
    
    print(f"🎯 Testing WOWY extraction for game {test_game_id}...")
    
    conn = sqlite3.connect('ludi.db')
    result = extract_lineup_data_for_game(test_game_id, conn)
    conn.close()
    
    if result:
        print(f"\n✅ SUCCESS! Extracted lineup data for {len(result)} players")
        
        # Show sample
        sample_player = list(result.keys())[0]
        sample_data = result[sample_player]
        print(f"\nSample player {sample_player}:")
        print(f"  Lineups played: {len(sample_data['with_lineups'])}")
        if sample_data['net_ratings']:
            avg_net = sum(sample_data['net_ratings']) / len(sample_data['net_ratings'])
            print(f"  Average net rating: {avg_net:.1f}")
    else:
        print("\n❌ Failed to extract data")

if __name__ == '__main__':
    main()
