
from nba_api.stats.endpoints import boxscoresummaryv2
import time

def test_nba_api_refs():
    # Game ID: 0022500010 (First Week 2025-26)
    game_id = "0022500010"
    print(f"Testing NBA API fetch for Game {game_id}...")
    
    try:
        box = boxscoresummaryv2.BoxScoreSummaryV2(game_id=game_id)
        # Officials are usually in the 'Officials' dataset
        officials = box.officials.get_data_frame()
        
        if not officials.empty:
            print("\n✅ Found Officials Data:")
            # Force pandas to print all columns
            import pandas as pd
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 1000)
            print(officials)
            return True
        else:
            print("❌ No officials data found in response.")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_nba_api_refs()
