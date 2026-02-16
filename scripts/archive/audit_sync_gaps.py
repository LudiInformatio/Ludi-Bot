#!/usr/bin/env python3
"""
LUDI INFORMATIO | Database Sync Gap Audit
Purpose: Identify missing game dates in player_game_logs table
Author: Senior Developer (Claude Sonnet 4.5)
Date: February 3, 2026
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Configuration
DB_PATH = "ludi.db"
OUTPUT_JSON = "cache/pending_sync_dates.json"
SEASON_START = datetime(2025, 10, 22)  # NBA 2025-26 season start
PARTIAL_SYNC_THRESHOLD = 100  # Records below this = likely incomplete


class SyncGapAuditor:
    """Audits database for missing or incomplete game date syncs"""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.today = datetime.now()
        self.yesterday = self.today - timedelta(days=1)

    def get_database_coverage(self) -> List[Tuple[str, int]]:
        """Query database for all game dates with record counts"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT game_date, COUNT(*) as record_count
                FROM player_game_logs
                GROUP BY game_date
                ORDER BY game_date
            """)

            results = cursor.fetchall()
            conn.close()

            return results

        except sqlite3.Error as e:
            print(f"❌ Database Error: {e}")
            return []

    def generate_expected_dates(self) -> List[str]:
        """Generate all dates from season start to yesterday"""
        expected_dates = []
        current = SEASON_START

        while current <= self.yesterday:
            expected_dates.append(current.strftime('%Y-%m-%d'))
            current += timedelta(days=1)

        return expected_dates

    def identify_gaps(self, db_dates: List[Tuple[str, int]],
                     expected_dates: List[str]) -> Tuple[List[str], List[Dict]]:
        """
        Identify missing dates and partial syncs

        Returns:
            Tuple of (missing_dates, partial_syncs)
        """
        # Convert database results to dict for easy lookup
        db_date_dict = {date: count for date, count in db_dates}
        db_date_set = set(db_date_dict.keys())
        expected_date_set = set(expected_dates)

        # Find completely missing dates
        missing_dates = sorted(expected_date_set - db_date_set)

        # Find partial syncs (dates with suspiciously low record counts)
        partial_syncs = []
        for date, count in db_dates:
            if count < PARTIAL_SYNC_THRESHOLD:
                partial_syncs.append({
                    "date": date,
                    "current_records": count
                })

        return missing_dates, partial_syncs

    def generate_console_report(self, db_dates: List[Tuple[str, int]],
                               missing_dates: List[str],
                               partial_syncs: List[Dict]) -> None:
        """Print human-readable audit report to console"""

        # Calculate stats
        total_records = sum(count for _, count in db_dates)
        first_date = db_dates[0][0] if db_dates else "N/A"
        last_date = db_dates[-1][0] if db_dates else "N/A"
        total_dates_in_db = len(db_dates)

        # Header
        print("\n" + "="*60)
        print("SYNC GAP AUDIT REPORT")
        print(f"Date: {self.today.strftime('%Y-%m-%d %I:%M %p EST')}")
        print("="*60)

        # Database Coverage Section
        print("\nDatabase Coverage:")
        print(f"  First Date: {first_date}")
        print(f"  Last Date: {last_date}")
        print(f"  Total Dates: {total_dates_in_db}")
        print(f"  Total Records: {total_records:,}")

        # Missing Dates Section
        print(f"\nMissing Dates ({len(missing_dates)} dates):")
        if missing_dates:
            # Show first 20, then indicate if there are more
            display_limit = 20
            for date in missing_dates[:display_limit]:
                print(f"  {date} - No data")

            if len(missing_dates) > display_limit:
                print(f"  ... and {len(missing_dates) - display_limit} more dates")
        else:
            print("  ✅ No missing dates found!")

        # Partial Syncs Section
        print(f"\nPartial Syncs (dates with < {PARTIAL_SYNC_THRESHOLD} records):")
        if partial_syncs:
            for item in partial_syncs:
                print(f"  {item['date']} - {item['current_records']} records (likely incomplete)")
        else:
            print("  ✅ No partial syncs detected!")

        # Summary Section
        print("\nSummary:")
        print(f"  Missing: {len(missing_dates)} dates")
        print(f"  Partial: {len(partial_syncs)} dates")
        print(f"  Total to Backfill: {len(missing_dates) + len(partial_syncs)} dates")

        # Recommendation
        print("\nRecommendation:")
        if missing_dates or partial_syncs:
            print("  ⚠️  Backfill required - Missing data detected")
            print(f"  📄 Sync list saved to: {OUTPUT_JSON}")
        else:
            print("  ✅ Database is complete - No backfill needed")

        print("="*60 + "\n")

    def save_json_output(self, missing_dates: List[str],
                        partial_syncs: List[Dict]) -> None:
        """Save machine-readable output for Module H consumption"""

        # Combine missing and partial dates for backfill
        dates_to_sync = sorted(set(missing_dates + [p['date'] for p in partial_syncs]))

        output_data = {
            "generated_at": self.today.isoformat(),
            "audit_summary": {
                "total_missing": len(missing_dates),
                "total_partial": len(partial_syncs),
                "total_to_sync": len(dates_to_sync),
                "date_range": f"{SEASON_START.strftime('%Y-%m-%d')} to {self.yesterday.strftime('%Y-%m-%d')}"
            },
            "dates_to_sync": dates_to_sync,
            "partial_dates": partial_syncs
        }

        # Ensure cache directory exists
        os.makedirs("cache", exist_ok=True)

        # Write JSON file
        try:
            with open(OUTPUT_JSON, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"✅ JSON output saved: {OUTPUT_JSON}\n")
        except Exception as e:
            print(f"❌ Error saving JSON: {e}\n")

    def run_audit(self) -> None:
        """Execute full audit workflow"""
        print("\n🔍 Starting Database Sync Gap Audit...")

        # Step 1: Query database
        print("   📊 Querying database...")
        db_dates = self.get_database_coverage()

        if not db_dates:
            print("❌ No data found in database. Cannot proceed with audit.")
            return

        print(f"   ✅ Found {len(db_dates)} distinct dates in database")

        # Step 2: Generate expected dates
        print("   📅 Generating expected date range...")
        expected_dates = self.generate_expected_dates()
        print(f"   ✅ Expected {len(expected_dates)} dates from season start to yesterday")

        # Step 3: Identify gaps
        print("   🔎 Analyzing gaps...")
        missing_dates, partial_syncs = self.identify_gaps(db_dates, expected_dates)
        print(f"   ✅ Analysis complete")

        # Step 4: Generate report
        self.generate_console_report(db_dates, missing_dates, partial_syncs)

        # Step 5: Save JSON output
        if missing_dates or partial_syncs:
            self.save_json_output(missing_dates, partial_syncs)


def main():
    """Main entry point"""
    auditor = SyncGapAuditor(db_path=DB_PATH)
    auditor.run_audit()


if __name__ == "__main__":
    main()
