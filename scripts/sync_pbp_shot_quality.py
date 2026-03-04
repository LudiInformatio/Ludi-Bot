#!/usr/bin/env python3
"""
LUDI INFORMATIO | PBP SHOT QUALITY SYNC
=======================================
Syncs "Expected eFG%" (Shot Quality) and "Avg Shot Distance" from PBP Stats API.
This data forms the "Quality" layer of the Ludi "Super Signal" (Actual vs Expected).

Usage:
    python scripts/sync_pbp_shot_quality.py --season 2025-26
"""

import sys
import os
import argparse
import sqlite3
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH
from utils.pbp_stats_client import get_totals, get_all_players

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    return conn

def ensure_table_exists():
    """Creates player_shot_quality table if not exists."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # FORCE RESET: Drop old table to ensure schema match
    c.execute('DROP TABLE IF EXISTS player_shot_quality')
    
    # Table Schema: Links to player_id (NBA ID)
    # Includes ShotQualityAvg (Expected eFG%) and Distance metrics
    c.execute('''
        CREATE TABLE IF NOT EXISTS player_shot_quality (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL,
            player_name TEXT,
            team_id TEXT,
            season TEXT,
            games_played INTEGER,
            minutes INTEGER,
            
            -- Core Quality Metrics
            shot_quality_avg REAL,        -- Expected eFG%
            avg_2pt_distance REAL,
            avg_3pt_distance REAL,
            
            -- Frequencies (Style Profile)
            at_rim_freq REAL,             -- % of shots at rim
            short_mid_freq REAL,
            long_mid_freq REAL,
            corner_3_freq REAL,
            arc_3_freq REAL,
            
            -- Efficiency Context
            points_added REAL,            -- Points over expectation
            off_rating REAL,
            
            synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(player_id, season)
        );
    ''')
    
    conn.commit()
    conn.close()

def sync_shot_quality(season="2025-26"):
    print(f"\n💎 PBP SHOT QUALITY SYNC | Season {season}")
    print("="*60)
    
    ensure_table_exists()
    
    # 1. Fetch Totals for ALL Players (One giant efficient call)
    print("🚀 Fetching league-wide player totals from PBP Stats...")
    # "Player" type with no TeamId fetches entire league
    data = get_totals("Player", season=season)
    
    if not data or 'multi_row_table_data' not in data:
        print("❌ Failed to fetch data from PBP Stats.")
        return

    players = data['multi_row_table_data']
    print(f"   ✅ Received {len(players)} player records.")
    
    # 2. Process & Save
    print(f"💾 Saving to SQLite ({DB_PATH})...")
    conn = get_db_connection()
    c = conn.cursor()
    
    count = 0
    updated = 0
    
    for p in players:
        try:
            # Extract key fields
            pid = p.get('EntityId')
            name = p.get('Name')
            team_id = p.get('TeamId')
            gp = p.get('GamesPlayed', 0)
            mins = p.get('Minutes', 0)
            
            # Skip players with negligible minutes (noise)
            if mins < 10: 
                continue
                
            # Quality Metrics
            sq_avg = p.get('ShotQualityAvg', 0.0)
            dist_2 = p.get('Avg2ptShotDistance', 0.0)
            dist_3 = p.get('Avg3ptShotDistance', 0.0)
            
            # Frequencies
            at_rim = p.get('AtRimFrequency', 0.0)
            short_mid = p.get('ShortMidRangeFrequency', 0.0)
            long_mid = p.get('LongMidRangeFrequency', 0.0)
            corner_3 = p.get('Corner3Frequency', 0.0)
            arc_3 = p.get('Arc3Frequency', 0.0)
            
            # Context
            # PointsAdded is useful but sometimes missing, default to 0
            pts_added = p.get('ShotQualityPointsAdded', 0.0) 
            off_rtg = p.get('OffRtg', 0.0)

            # UPSERT Query
            sql = '''
                INSERT INTO player_shot_quality (
                    player_id, player_name, team_id, season, games_played, minutes,
                    shot_quality_avg, avg_2pt_distance, avg_3pt_distance,
                    at_rim_freq, short_mid_freq, long_mid_freq, corner_3_freq, arc_3_freq,
                    points_added, off_rating, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(player_id, season) DO UPDATE SET
                    games_played=excluded.games_played,
                    minutes=excluded.minutes,
                    shot_quality_avg=excluded.shot_quality_avg,
                    avg_2pt_distance=excluded.avg_2pt_distance,
                    avg_3pt_distance=excluded.avg_3pt_distance,
                    at_rim_freq=excluded.at_rim_freq,
                    short_mid_freq=excluded.short_mid_freq,
                    long_mid_freq=excluded.long_mid_freq,
                    corner_3_freq=excluded.corner_3_freq,
                    arc_3_freq=excluded.arc_3_freq,
                    points_added=excluded.points_added,
                    off_rating=excluded.off_rating,
                    synced_at=CURRENT_TIMESTAMP
            '''
            
            vals = [
                pid, name, team_id, season, gp, mins,
                sq_avg, dist_2, dist_3,
                at_rim, short_mid, long_mid, corner_3, arc_3,
                pts_added, off_rtg
            ]
            
            c.execute(sql, vals)
            count += 1
            
        except Exception as e:
            print(f"   ⚠️ Error processing {p.get('Name')}: {e}")
            continue
            
    conn.commit()
    conn.close()
    
    print("="*60)
    print(f"✅ Sync Complete. Processed {count} players.")
    print("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2025-26", help="NBA Season (e.g. 2025-26)")
    args = parser.parse_args()
    
    sync_shot_quality(season=args.season)
