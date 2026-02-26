#!/usr/bin/env python3
"""
Player Foul Splits Sync - Phase 8.17 Foul Intelligence

Purpose:
    - Builds rolling 21-day foul stats from player_game_logs.pf
    - Uses player_canonical_ids for accent-safe player matching
    - Uses canonical_teams for team abbreviation normalization
    - Calculates min_dampener for foul-trouble minutes projection

Usage:
    python scripts/sync_player_foul_splits.py [--dry-run]
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')


def get_canonical_player_mapping(conn: sqlite3.Connection) -> dict:
    """
    Build mapping from normalized names to player_id and full_name.
    Uses player_canonical_ids for accent-safe matching.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT player_id, full_name, normalized_name
        FROM player_canonical_ids
    """)
    
    mapping = {}
    for row in cursor.fetchall():
        player_id, full_name, normalized_name = row
        if normalized_name:
            mapping[normalized_name.lower()] = (player_id, full_name)
    
    return mapping


def get_team_normalization(conn: sqlite3.Connection) -> dict:
    """
    Build mapping from various team abbreviations to standard abbreviation.
    Uses canonical_teams table.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT standard_abbr, bdl_abbr, espn_abbr
        FROM canonical_teams
    """)
    
    mapping = {}
    for row in cursor.fetchall():
        standard, bdl, espn = row
        if bdl:
            mapping[bdl.lower()] = standard
        if espn:
            mapping[espn.lower()] = standard
    
    return mapping


def calculate_foul_splits(conn: sqlite3.Connection, player_id: int, player_name: str,
                          window_days: int = 60) -> Optional[dict]:
    """
    Calculate foul splits for a single player over the rolling window.
    """
    cursor = conn.cursor()

    cutoff_date = (datetime.now() - timedelta(days=window_days)).strftime('%Y-%m-%d')

    # Join through player_canonical_ids for accent-safe name resolution.
    # BDL/Tank01 write non-accented names to player_game_logs; the canonical
    # table's normalized_name (lowercased, accent-stripped) bridges the gap.
    cursor.execute("""
        SELECT
            g.pf,
            g.minutes,
            g.game_date,
            g.team_abbreviation,
            gm.home_team,
            gm.away_team,
            gm.referee_crew
        FROM player_game_logs g
        JOIN player_canonical_ids pci ON LOWER(g.player_name) = pci.normalized_name
        LEFT JOIN games gm ON g.game_id = gm.game_id
        WHERE pci.canonical_id = ?
          AND g.game_date >= ?
          AND g.minutes > 0
          AND g.pf IS NOT NULL
    """, (player_id, cutoff_date))
    
    games = cursor.fetchall()
    
    if len(games) < 3:
        return None
    
    games_count = len(games)
    total_pf = sum(g[0] for g in games if g[0] is not None)
    avg_pf = total_pf / games_count if games_count > 0 else 0.0
    
    total_minutes = sum(g[1] for g in games if g[1] is not None and g[1] > 0)
    pf_per_36 = (total_pf * 36.0 / total_minutes) if total_minutes > 0 else 0.0
    
    games_4plus = sum(1 for g in games if g[0] is not None and g[0] >= 4)
    pct_4plus = games_4plus / games_count if games_count > 0 else 0.0
    
    minutes_normal = [g[1] for g in games if g[0] is not None and g[0] < 4 and g[1] is not None]
    minutes_foul = [g[1] for g in games if g[0] is not None and g[0] >= 4 and g[1] is not None]
    
    avg_min_normal = sum(minutes_normal) / len(minutes_normal) if minutes_normal else None
    avg_min_foul = sum(minutes_foul) / len(minutes_foul) if minutes_foul else None
    
    min_dampener = 1.0
    if avg_min_foul and avg_min_normal and avg_min_normal > 0:
        min_dampener = round(avg_min_foul / avg_min_normal, 3)
        min_dampener = max(0.70, min(1.0, min_dampener))
    elif pct_4plus > 0:
        min_dampener = max(0.80, 1.0 - (pct_4plus * 0.25))
    
    cursor.execute("""
        SELECT archetype FROM players WHERE name = ?
    """, (player_name,))
    archetype_row = cursor.fetchone()
    archetype = archetype_row[0] if archetype_row else None
    
    pf_vs_strict = None
    pf_vs_lenient = None
    
    cursor.execute("""
        SELECT AVG(g.pf)
        FROM player_game_logs g
        JOIN player_canonical_ids pci ON LOWER(g.player_name) = pci.normalized_name
        JOIN games gm ON g.game_id = gm.game_id
        JOIN referee_profiles rp ON gm.referee_crew LIKE '%' || rp.referee_name || '%'
        WHERE pci.canonical_id = ?
          AND g.game_date >= ?
          AND rp.style = 'STRICT'
          AND g.minutes > 0
    """, (player_id, cutoff_date))
    strict_row = cursor.fetchone()
    if strict_row and strict_row[0]:
        pf_vs_strict = strict_row[0]

    cursor.execute("""
        SELECT AVG(g.pf)
        FROM player_game_logs g
        JOIN player_canonical_ids pci ON LOWER(g.player_name) = pci.normalized_name
        JOIN games gm ON g.game_id = gm.game_id
        JOIN referee_profiles rp ON gm.referee_crew LIKE '%' || rp.referee_name || '%'
        WHERE pci.canonical_id = ?
          AND g.game_date >= ?
          AND rp.style = 'LENIENT'
          AND g.minutes > 0
    """, (player_id, cutoff_date))
    lenient_row = cursor.fetchone()
    if lenient_row and lenient_row[0]:
        pf_vs_lenient = lenient_row[0]
    
    if games_count >= 15:
        confidence = 'HIGH'
    elif games_count >= 8:
        confidence = 'MEDIUM'
    else:
        confidence = 'LOW'
    
    return {
        'player_id': player_id,
        'player_name': player_name,
        'season': '2025-26',
        'games_in_window': games_count,
        'avg_pf_per_game': round(avg_pf, 2),
        'pf_per_36_min': round(pf_per_36, 2),
        'games_4plus_fouls': games_4plus,
        'pct_games_4plus_fouls': round(pct_4plus, 3),
        'archetype': archetype,
        'avg_min_normal': round(avg_min_normal, 1) if avg_min_normal else None,
        'avg_min_foul_trouble': round(avg_min_foul, 1) if avg_min_foul else None,
        'min_dampener': round(min_dampener, 3),
        'avg_pf_vs_strict': round(pf_vs_strict, 2) if pf_vs_strict else None,
        'avg_pf_vs_lenient': round(pf_vs_lenient, 2) if pf_vs_lenient else None,
        'data_confidence': confidence
    }


def sync_foul_splits(dry_run: bool = False, window_days: int = 60):
    """
    Main sync function - builds foul splits for all active players.
    Default window: 60 days (305 HIGH confidence players vs 0 at 21 days).
    Use --window-days 21 for recent-form analysis.
    """
    print("\n" + "=" * 60)
    print("PLAYER FOUL SPLITS SYNC - Phase 8.17 Foul Intelligence")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}  |  Window: {window_days} days")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT canonical_id, full_name
            FROM player_canonical_ids
            WHERE is_active = 1
        """)

        players = cursor.fetchall()
        print(f"\n📊 Found {len(players)} active players to process\n")

        processed = 0
        skipped = 0

        for canonical_id, full_name in players:
            try:
                splits = calculate_foul_splits(conn, canonical_id, full_name, window_days=window_days)
                
                if splits:
                    if dry_run:
                        print(f"   [DRY] {full_name}: {splits['games_in_window']} games, "
                              f"avg PF: {splits['avg_pf_per_game']}, dampener: {splits['min_dampener']}")
                    else:
                        cursor.execute("""
                            INSERT OR REPLACE INTO player_foul_splits (
                                player_id, player_name, season,
                                games_in_window, avg_pf_per_game, pf_per_36_min,
                                games_4plus_fouls, pct_games_4plus_fouls,
                                archetype, avg_min_normal, avg_min_foul_trouble,
                                min_dampener, avg_pf_vs_strict, avg_pf_vs_lenient,
                                data_confidence, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (
                            splits['player_id'], splits['player_name'], splits['season'],
                            splits['games_in_window'], splits['avg_pf_per_game'], splits['pf_per_36_min'],
                            splits['games_4plus_fouls'], splits['pct_games_4plus_fouls'],
                            splits['archetype'], splits['avg_min_normal'], splits['avg_min_foul_trouble'],
                            splits['min_dampener'], splits['avg_pf_vs_strict'], splits['avg_pf_vs_lenient'],
                            splits['data_confidence']
                        ))
                    
                    processed += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"   ⚠️ Error processing {full_name}: {e}")
                skipped += 1
        
        if not dry_run:
            conn.commit()
        
        print("\n" + "=" * 60)
        print("SYNC SUMMARY")
        print("=" * 60)
        print(f"   Players processed: {processed}")
        print(f"   Players skipped (<3 games): {skipped}")
        
        if not dry_run:
            cursor.execute("""
                SELECT COUNT(*), AVG(avg_pf_per_game), 
                       COUNT(CASE WHEN data_confidence='HIGH' THEN 1 END) as high_conf,
                       COUNT(CASE WHEN data_confidence='MEDIUM' THEN 1 END) as med_conf
                FROM player_foul_splits
            """)
            row = cursor.fetchone()
            print(f"\n   Database stats:")
            print(f"      Total players: {row[0]}")
            print(f"      Avg PF/game: {row[1]:.2f}" if row[1] else "      Avg PF/game: N/A")
            print(f"      HIGH confidence: {row[2]}")
            print(f"      MEDIUM confidence: {row[3]}")
            print("\n   ✅ Database updated successfully")
        else:
            print("\n   🔍 DRY RUN complete (no changes made)")
        
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Player Foul Splits Sync')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without writing to DB')
    parser.add_argument('--window-days', type=int, default=60,
                        help='Rolling window in days (default: 60). Use 21 for recent form, 7 for hot/cold.')

    args = parser.parse_args()
    sync_foul_splits(dry_run=args.dry_run, window_days=args.window_days)
