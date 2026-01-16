#!/usr/bin/env python3
"""
LUDI INFORMATIO | REFEREE DATA SEEDER
Phase 4: Hybrid Seeding Strategy

Purpose:
    - Reads extracted JSON data (from browser subagent)
    - Populates 'referee_profiles' with valid 2025-26 season data
    - Initializes the Learning Engine with a strong baseline

Usage:
    python scripts/seed_referees.py [--dry-run]
"""

import json
import sqlite3
import argparse
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH

# League averages (2025-26 season)
LEAGUE_AVG_FOULS_PER_GAME = 21.5


def seed_database(json_path: str, dry_run: bool = False):
    print("\n" + "=" * 60)
    print("LUDI INFORMATIO | REFEREE SEEDING ENGINE")
    print(f"Source: {json_path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print("=" * 60)
    
    if not os.path.exists(json_path):
        print(f"❌ Error: File not found at {json_path}")
        return
    
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    print(f"   📥 Loaded {len(data)} referees from JSON")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    updated_count = 0
    
    for ref in data:
        name = ref.get('name')
        
        # 'pf' in input is Total Fouls Per Game (Combined Team Fouls)
        # BBR represents this as one number e.g. 41.5
        avg_fouls = ref.get('pf', 0.0)
        
        # Calculate pace impact relative to league average
        # Higher foul calls = higher pace/scoring potential via FTs
        avg_pace_impact = round(avg_fouls / LEAGUE_AVG_FOULS_PER_GAME, 3)
        
        # Determine Style
        # Values refer to Combined Team Fouls per Game
        # < 40 = Lenient (avg is ~42 total fouls per game: 21 home + 21 away)
        # > 44 = Strict
        # Note: BBR values seem to hover around 40-42.
        # Let's adjust thresholds based on the data sample we saw:
        # High: 43+ (Buchert 43.7) -> Strict
        # Low: < 40 (Van Duyne 39.9) -> Lenient
        # Neutral: 40-43
        
        if avg_fouls >= 42.5:
            style = 'STRICT'
        elif avg_fouls <= 40.0:
            style = 'LENIENT'
        else:
            style = 'NEUTRAL'
            
        if dry_run:
            print(f"      - {name}: {avg_fouls} PF/G -> {style}")
        else:
            c.execute('''
                INSERT INTO referee_profiles (
                    referee_name, avg_fouls_per_game, avg_pace_impact,
                    avg_technical_rate, style, last_updated, data_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(referee_name) DO UPDATE SET
                    avg_fouls_per_game = excluded.avg_fouls_per_game,
                    avg_pace_impact = excluded.avg_pace_impact,
                    style = excluded.style,
                    last_updated = excluded.last_updated,
                    data_source = excluded.data_source
            ''', (
                name,
                avg_fouls,
                avg_pace_impact,
                0.0, # Tech rate not in seed data
                style,
                datetime.now().isoformat(),
                'seed-json-2026'
            ))
            updated_count += 1
            
    if not dry_run:
        conn.commit()
        print(f"\n   ✅ Successfully seeded {updated_count} referees into database.")
    
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    JSON_PATH = os.path.join(PROJECT_ROOT, "scripts/data/referee_seed_2026.json")
    
    seed_database(JSON_PATH, args.dry_run)
