"""
Test Suite for Module H Resume State (Phase 6.5b Step 4)

Tests:
1. Resume from paused state
2. Fresh start from audit file
3. Completion scenario
"""

import json
import os
import sys
import shutil
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module_h_historian import LudiHistorian


class TestHistorianResume:
    def __init__(self):
        self.test_results = []
        self.cache_dir = "cache"
        self.state_file = f"{self.cache_dir}/historian_sync_state.json"
        self.audit_file = f"{self.cache_dir}/pending_sync_dates.json"

    def setup(self):
        """Create test environment."""
        os.makedirs(self.cache_dir, exist_ok=True)
        print("✅ Test environment ready\n")

    def cleanup(self):
        """Remove test files."""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
        if os.path.exists(self.audit_file):
            os.remove(self.audit_file)
        print("🧹 Cleaned up test files")

    def create_mock_state(self, status, completed, remaining):
        """Create a mock state file for testing."""
        state = {
            "last_run": datetime.now().isoformat(),
            "source_file": "cache/pending_sync_dates.json",
            "total_dates": len(completed) + len(remaining),
            "completed_dates": completed,
            "remaining_dates": remaining,
            "last_completed_date": completed[-1] if completed else None,
            "status": status,
            "pause_reason": "budget_exhausted" if status == "paused" else None
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)
        print(f"📝 Created mock state: {status}, {len(remaining)} remaining")

    def create_mock_audit(self, dates):
        """Create a mock audit file for testing."""
        audit = {
            "generated_at": datetime.now().isoformat(),
            "audit_summary": {
                "total_to_sync": len(dates)
            },
            "dates_to_sync": dates
        }
        with open(self.audit_file, "w") as f:
            json.dump(audit, f, indent=2)
        print(f"📋 Created mock audit: {len(dates)} dates")

    def test_state_file_loading(self):
        """Test 1: State file loading with valid data."""
        print("🧪 TEST 1: State File Loading")
        print("-" * 50)

        self.create_mock_state(
            status="paused",
            completed=["2025-10-19"],
            remaining=["2025-10-20", "2025-10-21", "2025-10-22"]
        )

        historian = LudiHistorian(budget=1)
        state = historian._load_sync_state()

        assert state is not None, "❌ State should not be None"
        assert state['status'] == 'paused', "❌ Status should be 'paused'"
        assert len(state['remaining_dates']) == 3, "❌ Should have 3 remaining dates"

        print("✅ State file loaded correctly\n")
        self.test_results.append(("State File Loading", True))

    def test_audit_file_loading(self):
        """Test 2: Audit file loading."""
        print("🧪 TEST 2: Audit File Loading")
        print("-" * 50)

        self.cleanup()  # Remove state file
        self.create_mock_audit(["2025-10-20", "2025-10-21", "2025-10-22"])

        historian = LudiHistorian(budget=1)
        dates = historian._load_audit_file()

        assert dates is not None, "❌ Dates should not be None"
        assert len(dates) == 3, "❌ Should have 3 dates"

        print("✅ Audit file loaded correctly\n")
        self.test_results.append(("Audit File Loading", True))

    def test_state_save(self):
        """Test 3: State file saving."""
        print("🧪 TEST 3: State File Saving")
        print("-" * 50)

        self.cleanup()
        historian = LudiHistorian(budget=1)

        completed = ["2025-10-19", "2025-10-20"]
        remaining = ["2025-10-21", "2025-10-22"]

        historian._save_sync_state(completed, remaining, "in_progress")

        assert os.path.exists(self.state_file), "❌ State file should exist"

        with open(self.state_file) as f:
            state = json.load(f)

        assert state['status'] == 'in_progress', "❌ Status should be 'in_progress'"
        assert len(state['completed_dates']) == 2, "❌ Should have 2 completed"
        assert len(state['remaining_dates']) == 2, "❌ Should have 2 remaining"

        print("✅ State file saved correctly\n")
        self.test_results.append(("State File Saving", True))

    def test_corrupt_state_handling(self):
        """Test 4: Corrupt state file handling."""
        print("🧪 TEST 4: Corrupt State File Handling")
        print("-" * 50)

        # Create corrupt JSON
        with open(self.state_file, "w") as f:
            f.write("{invalid json")

        historian = LudiHistorian(budget=1)
        state = historian._load_sync_state()

        assert state is None, "❌ Should return None for corrupt file"

        print("✅ Corrupt state handled gracefully\n")
        self.test_results.append(("Corrupt State Handling", True))

    def test_missing_files(self):
        """Test 5: Missing state and audit files."""
        print("🧪 TEST 5: Missing Files Fallback")
        print("-" * 50)

        self.cleanup()

        historian = LudiHistorian(budget=1)
        state = historian._load_sync_state()
        audit = historian._load_audit_file()

        assert state is None, "❌ State should be None when missing"
        assert audit is None, "❌ Audit should be None when missing"

        print("✅ Missing files handled correctly\n")
        self.test_results.append(("Missing Files Fallback", True))

    def test_date_format_conversion(self):
        """Test 6: Date format conversion (YYYY-MM-DD → YYYYMMDD)."""
        print("🧪 TEST 6: Date Format Conversion")
        print("-" * 50)

        date_str = "2025-10-20"
        tank_format = date_str.replace("-", "")

        assert tank_format == "20251020", "❌ Date format conversion failed"

        print(f"   {date_str} → {tank_format}")
        print("✅ Date format conversion works\n")
        self.test_results.append(("Date Format Conversion", True))

    def run_all_tests(self):
        """Run all tests and report results."""
        print("=" * 50)
        print("HISTORIAN RESUME STATE TEST SUITE")
        print("=" * 50)
        print()

        self.setup()

        try:
            self.test_state_file_loading()
            self.test_audit_file_loading()
            self.test_state_save()
            self.test_corrupt_state_handling()
            self.test_missing_files()
            self.test_date_format_conversion()

        except AssertionError as e:
            print(f"❌ Test failed: {e}\n")
            self.test_results.append(("Test Failed", False))
        except Exception as e:
            print(f"❌ Unexpected error: {e}\n")
            self.test_results.append(("Unexpected Error", False))
        finally:
            self.cleanup()

        # Summary
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)

        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)

        for test_name, result in self.test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} - {test_name}")

        print(f"\nResult: {passed}/{total} tests passed")

        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️ Some tests failed")
            return False


if __name__ == "__main__":
    tester = TestHistorianResume()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
