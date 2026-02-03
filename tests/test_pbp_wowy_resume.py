"""
Test Suite for PBP WOWY Resume State (Phase 6.5c)

Tests:
1. test_load_resume_state_missing_file - Returns None when file doesn't exist
2. test_load_resume_state_valid - Returns dict when file is valid
3. test_load_resume_state_corrupt - Returns None when file is corrupt
4. test_save_resume_state - Creates valid JSON file
5. test_clear_resume_state - Deletes file when exists
6. test_is_team_completed - Checks team completion correctly

Author: Ludi Informatio
Date: February 3, 2026 (Phase 6.5c)
"""

import json
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.sync_pbp_wowy import (
    _load_resume_state,
    _save_resume_state,
    _clear_resume_state,
    _is_team_completed,
    RESUME_STATE_FILE
)


class TestPbpWowyResume:
    def __init__(self):
        self.test_results = []
        self.cache_dir = "cache"

    def setup(self):
        """Create test environment."""
        os.makedirs(self.cache_dir, exist_ok=True)
        print("Test environment ready\n")

    def cleanup(self):
        """Remove test files."""
        if os.path.exists(RESUME_STATE_FILE):
            os.remove(RESUME_STATE_FILE)
        temp_file = RESUME_STATE_FILE + ".tmp"
        if os.path.exists(temp_file):
            os.remove(temp_file)
        print("Cleaned up test files")

    def test_load_resume_state_missing_file(self):
        """Test 1: Returns None when file doesn't exist."""
        print("TEST 1: Load Resume State - Missing File")
        print("-" * 50)

        self.cleanup()  # Ensure file doesn't exist

        state = _load_resume_state()

        assert state is None, "Should return None when file is missing"

        print("PASS: Returns None for missing file\n")
        self.test_results.append(("Load Resume State - Missing File", True))

    def test_load_resume_state_valid(self):
        """Test 2: Returns dict when file is valid."""
        print("TEST 2: Load Resume State - Valid File")
        print("-" * 50)

        self.cleanup()

        # Create valid state file
        valid_state = {
            "sync_version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_teams": 5,
            "completed_teams": ["LAL", "BOS"],
            "remaining_teams": ["MIA", "CHI", "NYK"],
            "last_completed_team": "BOS",
            "status": "paused",
            "pause_reason": "error: timeout"
        }

        os.makedirs(self.cache_dir, exist_ok=True)
        with open(RESUME_STATE_FILE, 'w') as f:
            json.dump(valid_state, f)

        state = _load_resume_state()

        assert state is not None, "Should return dict for valid file"
        assert state['status'] == 'paused', "Status should be 'paused'"
        assert len(state['completed_teams']) == 2, "Should have 2 completed teams"
        assert len(state['remaining_teams']) == 3, "Should have 3 remaining teams"

        print("PASS: Returns valid dict\n")
        self.test_results.append(("Load Resume State - Valid File", True))

    def test_load_resume_state_corrupt(self):
        """Test 3: Returns None when file is corrupt."""
        print("TEST 3: Load Resume State - Corrupt File")
        print("-" * 50)

        self.cleanup()

        # Create corrupt JSON file
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(RESUME_STATE_FILE, 'w') as f:
            f.write("{invalid json: this won't parse")

        state = _load_resume_state()

        assert state is None, "Should return None for corrupt file"

        print("PASS: Returns None for corrupt file\n")
        self.test_results.append(("Load Resume State - Corrupt File", True))

    def test_save_resume_state(self):
        """Test 4: Creates valid JSON file."""
        print("TEST 4: Save Resume State")
        print("-" * 50)

        self.cleanup()

        completed = ["LAL", "BOS", "MIA"]
        remaining = ["CHI", "NYK"]

        _save_resume_state(completed, remaining, "in_progress")

        assert os.path.exists(RESUME_STATE_FILE), "State file should exist"

        with open(RESUME_STATE_FILE, 'r') as f:
            state = json.load(f)

        assert state['status'] == 'in_progress', "Status should be 'in_progress'"
        assert len(state['completed_teams']) == 3, "Should have 3 completed teams"
        assert len(state['remaining_teams']) == 2, "Should have 2 remaining teams"
        assert state['total_teams'] == 5, "Total teams should be 5"
        assert state['last_completed_team'] == "MIA", "Last completed should be 'MIA'"
        assert 'last_updated' in state, "Should have last_updated timestamp"

        print("PASS: Creates valid JSON file\n")
        self.test_results.append(("Save Resume State", True))

    def test_clear_resume_state(self):
        """Test 5: Deletes file when exists."""
        print("TEST 5: Clear Resume State")
        print("-" * 50)

        # First create a file
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(RESUME_STATE_FILE, 'w') as f:
            json.dump({"test": "data"}, f)

        assert os.path.exists(RESUME_STATE_FILE), "File should exist before clear"

        _clear_resume_state()

        assert not os.path.exists(RESUME_STATE_FILE), "File should not exist after clear"

        # Test clearing when file doesn't exist (should not error)
        _clear_resume_state()  # Should not raise

        print("PASS: Deletes file when exists\n")
        self.test_results.append(("Clear Resume State", True))

    def test_is_team_completed(self):
        """Test 6: Checks team completion correctly."""
        print("TEST 6: Is Team Completed")
        print("-" * 50)

        # Test with None state
        assert _is_team_completed(None, "LAL") is False, "Should return False for None state"

        # Test with empty completed_teams
        state_empty = {"completed_teams": []}
        assert _is_team_completed(state_empty, "LAL") is False, "Should return False for empty list"

        # Test with team in completed list
        state_with_teams = {"completed_teams": ["LAL", "BOS", "MIA"]}
        assert _is_team_completed(state_with_teams, "LAL") is True, "Should return True for LAL"
        assert _is_team_completed(state_with_teams, "BOS") is True, "Should return True for BOS"
        assert _is_team_completed(state_with_teams, "CHI") is False, "Should return False for CHI"

        # Test with missing key
        state_no_key = {"status": "paused"}
        assert _is_team_completed(state_no_key, "LAL") is False, "Should return False for missing key"

        print("PASS: Checks team completion correctly\n")
        self.test_results.append(("Is Team Completed", True))

    def run_all_tests(self):
        """Run all tests and report results."""
        print("=" * 50)
        print("PBP WOWY RESUME STATE TEST SUITE")
        print("=" * 50)
        print()

        self.setup()

        try:
            self.test_load_resume_state_missing_file()
            self.test_load_resume_state_valid()
            self.test_load_resume_state_corrupt()
            self.test_save_resume_state()
            self.test_clear_resume_state()
            self.test_is_team_completed()

        except AssertionError as e:
            print(f"FAIL: Test failed: {e}\n")
            self.test_results.append(("Test Failed", False))
        except Exception as e:
            print(f"ERROR: Unexpected error: {e}\n")
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
            status = "PASS" if result else "FAIL"
            print(f"{status} - {test_name}")

        print(f"\nResult: {passed}/{total} tests passed")

        if passed == total:
            print("All tests passed!")
            return True
        else:
            print("Some tests failed")
            return False


if __name__ == "__main__":
    tester = TestPbpWowyResume()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
