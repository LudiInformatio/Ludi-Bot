import pandas as pd
import time
import json
import requests
import sys
import os
from datetime import datetime
from nba_api.stats.endpoints import leaguegamelog

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.api_helpers import retry_with_backoff

# ==========================================
# LUDI INFORMATIO | DATA INITIALIZER
# "THE CENSUS" (REALITY COMPATIBLE)
# ==========================================

def get_current_nba_season():
    """
    Determines the correct NBA season string (e.g., '2024-25') 
    based on the actual real-world date.
    """
    now = datetime.now()
    # NBA seasons start in October (Month 10).
    # If we are in Jan-Sept (1-9), the season started the previous year.
    if now.month >= 10:
        start_year = now.year
        end_year = now.year + 1
    else:
        start_year = now.year - 1
        end_year = now.year
        
    # Format: "YYYY-YY" (e.g. 2024-25)
    season_str = f"{start_year}-{str(end_year)[-2:]}"
    return season_str

@retry_with_backoff(max_attempts=3, backoff=2.0, exceptions=(Exception,))
def fetch_season_game_logs(target_season: str, headers: dict):
    """
    Fetch full season game logs from NBA API with retry logic.

    Args:
        target_season: Season string (e.g., "2025-26")
        headers: HTTP headers for API request

    Returns:
        DataFrame of game logs

    Note:
        Enhanced with 120s timeout + retry logic (Phase 6.4)
    """
    logs = leaguegamelog.LeagueGameLog(
        season=target_season,
        player_or_team_abbreviation='P',
        headers=headers,
        timeout=120
    ).get_data_frames()[0]

    return logs

def update_stats():
    print(f"\n{'='*40}")
    print(f"LUDI INFORMATIO: SEASON INITIALIZATION")
    print(f"{'='*40}")

    # 1. AUTO-DETECT REALITY
    # We use real-world data to populate the history db
    target_season = get_current_nba_season()
    
    print(f"[CENSUS] 📡 Detected Real-World Season: {target_season}")
    print(f"[CENSUS] 📡 Connecting to NBA API...")
    
    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Referer': 'https://www.nba.com/',
        'Origin': 'https://www.nba.com',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true'
    }

    try:
        # 2. FETCH FULL GAME LOGS
        print("   > Downloading Full Season Game Logs...", end=" ")

        logs = fetch_season_game_logs(target_season, headers)

        count = len(logs)
        
        if count < 100:
            print(f"❌ FAILED. Only found {count} rows. (Season might be inactive).")
            return
            
        print(f"✅ Success. ({count} Rows Downloaded)")
        
        # 3. SAVE TO JSON
        # Standardize dates to YYYY-MM-DD
        logs['GAME_DATE'] = pd.to_datetime(logs['GAME_DATE']).dt.strftime('%Y-%m-%d')
        
        filename = "ludi_history_db.json"
        logs.to_json(filename, orient='records', indent=4)
        
        print(f"[CENSUS] 💾 Saved to {filename}")
        print(f"[CENSUS] Database size: {round(len(logs) * 0.001, 2)} KB")
        print(f"[CENSUS] System Ready.")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    update_stats()