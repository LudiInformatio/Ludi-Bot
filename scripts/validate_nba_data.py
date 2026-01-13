#!/usr/bin/env python3
"""
LUDI INFORMATIO | NBA Data Validation Script
=============================================
Validates CSV data quality before loading into database.

Phase 1.3 of nba_api historical backtest plan.

Usage:
    ./venv/bin/python scripts/validate_nba_data.py
"""

import os
import sys
import pandas as pd
from typing import Dict, List, Tuple, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# CONFIGURATION
# =============================================================================

DATA_DIR = "data/raw_nba_data"

# Expected columns for each CSV (minimum required columns)
EXPECTED_COLUMNS = {
    'shot_quality_history.csv': [
        'player_id', 'player_name', 'team', 'fetch_date',
        'total_fgm', 'total_fga', 'total_fg_pct',
        'restricted_area_fga', 'restricted_area_fg_pct',
        'paint_non_ra_fga', 'paint_non_ra_fg_pct',
        'midrange_fga', 'midrange_fg_pct',
        'corner_3_fga', 'corner_3_fg_pct',
        'above_break_3_fga', 'above_break_3_fg_pct',
        'very_tight_fga', 'very_tight_fg_pct',
        'tight_fga', 'tight_fg_pct',
        'open_fga', 'open_fg_pct',
        'wide_open_fga', 'wide_open_fg_pct',
        'contested_shot_pct'
    ],
    'workload_history.csv': [
        'player_id', 'player_name', 'team', 'fetch_date',
        'games_played', 'total_reb', 'oreb', 'dreb',
        'contested_reb', 'uncontested_reb', 'contested_reb_pct',
        'total_passes', 'total_assists'
    ],
    'matchup_history.csv': [
        'player_id', 'player_name', 'team', 'fetch_date',
        'games_sampled', 'defender_id', 'defender_name',
        'matchup_minutes', 'fga_vs_defender', 'fgm_vs_defender',
        'fg_pct_vs_defender', 'games_vs_defender'
    ]
}

# Minimum row counts for each CSV
MIN_ROWS = {
    'shot_quality_history.csv': 1,
    'workload_history.csv': 1,
    'matchup_history.csv': 1
}

# Critical columns that should not have NULL values
CRITICAL_COLUMNS = {
    'shot_quality_history.csv': ['player_id', 'player_name'],
    'workload_history.csv': ['player_id', 'player_name'],
    'matchup_history.csv': ['player_id', 'player_name', 'defender_id', 'defender_name']
}


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_csv(filepath: str, expected_cols: List[str], min_rows: int,
                 critical_cols: List[str]) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate a single CSV file.

    Returns:
        Tuple of (passed: bool, report: dict)
    """
    report = {
        'filepath': filepath,
        'exists': False,
        'row_count': 0,
        'columns': [],
        'missing_columns': [],
        'extra_columns': [],
        'null_counts': {},
        'critical_nulls': {},
        'sample_rows': None,
        'issues': [],
        'passed': False
    }

    # Check file exists
    if not os.path.exists(filepath):
        report['issues'].append(f"File not found: {filepath}")
        return False, report

    report['exists'] = True

    # Load CSV
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        report['issues'].append(f"Failed to read CSV: {str(e)}")
        return False, report

    # Row count
    report['row_count'] = len(df)
    report['columns'] = list(df.columns)

    # Check minimum rows
    if len(df) < min_rows:
        report['issues'].append(f"Too few rows: {len(df)} < {min_rows} minimum")

    # Check expected columns
    missing = [col for col in expected_cols if col not in df.columns]
    extra = [col for col in df.columns if col not in expected_cols]

    report['missing_columns'] = missing
    report['extra_columns'] = extra

    if missing:
        report['issues'].append(f"Missing columns: {missing}")

    # Check NULL values
    null_counts = df.isnull().sum().to_dict()
    report['null_counts'] = {k: v for k, v in null_counts.items() if v > 0}

    # Check critical columns for NULLs
    for col in critical_cols:
        if col in df.columns:
            nulls = df[col].isnull().sum()
            if nulls > 0:
                report['critical_nulls'][col] = nulls
                report['issues'].append(f"Critical column '{col}' has {nulls} NULL values")

    # Sample rows
    sample_count = min(5, len(df))
    if sample_count > 0:
        report['sample_rows'] = df.head(sample_count).to_dict('records')

    # Determine pass/fail
    # Fail conditions: file missing, can't read, missing critical columns, too few rows
    critical_missing = [col for col in critical_cols if col in missing]

    passed = (
        report['exists'] and
        len(df) >= min_rows and
        len(critical_missing) == 0 and
        len(report['critical_nulls']) == 0
    )

    report['passed'] = passed
    return passed, report


def print_report(report: Dict[str, Any], csv_name: str):
    """Print a formatted validation report."""
    print(f"\n{'='*60}")
    print(f"   {csv_name}")
    print(f"{'='*60}")

    if not report['exists']:
        print(f"   STATUS: FAIL - File not found")
        return

    # Basic info
    print(f"   Rows: {report['row_count']}")
    print(f"   Columns ({len(report['columns'])}): {', '.join(report['columns'][:8])}...")

    # Missing/Extra columns
    if report['missing_columns']:
        print(f"\n   MISSING COLUMNS: {report['missing_columns']}")
    if report['extra_columns']:
        print(f"   Extra columns: {report['extra_columns']}")

    # NULL values
    if report['null_counts']:
        print(f"\n   NULL value counts:")
        for col, count in list(report['null_counts'].items())[:10]:
            pct = count / report['row_count'] * 100 if report['row_count'] > 0 else 0
            print(f"      {col}: {count} ({pct:.1f}%)")
    else:
        print(f"\n   NULL values: None detected")

    # Critical NULLs
    if report['critical_nulls']:
        print(f"\n   CRITICAL NULL VALUES:")
        for col, count in report['critical_nulls'].items():
            print(f"      {col}: {count}")

    # Sample rows
    if report['sample_rows']:
        print(f"\n   Sample rows (first 3):")
        for i, row in enumerate(report['sample_rows'][:3], 1):
            # Show key fields only
            player = row.get('player_name', 'N/A')
            team = row.get('team', 'N/A')
            print(f"      {i}. {player} ({team})")

    # Issues
    if report['issues']:
        print(f"\n   ISSUES FOUND:")
        for issue in report['issues']:
            print(f"      - {issue}")

    # Final status
    status = "PASS" if report['passed'] else "FAIL"
    print(f"\n   STATUS: {status}")


def validate_all_csvs() -> Dict[str, bool]:
    """
    Validate all CSV files and print reports.

    Returns:
        Dict mapping CSV name to pass/fail status
    """
    print("\n" + "="*60)
    print("   LUDI NBA DATA VALIDATION")
    print("   Phase 1.3: Data Quality Check")
    print("="*60)

    results = {}

    for csv_name in EXPECTED_COLUMNS.keys():
        filepath = os.path.join(DATA_DIR, csv_name)
        expected_cols = EXPECTED_COLUMNS[csv_name]
        min_rows = MIN_ROWS[csv_name]
        critical_cols = CRITICAL_COLUMNS[csv_name]

        passed, report = validate_csv(filepath, expected_cols, min_rows, critical_cols)
        results[csv_name] = passed

        print_report(report, csv_name)

    # Summary
    print("\n" + "="*60)
    print("   VALIDATION SUMMARY")
    print("="*60)

    all_passed = True
    for csv_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        symbol = "+" if passed else "X"
        print(f"   [{symbol}] {csv_name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("   ALL VALIDATIONS PASSED - Ready for database import")
    else:
        print("   VALIDATION FAILED - Fix issues before database import")

    print("="*60)

    return results


def get_data_summary() -> Dict[str, Any]:
    """
    Get a summary of all CSV data for database import planning.

    Returns:
        Dict with stats useful for import
    """
    summary = {}

    for csv_name in EXPECTED_COLUMNS.keys():
        filepath = os.path.join(DATA_DIR, csv_name)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            summary[csv_name] = {
                'rows': len(df),
                'unique_players': df['player_id'].nunique() if 'player_id' in df.columns else 0,
                'columns': list(df.columns),
                'date_range': {
                    'min': df['fetch_date'].min() if 'fetch_date' in df.columns else None,
                    'max': df['fetch_date'].max() if 'fetch_date' in df.columns else None
                }
            }

    return summary


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    results = validate_all_csvs()

    # Exit with appropriate code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)
