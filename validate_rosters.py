#!/usr/bin/env python
"""
validate_rosters.py - NBA Roster Validation Script
Checks Tank01 API for roster changes and updates database.

Purpose:
    - Detects trades, signings, waivers since last database update
    - Syncs database with current NBA rosters
    - Generates validation reports in logs/rosters/

Usage:
    # Preview changes without applying:
    ./venv/bin/python validate_rosters.py --dry-run

    # Apply roster updates to database:
    ./venv/bin/python validate_rosters.py

    # Quiet mode (minimal output):
    ./venv/bin/python validate_rosters.py --quiet

Cost:
    - 31 Tank01 API requests per run
    - 3.1% of daily quota (1,000 requests/day)
    - Estimated cost: $0.0103 per validation

Author: Ludi Informatio v2.0
Date: January 8, 2026
"""

import argparse
import sys
from utils.roster_validator import get_roster_validator


def main():
    """
    Main entry point for roster validation script.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Validate NBA rosters against Tank01 API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes:
  python validate_rosters.py --dry-run

  # Apply updates:
  python validate_rosters.py

  # Quiet mode:
  python validate_rosters.py --quiet
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying to database'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output (errors only)'
    )

    args = parser.parse_args()

    try:
        # Initialize validator
        if not args.quiet:
            print("\n" + "="*60)
            print("   LUDI INFORMATIO: ROSTER VALIDATION")
            print("="*60)

        validator = get_roster_validator()

        # Run validation
        results = validator.validate_and_update(dry_run=args.dry_run)

        # Display report (unless quiet mode)
        if not args.quiet:
            print(results['report'])
            print(f"\n📄 Full report saved: {results['report_file']}")

        # Exit codes:
        # 0 = Success, changes detected and applied (or previewed)
        # 1 = Error occurred
        # 2 = No changes detected
        total_changes = (
            len(results['changes']['trades']) +
            len(results['changes']['signings']) +
            len(results['changes']['waivers'])
        )

        if total_changes > 0:
            sys.exit(0)
        else:
            if not args.quiet:
                print("\n   ℹ️  No roster changes detected.")
            sys.exit(0)  # Changed from 2 to 0 - no changes is still success

    except KeyboardInterrupt:
        print("\n\n   ⚠️  Validation interrupted by user.")
        sys.exit(1)

    except Exception as e:
        print(f"\n   ❌ ERROR: {type(e).__name__}: {str(e)}")
        if not args.quiet:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
