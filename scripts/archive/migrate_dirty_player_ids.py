"""
Migrate dirty Tank01 composite IDs to canonical NBA IDs in player_game_logs.

Phase 6.5b Step 5.5: Canonical ID Resolution Migration

This script:
1. Identifies all composite IDs (length > 8) in player_game_logs
2. Resolves them using player_canonical_ids table via PlayerIDResolver
3. Updates records with canonical IDs
4. Reports success/failure stats

Created: February 3, 2026
Author: Claude (Ludi Informatio)
"""

import sqlite3
import sys
import os
from typing import List, Tuple

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.player_id_resolver import PlayerIDResolver

DB_PATH = "ludi.db"


def get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with WAL mode."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def find_dirty_ids() -> List[Tuple[str, str, int]]:
    """
    Find all dirty (composite) player IDs.

    Returns:
        List of (player_id, player_name, record_count) tuples for IDs needing resolution
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Find IDs with length > 8 (canonical IDs are typically 7 digits)
    cursor.execute("""
        SELECT player_id, player_name, COUNT(*) as record_count
        FROM player_game_logs
        WHERE LENGTH(player_id) > 8
        GROUP BY player_id, player_name
        ORDER BY record_count DESC, player_name
    """)

    results = cursor.fetchall()
    conn.close()

    return [(row['player_id'], row['player_name'], row['record_count']) for row in results]


def resolve_id(dirty_id: str, player_name: str, resolver: PlayerIDResolver) -> str:
    """
    Resolve dirty ID to canonical ID using PlayerIDResolver.

    Args:
        dirty_id: Tank01 composite ID
        player_name: Player full name
        resolver: PlayerIDResolver instance

    Returns:
        Canonical ID if found, original ID if not
    """
    try:
        # Try ID-based resolution first
        return resolver.resolve_to_canonical_id(dirty_id)
    except ValueError:
        # Try name-based resolution
        try:
            return resolver.resolve_to_canonical_id(player_name)
        except ValueError:
            # No match found
            return dirty_id


def migrate_player_id(old_id: str, new_id: str) -> int:
    """
    Update all records for a player with canonical ID.

    Handles duplicate records (same game_id + player, different IDs):
    1. Identify games where both composite and canonical IDs exist
    2. Delete composite ID records (keep canonical as source of truth)
    3. Update remaining composite ID records to canonical

    Args:
        old_id: Dirty Tank01 composite ID
        new_id: Clean canonical NBA ID

    Returns:
        Number of records updated
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # First, delete duplicate records where canonical ID already exists
    # (This prevents UNIQUE constraint violation on UPDATE)
    cursor.execute("""
        DELETE FROM player_game_logs
        WHERE player_id = ?
          AND game_id IN (
              SELECT game_id
              FROM player_game_logs
              WHERE player_id = ?
          )
    """, (old_id, new_id))

    duplicates_deleted = cursor.rowcount

    # Now update remaining composite ID records to canonical
    cursor.execute("""
        UPDATE player_game_logs
        SET player_id = ?
        WHERE player_id = ?
    """, (new_id, old_id))

    rows_updated = cursor.rowcount
    conn.commit()
    conn.close()

    return rows_updated + duplicates_deleted


def verify_results():
    """Check migration results."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Count remaining dirty IDs
    cursor.execute("""
        SELECT COUNT(DISTINCT player_id) as dirty_count
        FROM player_game_logs
        WHERE LENGTH(player_id) > 8
    """)
    dirty_count = cursor.fetchone()['dirty_count']

    # Count clean IDs
    cursor.execute("""
        SELECT COUNT(DISTINCT player_id) as clean_count
        FROM player_game_logs
        WHERE LENGTH(player_id) <= 8
    """)
    clean_count = cursor.fetchone()['clean_count']

    # Total unique players
    cursor.execute("""
        SELECT COUNT(DISTINCT player_id) as total
        FROM player_game_logs
    """)
    total_count = cursor.fetchone()['total']

    conn.close()

    return dirty_count, clean_count, total_count


def main():
    """Run migration process."""
    print("=" * 70)
    print("CANONICAL ID MIGRATION - player_game_logs")
    print("Phase 6.5b Step 5.5: Clean Tank01 Composite IDs")
    print("=" * 70)

    # Initialize resolver
    print("\n🔧 Initializing PlayerIDResolver...")
    resolver = PlayerIDResolver(db_path=DB_PATH)
    print("   ✅ Resolver loaded")

    # Find all dirty IDs
    print("\n📊 Scanning for dirty IDs...")
    dirty_ids = find_dirty_ids()
    print(f"   Found {len(dirty_ids)} unique dirty IDs to resolve")

    if not dirty_ids:
        print("✅ No dirty IDs found - database is clean!")
        return

    # Show top 5 by record count
    print("\n   Top 5 players by record count:")
    for player_id, player_name, count in dirty_ids[:5]:
        print(f"      {player_name:30s} {count:3d} records ({player_id})")

    # Confirm before proceeding
    print(f"\n⚠️  About to update {sum(r[2] for r in dirty_ids):,} total records")
    response = input("   Continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("   ❌ Migration cancelled by user")
        return

    # Resolve and migrate
    print("\n🔄 Resolving and migrating IDs...\n")

    success_count = 0
    failed_count = 0
    total_records_updated = 0

    for dirty_id, player_name, record_count in dirty_ids:
        canonical_id = resolve_id(dirty_id, player_name, resolver)

        if canonical_id != dirty_id and len(canonical_id) <= 8:
            # Resolution successful
            records_updated = migrate_player_id(dirty_id, canonical_id)
            total_records_updated += records_updated
            success_count += 1
            print(f"   ✅ {player_name:30s} {dirty_id} → {canonical_id:8s} ({records_updated:3d} records)")
        else:
            # No canonical ID found
            failed_count += 1
            print(f"   ⚠️  {player_name:30s} {dirty_id} → NO MATCH ({record_count:3d} records)")

    # Verify results
    print("\n🔍 Verifying migration results...")
    dirty_remaining, clean_ids, total_ids = verify_results()

    # Summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"Successfully resolved:  {success_count}/{len(dirty_ids)} players")
    print(f"Failed to resolve:      {failed_count}/{len(dirty_ids)} players")
    print(f"Total records updated:  {total_records_updated:,}")
    print()
    print(f"Post-migration stats:")
    print(f"  Dirty IDs remaining:  {dirty_remaining} ({dirty_remaining/total_ids*100:.1f}%)")
    print(f"  Clean IDs:            {clean_ids} ({clean_ids/total_ids*100:.1f}%)")
    print(f"  Total unique players: {total_ids}")
    print()

    if failed_count > 0:
        print("⚠️  Some IDs could not be resolved.")
        print("   These players may need manual addition to player_canonical_ids table.")
    else:
        print("✅ All dirty IDs successfully resolved!")

    # Success criteria check
    if dirty_remaining < 10:
        print(f"\n🎉 SUCCESS: Dirty IDs reduced to {dirty_remaining} (< 10 target met)")
    else:
        print(f"\n⚠️  WARNING: {dirty_remaining} dirty IDs remain (target was < 10)")


if __name__ == "__main__":
    main()
