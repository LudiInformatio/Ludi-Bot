
"""
DIAGNOSTIC SCRIPT: DATA GAPS
----------------------------
Checks ludi.db for missing game logs and tracking data
for the period Jan 7 - Jan 13, 2026.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

DB_PATH = "ludi.db"

def check_dates():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    
    # Define date range
    start_date = datetime(2026, 1, 7)
    end_date = datetime(2026, 1, 13)
    current = start_date
    
    dates_to_check = []
    while current <= end_date:
        dates_to_check.append(current.strftime('%Y-%m-%d'))
        current += timedelta(days=1)
        
    print(f"\n🔍 CHECKING DATA INTEGRITY: {dates_to_check[0]} to {dates_to_check[-1]}")
    print("=" * 60)
    print(f"{'DATE':<12} | {'LOGS (Tank01)':<15} | {'TRACKING (NBA)':<15} | {'STATUS'}")
    print("-" * 60)
    
    missing_logs = []
    missing_tracking = []

    for date_str in dates_to_check:
        # Check Box Scores (Tank01)
        try:
            df_logs = pd.read_sql_query(f"SELECT COUNT(*) as count FROM player_game_logs WHERE game_date = '{date_str}'", conn)
            logs_count = df_logs['count'].iloc[0]
        except:
            logs_count = 0
            
        # Check Tracking Data (NBA API)
        try:
            df_track = pd.read_sql_query(f"SELECT COUNT(*) as count FROM player_game_tracking WHERE game_date = '{date_str}'", conn)
            track_count = df_track['count'].iloc[0]
        except:
            track_count = 0
            
        # Status
        status = "✅ OK"
        if logs_count == 0:
            status = "❌ MISSING LOGS"
            missing_logs.append(date_str)
        elif track_count == 0:
            status = "⚠️  NO TRACKING"
            missing_tracking.append(date_str)
        elif track_count < logs_count * 0.5:
             status = "⚠️  PARTIAL TRACK"
            
        print(f"{date_str:<12} | {logs_count:<15} | {track_count:<15} | {status}")

    conn.close()
    
    print("=" * 60)
    if missing_logs:
        print(f"❌ MISSING GAME LOGS FOR: {', '.join(missing_logs)}")
        print("   Action: Need to re-fetch/migrate daily box scores for these dates.")
    else:
        print("✅ Box score coverage is complete for this range.")
        
    if missing_tracking:
        print(f"⚠️  MISSING TRACKING DATA FOR: {', '.join(missing_tracking)}")
        print("   Action: These should be filled by the ongoing parallel backfill.")

if __name__ == "__main__":
    check_dates()
