#!/usr/bin/env python3
"""
Database Schema Validation Script (Phase 6.5b)

Pre-flight check for data_sync.yml workflow to catch schema mismatches
before they cause silent failures.

Usage:
    python scripts/validate_schema.py [--db ludi.db] [--verbose]

Exit Codes:
    0 = All validations passed
    1 = One or more validations failed

Author: Ludi Informatio
Date: February 3, 2026 (Phase 6.5b Step 3)
"""

import argparse
import sqlite3
import sys
from typing import List, Tuple, Dict


# Required unique indexes for ON CONFLICT operations
# Note: player_game_logs intentionally has NO unique constraint (uses deduplication instead)
# Note: player_game_tracking has UNIQUE(player_id, game_date) in table def
REQUIRED_UNIQUE_INDEXES = [
    ('referee_daily_stats', 'idx_referee_daily_unique', ['referee_id', 'sync_date']),
    ('player_season_wowy', None, ['player_id', 'season']),  # Table constraint, not named index
    ('player_shot_quality', None, ['player_id', 'season']),
    ('player_game_advanced', None, ['player_id', 'game_date']),
    ('player_wowy_stats', None, ['player_id', 'game_date']),
]

# Required tables
REQUIRED_TABLES = [
    'players',
    'games',
    'player_game_logs',
    'referee_profiles',
    'referee_daily_stats',
    'player_season_wowy',
    'player_canonical_ids',
    'depth_charts',
]


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get database connection with WAL mode."""
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def check_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    return cursor.fetchone() is not None


def check_unique_constraint(conn: sqlite3.Connection, table_name: str,
                           columns: List[str], index_name: str = None) -> bool:
    """
    Check if a table has a unique constraint on the specified columns.

    Checks both named indexes and table constraints (UNIQUE clauses).
    """
    cursor = conn.cursor()

    # Method 1: Check for named unique index
    if index_name:
        cursor.execute("""
            SELECT sql FROM sqlite_master
            WHERE type='index' AND name=? AND tbl_name=?
        """, (index_name, table_name))
        result = cursor.fetchone()
        if result and 'UNIQUE' in (result[0] or '').upper():
            return True

    # Method 2: Check pragma index_list for any unique index on these columns
    cursor.execute(f"PRAGMA index_list('{table_name}')")
    indexes = cursor.fetchall()

    for idx in indexes:
        if idx['unique']:
            # Get columns in this index
            cursor.execute(f"PRAGMA index_info('{idx['name']}')")
            idx_cols = [col['name'] for col in cursor.fetchall()]
            if set(idx_cols) == set(columns):
                return True

    # Method 3: Check table schema for inline UNIQUE constraint
    cursor.execute("""
        SELECT sql FROM sqlite_master
        WHERE type='table' AND name=?
    """, (table_name,))
    result = cursor.fetchone()
    if result:
        sql = result[0].upper()
        # Check for UNIQUE(col1, col2) pattern
        cols_pattern = ', '.join(columns).upper()
        if f'UNIQUE({cols_pattern})' in sql.replace(' ', ''):
            return True

    return False


def validate_schema(db_path: str, verbose: bool = False) -> Tuple[bool, List[str]]:
    """
    Run all schema validations.

    Args:
        db_path: Path to SQLite database
        verbose: Print detailed output

    Returns:
        Tuple of (all_passed: bool, errors: List[str])
    """
    errors = []
    warnings = []

    try:
        conn = get_db_connection(db_path)
    except sqlite3.Error as e:
        return False, [f"Cannot connect to database: {e}"]

    if verbose:
        print(f"Validating database: {db_path}")
        print("=" * 60)

    # Check required tables
    if verbose:
        print("\n📋 Checking required tables...")

    for table in REQUIRED_TABLES:
        exists = check_table_exists(conn, table)
        if not exists:
            errors.append(f"Missing required table: {table}")
            if verbose:
                print(f"   ❌ {table} - MISSING")
        elif verbose:
            print(f"   ✅ {table}")

    # Check unique constraints
    if verbose:
        print("\n🔑 Checking unique constraints...")

    for table, index_name, columns in REQUIRED_UNIQUE_INDEXES:
        if not check_table_exists(conn, table):
            continue  # Already flagged as missing table

        has_constraint = check_unique_constraint(conn, table, columns, index_name)
        cols_str = ', '.join(columns)

        if not has_constraint:
            errors.append(f"Missing UNIQUE constraint on {table}({cols_str})")
            if verbose:
                print(f"   ❌ {table}({cols_str}) - NO UNIQUE CONSTRAINT")
        elif verbose:
            print(f"   ✅ {table}({cols_str})")

    # Check player_canonical_ids has data (needed for ID resolution)
    if verbose:
        print("\n📊 Checking reference data...")

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM player_canonical_ids")
    canonical_count = cursor.fetchone()[0]

    if canonical_count < 100:
        warnings.append(f"player_canonical_ids has only {canonical_count} records (expected 400+)")
        if verbose:
            print(f"   ⚠️  player_canonical_ids: {canonical_count} records (low)")
    elif verbose:
        print(f"   ✅ player_canonical_ids: {canonical_count} records")

    # Check referee_profiles has data
    cursor.execute("SELECT COUNT(*) FROM referee_profiles")
    ref_count = cursor.fetchone()[0]

    if ref_count < 50:
        warnings.append(f"referee_profiles has only {ref_count} records (expected 70+)")
        if verbose:
            print(f"   ⚠️  referee_profiles: {ref_count} records (low)")
    elif verbose:
        print(f"   ✅ referee_profiles: {ref_count} records")

    conn.close()

    # Summary
    if verbose:
        print("\n" + "=" * 60)
        if errors:
            print(f"❌ VALIDATION FAILED: {len(errors)} error(s)")
            for err in errors:
                print(f"   - {err}")
        else:
            print("✅ VALIDATION PASSED")

        if warnings:
            print(f"\n⚠️  {len(warnings)} warning(s):")
            for warn in warnings:
                print(f"   - {warn}")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate database schema for data sync workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Quick validation (exit code only)
    python scripts/validate_schema.py

    # Verbose output
    python scripts/validate_schema.py --verbose

    # Check specific database
    python scripts/validate_schema.py --db archives/data/ludi.db.backup
        """
    )

    parser.add_argument('--db', type=str, default='ludi.db',
                       help='Database path (default: ludi.db)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Print detailed validation results')

    args = parser.parse_args()

    passed, errors = validate_schema(args.db, args.verbose)

    if not passed:
        if not args.verbose:
            print(f"Schema validation FAILED: {len(errors)} error(s)")
            for err in errors:
                print(f"  - {err}")
        sys.exit(1)

    if not args.verbose:
        print("Schema validation passed")

    sys.exit(0)


if __name__ == "__main__":
    main()
