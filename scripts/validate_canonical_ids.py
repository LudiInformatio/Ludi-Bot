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


def get_dirty_id_stats(cursor):
    """Get counts of clean vs dirty IDs in player_game_logs."""
    cursor.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN LENGTH(player_id) > 8 THEN 1 ELSE 0 END) as dirty,
            SUM(CASE WHEN LENGTH(player_id) <= 8 THEN 1 ELSE 0 END) as clean
        FROM player_game_logs
    ''')
    row = cursor.fetchone()
    return {
        'total': row[0] or 0,
        'dirty': row[1] or 0,
        'clean': row[2] or 0,
        'clean_pct': (row[2] / row[0] * 100) if row[0] else 0
    }


def get_unresolvable_ids(cursor):
    """Find dirty IDs not in player_canonical_ids table."""
    cursor.execute('''
        SELECT DISTINCT pgl.player_id, pgl.player_name, COUNT(*) as games
        FROM player_game_logs pgl
        WHERE LENGTH(pgl.player_id) > 8
        AND pgl.player_id NOT IN (SELECT canonical_id FROM player_canonical_ids)
        GROUP BY pgl.player_id, pgl.player_name
        ORDER BY games DESC
    ''')
    return cursor.fetchall()


def get_canonical_ids_stats(cursor):
    """Get stats about player_canonical_ids table."""
    cursor.execute('SELECT COUNT(*) FROM player_canonical_ids WHERE is_active = 1')
    active = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM player_canonical_ids')
    total = cursor.fetchone()[0]

    cursor.execute('''
        SELECT COUNT(*) FROM player_canonical_ids
        WHERE tank01_aliases IS NOT NULL AND tank01_aliases != '[]'
    ''')
    with_aliases = cursor.fetchone()[0]

    return {
        'total': total,
        'active': active,
        'with_aliases': with_aliases
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
    conn = sqlite3.connect(DB_PATH)
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

    # 3. Unresolvable IDs
    unresolvable = get_unresolvable_ids(cursor)
    print(f"\n⚠️  Unresolvable dirty IDs: {len(unresolvable)}")

    if verbose and unresolvable:
        print("   Details:")
        for pid, pname, games in unresolvable[:10]:
            print(f"      {pname:30s} | {games:3d} games | {pid}")
        if len(unresolvable) > 10:
            print(f"      ... and {len(unresolvable) - 10} more")

    # 4. Validation Results
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

    # Check 3: Unresolvable IDs
    if unresolvable:
        if fail_on_unresolvable:
            errors.append(f"{len(unresolvable)} IDs are not in player_canonical_ids")
        else:
            warnings.append(f"{len(unresolvable)} IDs are not in player_canonical_ids")

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
