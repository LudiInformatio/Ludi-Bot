#!/usr/bin/env python3
"""
Ludi-Bot Player Duplicate Cleanup Script
=========================================
Removes Tank01 composite ID duplicates from the players table.

Problem: Tank01 API sends composite IDs (>10 chars like "28138379499")
that create duplicate records for players who also have valid NBA IDs.

Solution: Keep valid NBA IDs (<=10 chars), remove Tank01 composites
where a valid NBA ID exists for the same player name.

Usage:
    python scripts/cleanup_player_duplicates.py          # Dry run (default)
    python scripts/cleanup_player_duplicates.py --execute  # Actually delete

Created: Feb 2, 2026
"""

import sqlite3
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "ludi.db"


def analyze_duplicates(conn):
    """Analyze the current state of duplicates in the players table."""
    c = conn.cursor()

    print("\n" + "=" * 60)
    print("PLAYER TABLE ANALYSIS")
    print("=" * 60)

    # Total counts
    c.execute('SELECT COUNT(*) FROM players WHERE is_active=1')
    total_active = c.fetchone()[0]
    print(f"\nTotal active players: {total_active}")

    c.execute('SELECT COUNT(*) FROM players')
    total_all = c.fetchone()[0]
    print(f"Total players (all): {total_all}")

    # ID type distribution
    c.execute('''
        SELECT
            CASE
                WHEN LENGTH(player_id) > 10 THEN 'Tank01 Composite (>10 chars)'
                ELSE 'Valid NBA ID (<=10 chars)'
            END as id_type,
            COUNT(*) as cnt
        FROM players
        WHERE is_active=1
        GROUP BY id_type
    ''')
    print("\nID Type Distribution (active players):")
    for id_type, cnt in c.fetchall():
        pct = (cnt / total_active) * 100 if total_active > 0 else 0
        print(f"  {id_type}: {cnt} ({pct:.1f}%)")

    # Find duplicates
    c.execute('''
        SELECT name, COUNT(*) as cnt, GROUP_CONCAT(player_id, ' | ') as ids
        FROM players
        WHERE is_active=1
        GROUP BY name
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
    ''')
    duplicates = c.fetchall()

    print(f"\nDuplicate player names: {len(duplicates)} players with multiple records")

    if duplicates:
        print("\nTop 10 duplicates:")
        for name, cnt, ids in duplicates[:10]:
            print(f"  {name}: {cnt} records")
            print(f"    IDs: {ids}")

    return duplicates


def find_records_to_delete(conn):
    """
    Find Tank01 composite ID records that should be deleted.

    Logic:
    - If a player has BOTH a valid NBA ID (<=10 chars) AND a Tank01 composite (>10 chars),
      keep the valid NBA ID and mark the composite for deletion.
    - If a player ONLY has Tank01 composite IDs, keep them (no valid ID to prefer).
    """
    c = conn.cursor()

    # Find players with both ID types
    c.execute('''
        WITH player_id_types AS (
            SELECT
                name,
                player_id,
                CASE WHEN LENGTH(player_id) > 10 THEN 'composite' ELSE 'valid' END as id_type,
                is_active
            FROM players
        ),
        players_with_both AS (
            SELECT DISTINCT name
            FROM player_id_types
            WHERE is_active = 1
            GROUP BY name
            HAVING
                SUM(CASE WHEN id_type = 'valid' THEN 1 ELSE 0 END) > 0
                AND SUM(CASE WHEN id_type = 'composite' THEN 1 ELSE 0 END) > 0
        )
        SELECT p.player_id, p.name, p.team, p.archetype
        FROM players p
        JOIN players_with_both pwb ON p.name = pwb.name
        WHERE LENGTH(p.player_id) > 10
        AND p.is_active = 1
        ORDER BY p.name
    ''')

    to_delete = c.fetchall()
    return to_delete


def find_composite_only_players(conn):
    """Find players who ONLY have composite IDs (no valid NBA ID)."""
    c = conn.cursor()

    c.execute('''
        SELECT name, player_id, team
        FROM players
        WHERE is_active = 1
        AND LENGTH(player_id) > 10
        AND name NOT IN (
            SELECT name FROM players
            WHERE is_active = 1 AND LENGTH(player_id) <= 10
        )
        ORDER BY name
    ''')

    return c.fetchall()


def execute_cleanup(conn, dry_run=True):
    """Execute the cleanup, optionally in dry-run mode."""
    c = conn.cursor()

    to_delete = find_records_to_delete(conn)

    print("\n" + "=" * 60)
    print("CLEANUP PLAN")
    print("=" * 60)

    print(f"\nRecords to DELETE (Tank01 composites with valid NBA ID alternatives):")
    print(f"  Total: {len(to_delete)} records")

    if to_delete:
        print("\nSample records to delete:")
        for player_id, name, team, archetype in to_delete[:15]:
            print(f"  - {name} ({team}): ID={player_id}, archetype={archetype}")
        if len(to_delete) > 15:
            print(f"  ... and {len(to_delete) - 15} more")

    # Show composite-only players (will be kept)
    composite_only = find_composite_only_players(conn)
    print(f"\nRecords to KEEP (composite-only, no valid NBA ID alternative):")
    print(f"  Total: {len(composite_only)} players")

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - No changes made")
        print("Run with --execute to actually delete records")
        print("=" * 60)
        return 0

    # Execute deletion
    print("\n" + "=" * 60)
    print("EXECUTING CLEANUP...")
    print("=" * 60)

    deleted_count = 0
    for player_id, name, team, archetype in to_delete:
        c.execute('DELETE FROM players WHERE player_id = ?', (player_id,))
        deleted_count += 1
        if deleted_count <= 10:
            print(f"  Deleted: {name} (ID={player_id})")

    conn.commit()

    print(f"\nDeleted {deleted_count} duplicate records")

    return deleted_count


def verify_cleanup(conn):
    """Verify the cleanup was successful."""
    c = conn.cursor()

    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    # Check for remaining duplicates
    c.execute('''
        SELECT name, COUNT(*) as cnt
        FROM players
        WHERE is_active=1
        GROUP BY name
        HAVING COUNT(*) > 1
    ''')
    remaining_dups = c.fetchall()

    print(f"\nRemaining duplicate names: {len(remaining_dups)}")
    if remaining_dups:
        print("WARNING: Some duplicates remain:")
        for name, cnt in remaining_dups[:5]:
            print(f"  {name}: {cnt} records")

    # Final counts
    c.execute('SELECT COUNT(*) FROM players WHERE is_active=1')
    final_active = c.fetchone()[0]

    c.execute('''
        SELECT
            CASE WHEN LENGTH(player_id) > 10 THEN 'composite' ELSE 'valid' END as id_type,
            COUNT(*) as cnt
        FROM players
        WHERE is_active=1
        GROUP BY id_type
    ''')
    id_dist = dict(c.fetchall())

    print(f"\nFinal active player count: {final_active}")
    print(f"  Valid NBA IDs: {id_dist.get('valid', 0)}")
    print(f"  Composite IDs (kept): {id_dist.get('composite', 0)}")

    # Check archetype distribution
    c.execute('''
        SELECT archetype, COUNT(*) as cnt
        FROM players
        WHERE is_active=1
        GROUP BY archetype
        ORDER BY cnt DESC
    ''')
    print("\nArchetype distribution:")
    for archetype, cnt in c.fetchall():
        print(f"  {archetype or 'NULL'}: {cnt}")

    return len(remaining_dups) == 0


def main():
    """Main entry point."""
    dry_run = '--execute' not in sys.argv

    print("\n" + "=" * 60)
    print("LUDI-BOT PLAYER DUPLICATE CLEANUP")
    print("=" * 60)
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print(f"Database: {os.path.abspath(DB_PATH)}")

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)

    try:
        # Analyze current state
        analyze_duplicates(conn)

        # Execute cleanup
        deleted = execute_cleanup(conn, dry_run=dry_run)

        # Verify if we made changes
        if not dry_run and deleted > 0:
            verify_cleanup(conn)

    finally:
        conn.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
