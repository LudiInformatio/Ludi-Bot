#!/usr/bin/env python3
"""
PBP Stats Season Totals Sync

Syncs season-level player statistics from PBP Stats API including:
- Shot quality average (ShotQualityAvg)
- Shot zone frequencies (AtRimFrequency, Corner3Frequency, etc.)
- Efficiency metrics (EfgPct, TsPct, etc.)

This is an alternative to per-game shot quality when the game stats endpoint is unavailable.

Usage:
    python scripts/sync_pbp_totals.py
"""
import sys
import os
import sqlite3
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "ludi.db"
CURRENT_SEASON = "2025-26"


def fetch_player_totals():
    """Fetch season totals for all players from PBP Stats."""
    print(f"[PBP_TOTALS] Fetching player totals for {CURRENT_SEASON}...")
    
    url = "https://api.pbpstats.com/get-totals/nba"
    params = {
        "Season": CURRENT_SEASON,
        "SeasonType": "Regular Season",
        "Type": "Player"
    }
    
    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        players = data.get('multi_row_table_data', [])
        print(f"[PBP_TOTALS] Fetched {len(players)} player records")
        return players
    except requests.RequestException as e:
        print(f"[PBP_TOTALS] Error fetching totals: {e}")
        return []


def ensure_player_season_quality_table(conn):
    """Create table for storing season-level shot quality data."""
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS player_season_quality (
            player_id INTEGER PRIMARY KEY,
            player_name TEXT NOT NULL,
            team_id INTEGER,
            team_abbr TEXT,
            season TEXT NOT NULL,
            
            -- Shot Quality Metrics
            shot_quality_avg REAL,
            efg_pct REAL,
            ts_pct REAL,
            
            -- Shot Zone Frequencies
            at_rim_frequency REAL,
            at_rim_accuracy REAL,
            short_mid_range_frequency REAL,
            short_mid_range_accuracy REAL,
            long_mid_range_frequency REAL,
            long_mid_range_accuracy REAL,
            corner3_frequency REAL,
            corner3_accuracy REAL,
            arc3_frequency REAL,
            arc3_accuracy REAL,
            
            -- Volume
            fga INTEGER,
            fgm INTEGER,
            fg3a INTEGER,
            fg3m INTEGER,
            minutes INTEGER,
            games_played INTEGER,
            
            -- Assisted rates
            assisted_2s_pct REAL,
            assisted_3s_pct REAL,
            
            -- Metadata
            synced_at TEXT,
            source TEXT DEFAULT 'pbp_stats',
            
            UNIQUE(player_id, season)
        )
    ''')
    
    conn.commit()
    print("[PBP_TOTALS] Ensured player_season_quality table exists")


def sync_player_totals(players, conn):
    """Insert/update player season quality data."""
    c = conn.cursor()
    
    inserted = 0
    for p in players:
        try:
            c.execute('''
                INSERT OR REPLACE INTO player_season_quality (
                    player_id, player_name, team_id, team_abbr, season,
                    shot_quality_avg, efg_pct, ts_pct,
                    at_rim_frequency, at_rim_accuracy,
                    short_mid_range_frequency, short_mid_range_accuracy,
                    long_mid_range_frequency, long_mid_range_accuracy,
                    corner3_frequency, corner3_accuracy,
                    arc3_frequency, arc3_accuracy,
                    fga, fgm, fg3a, fg3m, minutes, games_played,
                    assisted_2s_pct, assisted_3s_pct,
                    synced_at, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                p.get('EntityId'),
                p.get('Name'),
                p.get('TeamId'),
                p.get('TeamAbbreviation'),
                CURRENT_SEASON,
                p.get('ShotQualityAvg'),
                p.get('EfgPct'),
                p.get('TsPct'),
                p.get('AtRimFrequency'),
                p.get('AtRimAccuracy'),
                p.get('ShortMidRangeFrequency'),
                p.get('ShortMidRangeAccuracy'),
                p.get('LongMidRangeFrequency'),
                p.get('LongMidRangeAccuracy'),
                p.get('Corner3Frequency'),
                p.get('Corner3Accuracy'),
                p.get('Arc3Frequency'),
                p.get('Arc3Accuracy'),
                p.get('FGA'),
                p.get('FGM'),
                p.get('FG3A'),
                p.get('FG3M'),
                p.get('Minutes'),
                p.get('GamesPlayed'),
                p.get('Assisted2sPct'),
                p.get('Assisted3sPct'),
                datetime.now().isoformat(),
                'pbp_stats'
            ))
            inserted += 1
        except Exception as e:
            print(f"[PBP_TOTALS] Error inserting {p.get('Name')}: {e}")
    
    conn.commit()
    return inserted


def main():
    print("=" * 60)
    print("   PBP STATS SEASON TOTALS SYNC")
    print(f"   Season: {CURRENT_SEASON}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Fetch data
    players = fetch_player_totals()
    if not players:
        print("[PBP_TOTALS] No data fetched. Exiting.")
        return
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH, timeout=30)
    
    # Ensure table exists
    ensure_player_season_quality_table(conn)
    
    # Sync data
    inserted = sync_player_totals(players, conn)
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"   SYNC COMPLETE")
    print(f"   Players inserted/updated: {inserted}")
    print("=" * 60)


if __name__ == "__main__":
    main()
