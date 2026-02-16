#!/usr/bin/env python3
"""
LUDI INFORMATIO | CREATE TRACKING SCHEMA
=========================================
Creates 3 new tables for advanced tracking stats:
1. player_game_tracking - Per-game shot types & difficulty
2. player_speed_stats - Season-level speed/distance
3. game_matchups - Per-game defensive matchups

Usage:
    ./venv/bin/python scripts/create_tracking_schema.py
"""

import sqlite3
import sys
import os

def create_tracking_schema():
    """Create all tracking tables and indexes."""
    db_path = 'ludi.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    print("=" * 60)
    print("LUDI INFORMATIO: TRACKING SCHEMA CREATION")
    print("=" * 60)
    
    # Table 1: player_game_tracking
    print("\n[1/3] Creating player_game_tracking table...")
    c.execute('''
        CREATE TABLE IF NOT EXISTS player_game_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Identifiers
            nba_player_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            nba_game_id TEXT NOT NULL,
            game_date TEXT NOT NULL,
            team_abbr TEXT,
            
            -- SHOT TYPES (PlayerDashboardByShootingSplits)
            drives_fga INTEGER DEFAULT 0,
            drives_fgm INTEGER DEFAULT 0,
            catch_shoot_fga INTEGER DEFAULT 0,
            catch_shoot_fgm INTEGER DEFAULT 0,
            pull_up_fga INTEGER DEFAULT 0,
            pull_up_fgm INTEGER DEFAULT 0,
            
            -- SHOT DIFFICULTY (PlayerDashPtShots)
            contested_fga INTEGER DEFAULT 0,
            tight_fga INTEGER DEFAULT 0,
            open_fga INTEGER DEFAULT 0,
            wide_open_fga INTEGER DEFAULT 0,
            avg_defender_dist REAL DEFAULT 0,
            
            -- Metadata
            synced_at TEXT,
            
            UNIQUE(nba_player_id, nba_game_id)
        )
    ''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_tracking_player ON player_game_tracking(nba_player_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_tracking_date ON player_game_tracking(game_date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_tracking_game ON player_game_tracking(nba_game_id)')
    print("   ✅ player_game_tracking created")
    
    # Table 2: player_speed_stats
    print("\n[2/3] Creating player_speed_stats table...")
    c.execute('''
        CREATE TABLE IF NOT EXISTS player_speed_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            nba_player_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            team_abbr TEXT,
            season TEXT NOT NULL,
            
            -- SPEED/DISTANCE (LeagueDashPtStats)
            games_played INTEGER DEFAULT 0,
            avg_minutes REAL DEFAULT 0,
            dist_miles REAL DEFAULT 0,
            dist_miles_off REAL DEFAULT 0,
            dist_miles_def REAL DEFAULT 0,
            avg_speed REAL DEFAULT 0,
            avg_speed_off REAL DEFAULT 0,
            avg_speed_def REAL DEFAULT 0,
            
            synced_at TEXT,
            
            UNIQUE(nba_player_id, season)
        )
    ''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_speed_player ON player_speed_stats(nba_player_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_speed_season ON player_speed_stats(season)')
    print("   ✅ player_speed_stats created")
    
    # Table 3: game_matchups
    print("\n[3/3] Creating game_matchups table...")
    c.execute('''
        CREATE TABLE IF NOT EXISTS game_matchups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Offense
            off_player_id INTEGER NOT NULL,
            off_player_name TEXT,
            
            -- Defense
            def_player_id INTEGER NOT NULL,
            def_player_name TEXT,
            def_team TEXT,
            
            -- Game
            nba_game_id TEXT NOT NULL,
            game_date TEXT,
            
            -- Stats
            matchup_minutes REAL DEFAULT 0,
            possessions INTEGER DEFAULT 0,
            fgm INTEGER DEFAULT 0,
            fga INTEGER DEFAULT 0,
            fg_pct REAL DEFAULT 0,
            fg3m INTEGER DEFAULT 0,
            fg3a INTEGER DEFAULT 0,
            player_points INTEGER DEFAULT 0,
            
            synced_at TEXT,
            
            UNIQUE(off_player_id, def_player_id, nba_game_id)
        )
    ''')
    
    c.execute('CREATE INDEX IF NOT EXISTS idx_matchups_off ON game_matchups(off_player_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_matchups_def ON game_matchups(def_player_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_matchups_game ON game_matchups(nba_game_id)')
    print("   ✅ game_matchups created")
    
    conn.commit()
    
    # Verify
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    tables = ['player_game_tracking', 'player_speed_stats', 'game_matchups']
    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        count = c.fetchone()[0]
        print(f"   {table}: {count} records")
    
    conn.close()
    
    print("\n✅ Schema creation complete!")
    print("=" * 60)

if __name__ == "__main__":
    create_tracking_schema()
