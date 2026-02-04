#!/usr/bin/env python3
"""
Phase 6.5d: Comprehensive Canonical ID Fix

This script:
1. Adds missing players to player_canonical_ids table
2. Maps Tank01 aliases to existing canonical IDs
3. Migrates dirty IDs in player_game_logs to canonical format

Created: February 3, 2026
"""

import sqlite3
import json
from datetime import datetime

DB_PATH = "ludi.db"

# Players that need aliases added (dirty ID → canonical ID)
# Format: (dirty_tank01_id, canonical_id, player_name_for_verification)
ALIAS_MAPPINGS = [
    # EJ Harkless is actually Elijah Harkless
    ("94464499047", "1641989", "Elijah Harkless"),
]

# Players to add to player_canonical_ids
# These players exist in players table but not in player_canonical_ids
# Format: (canonical_id, full_name, normalized_name, team, position, tank01_aliases)
NEW_PLAYERS = [
    # Using their Tank01 ID as canonical since no NBA ID exists
    # These are G-League/two-way players
    ("94544426027", "Isaiah Stevens", "isaiah stevens", "SAC", "G", []),
    ("948247065539", "Kobe Bufkin", "kobe bufkin", "LAL", "G", []),
    ("94454205527", "L.J. Cryer", "lj cryer", "GS", "G", []),
    ("28838569499", "Moe Wagner", "moe wagner", "ORL", "C", []),
    ("28808359499", "Skal Labissiere", "skal labissiere", "WAS", "C", []),
    ("28908536399", "Ty Jerome", "ty jerome", "MEM", "G", []),
    ("947042835539", "TyTy Washington Jr.", "tyty washington jr", "LAC", "G", []),
    ("945542613189", "Yuki Kawamura", "yuki kawamura", "CHI", "G", []),
    ("941742772339", "David Jones", "david jones", "SA", "F", []),
    ("287488965539", "Malevy Leons", "malevy leons", "GS", "G", []),
    ("28228879027", "Oscar Tshiebwe", "oscar tshiebwe", "UTA", "C", []),
    ("28608827869", "Stanley Umude", "stanley umude", "SA", "G", []),
    ("94714229027", "Tristan Enaruna", "tristan enaruna", "CLE", "G", []),
]


def add_alias_to_player(cursor, canonical_id, new_alias):
    """Add Tank01 alias to existing player's alias list."""
    cursor.execute("""
        SELECT tank01_aliases FROM player_canonical_ids WHERE canonical_id = ?
    """, (canonical_id,))

    result = cursor.fetchone()
    if not result:
        return False

    current_aliases = json.loads(result[0]) if result[0] else []

    if new_alias not in current_aliases:
        current_aliases.append(new_alias)
        cursor.execute("""
            UPDATE player_canonical_ids
            SET tank01_aliases = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE canonical_id = ?
        """, (json.dumps(current_aliases), canonical_id))
        return True
    return False


def add_new_player(cursor, player_data):
    """Add new player to player_canonical_ids table."""
    canonical_id, full_name, normalized_name, team, position, aliases = player_data

    # Check if already exists
    cursor.execute("SELECT canonical_id FROM player_canonical_ids WHERE canonical_id = ?", (canonical_id,))
    if cursor.fetchone():
        return False

    cursor.execute("""
        INSERT INTO player_canonical_ids
        (canonical_id, full_name, normalized_name, team, position, is_active, tank01_aliases, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
    """, (
        canonical_id,
        full_name,
        normalized_name,
        team,
        position,
        json.dumps(aliases),
        datetime.now().isoformat(),
        datetime.now().isoformat()
    ))
    return True


def migrate_dirty_ids(cursor):
    """
    Migrate dirty IDs in player_game_logs to canonical IDs.
    For EJ Harkless → Elijah Harkless (1641989)
    """
    # Migrate EJ Harkless records to canonical Elijah Harkless ID
    cursor.execute("""
        UPDATE player_game_logs
        SET player_id = ?, player_name = ?
        WHERE player_id = ?
    """, ("1641989", "Elijah Harkless", "94464499047"))

    return cursor.rowcount


def get_dirty_id_count(cursor):
    """Get current count of dirty IDs."""
    cursor.execute("""
        SELECT COUNT(*) FROM player_game_logs WHERE LENGTH(player_id) > 8
    """)
    return cursor.fetchone()[0]


def main():
    print("=" * 70)
    print("PHASE 6.5d: COMPREHENSIVE CANONICAL ID FIX")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Initial state
    initial_dirty = get_dirty_id_count(cursor)
    print(f"\n📊 Initial dirty IDs: {initial_dirty}")

    # Step 1: Add aliases to existing players
    print("\n📝 STEP 1: Adding aliases to existing players...")
    aliases_added = 0
    for dirty_id, canonical_id, name in ALIAS_MAPPINGS:
        if add_alias_to_player(cursor, canonical_id, dirty_id):
            print(f"   ✅ {name}: added alias {dirty_id} → {canonical_id}")
            aliases_added += 1
        else:
            print(f"   ⚠️  {name}: canonical ID {canonical_id} not found or alias exists")

    # Step 2: Add new players
    print("\n📝 STEP 2: Adding new players to canonical_ids...")
    players_added = 0
    for player_data in NEW_PLAYERS:
        if add_new_player(cursor, player_data):
            print(f"   ✅ {player_data[1]}: added as {player_data[0]}")
            players_added += 1
        else:
            print(f"   ⚠️  {player_data[1]}: already exists")

    # Step 3: Migrate EJ Harkless to Elijah Harkless
    print("\n📝 STEP 3: Migrating name mismatches...")
    migrated = migrate_dirty_ids(cursor)
    print(f"   ✅ Migrated {migrated} EJ Harkless records to Elijah Harkless")

    # Commit changes
    conn.commit()

    # Final state
    final_dirty = get_dirty_id_count(cursor)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Aliases added:     {aliases_added}")
    print(f"Players added:     {players_added}")
    print(f"Records migrated:  {migrated}")
    print(f"Dirty IDs before:  {initial_dirty}")
    print(f"Dirty IDs after:   {final_dirty}")
    print(f"Improvement:       {initial_dirty - final_dirty} fewer dirty IDs")
    print()

    # Note: The remaining dirty IDs are now in canonical_ids table
    # but still have long IDs (because Tank01 doesn't provide NBA IDs)
    print("ℹ️  Note: Remaining dirty IDs are G-League/two-way players")
    print("   Their Tank01 IDs are now registered as canonical IDs")
    print("   This ensures consistent lookups going forward")

    conn.close()


if __name__ == "__main__":
    main()
