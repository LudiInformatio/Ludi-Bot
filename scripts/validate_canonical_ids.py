#!/usr/bin/env python3
"""
Canonical ID Validation Script

Validates the canonical ID system health as part of CI/CD pipeline.
Checks for:
1. Dirty IDs in player_game_logs
2. Unresolvable IDs (not in player_canonical_ids)
3. Data quality metrics

Usage:
    python scripts/validate_canonical_ids.py
    python scripts/validate_canonical_ids.py --warn-threshold 50
    python scripts/validate_canonical_ids.py --fail-on-unresolvable

Created: February 3, 2026
Phase: 6.5d
"""

import sqlite3
import argparse
import sys
import json

DB_PATH = "ludi.db"


def is_id_dirty_sql(col_name):
    """SQL expression for dirty ID detection."""
    return f"(LENGTH({col_name}) > 7 OR {col_name} NOT GLOB '[12]*')"

def get_dirty_id_stats(cursor):
    """Get counts of clean vs dirty IDs in player_game_logs."""
    dirty_expr = is_id_dirty_sql('player_id')
    cursor.execute(f'''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN {dirty_expr} THEN 1 ELSE 0 END) as dirty,
            SUM(CASE WHEN NOT {dirty_expr} THEN 1 ELSE 0 END) as clean
        FROM player_game_logs
    ''')
    row = cursor.fetchone()
    total = row[0] or 0
    dirty = row[1] or 0
    clean = row[2] or 0
    return {
        'total': total,
        'dirty': dirty,
        'clean': clean,
        'clean_pct': (clean / total * 100) if total else 0
    }


def get_orphan_stats(cursor):
    """Find IDs in downstream tables not in player_canonical_ids."""
    tables = {
        'player_game_logs': 'player_id',
        'player_game_advanced': 'player_id',
        'player_game_tracking': 'nba_player_id',
        'player_game_opponent': 'player_id',
        'player_game_hustle': 'player_id',
        'player_clutch_stats': 'nba_player_id',
        'beneficiary_minutes': 'out_player_id',
        'player_season_averages_bdl': 'player_id'
    }
    
    orphans = {}
    for table, col in tables.items():
        try:
            cursor.execute(f'''
                SELECT COUNT(DISTINCT {col}) 
                FROM {table} 
                WHERE {col} NOT IN (SELECT canonical_id FROM player_canonical_ids)
            ''')
            orphans[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            continue # Table might not exist
            
    return orphans


def get_canonical_ids_stats(cursor):
    """Get stats about player_canonical_ids table."""
    cursor.execute('SELECT COUNT(*) FROM player_canonical_ids WHERE is_active = 1')
    active = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM player_canonical_ids')
    total = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(*) FROM player_canonical_ids
        WHERE (aliases IS NOT NULL AND aliases != '[]')
           OR (tank01_aliases IS NOT NULL AND tank01_aliases != '[]')
    ''')
    with_aliases = cursor.fetchone()[0]
    
    # ESPN ID completeness for active players
    cursor.execute('''
        SELECT COUNT(*) FROM player_canonical_ids
        WHERE is_active = 1 AND espn_id IS NOT NULL AND espn_id != ''
    ''')
    with_espn = cursor.fetchone()[0]

    return {
        'total': total,
        'active': active,
        'with_aliases': with_aliases,
        'with_espn': with_espn,
        'espn_pct': (with_espn / active * 100) if active else 0
    }


def validate(warn_threshold=50, fail_on_unresolvable=False, verbose=False):
    """
    Run canonical ID validation.

    Args:
        warn_threshold: Warn if dirty IDs exceed this count
        fail_on_unresolvable: Exit with error if any IDs are unresolvable
        verbose: Print detailed output

    Returns:
        0 if validation passes, 1 if fails
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA busy_timeout = 10000")
    cursor = conn.cursor()

    print("=" * 60)
    print("CANONICAL ID VALIDATION REPORT")
    print("=" * 60)

    # 1. Dirty ID Stats
    stats = get_dirty_id_stats(cursor)
    print(f"\n📊 player_game_logs:")
    print(f"   Total records:  {stats['total']:,}")
    print(f"   Clean IDs:      {stats['clean']:,} ({stats['clean_pct']:.2f}%)")
    print(f"   Dirty IDs:      {stats['dirty']:,}")

    # 2. Canonical IDs Table
    canonical_stats = get_canonical_ids_stats(cursor)
    print(f"\n📋 player_canonical_ids:")
    print(f"   Total players:  {canonical_stats['total']}")
    print(f"   Active:         {canonical_stats['active']}")
    print(f"   With aliases:   {canonical_stats['with_aliases']}")
    print(f"   With ESPN ID:   {canonical_stats['with_espn']} ({canonical_stats['espn_pct']:.2f}%)")

    # 3. Orphan Checks
    orphans = get_orphan_stats(cursor)
    print(f"\n⚠️  Orphaned IDs (not in canonical table):")
    total_orphans = 0
    for table, count in orphans.items():
        total_orphans += count
        if count > 0:
            print(f"   {table:<30}: {count}")
    
    if total_orphans == 0:
        print("   ✅ No orphans found across all tables.")

    # 4. Unresolvable Details (for player_game_logs specifically)
    cursor.execute(f'''
        SELECT DISTINCT player_id, player_name, COUNT(*) as games
        FROM player_game_logs
        WHERE player_id NOT IN (SELECT canonical_id FROM player_canonical_ids)
        GROUP BY player_id, player_name
        ORDER BY games DESC
    ''')
    unresolvable = cursor.fetchall()

    if verbose and unresolvable:
        print("   Details:")
        for pid, pname, games in unresolvable[:10]:
            print(f"      {pname:30s} | {games:3d} games | {pid}")
        if len(unresolvable) > 10:
            print(f"      ... and {len(unresolvable) - 10} more")

    # 5. Validation Results
    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    exit_code = 0
    warnings = []
    errors = []

    # Check 1: Clean ID ratio
    if stats['clean_pct'] < 99.0:
        warnings.append(f"Clean ID ratio below 99%: {stats['clean_pct']:.2f}%")

    # Check 2: Dirty ID threshold
    if stats['dirty'] > warn_threshold:
        warnings.append(f"Dirty IDs ({stats['dirty']}) exceed threshold ({warn_threshold})")

    # Check 3: Orphan IDs
    if total_orphans > 0:
        if fail_on_unresolvable:
            errors.append(f"{total_orphans} orphan IDs found across tables")
        else:
            warnings.append(f"{total_orphans} orphan IDs found across tables")

    # Check 4: ESPN completeness
    if canonical_stats['espn_pct'] < 90.0:
        warnings.append(f"ESPN ID completeness below 90%: {canonical_stats['espn_pct']:.2f}%")

    # Print results
    if errors:
        for e in errors:
            print(f"❌ ERROR: {e}")
        exit_code = 1
    elif warnings:
        for w in warnings:
            print(f"⚠️  WARNING: {w}")
    else:
        print("✅ All checks passed!")

    # Summary
    print(f"\n📈 Data Quality Score: {stats['clean_pct']:.2f}%")

    conn.close()
    return exit_code


def main():
    parser = argparse.ArgumentParser(description="Validate canonical ID system health")
    parser.add_argument(
        "--warn-threshold", type=int, default=50,
        help="Warn if dirty ID count exceeds this threshold (default: 50)"
    )
    parser.add_argument(
        "--fail-on-unresolvable", action="store_true",
        help="Exit with error code if any IDs are unresolvable"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print detailed output"
    )

    args = parser.parse_args()

    exit_code = validate(
        warn_threshold=args.warn_threshold,
        fail_on_unresolvable=args.fail_on_unresolvable,
        verbose=args.verbose
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
