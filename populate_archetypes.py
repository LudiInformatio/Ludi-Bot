#!/usr/bin/env python3
"""
Ludi Informatio: Archetype Population Script
Week 2 Day 6 Enhancement - Bulk classify all players in database

Uses Module E's 8-archetype system to populate players.archetype column
based on their last 20 games of data.
"""

import sqlite3
from datetime import datetime, timedelta

# Database path
DB_PATH = "ludi.db"

# Archetype thresholds (from Module E v2.0)
def classify_archetype(pts, reb, ast, tpm, stl, blk, usg):
    """
    10-Archetype Classification System (Matched to Module E v7.0)
    Evaluates in priority order.
    """
    stocks = stl + blk
    
    # === TIER 1: ENGINES (The System) ===
    
    # 1. HELIOCENTRIC: Usage > 30% OR (Usage > 28% and High Assists)
    # Examples: Luka, Trae
    if (usg > 0.30 and ast > 6.0) or (usg > 0.28 and ast > 8.0):
        return "HELIOCENTRIC"

    # 2. SLASHER: High PTS, High Usage, Low 3PM
    # Examples: Zion, Giannis, Ja
    if pts > 22.0 and usg > 0.30 and tpm < 2.0:
        return "SLASHER"

    # 3. ELITE_SCORER: High PTS, High 3PM (3-Level Scorers)
    # Examples: Tatum, Durant, Booker
    if pts > 24.5 and tpm > 2.4:
        return "ELITE_SCORER"

    # === TIER 2: REBOUNDING CREATORS ===

    # 4. HUB_BIG: Elite Reb, Elite Pass, Big Traits
    # Examples: Jokic, Sabonis, Sengun
    if reb > 7.5 and ast > 4.2 and (reb > ast or blk > 0.6):
        return "HUB_BIG"

    # 5. JUMBO_CREATOR: High Reb, High Pass, Guard/Wing Traits
    # Examples: LeBron, Giddey, Barnes
    if reb > 6.0 and ast > 5.0 and (ast >= reb or blk <= 0.5):
        return "JUMBO_CREATOR"

    # === TIER 3: SPECIALISTS ===
    
    # 6. STRETCH_BIG: Rebounding + floor spacing
    # Examples: KAT, Porzingis, Turner
    if reb > 6.5 and tpm > 1.8:
        return "STRETCH_BIG"
    
    # 7. RIM_RUNNER: Elite rebounding + no perimeter game
    # Examples: Gobert, Allen, Capela
    if reb > 8.0 and tpm < 0.6:
        return "RIM_RUNNER"
    
    # 8. SNIPER: High 3PM volume
    # Examples: Curry, Klay, Hield
    if tpm > 2.8 and ast < 4.0:
        return "SNIPER"
    
    # === TIER 4: ROLE PLAYERS ===
    
    # 9. TWO_WAY_WING: Defense + 3s
    # Examples: OG Anunoby, Bridges, Herb Jones
    if stocks >= 1.8 and tpm >= 1.5 and pts < 22.0:
        return "TWO_WAY_WING"
    
    # 10. FACILITATOR: High Ast, Low Usg
    # Examples: Tyus Jones, CP3 (current), Conley
    if ast >= 5.0 and pts < 16.0 and usg < 0.28:
        return "FACILITATOR"
    
    # === TIER 5: DEFAULT ===
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
        
        # Classify archetype
        archetype = classify_archetype(pts, reb, ast, tpm, stl, blk, usg)
        
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
