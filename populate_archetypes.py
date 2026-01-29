#!/usr/bin/env python3
"""
Ludi Informatio: Archetype Population Script
Phase 5.5 - 16-Archetype System

Uses Module E's 16-archetype system to populate players.archetype column
based on their last 20 games of data.

Note: This is a simplified version for bulk population. Full classification
with synergy playtype modifiers happens in Module E during calibration.
"""

import sqlite3
from datetime import datetime, timedelta

# Database path
DB_PATH = "ludi.db"

# 16-Archetype Classification (With tracking/synergy data)
def classify_archetype(pts, reb, ast, tpm, stl, blk, usg, synergy_data, tracking_data):
    """
    16-Archetype Classification System (Phase 5.5)
    Uses synergy playtypes and tracking data from database for accurate classification.
    """
    stocks = stl + blk

    # Extract synergy frequencies
    prh_freq = synergy_data.get('PR_BALL_HANDLER', 0)
    iso_freq = synergy_data.get('ISO', 0)
    trans_freq = synergy_data.get('TRANSITION', 0)
    spot_freq = synergy_data.get('SPOT_UP', 0)
    prr_freq = synergy_data.get('PR_ROLL_MAN', 0)
    post_freq = synergy_data.get('POST_UP', 0)
    cut_freq = synergy_data.get('CUT', 0)

    # Extract tracking data
    drives = tracking_data.get('avg_drives', 0)
    cs_fga = tracking_data.get('avg_cs_fga', 0)
    pu_fga = tracking_data.get('avg_pu_fga', 0)

    # === TIER 1: ENGINES (High-Usage Creators) ===

    # HELIOCENTRIC_MAESTRO - High assists + P&R handler
    if (usg > 0.28 and ast > 8.0) or (usg > 0.30 and ast > 6.0 and prh_freq > 15.0):
        return "HELIOCENTRIC_MAESTRO"

    # ISO_ASSASSIN - High scoring + ISO frequency
    if pts > 22.0 and usg > 0.26 and iso_freq > 10.0:
        return "ISO_ASSASSIN"

    # SLASHING_CREATOR - High drives + low 3s
    if (pts > 18.0 and drives > 6.0 and tpm < 1.5) or (pts > 20.0 and tpm < 1.5 and trans_freq > 10.0):
        return "SLASHING_CREATOR"

    # JUMBO_FACILITATOR - Big body + passing + P&R
    if reb > 5.0 and ast > 4.0 and prh_freq > 8.0:
        return "JUMBO_FACILITATOR"

    # === TIER 2: SCORING SPECIALISTS ===

    # SNIPER_ELITE - High 3PM + spot-up
    if (tpm > 2.2 and spot_freq > 12.0) or (tpm > 2.5 and cs_fga > 4.0):
        return "SNIPER_ELITE"

    # TWO_LEVEL_SCORER - Mid-range + ISO
    if pts > 20.0 and 1.5 < tpm < 2.5 and iso_freq > 8.0:
        return "TWO_LEVEL_SCORER"

    # ATHLETIC_FINISHER - Moderate scoring + transition
    if pts > 15.0 and pts < 22.0 and trans_freq > 10.0:
        return "ATHLETIC_FINISHER"

    # === TIER 3: BIG MEN (Rebounding & Rim) ===

    # WARRIOR_BIG - Elite rebounding + P&R roll man
    if reb > 7.5 and ast > 2.0 and prr_freq > 8.0:
        return "WARRIOR_BIG"

    # VULTURE_BIG - Elite rebounding + transition
    if reb > 8.0 and ast < 2.5 and trans_freq > 8.0:
        return "VULTURE_BIG"

    # STRETCH_BIG - Rebounding + 3pt + spot-up
    if reb > 4.5 and tpm > 1.3 and (spot_freq > 8.0 or cs_fga > 2.0):
        return "STRETCH_BIG"

    # POST_ANCHOR - High reb + post-up
    if reb > 7.0 and post_freq > 8.0:
        return "POST_ANCHOR"

    # ROLL_MAN - P&R roll man + low usage
    if (prr_freq > 12.0 and usg < 0.25) or (reb > 5.5 and prr_freq > 10.0 and tpm < 1.2):
        return "ROLL_MAN"

    # === TIER 4: ROLE PLAYERS & DEFENDERS ===

    # SCREEN_NAVIGATOR - High steals
    if stl > 1.0 and pts < 20.0:
        return "SCREEN_NAVIGATOR"

    # ISLAND_DEFENDER - High stocks
    if stocks > 1.5 and pts < 18.0:
        return "ISLAND_DEFENDER"

    # CUTTER_SPECIALIST - Cutting + low usage
    if (cut_freq > 10.0 and usg < 0.22) or (pts > 6.0 and pts < 16.0 and drives < 2.0):
        return "CUTTER_SPECIALIST"

    # FACILITATOR - High assists
    if (ast > 3.5 and pts < 20.0) or (prh_freq > 10.0 and ast > 3.0 and usg < 0.25):
        return "FACILITATOR"

    # === RELAXED FALLBACKS (reduce GENERALIST %) ===

    # Relaxed engines
    if ast > 6.0 and usg > 0.22:
        return "HELIOCENTRIC_MAESTRO"
    if pts > 18.0 and usg > 0.24:
        return "ISO_ASSASSIN"
    if pts > 16.0 and tpm < 1.5 and usg > 0.22:
        return "SLASHING_CREATOR"

    # Relaxed specialists
    if tpm > 2.0 and ast < 4.5:
        return "SNIPER_ELITE"
    if pts > 14.0 and pts < 22.0:
        return "ATHLETIC_FINISHER"

    # Relaxed bigs
    if reb > 6.5 and ast > 1.5:
        return "WARRIOR_BIG"
    if reb > 7.5:
        return "VULTURE_BIG"
    if reb > 4.0 and tpm > 1.2:
        return "STRETCH_BIG"
    if reb > 5.0 and usg < 0.20:
        return "ROLL_MAN"

    # Relaxed role players
    if ast > 3.0 and pts < 22.0:
        return "FACILITATOR"
    if stl > 0.8 and pts < 20.0:
        return "SCREEN_NAVIGATOR"
    if stocks > 1.2 and pts < 18.0:
        return "ISLAND_DEFENDER"
    if pts > 5.0 and pts < 16.0 and usg < 0.22:
        return "CUTTER_SPECIALIST"

    # === FINAL FALLBACK ===
    return "GENERALIST"


def calculate_usage(fga, fta, tov, minutes, team_minutes=48.0):
    """
    Estimate usage rate from available stats.
    Simplified formula: (FGA + 0.44*FTA + TOV) / Minutes / Team Pace Factor (2.1)
    """
    if minutes < 5:
        return 0.0
    
    possessions = fga + (0.44 * fta) + tov
    per_minute = possessions / minutes
    
    # Usage % = (Player Poss / Player Mins) / (Team Poss / Team Mins)
    # Team Poss / Team Mins is roughly 100 / 48 = ~2.08 (round to 2.1)
    usage = per_minute / 2.1
    
    return min(max(usage, 0.05), 0.50)  # Clamp to realistic range (5% to 50%)


def populate_archetypes():
    """Main function to classify and update all players."""
    print("=" * 50)
    print("LUDI INFORMATIO: ARCHETYPE POPULATION SCRIPT")
    print("=" * 50)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all unique players from player_game_logs
    c.execute('''
        SELECT DISTINCT player_id, player_name, team_abbreviation
        FROM player_game_logs
        WHERE game_date >= date('now', '-60 days')
        ORDER BY player_name
    ''')
    players = c.fetchall()
    print(f"\n📊 Found {len(players)} active players (games in last 60 days)")
    
    # Stats tracking
    archetype_counts = {}
    updated = 0
    skipped = 0
    
    for player in players:
        player_id = player['player_id']
        player_name = player['player_name']
        team = player['team_abbreviation']
        
        # Get last 20 games for this player
        c.execute('''
            SELECT 
                AVG(pts) as avg_pts,
                AVG(reb) as avg_reb,
                AVG(ast) as avg_ast,
                AVG(fg3m) as avg_3pm,
                AVG(stl) as avg_stl,
                AVG(blk) as avg_blk,
                AVG(fga) as avg_fga,
                AVG(fta) as avg_fta,
                AVG(tov) as avg_tov,
                AVG(minutes) as avg_min,
                COUNT(*) as games
            FROM player_game_logs
            WHERE player_id = ?
            ORDER BY game_date DESC
            LIMIT 20
        ''', (player_id,))
        
        stats = c.fetchone()
        
        if stats['games'] < 3:
            skipped += 1
            continue
        
        # Extract averages
        pts = stats['avg_pts'] or 0
        reb = stats['avg_reb'] or 0
        ast = stats['avg_ast'] or 0
        tpm = stats['avg_3pm'] or 0
        stl = stats['avg_stl'] or 0
        blk = stats['avg_blk'] or 0
        fga = stats['avg_fga'] or 0
        fta = stats['avg_fta'] or 0
        tov = stats['avg_tov'] or 0
        minutes = stats['avg_min'] or 0
        
        # Calculate usage
        usg = calculate_usage(fga, fta, tov, minutes)

        # Get synergy playtype data
        c.execute('''
            SELECT playtype, freq_pct
            FROM player_synergy_playtypes
            WHERE player_name = ? AND season = '2025-26'
        ''', (player_name,))
        synergy_rows = c.fetchall()
        synergy_data = {row[0]: row[1] for row in synergy_rows}

        # Get tracking data
        c.execute('''
            SELECT
                AVG(drives_fga) as avg_drives,
                AVG(catch_shoot_fga) as avg_cs_fga,
                AVG(pull_up_fga) as avg_pu_fga
            FROM player_game_tracking
            WHERE player_name = ? AND game_date >= date('now', '-60 days')
        ''', (player_name,))
        tracking_row = c.fetchone()
        tracking_data = {}
        if tracking_row:
            tracking_data = {
                'avg_drives': tracking_row[0] or 0,
                'avg_cs_fga': tracking_row[1] or 0,
                'avg_pu_fga': tracking_row[2] or 0
            }

        # Classify archetype with enriched data
        archetype = classify_archetype(pts, reb, ast, tpm, stl, blk, usg, synergy_data, tracking_data)
        
        # Update players table (upsert)
        # FIXED: Now updates base_ppg and usg_pct
        c.execute('''
            INSERT INTO players (player_id, name, team, archetype, base_ppg, usg_pct, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(player_id) DO UPDATE SET
                archetype = excluded.archetype,
                team = excluded.team,
                base_ppg = excluded.base_ppg,
                usg_pct = excluded.usg_pct,
                updated_at = CURRENT_TIMESTAMP
        ''', (player_id, player_name, team, archetype, pts, usg))
        
        # Track counts
        archetype_counts[archetype] = archetype_counts.get(archetype, 0) + 1
        updated += 1
    
    conn.commit()
    
    # Print summary
    print(f"\n✅ Updated {updated} players, skipped {skipped} (< 3 games)")
    print("\n📈 Archetype Distribution:")
    print("-" * 30)
    for arch, count in sorted(archetype_counts.items(), key=lambda x: -x[1]):
        pct = (count / updated * 100) if updated > 0 else 0
        print(f"   {arch:15} : {count:3} ({pct:.1f}%)")
    
    # Verify update
    c.execute('SELECT COUNT(*) FROM players WHERE archetype IS NOT NULL')
    total_classified = c.fetchone()[0]
    print(f"\n📊 Total players with archetypes: {total_classified}")
    
    conn.close()
    print("\n" + "=" * 50)
    print("✅ ARCHETYPE POPULATION COMPLETE!")
    print("=" * 50)


if __name__ == "__main__":
    populate_archetypes()
