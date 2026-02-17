#!/usr/bin/env python3
"""
Re-classify all active players using the existing _assign_unified_archetype() function.

This script:
1. Fetches season stats from player_game_logs for all active players
2. Builds proper player data dicts with required fields
3. Calls _assign_unified_archetype() from Module E
4. Updates the players table with new archetypes
5. Reports before/after distribution

Author: Claude Code
Date: February 15, 2026
"""

import sqlite3
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, '/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot')

from module_e import LudiCalibrator


def fetch_season_stats(conn, player_name, team_abbr=None):
    """
    Fetch aggregated season stats from player_game_logs.

    Returns dict with keys matching what _assign_unified_archetype() expects.
    """
    cursor = conn.cursor()

    # Build query
    query = """
        SELECT
            COUNT(*) as games,
            AVG(pts) as ppg,
            AVG(ast) as apg,
            AVG(reb) as rpg,
            AVG(fg3m) as tpm,
            AVG(stl) as spg,
            AVG(blk) as bpg,
            AVG(fga) as fga,
            AVG(fta) as fta,
            AVG(tov) as tov,
            AVG(minutes) as min,
            AVG(oreb) as oreb,
            AVG(dreb) as dreb
        FROM player_game_logs
        WHERE player_name = ?
        AND game_date >= '2025-10-01'
    """

    params = [player_name]
    if team_abbr:
        query += " AND team_abbreviation = ?"
        params.append(team_abbr)

    cursor.execute(query, params)
    row = cursor.fetchone()

    if not row or row[0] == 0:
        return None

    games, ppg, apg, rpg, tpm, spg, bpg, fga, fta, tov, mins, oreb, dreb = row

    # Calculate usage percentage
    # USG% = (FGA + 0.44*FTA + TOV) / (MIN * TeamPace/48)
    # Simplified: (FGA + 0.44*FTA + TOV) / (MIN * 2.1)
    usg_pct = 0.0
    if mins and mins > 0:
        usg_pct = ((fga + 0.44 * fta + tov) / mins) / 2.1

    return {
        'name': player_name,
        'games': games,
        'base_pts': ppg or 0.0,
        'base_ast': apg or 0.0,
        'base_reb': rpg or 0.0,
        'base_3pm': tpm or 0.0,
        'base_stl': spg or 0.0,
        'base_blk': bpg or 0.0,
        'base_usg': usg_pct,
        'base_fga': fga or 0.0,
        'base_fta': fta or 0.0,
        'base_tov': tov or 0.0,
        'base_min': mins or 0.0,
        'base_oreb': oreb or 0.0,
        'base_dreb': dreb or 0.0
    }


def get_pbp_shot_quality(conn, player_name):
    """Fetch PBP Stats shot quality data."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT at_rim_freq, corner_3_freq
        FROM player_shot_quality
        WHERE player_name = ?
        AND season = '2025-26'
    """, (player_name,))

    row = cursor.fetchone()
    if row:
        return {
            'pbp_rim_freq': row[0] or 0.0,
            'pbp_corner_3_freq': row[1] or 0.0
        }
    return {}


def main():
    db_path = '/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/ludi.db'

    print("=" * 80)
    print("PLAYER ARCHETYPE RE-CLASSIFICATION")
    print("=" * 80)
    print()

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get BEFORE distribution
    print("BEFORE DISTRIBUTION:")
    print("-" * 80)
    cursor.execute("""
        SELECT archetype, COUNT(*) as count
        FROM players
        WHERE is_active = 1
        GROUP BY archetype
        ORDER BY count DESC
    """)
    before_dist = {}
    total_players = 0
    for row in cursor.fetchall():
        archetype = row[0] if row[0] else 'NULL'
        count = row[1]
        before_dist[archetype] = count
        total_players += count
        print(f"{archetype:30} {count:4} ({count/total_players*100:.1f}%)")

    print()
    print(f"Total active players: {total_players}")
    print()

    defensive_archetypes = {
        'RIM_GUARDIAN', 'PERIMETER_HAWK', 'SWITCHABLE_ANCHOR', 'HUSTLE_DISRUPTOR', 'WEAK_LINK'
    }

    # Count problematic cases
    null_count = before_dist.get('NULL', 0)
    two_way_count = before_dist.get('TWO_WAY_WING', 0)
    generalist_count = before_dist.get('GENERALIST', 0)
    problematic = null_count + two_way_count + generalist_count

    print(f"Problematic classifications:")
    print(f"  NULL:         {null_count:4} ({null_count/total_players*100:.1f}%)")
    print(f"  TWO_WAY_WING: {two_way_count:4} ({two_way_count/total_players*100:.1f}%)")
    print(f"  GENERALIST:   {generalist_count:4} ({generalist_count/total_players*100:.1f}%)")
    print(f"  TOTAL:        {problematic:4} ({problematic/total_players*100:.1f}%)")
    print()

    # Initialize Module E calibrator
    print("Initializing Module E calibrator...")
    calibrator = LudiCalibrator()
    print("✓ Calibrator loaded")
    print()

    # Fetch all active players
    cursor.execute("""
        SELECT player_id, name, team, position, archetype
        FROM players
        WHERE is_active = 1
        ORDER BY name
    """)
    players = cursor.fetchall()

    print(f"Processing {len(players)} active players...")
    print()

    # Track changes
    updated_count = 0
    no_data_count = 0
    unchanged_count = 0
    changes = []

    for player_id, name, team, position, old_archetype in players:
        # Fetch season stats
        stats = fetch_season_stats(conn, name, team)

        if not stats:
            no_data_count += 1
            print(f"⚠️  {name:30} - No game logs found, skipping")
            continue

        # Add position
        stats['position'] = position or 'UNK'
        stats['team'] = team

        # Add PBP shot quality if available
        pbp_data = get_pbp_shot_quality(conn, name)
        stats.update(pbp_data)

        # Call the archetype assignment function
        new_archetype, synergy_dict = calibrator._assign_unified_archetype(stats)

        # Check if changed
        if new_archetype != old_archetype:
            updated_count += 1
            changes.append({
                'name': name,
                'team': team,
                'old': old_archetype or 'NULL',
                'new': new_archetype,
                'stats': stats
            })

            # Update database
            cursor.execute("""
                UPDATE players
                SET archetype = ?, updated_at = ?
                WHERE player_id = ?
            """, (new_archetype, datetime.now(), player_id))

            print(f"✓ {name:30} {old_archetype or 'NULL':20} → {new_archetype:20}")
        else:
            unchanged_count += 1

    # Commit changes
    conn.commit()

    print()
    print("=" * 80)
    print(f"RECLASSIFICATION COMPLETE")
    print("=" * 80)
    print(f"Updated:   {updated_count:4}")
    print(f"Unchanged: {unchanged_count:4}")
    print(f"No data:   {no_data_count:4}")
    print()

    # Get AFTER distribution
    print("AFTER DISTRIBUTION:")
    print("-" * 80)
    cursor.execute("""
        SELECT archetype, COUNT(*) as count
        FROM players
        WHERE is_active = 1
        GROUP BY archetype
        ORDER BY count DESC
    """)
    after_dist = {}
    for row in cursor.fetchall():
        archetype = row[0] if row[0] else 'NULL'
        count = row[1]
        after_dist[archetype] = count

        # Calculate change
        before = before_dist.get(archetype, 0)
        delta = count - before
        delta_str = f"({delta:+d})" if delta != 0 else ""

        print(f"{archetype:30} {count:4} ({count/total_players*100:.1f}%) {delta_str}")

    def_count = sum(after_dist.get(a, 0) for a in defensive_archetypes)
    print()
    print(f"Defensive archetype population: {def_count} ({(def_count/total_players*100):.1f}%)")

    print()

    # Count problematic cases AFTER
    null_after = after_dist.get('NULL', 0)
    two_way_after = after_dist.get('TWO_WAY_WING', 0)
    generalist_after = after_dist.get('GENERALIST', 0)
    problematic_after = null_after + two_way_after + generalist_after

    print(f"Problematic classifications AFTER:")
    print(f"  NULL:         {null_after:4} ({null_after/total_players*100:.1f}%) [was {null_count}]")
    print(f"  TWO_WAY_WING: {two_way_after:4} ({two_way_after/total_players*100:.1f}%) [was {two_way_count}]")
    print(f"  GENERALIST:   {generalist_after:4} ({generalist_after/total_players*100:.1f}%) [was {generalist_count}]")
    print(f"  TOTAL:        {problematic_after:4} ({problematic_after/total_players*100:.1f}%) [was {problematic} = {problematic/total_players*100:.1f}%]")
    print()

    improvement = problematic - problematic_after
    print(f"✓ Reduced problematic classifications by {improvement} players ({improvement/total_players*100:.1f}%)")
    print()

    # Show notable changes
    if changes:
        print("NOTABLE CHANGES (first 20):")
        print("-" * 80)
        for i, change in enumerate(changes[:20]):
            print(f"{change['name']:30} {change['team']:3} {change['old']:20} → {change['new']:20}")
            if i >= 19:
                remaining = len(changes) - 20
                if remaining > 0:
                    print(f"... and {remaining} more changes")
                break

    conn.close()

    print()
    print("=" * 80)
    print("Script complete. Database updated.")
    print("=" * 80)


if __name__ == '__main__':
    main()
